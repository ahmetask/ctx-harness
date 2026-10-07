"""Tests for the benchmark platform in bench/. Run with: python3 -m unittest discover -s tests

They need git and Go (the demo repo is a Go module). Without Go they are skipped.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "bench" / "demo"))

import run as bench  # noqa: E402
from agents import clean_env  # noqa: E402
from materialize import HISTORY, TEMPLATE, materialize  # noqa: E402
import sandbox  # noqa: E402

HAVE_GO = shutil.which("go") is not None

# A stand-in for the claude CLI: logs how it was called, writes a one-step
# transcript where Claude Code would, bootstraps .ctx/ when asked to build.
STUB_CLAUDE = '''#!{python}
import json, os, pathlib, subprocess, sys, uuid
argv = sys.argv[1:]
with open("{log}", "a") as f:
    f.write(json.dumps({{"argv": argv, "task": os.environ.get("CTXH_TASK"),
                        "disabled": os.environ.get("CTXH_DISABLED")}}) + "\\n")
if argv[1] == "/ctx-harness:build":
    subprocess.run([sys.executable, "{ctxh}", "build-index"], check=True, capture_output=True)
    subprocess.run([sys.executable, "{ctxh}", "skeleton"], check=True, capture_output=True)
    pathlib.Path(".ctx/map.draft.md").rename(".ctx/map.md")
sid = str(uuid.uuid4())
d = pathlib.Path("{config}") / "projects" / "stub"
d.mkdir(parents=True, exist_ok=True)
msg = {{"type": "assistant", "message": {{"id": "m1", "usage": {{"input_tokens": 100, "output_tokens": 50,
       "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 10}},
       "content": [{{"type": "tool_use", "id": "t1", "name": "Read", "input": {{"file_path": "go.mod"}}}}]}}}}
(d / (sid + ".jsonl")).write_text(json.dumps(msg) + "\\n")
print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "session_id": sid,
                  "total_cost_usd": 0.01, "num_turns": 1, "result": "done"}}))
'''


def tree(root: Path):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts}


class Materialize(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxh-bench-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, repo, *args):
        return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout

    def test_history_replays_to_the_template(self):
        repo = materialize(self.tmp / "a")
        self.assertEqual(tree(repo), tree(TEMPLATE))
        log = self.git(repo, "log", "--format=%s").splitlines()
        self.assertEqual(len(log), len(HISTORY) + 1)
        self.assertEqual(log[-1], "initial import")
        self.assertEqual(self.git(repo, "status", "--porcelain"), "")

    def test_history_is_deterministic(self):
        a = self.git(materialize(self.tmp / "a"), "rev-parse", "HEAD")
        b = self.git(materialize(self.tmp / "b"), "rev-parse", "HEAD")
        self.assertEqual(a, b)

    def test_index_finds_the_planted_signals(self):
        repo = materialize(self.tmp / "a")

        def q(*args):
            r = subprocess.run([sys.executable, str(bench.CTXH), *args], cwd=repo, env=clean_env(),
                               text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout

        q("build-index")
        self.assertIn("internal/payments/idempotency.go", q("q", "find", "IdempotencyKey"))
        self.assertIn("internal/notify/templates.go", q("q", "cochange", "internal/orders/state.go"))
        self.assertIn("fix:", q("q", "risk", "internal/orders/service.go"))
        self.assertIn("revert:", q("q", "risk", "internal/catalog/search.go"))
        self.assertIn("internal/pricing/pricing.go", q("q", "impact", "internal/money/money.go"))
        self.assertIn("Dana Ortiz", q("q", "owner", "internal/orders/state.go"))


@unittest.skipUnless(HAVE_GO, "go not installed")
class DemoAndTasks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="ctxh-bench-test-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_demo_builds_and_its_tests_pass(self):
        repo = materialize(self.tmp / "demo", history=False)
        for cmd in (["go", "vet", "./..."], ["go", "test", "-count=1", "./..."]):
            r = subprocess.run(cmd, cwd=repo, env=clean_env(), text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, f"{cmd}: {r.stdout}{r.stderr}")

    def test_demo_size(self):
        src = [p for p in TEMPLATE.rglob("*.go") if not p.name.endswith("_test.go")]
        mods = {p.parent for p in src}
        self.assertGreaterEqual(len(src), 40)
        self.assertGreaterEqual(len(mods), 6)

    def test_every_task_fails_untouched_and_passes_with_its_solution(self):
        tasks = bench.load_tasks()
        self.assertGreaterEqual(len(tasks), 6)
        self.assertGreaterEqual(len({t.category for t in tasks}), 4)
        for task in tasks:
            with self.subTest(task=task.id):
                before = materialize(self.tmp / f"{task.id}-before", history=False)
                ok, why = bench.run_check(before, task)
                self.assertFalse(ok, f"{task.id}: check passes on the untouched repo")
                after = materialize(self.tmp / f"{task.id}-after", history=False)
                shutil.copytree(task.solution, after, dirs_exist_ok=True)
                ok, why = bench.run_check(after, task)
                self.assertTrue(ok, f"{task.id}: reference solution fails: {why}")

    def test_task_selection(self):
        self.assertEqual([t.id for t in bench.load_tasks("t2,t4-refunds")], ["t2-fixed-coupon-tax", "t4-refunds"])
        with self.assertRaises(SystemExit):
            bench.load_tasks("t99")


@unittest.skipUnless(HAVE_GO, "go not installed")
class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp(prefix="ctxh-bench-out-"))

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def rows(self, run_dir):
        return [json.loads(x) for x in (run_dir / "results.jsonl").read_text().splitlines()]

    def test_fake_run_records_both_modes_and_reports(self):
        run_dir = bench.main(["--agent", "fake", "--tasks", "t1,t3", "--repeats", "2", "--out", str(self.out)])
        rows = self.rows(run_dir)
        self.assertEqual([r["mode"] for r in rows][0], "bootstrap")
        work = [r for r in rows if r["mode"] != "bootstrap"]
        self.assertEqual(len(work), 2 * 2 * 2)
        self.assertTrue(all(r["passed"] for r in rows), [r["check"] for r in rows if not r["passed"]])
        self.assertTrue(all(r["transcript_ok"] and r["tokens_total"] > 0 for r in rows))
        self.assertTrue((run_dir / "ctx" / "map.md").exists())
        report = (run_dir / "report.md").read_text()
        for heading in ("## Overall", "## Per task", "## By category", "## Harness overhead", "synthetic"):
            self.assertIn(heading, report)

    def test_claude_agent_invocation_with_stub_cli(self):
        """Drive the real-agent path against a stub `claude` that logs its argv and env."""
        bin_dir, config = self.out / "bin", self.out / "claude-config"
        bin_dir.mkdir()
        log = self.out / "calls.jsonl"
        stub = bin_dir / "claude"
        stub.write_text(STUB_CLAUDE.format(python=sys.executable, ctxh=bench.CTXH, log=log, config=config))
        stub.chmod(0o755)
        env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "CLAUDE_CONFIG_DIR": str(config),
               "CTXH_TASK": "leaked-from-caller"}
        with unittest.mock.patch.dict(os.environ, env):
            run_dir = bench.main(["--agent", "claude", "--tasks", "t1", "--repeats", "1", "--model", "m-test",
                                  "--out", str(self.out / "res")])
        calls = [json.loads(x) for x in log.read_text().splitlines()]
        boot, *work = calls
        self.assertEqual(boot["argv"][:2], ["-p", "/ctx-harness:build"])
        self.assertEqual(boot["task"], "bootstrap")
        by_mode = {("--plugin-dir" in c["argv"]): c for c in work}
        harness, baseline = by_mode[True], by_mode[False]
        self.assertIsNone(harness["disabled"])
        self.assertEqual(baseline["disabled"], "1")
        self.assertEqual({harness["task"], baseline["task"]}, {"t1-locate-idempotency"})
        for c in work:
            self.assertIn("non-interactive run", c["argv"][1])
            self.assertIn("m-test", c["argv"])
            self.assertNotIn("--max-turns", c["argv"])
        rows = self.rows(run_dir)
        self.assertTrue(all(r["transcript_ok"] for r in rows), rows)
        self.assertTrue(all(r["cost_usd"] == 0.01 for r in rows))
        self.assertTrue((run_dir / "transcripts" / "t1-locate-idempotency-harness-0.jsonl").exists())

    def test_noop_run_fails_and_reuses_context(self):
        first = bench.main(["--agent", "fake", "--tasks", "t1", "--repeats", "1", "--modes", "harness",
                            "--out", str(self.out)])
        run_dir = bench.main(["--agent", "noop", "--tasks", "t1", "--repeats", "1",
                              "--ctx-from", str(first / "ctx"), "--out", str(self.out)])
        rows = self.rows(run_dir)
        self.assertEqual({r["mode"] for r in rows}, {"harness", "baseline"})
        self.assertFalse(any(r["passed"] for r in rows))
        self.assertIn("## Failed runs", (run_dir / "report.md").read_text())


@unittest.skipUnless(HAVE_GO, "go not installed")
class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ctxh-bench-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_smoke_passes_and_leaves_no_trace(self):
        repo = self.tmp / "box"
        with unittest.mock.patch("sys.stdout"):
            self.assertEqual(sandbox.main([str(repo)]), 0)
            self.assertEqual(sandbox.main([str(repo)]), 0)  # reuse re-indexes in place
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=repo, text=True,
                                        capture_output=True).stdout, "")
        self.assertEqual(list((repo / ".ctx").rglob("sandbox-smoke*")), [])

    def test_refuses_to_delete_a_directory_it_did_not_make(self):
        (self.tmp / "keep").mkdir()
        with self.assertRaises(SystemExit):
            sandbox.main([str(self.tmp / "keep"), "--fresh"])
        self.assertTrue((self.tmp / "keep").exists())


if __name__ == "__main__":
    unittest.main()
