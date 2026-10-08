#!/usr/bin/env python3
"""Benchmark ctx-harness: the same coding tasks on the shopd demo repo, harness on and off.

Every run gets a freshly materialized repo. Harness runs also get a .ctx/ that
was built once at the start (its cost is recorded as the 'bootstrap' row).
After the agent finishes, the task's hidden tests are copied in and the checks
run, so a run only counts as passed if the change is correct, not just cheap.

  python3 bench/run.py --agent fake                         # offline smoke run, synthetic numbers
  python3 bench/run.py --agent claude --repeats 3           # real run; uses your Claude Code login
  python3 bench/run.py --agent claude --tasks t2,t4 --repeats 1 --model <id>

Results go to bench/results/<run>/: results.jsonl (one row per run), run.json,
the .ctx snapshot used, transcripts copied for fake agents, and report.md.
"""
import argparse
import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH / "demo"))

import report  # noqa: E402
from agents import CTXH, clean_env, make_agent  # noqa: E402
from materialize import materialize  # noqa: E402

TASKS_DIR = BENCH / "tasks"
REGRESSION = ["go", "test", "-count=1", "./..."]  # every run must also leave the whole suite green
MODES = ("harness", "baseline")


@dataclass
class Task:
    id: str
    category: str
    prompt: str
    check: list
    hidden: dict
    max_turns: int
    dir: Path

    @property
    def solution(self) -> Path:
        return self.dir / "solution"


def load_tasks(selected=None):
    tasks = []
    for spec in sorted(TASKS_DIR.glob("*/task.json")):
        d = json.loads(spec.read_text())
        tasks.append(Task(d["id"], d["category"], d["prompt"], d["check"], d.get("hidden", {}),
                          d.get("max_turns", 40), spec.parent))
    if selected:
        want = [s.strip() for s in selected.split(",") if s.strip()]
        picked = [t for t in tasks if any(t.id == w or t.id.startswith(w + "-") for w in want)]
        missing = [w for w in want if not any(t.id == w or t.id.startswith(w + "-") for t in tasks)]
        if missing:
            raise SystemExit(f"unknown task(s): {', '.join(missing)}; have {', '.join(t.id for t in tasks)}")
        tasks = picked
    return tasks


def run_check(repo: Path, task: Task):
    """Copy the hidden tests in and run the task's checks plus the regression suite."""
    for src, dst in task.hidden.items():
        (repo / dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(task.dir / src, repo / dst)
    for cmd in [*task.check, REGRESSION]:
        try:
            r = subprocess.run(cmd, cwd=repo, env=clean_env(), text=True, capture_output=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, f"{' '.join(cmd)}: {e}"
        if r.returncode != 0:
            tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-8:])
            return False, f"{' '.join(cmd)} (exit {r.returncode})\n{tail}"
    return True, ""


def load_engine():
    """Import the ctxh script as a module to reuse its transcript parser."""
    loader = importlib.machinery.SourceFileLoader("ctxh_engine", str(CTXH))
    spec = importlib.util.spec_from_loader("ctxh_engine", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def usage_fields(engine, transcript):
    data = engine.parse_transcript(transcript) if transcript else None
    if not data:
        return {"tokens_total": None, "tokens_uncached": None, "steps": None, "files_read": None,
                "subagents": {}, "transcript_ok": False}
    return {"tokens_total": data["tokens_total"], "tokens_uncached": data["tokens_uncached"],
            "steps": data["steps"], "files_read": len(data["files_read"]), "ctx_queries": len(data["ctx_queries"]),
            "subagents": data["subagents"], "transcript_ok": data["tokens_total"] > 0}


def keep_transcript(res, dest: Path):
    """Copy a transcript (and its subagent transcripts) into the run directory."""
    src = res.transcript
    if not src or not src.exists() or src.resolve() == dest.resolve():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    subs = src.with_suffix("") / "subagents"
    if subs.is_dir():
        shutil.copytree(subs, dest.with_suffix("") / "subagents", dirs_exist_ok=True)
    res.transcript = dest


def add_harness_context(repo: Path, snapshot: Path):
    shutil.copytree(snapshot, repo / ".ctx")
    subprocess.run(["git", "add", ".ctx"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "user.name=bench", "-c", "user.email=bench@example.com",
                    "commit", "-q", "-m", "add harness context"], cwd=repo, check=True, capture_output=True)


def snapshot_ctx(repo: Path, dest: Path):
    shutil.copytree(repo / ".ctx", dest, ignore=shutil.ignore_patterns("tmp", "traces", "metrics"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", default="fake", help="claude | fake | noop (default: fake)")
    ap.add_argument("--tasks", help="comma-separated task ids or prefixes such as t2,t4 (default: all)")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--modes", default=",".join(MODES), help="harness,baseline (default: both)")
    ap.add_argument("--model", help="model passed to claude --model")
    ap.add_argument("--gates", action="store_true", help="turn the opt-in plan and review gates on for harness runs")
    ap.add_argument("--max-turns", action="store_true", help="pass each task's max_turns to claude --max-turns")
    ap.add_argument("--timeout", type=int, default=3600, help="seconds before a claude run is killed")
    ap.add_argument("--ctx-from", help="reuse a .ctx snapshot (e.g. bench/results/<run>/ctx) instead of bootstrapping")
    ap.add_argument("--out", default=str(BENCH / "results"))
    ap.add_argument("--keep", action="store_true", help="keep the per-run repos for inspection")
    args = ap.parse_args(argv)

    modes = [m for m in args.modes.split(",") if m]
    if not set(modes) <= set(MODES):
        raise SystemExit(f"--modes must be a subset of {','.join(MODES)}")
    if not shutil.which("go"):
        raise SystemExit("go is required to run the demo repo's checks")
    tasks = load_tasks(args.tasks)
    agent = make_agent(args.agent, model=args.model, gates=args.gates,
                       max_turns=args.max_turns, timeout=args.timeout)
    engine = load_engine()

    run_id = time.strftime("%Y%m%d-%H%M%S") + f"-{agent.name}"
    run_dir, n = Path(args.out) / run_id, 1
    while run_dir.exists():
        n += 1
        run_dir = Path(args.out) / f"{run_id}-{n}"
    run_id = run_dir.name
    run_dir.mkdir(parents=True)
    work = Path(tempfile.mkdtemp(prefix="ctxh-bench-"))
    scratch = run_dir / "transcripts"
    meta = {"run": run_id, "agent": agent.name, "model": args.model, "repeats": args.repeats, "modes": modes,
            "tasks": [t.id for t in tasks], "gates": args.gates,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "synthetic": agent.name != "claude"}
    (run_dir / "run.json").write_text(json.dumps(meta, indent=1))
    results = run_dir / "results.jsonl"

    def record(row):
        with results.open("a") as f:
            f.write(json.dumps(row) + "\n")
        status = "pass" if row["passed"] else "FAIL"
        print(f"  {row['task']:<28} {row['mode']:<9} r{row['repeat']}  {status:<4}  "
              f"{row.get('tokens_total') or '-':>9} tokens  {row['seconds']:.0f}s"
              + (f"  ({row['error']})" if row.get("error") else ""), flush=True)

    print(f"benchmark {run_id}: {len(tasks)} tasks x {len(modes)} modes x {args.repeats} repeats -> {run_dir}")
    snapshot = None
    if "harness" in modes:
        if args.ctx_from:
            snapshot = Path(args.ctx_from).resolve()
            meta["ctx_from"] = str(snapshot)
        else:
            repo = materialize(work / "bootstrap")
            res = agent.bootstrap(repo, scratch)
            keep_transcript(res, scratch / "bootstrap.jsonl")
            ok = (repo / ".ctx" / "map.md").exists()
            chk = subprocess.run([sys.executable, str(CTXH), "check"], cwd=repo, env=clean_env(),
                                 text=True, capture_output=True)
            record({"run": run_id, "task": "bootstrap", "category": "overhead", "mode": "bootstrap", "repeat": 0,
                    "passed": ok, "check": chk.stdout.strip()[-500:], "seconds": round(res.seconds, 1),
                    "error": res.error, "cost_usd": res.cost_usd, "num_turns": res.num_turns,
                    **usage_fields(engine, res.transcript)})
            if not ok:
                raise SystemExit(f"bootstrap produced no .ctx/map.md; see {results}")
            snapshot = run_dir / "ctx"
            snapshot_ctx(repo, snapshot)
            shutil.rmtree(repo, ignore_errors=True)

    for repeat in range(args.repeats):
        for i, task in enumerate(tasks):
            order = modes if (repeat + i) % 2 == 0 else modes[::-1]  # alternate who goes first
            for mode in order:
                repo = materialize(work / f"{task.id}-{mode}-{repeat}")
                if mode == "harness":
                    add_harness_context(repo, snapshot)
                res = agent.run(repo, task, mode, repeat, scratch)
                keep_transcript(res, scratch / f"{task.id}-{mode}-{repeat}.jsonl")
                passed, why = run_check(repo, task)
                record({"run": run_id, "task": task.id, "category": task.category, "mode": mode,
                        "repeat": repeat, "passed": passed, "check": why[-800:], "seconds": round(res.seconds, 1),
                        "error": res.error, "cost_usd": res.cost_usd, "num_turns": res.num_turns,
                        "transcript": str(res.transcript) if res.transcript else None,
                        **usage_fields(engine, res.transcript)})
                if not args.keep:
                    shutil.rmtree(repo, ignore_errors=True)
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (run_dir / "run.json").write_text(json.dumps(meta, indent=1))
    text = report.write(run_dir)
    print("\n" + text)
    return run_dir


if __name__ == "__main__":
    main()
