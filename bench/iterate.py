#!/usr/bin/env python3
"""Benchmark iterative work: a chain of dependent tasks, each in a new session on the previous one's result.

A normal run gives every task a fresh repo. Here one repo per (repeat, mode) lives through the whole
chain: session 1 starts on the pristine project, session 2 on what session 1 left, and so on. Each task's
prompt builds on the one before it, and each session is a separate `claude -p` with no shared conversation.

  baseline: the plugin is off and the repo has no .ctx/ at all. The only thing that carries from one session
            to the next is the code the previous sessions committed.
  harness:  the plugin is on, with the repo's map and cards from the start. What the previous sessions
            left in .ctx/ (the agent's own notes, traces) and the index refreshed over their commits carry
            on too; the session-start hook names the previous session's request, edited files and failures.

  python3 bench/iterate.py --suite hugo-iterate --agent fake                  # offline smoke run
  python3 bench/iterate.py --suite hugo-iterate --agent claude --repeats 4 --ctx-from <ctx dir>

After each session the task's checks run (its hidden test plus the hidden tests of the earlier tasks), the hidden
files are removed again, and the code is committed. A failed task does not stop the chain: the next session
starts on whatever was left, as a developer's would. Results go to bench/results/<run>/.
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH / "demo"))

import run as runner  # noqa: E402
from agents import CTXH, clean_env, make_agent  # noqa: E402
from suite import GIT_ID, load_suite  # noqa: E402

MODES = ("baseline", "harness")


def check_step(repo: Path, tasks, i):
    """Task i's checks, with the hidden tests of tasks 0..i in place; the hidden files are removed afterwards."""
    placed = []
    try:
        for t in tasks[: i + 1]:
            for src, dst in t.hidden.items():
                (repo / dst).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(t.dir / src, repo / dst)
                placed.append(repo / dst)
        for cmd in [*tasks[i].check, tasks[i].regression or runner.REGRESSION]:
            try:
                r = subprocess.run(cmd, cwd=repo, env=clean_env(), text=True, capture_output=True, timeout=600)
            except (OSError, subprocess.TimeoutExpired) as e:
                return False, f"{' '.join(cmd)}: {e}"
            if r.returncode != 0:
                tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-8:])
                return False, f"{' '.join(cmd)} (exit {r.returncode})\n{tail}"
        return True, ""
    finally:
        for p in placed:
            p.unlink(missing_ok=True)


def commit_code(repo: Path, message: str):
    """Commit what the session left, except .ctx/ (the harness keeps its own state there)."""
    subprocess.run(["git", "add", "-A", "--", ".", ":!.ctx"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", *GIT_ID, "commit", "-q", "--allow-empty", "-m", message], cwd=repo, check=True,
                   capture_output=True)


def summarize(rows):
    """{(mode, step): {...}} and per-mode totals from the result rows."""
    out = {}
    for r in rows:
        out.setdefault((r["mode"], r["step"]), []).append(r)

    def agg(rs):
        med = lambda key: statistics.median([r[key] for r in rs if r.get(key) is not None] or [0])
        return {"n": len(rs), "pass": sum(1 for r in rs if r["passed"]),
                "tokens": med("tokens_total"), "uncached": med("tokens_uncached"), "steps": med("steps"),
                "reads": med("files_read"), "seconds": med("seconds"),
                "cost": sum(r.get("cost_usd") or 0 for r in rs), "tokens_sum": sum(r.get("tokens_total") or 0 for r in rs)}
    return {k: agg(v) for k, v in out.items()}, {m: agg([r for r in rows if r["mode"] == m]) for m in {r["mode"] for r in rows}}


def write_report(run_dir: Path):
    rows = [json.loads(x) for x in (run_dir / "results.jsonl").read_text().splitlines() if x.strip()]
    meta = json.loads((run_dir / "run.json").read_text())
    per, total = summarize(rows)
    modes = [m for m in meta["modes"] if m in total]
    tasks = meta["tasks"]
    k = lambda n: f"{n / 1000:.1f}k" if abs(n) >= 1000 else f"{n:.0f}"
    lines = [f"# Iterative benchmark {meta['run']}", "",
             f"Suite `{meta['suite']}`, {meta['repeats']} repeats, chain: {' -> '.join(tasks)}. Medians per step.", "",
             "| arm | passes | total tokens | median steps/session | median files read | cost |", "|---|---|---|---|---|---|"]
    for m in modes:
        t = total[m]
        lines.append(f"| {m} | {t['pass']}/{t['n']} | {k(t['tokens_sum'])} | {t['steps']:.0f} | {t['reads']:.0f} | ${t['cost']:.2f} |")
    if len(modes) == 2:
        a, b = (total[m] for m in modes)
        if a["tokens_sum"]:
            lines += ["", f"{modes[1]} vs {modes[0]}: tokens {100 * (b['tokens_sum'] / a['tokens_sum'] - 1):+.0f}%"
                      + (f", cost {100 * (b['cost'] / a['cost'] - 1):+.0f}%" if a["cost"] else "")]
    lines += ["", "## By step (median tokens, steps, files read; passes)", "",
              "| step | " + " | ".join(modes) + (" | change |" if len(modes) == 2 else " |"),
              "|---|" + "---|" * (len(modes) + (1 if len(modes) == 2 else 0))]
    for i, t in enumerate(tasks):
        cells, vals = [], []
        for m in modes:
            s = per.get((m, i))
            if not s:
                cells.append("-"), vals.append(None)
                continue
            cells.append(f"{k(s['tokens'])}, {s['steps']:.0f} steps, {s['reads']:.0f} reads; {s['pass']}/{s['n']}")
            vals.append(s["tokens"])
        change = ""
        if len(modes) == 2 and all(vals) and vals[0]:
            change = f" | {100 * (vals[1] / vals[0] - 1):+.0f}%"
        lines.append(f"| {i + 1} {t} | " + " | ".join(cells) + change + " |")
    fails = [r for r in rows if not r["passed"]]
    if fails:
        lines += ["", "## Failed sessions", ""]
        lines += [f"- {r['mode']} r{r['repeat']} step {r['step'] + 1} {r['task']}: "
                  f"{(r.get('error') or r.get('check') or '').splitlines()[0][:160]}" for r in fails]
    text = "\n".join(lines) + "\n"
    (run_dir / "report.md").write_text(text)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", default="fake")
    ap.add_argument("--suite", default="hugo-iterate")
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--start-repeat", type=int, default=0, help="number the repeats from here (to continue an earlier run)")
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--ctx-from", required=True, help="a .ctx snapshot (map, cards, ...) the harness arm starts with")
    ap.add_argument("--out", default=str(BENCH / "results"))
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args(argv)

    modes = [m for m in args.modes.split(",") if m]
    if not set(modes) <= set(MODES):
        raise SystemExit(f"--modes must be a subset of {','.join(MODES)}")
    suite = load_suite(args.suite)
    for key, value in (suite.env or {}).items():
        os.environ.setdefault(key, value)
    os.environ.setdefault("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "1")  # nothing but the repo carries between sessions
    tasks = runner.load_tasks(None, suite)
    agent = make_agent(args.agent, model=args.model, gates=False, max_turns=False, timeout=args.timeout, graphify_bin=None)
    snapshot = Path(args.ctx_from).resolve()

    run_id = time.strftime("%Y%m%d-%H%M%S") + f"-iterate-{agent.name}"
    run_dir = Path(args.out) / run_id
    run_dir.mkdir(parents=True)
    work = Path(tempfile.mkdtemp(prefix="ctxh-iter-"))
    scratch = run_dir / "transcripts"
    meta = {"run": run_id, "suite": suite.name, "agent": agent.name, "model": args.model, "repeats": args.repeats,
            "modes": modes, "tasks": [t.id for t in tasks], "ctx_from": str(snapshot),
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "synthetic": agent.name != "claude"}
    (run_dir / "run.json").write_text(json.dumps(meta, indent=1))
    results = run_dir / "results.jsonl"
    engine = runner.load_engine()
    print(f"iterative benchmark {run_id}: {len(tasks)} chained tasks x {len(modes)} modes x {args.repeats} repeats -> {run_dir}")

    for repeat in range(args.start_repeat, args.start_repeat + args.repeats):
        order = modes if repeat % 2 == 0 else modes[::-1]
        for mode in order:
            repo = suite.materialize(work / f"{mode}-{repeat}")
            if mode == "harness":
                runner.add_harness_context(repo, snapshot)
            for i, task in enumerate(tasks):
                res = agent.run(repo, task, mode, repeat, scratch)
                runner.keep_transcript(res, scratch / f"{i + 1}-{task.id}-{mode}-{repeat}.jsonl")
                passed, why = check_step(repo, tasks, i)
                commit_code(repo, f"bench: after {task.id}")
                if mode == "harness":  # the index follows the new commit; deterministic, no model
                    subprocess.run([sys.executable, str(CTXH), "build-index", "--quiet"], cwd=repo, env=clean_env(),
                                   capture_output=True)
                row = {"run": run_id, "task": task.id, "step": i, "category": "iterative", "mode": mode, "repeat": repeat,
                       "passed": passed, "check": why[-800:], "seconds": round(res.seconds, 1), "error": res.error,
                       "cost_usd": res.cost_usd, "num_turns": res.num_turns,
                       "transcript": str(res.transcript) if res.transcript else None,
                       **runner.usage_fields(engine, res.transcript)}
                with results.open("a") as f:
                    f.write(json.dumps(row) + "\n")
                print(f"  r{repeat} {mode:<8} step {i + 1} {task.id:<14} {'pass' if passed else 'FAIL':<4} "
                      f"{row.get('tokens_total') or '-':>9} tokens  {row['steps'] or '-'} steps  {res.seconds:.0f}s"
                      + (f"  ({res.error})" if res.error else ""), flush=True)
            if args.keep and mode == "harness":
                shutil.copytree(repo / ".ctx", run_dir / f"ctx-after-r{repeat}", ignore=shutil.ignore_patterns("graph.json"),
                                dirs_exist_ok=True)
            shutil.rmtree(repo, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (run_dir / "run.json").write_text(json.dumps(meta, indent=1))
    print("\n" + write_report(run_dir))
    return run_dir


if __name__ == "__main__":
    main()
