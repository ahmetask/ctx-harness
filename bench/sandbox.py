#!/usr/bin/env python3
"""A demo repo wired to this checkout's plugin, for verifying a task end to end.

The unit tests use tiny throwaway repos. This gives you the shopd demo (43 Go
files, scripted history) with the committed demo context (bench/demo/ctx) as its
`.ctx/`, indexed by the working-tree `ctxh`, so a change can be tried on
something realistic before it is called done.

  python3 bench/sandbox.py                       # build (or refresh) the sandbox and run the smoke checks
  python3 bench/sandbox.py --fresh               # rebuild it from scratch
  python3 bench/sandbox.py --prompt "<task>"     # also run one real `claude -p` session in it
  python3 bench/sandbox.py --prompt "<task>" --baseline   # the same session with the harness off

The smoke checks drive the hooks and queries the way Claude Code would and exit
non-zero if any fails. For an interactive session, run the command it prints.
Needs git, Python 3.10+ and Go; --prompt also needs the `claude` CLI.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH / "demo"))

from agents import CTXH, PLUGIN_DIR, ClaudeAgent, clean_env, write_transcript  # noqa: E402
from materialize import materialize  # noqa: E402
from run import add_harness_context, load_engine, usage_fields  # noqa: E402

DEFAULT_DIR = Path(tempfile.gettempdir()) / "ctxh-sandbox"
DEMO_CTX = BENCH / "demo" / "ctx"  # what /ctx-harness:build produced for the demo, committed
MARKER = ".git/ctxh-sandbox"  # only directories carrying it are ever deleted


def ctxh(repo: Path, *args, payload=None, **env):
    """Run the working-tree engine; hooks get their JSON payload on stdin, as Claude Code sends it."""
    return subprocess.run([sys.executable, str(CTXH), *args], cwd=repo, input=json.dumps(payload or {}), text=True,
                          capture_output=True, env=clean_env(**env), timeout=900)


def setup(repo: Path, fresh: bool) -> Path:
    if repo.exists() and fresh:
        if not (repo / MARKER).exists():
            sys.exit(f"{repo} exists and is not a sandbox; pick another directory")
        shutil.rmtree(repo)
    if not repo.exists():
        materialize(repo)
        (repo / MARKER).write_text("made by bench/sandbox.py\n")
        add_harness_context(repo, DEMO_CTX)  # committed, as a team that opted in would have it
        ctxh(repo, "build-index")
    elif not (repo / MARKER).exists():
        sys.exit(f"{repo} exists and is not a sandbox; pick another directory")
    else:
        ctxh(repo, "build-index")  # pick up engine changes made since the last run
    return repo


def smoke(repo: Path) -> bool:
    """Each check mirrors something Claude Code does with the plugin."""
    scratch = Path(tempfile.mkdtemp(prefix="ctxh-sandbox-"))
    edit = write_transcript(scratch / "edit.jsonl", [("Edit", {"file_path": str(repo / "internal/orders/service.go")})])
    default_stop = ctxh(repo, "hook-stop", payload={"session_id": "sandbox-smoke", "transcript_path": str(edit)})
    gate = ctxh(repo, "hook-stop", payload={"session_id": "sandbox-smoke-gate", "transcript_path": str(edit)},
                CTXH_REVIEW_GATE="1")
    for leftover in (".ctx/tmp/gates", ".ctx/metrics", ".ctx/traces"):  # keep the fake session out of stats
        for f in (repo / leftover).glob("sandbox-smoke*"):
            f.unlink()
    shutil.rmtree(scratch)

    checks = [
        ("SessionStart injects the protocol", "Working protocol" in ctxh(repo, "hook-start").stdout),
        ("UserPromptSubmit adds nothing by default", ctxh(repo, "hook-prompt").stdout == ""),
        ("UserPromptSubmit names the reviewer once its gate is on",
         "ctx-harness:reviewer" in ctxh(repo, "hook-prompt", CTXH_REVIEW_GATE="1").stdout),
        ("CTXH_DISABLED=1 injects nothing", ctxh(repo, "hook-start", CTXH_DISABLED="1").stdout == ""),
        ("q find answers from the index", "internal/payments/idempotency.go" in ctxh(repo, "q", "find", "IdempotencyKey").stdout),
        ("q cochange finds the planted pair",
         "internal/notify/templates.go" in ctxh(repo, "q", "cochange", "internal/orders/state.go").stdout),
        ("ctxh check passes", ctxh(repo, "check").returncode == 0),
        ("Stop does not block by default", '"block"' not in default_stop.stdout),
        ("Stop blocks an unreviewed edit once the review gate is on", '"block"' in gate.stdout),
    ]
    for name, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
    return all(ok for _, ok in checks)


def session(repo: Path, prompt: str, model: str | None, baseline: bool, timeout: int) -> bool:
    mode = "baseline" if baseline else "harness"
    print(f"\nrunning one {mode} session (claude -p) ...")
    res = ClaudeAgent(model=model, timeout=timeout)._invoke(repo, prompt, mode, "sandbox", None, None)
    usage = usage_fields(load_engine(), res.transcript)
    changed = subprocess.run(["git", "status", "--short"], cwd=repo, text=True, capture_output=True).stdout
    print(f"  error:      {res.error or 'none'}")
    print(f"  transcript: {res.transcript}")
    print(f"  turns: {res.num_turns}  cost: ${res.cost_usd}  tokens: {usage['tokens_total']}  steps: {usage['steps']}")
    print("  changed files:\n" + ("".join(f"    {line}\n" for line in changed.splitlines()) or "    none\n"), end="")
    return not res.error


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", nargs="?", type=Path, default=DEFAULT_DIR, help=f"sandbox location (default {DEFAULT_DIR})")
    ap.add_argument("--fresh", action="store_true", help="delete and rebuild the sandbox")
    ap.add_argument("--prompt", help="run one real Claude Code session with this prompt")
    ap.add_argument("--baseline", action="store_true", help="with --prompt: harness off (CTXH_DISABLED=1)")
    ap.add_argument("--model", help="with --prompt: model id")
    ap.add_argument("--timeout", type=int, default=1800, help="with --prompt: seconds before the session is killed")
    args = ap.parse_args(argv)

    repo = setup(args.dir.resolve(), args.fresh)
    print(f"sandbox: {repo}\nsmoke checks:")
    ok = smoke(repo)
    if args.prompt:
        ok = session(repo, args.prompt, args.model, args.baseline, args.timeout) and ok
    print(f"\ninteractive: cd {repo} && claude --plugin-dir {PLUGIN_DIR}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
