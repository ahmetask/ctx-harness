"""Benchmark suites: the repo the tasks run on, and where its tasks live.

`demo` is the built-in shopd repo (bench/demo, 43 files, tasks in bench/tasks).
Any other suite is a folder bench/suites/<name>/ with a suite.json:

  {"repo": "bench/repos/hugo",                  # a git submodule pinned to one commit
   "regression": ["go", "build", "./..."],      # default regression check
   "env": {"GOTOOLCHAIN": "auto"}}              # environment defaults for the run

and tasks in bench/suites/<name>/tasks/<id>/. A task may carry a `setup.patch`: it is applied and
committed in every fresh repo before the agent starts, which is how a bug gets planted in a real
project. Each run clones the submodule, so the pinned commit is the same on every machine.
"""
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
GIT_ID = ["-c", "commit.gpgsign=false", "-c", "user.name=bench", "-c", "user.email=bench@example.com"]


@dataclass
class Suite:
    name: str
    tasks_dir: Path
    repo: Path | None = None
    regression: list | None = None
    env: dict | None = None  # defaults for the environment of every run, e.g. GOTOOLCHAIN

    def materialize(self, dest: Path, task=None) -> Path:
        """A fresh repo for one run. With a task, its setup patch is applied and committed."""
        if self.repo is None:
            from materialize import materialize  # bench/demo, on sys.path via run.py
            return materialize(dest)
        if not (self.repo / ".git").exists():
            raise SystemExit(f"suite '{self.name}' needs its repo: git submodule update --init "
                             f"{self.repo.relative_to(ROOT)}")
        dest = Path(dest)
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(self.repo), str(dest)], check=True,
                       capture_output=True)
        subprocess.run(["git", "remote", "remove", "origin"], cwd=dest, check=True, capture_output=True)
        patch = task.dir / "setup.patch" if task is not None else None
        if patch is not None and patch.exists():
            subprocess.run(["git", "apply", str(patch)], cwd=dest, check=True, capture_output=True)
            subprocess.run(["git", *GIT_ID, "commit", "-q", "-am", "bench: task setup"], cwd=dest, check=True,
                           capture_output=True)
        return dest


def load_suite(name: str) -> Suite:
    if name == "demo":
        return Suite("demo", BENCH / "tasks")
    base = BENCH / "suites" / name
    spec = base / "suite.json"
    if not spec.exists():
        known = ["demo", *sorted(p.parent.name for p in (BENCH / "suites").glob("*/suite.json"))]
        raise SystemExit(f"unknown suite '{name}'; have {', '.join(known)}")
    d = json.loads(spec.read_text())
    return Suite(name, base / "tasks", ROOT / d["repo"], d.get("regression"), d.get("env"))
