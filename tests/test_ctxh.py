"""Tests for the ctxh engine. Run with: python3 -m unittest discover -s tests

Each test builds a throwaway git repo and runs ctxh as a subprocess, the way
Claude Code hooks and agents do.
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

CTXH = Path(__file__).resolve().parents[1] / "plugins" / "ctx-harness" / "bin" / "ctxh"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "transcripts"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def write(root: Path, rel: str, text: str):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).lstrip("\n"))


class Repo:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="ctxh-test-"))
        self.git("init", "-q", "-b", "main")

    def env(self, extra=None):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("CLAUDE_PROJECT_DIR", "CTXH_", "CTX_"))}
        env.update(GIT_ENV)
        env.update({"CTXH_PLAN_GATE": "1", "CTXH_REVIEW_GATE": "1"})  # the gates are opt-in; most tests exercise them
        env.update(extra or {})
        return env

    def git(self, *args):
        subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=self.root, check=True,
                       env=self.env(), capture_output=True)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def ctxh(self, *args, stdin="", env=None, check=True):
        r = subprocess.run([sys.executable, str(CTXH), *args], cwd=self.root, input=stdin, text=True,
                           capture_output=True, env=self.env(env))
        if check and r.returncode != 0:
            raise AssertionError(f"ctxh {' '.join(args)} failed ({r.returncode}): {r.stderr}{r.stdout}")
        return r

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def python_app(repo: Repo):
    """Small app with a hotfix in history and a pair of files that change together."""
    write(repo.root, "app/__init__.py", "")
    write(repo.root, "app/common/__init__.py", "")
    write(repo.root, "app/common/retry.py", """
        def retry(fn, attempts=3):
            for _ in range(attempts):
                try:
                    return fn()
                except ConnectionError:
                    pass
            raise RuntimeError("gave up")
    """)
    write(repo.root, "app/payments/__init__.py", "")
    write(repo.root, "app/payments/client.py", """
        from app.common.retry import retry


        class PaymentClient:
            def charge(self, order_id, amount):
                return retry(lambda: {"id": order_id, "amount": amount})
    """)
    write(repo.root, "app/orders/__init__.py", "")
    write(repo.root, "app/orders/service.py", """
        from app.payments.client import PaymentClient


        class OrderService:
            def create(self, order_id):
                return PaymentClient().charge(order_id, 100)
    """)
    write(repo.root, "tests/test_service.py", """
        from app.orders.service import OrderService


        def test_create():
            assert OrderService().create("1")["id"] == "1"
    """)
    write(repo.root, "Makefile", "test:\n\ttrue\n\nlint:\n\ttrue\n")
    repo.commit("init")
    write(repo.root, "app/payments/client.py", (repo.root / "app/payments/client.py").read_text() + "# key\n")
    write(repo.root, "app/orders/service.py", (repo.root / "app/orders/service.py").read_text() + "# key\n")
    repo.commit("hotfix: double charge on retry")
    write(repo.root, "app/payments/client.py", (repo.root / "app/payments/client.py").read_text() + "# k2\n")
    write(repo.root, "app/orders/service.py", (repo.root / "app/orders/service.py").read_text() + "# k2\n")
    repo.commit("pass idempotency key")


def transcript(path: Path, events):
    lines = []
    for i, (name, inp) in enumerate(events):
        lines.append({"type": "assistant", "isSidechain": False,
                      "message": {"id": f"m{i}", "usage": {"input_tokens": 10, "output_tokens": 5,
                                                           "cache_read_input_tokens": 100,
                                                           "cache_creation_input_tokens": 20},
                                  "content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}]}})
        lines.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"t{i}", "content": "ok"}]}})
    path.write_text("\n".join(json.dumps(x) for x in lines))


class NotOptedIn(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)

    def tearDown(self):
        self.repo.cleanup()

    def test_hooks_do_not_touch_repo(self):
        out = self.repo.ctxh("hook-start", stdin="{}").stdout
        self.assertIn("/ctx-harness:build", out)
        self.assertEqual(self.repo.ctxh("hook-prompt", stdin="{}").stdout, "")
        tp = self.repo.root / "t.jsonl"
        transcript(tp, [("Read", {"file_path": str(self.repo.root / "app/orders/service.py")})])
        self.repo.ctxh("hook-stop", stdin=json.dumps({"session_id": "s", "transcript_path": str(tp)}))
        self.assertFalse((self.repo.root / ".ctx").exists())

    def test_query_explains_how_to_opt_in(self):
        r = self.repo.ctxh("q", "hot", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("/ctx-harness:build", r.stderr)


class Index(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Repo()
        python_app(cls.repo)
        cls.out = cls.repo.ctxh("build-index", "--verify").stdout

    @classmethod
    def tearDownClass(cls):
        cls.repo.cleanup()

    def test_build_creates_ctx_and_gitignore(self):
        self.assertIn("2 verified", self.out)
        ctx = self.repo.root / ".ctx"
        self.assertTrue((ctx / "graph.json").exists())
        self.assertIn("graph.json", (ctx / ".gitignore").read_text())

    def test_queries(self):
        q = lambda *a: self.repo.ctxh("q", *a).stdout
        self.assertIn("app/orders/service.py", q("find", "OrderService"))
        self.assertIn("app/payments/client.py", q("rdeps", "retry.py"))
        impact = q("impact", "client.py")
        self.assertIn("1  app/orders/service.py", impact)
        self.assertIn("tests/test_service.py  (test)", impact)
        self.assertIn("app/orders/service.py", q("cochange", "client.py"))
        self.assertIn("tests/test_service.py", q("tests", "service.py"))
        self.assertIn("hotfix", q("risk", "client.py"))
        self.assertIn("app/common/retry.py", q("hot", "1"))

    def test_skeleton(self):
        self.repo.ctxh("skeleton")
        draft = (self.repo.root / ".ctx" / "map.draft.md").read_text()
        self.assertIn("TODO(llm)", draft)
        self.assertIn("`make lint` · `make test`", draft)
        self.assertIn("app/orders/service.py <-> app/payments/client.py", draft)
        self.assertTrue((self.repo.root / ".ctx" / "learned.md").exists())

    def test_reindex_keeps_verification(self):
        self.repo.ctxh("build-index", "--quiet")
        cmds = json.loads((self.repo.root / ".ctx" / "commands.json").read_text())["commands"]
        self.assertTrue(all(c["verified"] for c in cmds))


class CardsAndHooks(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.ctxh("build-index")
        self.repo.ctxh("skeleton")
        ctx = self.repo.root / ".ctx"
        draft = (ctx / "map.draft.md").read_text().replace("TODO(llm)", "purpose")
        (ctx / "map.md").write_text(draft)
        (ctx / "map.draft.md").unlink()
        self.card = ctx / "cards" / "app-orders.md"
        self.card.write_text("---\nmodule: app/orders\nanchors:\n  path: app/orders/service.py\n---\n"
                             "Owns order creation; `OrderService.create` charges once.\n")

    def tearDown(self):
        self.repo.cleanup()

    def test_unstamped_anchor_is_reported_then_fixed(self):
        r = self.repo.ctxh("check", check=False)
        self.assertIn("anchors not stamped", r.stdout)
        self.repo.ctxh("anchor", str(self.card))
        self.assertRegex(self.card.read_text(), r"app/orders/service.py: [0-9a-f]{12}")
        self.assertIn("ok", self.repo.ctxh("check").stdout)

    def test_ready_blocks_until_map_is_filled_then_reports_warnings(self):
        ctx = self.repo.root / ".ctx"
        (ctx / "map.md").write_text("Stack: python.\n| app/orders | TODO(llm) | service.py | - |\n")
        r = self.repo.ctxh("ready", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("TODO(llm)", r.stdout)
        self.assertIn("not ready", r.stdout)
        (ctx / "map.md").write_text("Stack: python.\n| app/orders | orders | service.py | - |\n")
        self.repo.ctxh("anchor", str(self.card))
        r = self.repo.ctxh("ready", check=False)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ready: 0 blocking", r.stdout)
        self.assertIn("small repo", r.stdout)  # a handful of files needs no cards
        self.assertIn(".ctx/ is not committed", r.stdout)

    def test_ready_without_ctx_dir_says_how_to_start(self):
        bare = Repo()
        try:
            r = bare.ctxh("ready", check=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no .ctx/", r.stdout + r.stderr)
        finally:
            bare.cleanup()

    def test_stale_after_edit(self):
        self.repo.ctxh("anchor", str(self.card))
        self.assertIn("everything fresh", self.repo.ctxh("stale").stdout)
        path = self.repo.root / "app/orders/service.py"
        path.write_text(path.read_text() + "# change\n")
        self.assertIn("stale card app-orders.md", self.repo.ctxh("stale").stdout)

    def test_hook_start_injects_protocol_map_and_freshness(self):
        out = self.repo.ctxh("hook-start", stdin="{}").stdout
        self.assertIn("# Working protocol (context harness)", out)
        self.assertIn("# Repo map", out)
        self.assertIn("stale card app-orders.md", out)  # anchors never stamped
        (self.repo.root / ".ctx" / "protocol.md").write_text("# Team protocol\n")
        self.assertIn("# Team protocol", self.repo.ctxh("hook-start", stdin="{}").stdout)

    def test_compaction_resumes_from_the_active_plan(self):
        start = lambda source: self.repo.ctxh("hook-start", stdin=json.dumps({"source": source})).stdout
        self.assertEqual(start("compact"), start("startup"))  # no plan: compaction re-injects the same context
        log = "\n".join(f"- step {i} done" for i in range(1, 11))
        (self.repo.root / ".ctx" / "tasks").mkdir(parents=True, exist_ok=True)
        (self.repo.root / ".ctx" / "tasks" / "active.md").write_text(
            f"# T99 · Retry payments\n\n## Goal\nRetry.\n\n## Progress log\n{log}\n")
        out = start("compact")
        self.assertIn("# Working protocol (context harness)", out)
        self.assertIn("# Repo map", out)
        self.assertIn("Context was compacted mid-task. You are working on the plan in .ctx/tasks/active.md "
                      "(T99 · Retry payments)", out)
        self.assertIn("Last 8 progress entries:\n- step 3 done\n", out)
        self.assertIn("- step 10 done", out)
        self.assertNotIn("- step 2 done", out)
        self.assertIn("This session resumed mid-task", start("resume"))
        self.assertIn("Active plan exists: .ctx/tasks/active.md (read it first).", start("startup"))
        self.assertNotIn("progress entries", start("startup"))

    def test_disabled_injects_nothing(self):
        out = self.repo.ctxh("hook-start", stdin="{}", env={"CTXH_DISABLED": "1"}).stdout
        self.assertEqual(out, "")

    def test_background_reindex_after_commit(self):
        old = json.loads((self.repo.root / ".ctx" / "graph.json").read_text())["head"]
        path = self.repo.root / "app/common/retry.py"
        path.write_text(path.read_text() + "# change\n")
        self.repo.commit("touch retry")
        self.repo.ctxh("hook-start", stdin="{}")
        for _ in range(50):
            head = json.loads((self.repo.root / ".ctx" / "graph.json").read_text())["head"]
            if head != old and not (self.repo.root / ".ctx" / "tmp" / "index.lock").exists():
                break
            time.sleep(0.1)
        self.assertNotEqual(head, old)

    def test_stop_records_metrics_and_gates_review_once(self):
        tp = self.repo.root / "t.jsonl"
        svc = str(self.repo.root / "app/orders/service.py")
        transcript(tp, [("Bash", {"command": "ctxh q impact service.py"}),
                        ("Edit", {"file_path": svc, "old_string": "a", "new_string": "b"})])
        payload = json.dumps({"session_id": "s1", "transcript_path": str(tp)})
        first = self.repo.ctxh("hook-stop", stdin=payload).stdout
        self.assertEqual(json.loads(first)["decision"], "block")
        self.assertEqual(self.repo.ctxh("hook-stop", stdin=payload).stdout, "")  # never loops
        metrics = json.loads((self.repo.root / ".ctx" / "metrics" / "s1.json").read_text())
        self.assertEqual(metrics["tokens_total"], 270)
        self.assertEqual(metrics["label"], "harness")
        trace = json.loads((self.repo.root / ".ctx" / "traces" / "s1.json").read_text())
        self.assertEqual(trace["ctx_queries"], ["ctxh q impact service.py"])
        self.assertEqual(trace["files_edited"], ["app/orders/service.py"])

    def test_reviewer_after_edit_passes_gate(self):
        tp = self.repo.root / "t.jsonl"
        svc = str(self.repo.root / "app/orders/service.py")
        transcript(tp, [("Edit", {"file_path": svc}),
                        ("Agent", {"subagent_type": "ctx-harness:reviewer", "prompt": "review HEAD"})])
        out = self.repo.ctxh("hook-stop", stdin=json.dumps({"session_id": "s2", "transcript_path": str(tp)})).stdout
        self.assertEqual(out, "")

    def test_prompt_reminder(self):
        out = self.repo.ctxh("hook-prompt", stdin="{}").stdout
        self.assertIn("ctx-harness:planner", out)
        self.assertIn("ctx-harness:reviewer", out)
        self.assertIn("run_in_background: false", out)


class LeanDefaults(unittest.TestCase):
    """Out of the box the harness adds no subagent and no blocked turn: both gates are opt-in."""
    OFF = {"CTXH_PLAN_GATE": "", "CTXH_REVIEW_GATE": ""}

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.ctxh("build-index")

    def tearDown(self):
        self.repo.cleanup()

    def test_stop_hook_never_blocks_and_still_records(self):
        tp = self.repo.root / "lean.jsonl"
        files = ["app/orders/service.py", "app/payments/client.py", "app/common/retry.py"]
        transcript(tp, [("Edit", {"file_path": str(self.repo.root / f)}) for f in files])
        out = self.repo.ctxh("hook-stop", env=self.OFF, stdin=json.dumps(
            {"session_id": "lean", "transcript_path": str(tp)})).stdout
        self.assertEqual(out, "")
        self.assertTrue((self.repo.root / ".ctx" / "metrics" / "lean.json").exists())

    def test_prompt_hook_is_silent_without_a_gate_or_a_plan(self):
        self.assertEqual(self.repo.ctxh("hook-prompt", env=self.OFF, stdin="{}").stdout, "")
        active = self.repo.root / ".ctx" / "tasks" / "active.md"
        active.parent.mkdir(parents=True, exist_ok=True)
        active.write_text("# plan\n")
        self.assertEqual(self.repo.ctxh("hook-prompt", env=self.OFF, stdin="{}").stdout.strip(),
                         "Active plan: .ctx/tasks/active.md")
        only_review = self.repo.ctxh("hook-prompt", env={**self.OFF, "CTXH_REVIEW_GATE": "1"}, stdin="{}").stdout
        self.assertIn("ctx-harness:reviewer", only_review)
        self.assertNotIn("ctx-harness:planner", only_review)

    def test_protocol_makes_subagents_opt_in(self):
        start = self.repo.ctxh("hook-start", env=self.OFF, stdin="{}").stdout
        self.assertIn("opt-in", start)
        self.assertNotIn("ask `ctx-harness:planner` first", start)
        self.assertLess(len(start), 7000)  # protocol + map is paid for on every turn


class Polyglot(unittest.TestCase):
    def test_typescript_and_nested_go_module(self):
        repo = Repo()
        try:
            write(repo.root, "package.json", '{"name": "x", "scripts": {"test": "node -e 1"}}')
            write(repo.root, "src/util/slug.ts", "export function slug(s: string) { return s }\n")
            write(repo.root, "src/index.ts", 'import { slug } from "./util/slug";\nexport class Router {}\n')
            write(repo.root, "svc/go.mod", "module example.com/svc\n\ngo 1.22\n")
            write(repo.root, "svc/internal/store/store.go", "package store\n\ntype Store struct{}\n")
            write(repo.root, "svc/cmd/api/main.go", 'package main\n\nimport (\n\t"example.com/svc/internal/store"\n)\n\n'
                  "func main() { _ = store.Store{} }\n")
            repo.commit("init")
            repo.ctxh("build-index")
            self.assertIn("src/index.ts", repo.ctxh("q", "rdeps", "slug.ts").stdout)
            self.assertIn("svc/cmd/api/main.go", repo.ctxh("q", "rdeps", "store.go").stdout)
            cmds = [c["cmd"] for c in json.loads((repo.root / ".ctx" / "commands.json").read_text())["commands"]]
            self.assertIn("cd svc && go test ./...", cmds)
            self.assertIn("npm test", cmds)
        finally:
            repo.cleanup()


def load_ctxh():
    """The engine as a module, for unit tests of pure helpers."""
    loader = importlib.machinery.SourceFileLoader("ctxh_engine", str(CTXH))
    spec = importlib.util.spec_from_loader("ctxh_engine", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class Ignore(unittest.TestCase):
    def test_ctxignore_excludes_fixtures_from_index_and_commands(self):
        repo = Repo()
        try:
            python_app(repo)
            write(repo.root, "fixtures/demo/go.mod", "module example.com/demo\n\ngo 1.22\n")
            write(repo.root, "fixtures/demo/core/core.go", "package core\n\nfunc Hub() {}\n")
            write(repo.root, "app/testdata/sample.py", "def Hub():\n    pass\n")
            write(repo.root, "app/gen/schema_gen.py", "def Hub():\n    pass\n")
            write(repo.root, ".ctxignore", "# fixtures\n/fixtures/\n*_gen.py\n")
            repo.commit("fixtures")
            repo.ctxh("build-index")
            files = json.loads((repo.root / ".ctx" / "graph.json").read_text())["files"]
            self.assertIn("app/orders/service.py", files)
            for f in ("fixtures/demo/core/core.go", "app/testdata/sample.py", "app/gen/schema_gen.py"):
                self.assertNotIn(f, files)
            self.assertIn("no symbol matching 'Hub'", repo.ctxh("q", "find", "Hub").stdout)
            cmds = [c["cmd"] for c in json.loads((repo.root / ".ctx" / "commands.json").read_text())["commands"]]
            self.assertFalse([c for c in cmds if "go " in c], cmds)
            self.assertTrue(all(f.startswith("app/") for f in repo.ctxh("q", "hot").stdout.split()[1::2]))
            # edits to ignored files do not make the index lag
            write(repo.root, "fixtures/demo/core/core.go", "package core\n\nfunc Hub2() {}\n")
            repo.commit("touch fixture")
            self.assertEqual("everything fresh", repo.ctxh("stale").stdout.strip())
        finally:
            repo.cleanup()

    def test_pattern_semantics(self):
        m = load_ctxh()
        root = Path(tempfile.mkdtemp(prefix="ctxh-ignore-"))
        try:
            (root / ".ctxignore").write_text("docs/\n/top.py\n**/snap/**\n!keep_gen.py\n*_gen.py\nlib/*.js\n")
            m.ROOT = root
            rules = m.ignore_rules()
            cases = {"docs/a.py": True, "x/docs/a.py": True, "docs.py": False, "top.py": True,
                     "a/top.py": False, "a/snap/b/c.py": True, "a_gen.py": True, "x/keep_gen.py": True,
                     "lib/a.js": True, "lib/x/a.js": False, "src/app.py": False}
            for path, want in cases.items():
                self.assertEqual(m.ignored(path, rules), want, path)
            (root / ".ctxignore").write_text("*_gen.py\n!keep_gen.py\n")
            self.assertFalse(m.ignored("x/keep_gen.py", m.ignore_rules()))  # last match wins
        finally:
            shutil.rmtree(root, ignore_errors=True)


class Shebang(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        write(self.repo.root, "bin/tool", """
            #!/usr/bin/env python3
            from app.orders.service import OrderService


            def cmd_hook_stop(args):
                return OrderService()
        """)
        write(self.repo.root, "scripts/deploy", "#!/bin/bash -e\n\nfunction ship_it {\n  :\n}\nrollback() {\n  :\n}\n")
        write(self.repo.root, "NOTICE", "plain text, no shebang\n")
        self.repo.commit("scripts")
        self.repo.ctxh("build-index")

    def tearDown(self):
        self.repo.cleanup()

    def test_extensionless_scripts_are_indexed(self):
        files = json.loads((self.repo.root / ".ctx" / "graph.json").read_text())["files"]
        self.assertEqual(files["bin/tool"]["lang"], "python")
        self.assertEqual(files["scripts/deploy"]["lang"], "shell")
        self.assertNotIn("NOTICE", files)
        self.assertEqual("bin/tool:5", self.repo.ctxh("q", "find", "cmd_hook_stop").stdout.strip())
        self.assertIn("scripts/deploy:3", self.repo.ctxh("q", "find", "ship_it").stdout)
        self.assertIn("scripts/deploy:6", self.repo.ctxh("q", "find", "rollback").stdout)
        self.assertIn("bin/tool", self.repo.ctxh("q", "rdeps", "service.py").stdout)

    def test_edits_to_scripts_lag_the_index_and_need_review(self):
        tool = self.repo.root / "bin/tool"
        tool.write_text(tool.read_text() + "# change\n")
        self.repo.commit("touch tool")
        self.assertIn("index predates changes to 1 code files", self.repo.ctxh("stale").stdout)
        tp = self.repo.root / "t.jsonl"
        transcript(tp, [("Edit", {"file_path": str(tool)})])
        out = self.repo.ctxh("hook-stop", stdin=json.dumps({"session_id": "s", "transcript_path": str(tp)})).stdout
        self.assertEqual(json.loads(out)["decision"], "block")
        transcript(tp, [("Edit", {"file_path": str(self.repo.root / "NOTICE")})])
        out = self.repo.ctxh("hook-stop", stdin=json.dumps({"session_id": "s3", "transcript_path": str(tp)})).stdout
        self.assertEqual(out, "")

    def test_shebang_forms(self):
        m = load_ctxh()
        d = Path(tempfile.mkdtemp(prefix="ctxh-shebang-"))
        try:
            cases = {"#!/usr/bin/env python3\n": "python", "#!/usr/bin/python3.11 -u\n": "python",
                     "#!/usr/bin/env -S node --no-warnings\n": "javascript", "#!/bin/sh\n": "shell",
                     "#! /usr/bin/env ruby\n": "ruby", "#!/usr/bin/env perl\n": None, "hello\n": None,
                     "#!/usr/bin/shellcheck\n": None}
            for i, (first, want) in enumerate(cases.items()):
                (d / f"s{i}").write_text(first + "body\n")
                self.assertEqual(m.shebang_lang(d / f"s{i}"), want, first)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class CICommands(unittest.TestCase):
    def test_ci_run_lines_become_candidates(self):
        repo = Repo()
        try:
            write(repo.root, "lib/core.py", "def f():\n    return 1\n")
            write(repo.root, "tests/test_core.py", "import unittest\n\n\nclass T(unittest.TestCase):\n"
                  "    def test_f(self):\n        pass\n")
            write(repo.root, ".github/workflows/ci.yml", """
                on: push
                jobs:
                  t:
                    steps:
                      - run: pip install -r requirements.txt
                      - run: npm install -g some-cli
                      - run: python3 -m unittest discover -s tests
                      - run: echo "${{ secrets.TOKEN }}" | docker login
                      - name: lint
                        run: |
                          cd lib
                          python3 -m pyflakes . \\
                            --quiet
                          go vet ./...
                      - run: docker push example/image
            """)
            repo.commit("init")
            repo.ctxh("build-index", "--verify")
            data = json.loads((repo.root / ".ctx" / "commands.json").read_text())
            by = {c["cmd"]: c for c in data["commands"]}
            self.assertIn("cd lib && python3 -m pyflakes . --quiet", data["ci_runs"])
            ut = by["python3 -m unittest discover -s tests"]
            self.assertEqual((ut["source"], ut["in_ci"], ut["kind"], ut["verified"]), ("ci", True, "test", True))
            self.assertEqual(by["cd lib && go vet ./..."]["kind"], "lint")
            for c in by:
                self.assertNotRegex(c, r"install|docker|echo|pyflakes")
        finally:
            repo.cleanup()


class ManualCommands(unittest.TestCase):
    def test_manual_command_survives_reindex_and_is_reverified(self):
        repo = Repo()
        try:
            python_app(repo)
            write(repo.root, "Makefile", "test:\n\tfalse\n\nlint:\n\ttrue\n")
            repo.commit("broken make test")
            repo.ctxh("build-index", "--verify")
            out = repo.ctxh("add-command", "test", "true && echo fixed", "--replaces", "make test").stdout
            self.assertIn("verified", out)
            repo.ctxh("add-command", "build", "exit 3")
            repo.ctxh("build-index")  # a plain re-index keeps both, and their results
            cmds = {c["cmd"]: c for c in json.loads((repo.root / ".ctx" / "commands.json").read_text())["commands"]}
            self.assertNotIn("make test", cmds)  # replaced by the fixed invocation
            self.assertTrue(cmds["true && echo fixed"]["verified"])
            self.assertEqual(cmds["true && echo fixed"]["source"], "manual")
            self.assertFalse(cmds["exit 3"]["verified"])
            # --verify re-runs manual commands too
            cmds_path = repo.root / ".ctx" / "commands.json"
            data = json.loads(cmds_path.read_text())
            for c in data["commands"]:
                c["verified"] = None
            cmds_path.write_text(json.dumps(data))
            repo.ctxh("build-index", "--verify")
            cmds = {c["cmd"]: c for c in json.loads(cmds_path.read_text())["commands"]}
            self.assertTrue(cmds["true && echo fixed"]["verified"])
            self.assertEqual(cmds["exit 3"]["exit"], 3)
            repo.ctxh("skeleton")
            self.assertIn("`true && echo fixed`", (repo.root / ".ctx" / "map.draft.md").read_text())
            self.assertNotEqual(repo.ctxh("add-command", "bogus", "x", check=False).returncode, 0)
        finally:
            repo.cleanup()


class PlanGate(unittest.TestCase):
    """3+ code files changed without a plan: the Stop hook says so once."""

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.ctxh("build-index")
        self.active = self.repo.root / ".ctx" / "tasks" / "active.md"
        self.active.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.repo.cleanup()

    def session(self, files, extra=(), session_id="p1", env=None):
        """Edit each file, then run the reviewer, so only the plan gate can block."""
        tp = self.repo.root / f"{session_id}.jsonl"
        events = [("Edit", {"file_path": str(self.repo.root / f)}) for f in files]
        events += list(extra)
        events.append(("Agent", {"subagent_type": "ctx-harness:reviewer", "prompt": "review"}))
        transcript(tp, events)
        return self.repo.ctxh("hook-stop", env=env, stdin=json.dumps(
            {"session_id": session_id, "transcript_path": str(tp)})).stdout

    THREE = ["app/orders/service.py", "app/payments/client.py", "app/common/retry.py"]

    def test_three_unplanned_files_block_once(self):
        out = self.session(self.THREE)
        self.assertIn("plan gate", json.loads(out)["reason"])
        self.assertIn("ctx-harness:planner", json.loads(out)["reason"])
        self.assertEqual(self.session(self.THREE), "")  # same state, never loops

    def test_two_files_or_an_active_plan_pass(self):
        self.assertEqual(self.session(self.THREE[:2], session_id="p2"), "")
        self.active.write_text("# T0x\n\n## Steps\n1. do the thing\n")
        self.assertEqual(self.session(self.THREE, session_id="p3"), "")

    def test_a_planner_call_counts_as_the_plan(self):
        # The plan may already be filed under done/ by the time the session stops.
        out = self.session(self.THREE, extra=[("Agent", {"subagent_type": "ctx-harness:planner",
                                                         "prompt": "plan the change"})], session_id="p4")
        self.assertEqual(out, "")

    def test_a_plan_the_coder_wrote_counts(self):
        # A fully specified request skips the planner; the coder's own plan may also be filed under done/.
        plan = str(self.repo.root / ".ctx" / "tasks" / "active.md")
        out = self.session(self.THREE, extra=[("Write", {"file_path": plan, "content": "# plan"})], session_id="p8")
        self.assertEqual(out, "")

    def test_off_switch_leaves_the_review_gate_alone(self):
        self.assertEqual(self.session(self.THREE, session_id="p5", env={"CTXH_PLAN_GATE": "0"}), "")
        tp = self.repo.root / "p6.jsonl"
        transcript(tp, [("Edit", {"file_path": str(self.repo.root / f)}) for f in self.THREE])
        out = self.repo.ctxh("hook-stop", env={"CTXH_PLAN_GATE": "0"}, stdin=json.dumps(
            {"session_id": "p6", "transcript_path": str(tp)})).stdout
        self.assertIn("review gate", json.loads(out)["reason"])

    def test_both_gates_fire_in_turn(self):
        tp = self.repo.root / "p7.jsonl"
        transcript(tp, [("Edit", {"file_path": str(self.repo.root / f)}) for f in self.THREE])
        payload = json.dumps({"session_id": "p7", "transcript_path": str(tp)})
        self.assertIn("plan gate", json.loads(self.repo.ctxh("hook-stop", stdin=payload).stdout)["reason"])
        self.active.write_text("# plan\n")
        self.assertIn("review gate", json.loads(self.repo.ctxh("hook-stop", stdin=payload).stdout)["reason"])
        self.assertEqual(self.repo.ctxh("hook-stop", stdin=payload).stdout, "")


class TranscriptFixtures(unittest.TestCase):
    """Checked-in Claude Code transcripts: the format the whole measurement side depends on."""

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.ctxh("build-index")

    def tearDown(self):
        self.repo.cleanup()

    def load(self, name):
        """Copy a fixture (and its subagents) into the repo, with __ROOT__ pointing at it."""
        root = str(self.repo.root)
        dest = self.repo.root / f"{name}.jsonl"
        dest.write_text((FIXTURES / f"{name}.jsonl").read_text().replace("__ROOT__", root))
        subs = FIXTURES / name / "subagents"
        if subs.is_dir():
            out = self.repo.root / name / "subagents"
            out.mkdir(parents=True, exist_ok=True)
            for p in sorted(subs.glob("*.jsonl")):
                (out / p.name).write_text(p.read_text().replace("__ROOT__", root))
        return dest

    def metrics(self, session):
        return json.loads((self.repo.root / ".ctx" / "metrics" / f"{session}.json").read_text())

    def test_session_parses_to_known_tokens_files_and_commands(self):
        self.repo.ctxh("usage", str(self.load("session-edit")), "--label", "harness", "--task", "t1")
        m = self.metrics("session-edit")
        self.assertEqual(m["tokens_total"], 95819)  # main + subagents, deduplicated by message id
        self.assertEqual(m["tokens_uncached"], 18104)
        self.assertEqual(m["tokens_main"]["cache_read_input_tokens"], 74655)
        self.assertEqual(m["tokens_sub"]["cache_creation_input_tokens"], 5000)  # sidechain + subagents/
        self.assertEqual(m["steps"], 6)
        self.assertEqual(m["subagents"], {"ctx-harness:scout": 1})
        self.assertEqual(m["tool_version"], "2.0.14")
        t = json.loads((self.repo.root / ".ctx" / "traces" / "session-edit.json").read_text())
        self.assertEqual(t["files_read"], ["app/orders/service.py"])  # the subagent's read is not the session's
        self.assertEqual(t["files_edited"], ["app/orders/service.py"])
        self.assertEqual(t["ctx_queries"], ["ctxh q impact app/orders/service.py", "ctxh q find charge_token"])
        self.assertEqual(t["ctx_misses"], ["ctxh q find charge_token"])
        self.assertEqual([c["cmd"] for c in t["failed_commands"]], ["python3 -m pytest tests/test_service.py -q"])

    def test_gate_blocks_the_unreviewed_edit_and_passes_the_reviewed_one(self):
        blocked = self.repo.ctxh("hook-stop", stdin=json.dumps(
            {"session_id": "s1", "transcript_path": str(self.load("session-edit"))})).stdout
        self.assertEqual(json.loads(blocked)["decision"], "block")
        passed = self.repo.ctxh("hook-stop", stdin=json.dumps(
            {"session_id": "s2", "transcript_path": str(self.load("session-reviewed"))})).stdout
        self.assertEqual(passed, "")
        self.assertEqual(self.metrics("s2")["tokens_total"], 27612)

    def test_missing_usage_warns_once_and_records_nothing(self):
        payload = json.dumps({"session_id": "s3", "transcript_path": str(self.load("drift-no-usage"))})
        first = self.repo.ctxh("hook-stop", stdin=payload)
        self.assertIn("no `usage`", first.stderr)
        self.assertIn("2.0.14", first.stderr)  # the version to report the drift against
        self.assertFalse((self.repo.root / ".ctx" / "metrics" / "s3.json").exists())  # no row of zeros
        self.assertEqual(self.repo.ctxh("hook-stop", stdin=payload).stderr, "")  # warns once, not every session

    def test_unknown_tool_names_warn_but_keep_the_token_counts(self):
        out = self.repo.ctxh("hook-stop", stdin=json.dumps(
            {"session_id": "s4", "transcript_path": str(self.load("drift-unknown-tools"))}))
        self.assertIn("str_replace_editor", out.stderr)
        self.assertEqual(out.stdout, "")  # nothing to gate on: no recognized edit
        self.assertEqual(self.metrics("s4")["tokens_total"], 21602)

    def test_usage_command_fails_loudly_on_an_unreadable_transcript(self):
        r = self.repo.ctxh("usage", str(self.load("drift-no-usage")), check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no `usage`", r.stderr)
        self.assertFalse((self.repo.root / ".ctx" / "metrics").exists())


class Modules(unittest.TestCase):
    """Modules follow package manifests; markdown is indexed as docs; cards must name a real module."""

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        write(self.repo.root, "plugins/kit/.claude-plugin/plugin.json", '{"name": "kit"}')
        write(self.repo.root, "plugins/kit/bin/tool.py", "def run_tool():\n    return 1\n")
        write(self.repo.root, "plugins/kit/agents/reviewer.md", """
            # Reviewer prompt

            ```bash
            # not a heading
            ```

            ## Severity rules
            Findings come in three levels.
        """)
        write(self.repo.root, "svc/go.mod", "module example.com/svc\n\ngo 1.22\n")
        write(self.repo.root, "svc/internal/store/store.go", "package store\n\ntype Store struct{}\n")
        write(self.repo.root, "svc/main.go", "package main\n\nfunc main() {}\n")
        self.repo.commit("packages")
        for i in range(2):  # the prompt changes together with its tool, as plugin prompts do
            write(self.repo.root, "plugins/kit/bin/tool.py", f"def run_tool():\n    return {i + 2}\n")
            md = self.repo.root / "plugins/kit/agents/reviewer.md"
            md.write_text(md.read_text() + f"- rule {i}\n")
            self.repo.commit(f"tool and prompt {i}")
        self.out = self.repo.ctxh("build-index").stdout
        self.graph = json.loads((self.repo.root / ".ctx" / "graph.json").read_text())

    def tearDown(self):
        self.repo.cleanup()

    def test_package_roots_group_modules(self):
        files = self.graph["files"]
        self.assertEqual(files["plugins/kit/bin/tool.py"]["module"], "plugins/kit")
        self.assertEqual(files["svc/internal/store/store.go"]["module"], "svc/internal/store")
        self.assertEqual(files["svc/main.go"]["module"], "svc")
        self.assertEqual(files["app/orders/service.py"]["module"], "app/orders")  # no manifest: as before
        self.assertIn("module plugins/kit:", self.repo.ctxh("q", "module", "tool.py").stdout)

    def test_markdown_is_docs_findable_and_in_cochange_but_never_gated(self):
        doc = self.graph["files"]["plugins/kit/agents/reviewer.md"]
        self.assertEqual((doc["role"], doc["module"]), ("docs", "plugins/kit"))
        self.assertEqual([h for h, _ in doc["symbols"]], ["Reviewer prompt", "Severity rules"])
        self.assertNotIn("markdown", self.graph["stack"]["languages"])
        self.assertIn("plugins/kit/agents/reviewer.md:7", self.repo.ctxh("q", "find", "Severity rules").stdout)
        self.assertIn("plugins/kit/agents/reviewer.md", self.repo.ctxh("q", "cochange", "tool.py").stdout)
        self.assertNotIn("reviewer.md", self.repo.ctxh("q", "hot", "50").stdout)
        tp = self.repo.root / "t.jsonl"
        transcript(tp, [("Edit", {"file_path": str(self.repo.root / "plugins/kit/agents/reviewer.md")})])
        out = self.repo.ctxh("hook-stop", stdin=json.dumps({"session_id": "md", "transcript_path": str(tp)})).stdout
        self.assertEqual(out, "")

    def test_card_with_unknown_module_is_reported(self):
        cards = self.repo.root / ".ctx" / "cards"
        cards.mkdir(parents=True, exist_ok=True)
        (cards / "plugins.md").write_text("---\nmodule: plugins\nanchors:\n  plugins/kit/bin/tool.py: x\n---\nKit.\n")
        out = self.repo.ctxh("build-index").stdout
        self.assertIn("warning: plugins.md: module 'plugins' is not in the index (nearest: plugins/kit)", out)
        check = self.repo.ctxh("check", check=False)
        self.assertNotEqual(check.returncode, 0)
        self.assertIn("module 'plugins' is not in the index", check.stdout)


class InitTargets(unittest.TestCase):
    """`ctxh init --target` writes a marked, idempotent block into other agents' instruction files."""

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.ctxh("build-index")

    def tearDown(self):
        self.repo.cleanup()

    def test_each_target_is_written_once_and_points_at_ctx(self):
        out = self.repo.ctxh("init", "--target", "agents-md,gemini,cursor,aider").stdout
        files = {"AGENTS.md", "GEMINI.md", ".cursor/rules/ctx-harness.mdc", "CONVENTIONS.md"}
        before = {f: (self.repo.root / f).read_text() for f in files}
        for f, text in before.items():
            self.assertIn(f"{f}: created", out)
            self.assertEqual(text.count("<!-- ctx-harness:begin -->"), 1, f)
            self.assertIn(".ctx/map.md", text)
            self.assertIn("ctxh q find", text)
            self.assertNotIn("ctx-harness:scout", text)  # no Claude-only helpers in another agent's file
        self.assertTrue(before[".cursor/rules/ctx-harness.mdc"].startswith("---\ndescription:"))
        self.assertIn("alwaysApply: true", before[".cursor/rules/ctx-harness.mdc"])
        self.assertEqual((self.repo.root / ".aider.conf.yml").read_text(), "read: CONVENTIONS.md\n")
        self.assertNotIn("no .ctx/ yet", out)
        again = self.repo.ctxh("init", "--target", "agents-md,gemini,cursor,aider").stdout
        self.assertEqual(again.count("unchanged"), 4)
        self.assertEqual(before, {f: (self.repo.root / f).read_text() for f in files})

    def test_text_around_the_block_is_kept_and_an_old_block_replaced(self):
        agents = self.repo.root / "AGENTS.md"
        agents.write_text("# House rules\n\nTabs.\n\n<!-- ctx-harness:begin -->\nold\n<!-- ctx-harness:end -->\n\n"
                          "## After\nKeep me.\n")
        self.assertIn("AGENTS.md: updated", self.repo.ctxh("init", "--target", "agents-md").stdout)
        text = agents.read_text()
        self.assertTrue(text.startswith("# House rules\n\nTabs.\n\n<!-- ctx-harness:begin -->\n## Repository"))
        self.assertTrue(text.endswith("<!-- ctx-harness:end -->\n\n## After\nKeep me.\n"))
        self.assertNotIn("\nold\n", text)

    def test_aider_config_with_its_own_read_list_is_left_alone(self):
        conf = self.repo.root / ".aider.conf.yml"
        conf.write_text("read:\n  - STYLE.md\n")
        out = self.repo.ctxh("init", "--target", "aider").stdout
        self.assertIn("add CONVENTIONS.md to it", out)
        self.assertEqual(conf.read_text(), "read:\n  - STYLE.md\n")

    def test_unknown_target_and_missing_ctx(self):
        r = self.repo.ctxh("init", "--target", "vim", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("agents-md|gemini|cursor|aider", r.stderr)
        bare = Repo()
        try:
            out = bare.ctxh("init", "--target", "gemini").stdout
            self.assertIn("no .ctx/ yet", out)
            self.assertFalse((bare.root / ".ctx").exists())
        finally:
            bare.cleanup()


try:
    import tree_sitter  # noqa: F401  (optional: CI's tree-sitter job installs it, the default job does not)
    HAVE_TREE_SITTER = True
except ImportError:
    HAVE_TREE_SITTER = False


class Parsers(unittest.TestCase):
    """Tree-sitter when installed, regexes otherwise; the graph says which one ran per language."""

    def test_regex_is_recorded_when_forced_or_unavailable(self):
        repo = Repo()
        try:
            python_app(repo)
            repo.ctxh("build-index", env={"CTXH_PARSER": "regex"})
            stack = json.loads((repo.root / ".ctx" / "graph.json").read_text())["stack"]
            self.assertEqual(stack["parsers"], {"python": "regex"})
        finally:
            repo.cleanup()

    @unittest.skipUnless(HAVE_TREE_SITTER, "tree_sitter is not installed")
    def test_tree_sitter_finds_what_regexes_miss(self):
        m = load_ctxh()
        py = "def outer():\n" + "            def deeply_nested():\n                pass\n" \
             + 'DOC = """\ndef not_code():\n"""\nfrom .pkg import (\n    a,\n)\nimport os.path as p\n'
        specs, symbols = m.ts_extract("python", "x.py", py)
        self.assertEqual(symbols, [["outer", 1], ["deeply_nested", 2]])  # nested kept, string content ignored
        self.assertEqual(specs, [".pkg", "os.path"])
        js = "import {\n  a,\n} from './a';\nconst b = require('./b');\nexport class Router {\n  route() {}\n}\n"
        specs, symbols = m.ts_extract("javascript", "x.js", js)
        self.assertEqual(specs, ["./a", "./b"])
        self.assertEqual(symbols, [["b", 4], ["Router", 5], ["route", 6]])  # methods too
        go = 'package x\n\nimport (\n\t"example.com/m/a"\n)\n\nfunc F() {\n\ttype key struct{}\n}\n'
        self.assertEqual(m.ts_extract("go", "x.go", go), (["example.com/m/a"], [["F", 7], ["key", 8]]))
        self.assertIsNone(m.ts_extract("kotlin", "x.kt", "fun f() {}"))  # no grammar: regex path


class KeywordSearch(unittest.TestCase):
    """`ctxh q search` and the `q find` fallback: concept words find code through names, comments, docstrings."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Repo()
        python_app(cls.repo)
        write(cls.repo.root, "app/payments/ledger.py", """
            # Every provider call carries a key derived from the order, so a retried
            # request never produces a double charge.
            def provider_key(order_id):
                return f"order:{order_id}"


            def settle(entries):
                \"\"\"Close the books for the day: sum the settlements per merchant.\"\"\"
                return sum(entries)
        """)
        write(cls.repo.root, "docs/ops.md", "# Operations\n\n## Rotating secrets\nKeys are rotated every quarter.\n")
        cls.repo.commit("ledger")
        cls.repo.ctxh("build-index")

    @classmethod
    def tearDownClass(cls):
        cls.repo.cleanup()

    def q(self, *args):
        return self.repo.ctxh("q", *args).stdout

    def test_terms_split_identifiers_and_stem(self):
        m = load_ctxh()
        self.assertEqual(m.terms("chargeOnce retry_policies HTTPServer charging"),
                         ["charg", "once", "retry", "policy", "http", "server", "charg"])
        self.assertEqual(m.terms("where is the"), [])

    def test_search_answers_from_comments_and_docstrings(self):
        self.assertTrue(self.q("search", "double", "charge").startswith("app/payments/ledger.py:3  provider_key"))
        self.assertTrue(self.q("search", "close", "books", "merchant").startswith("app/payments/ledger.py:7  settle"))
        self.assertTrue(self.q("search", "retry").startswith("app/common/retry.py:1  retry"))
        self.assertTrue(self.q("search", "rotating", "secrets").startswith("docs/ops.md:3  Rotating secrets"))
        self.assertIn("no keyword matches for 'zebra'", self.q("search", "zebra"))

    def test_find_falls_back_to_keywords_for_concepts(self):
        out = self.q("find", "double", "charge")
        self.assertTrue(out.startswith("keyword matches for 'double charge' (not a symbol name):\n"
                                       "app/payments/ledger.py:3"), out)
        self.assertEqual(self.q("find", "settle").strip(), "app/payments/ledger.py:7")  # a name still wins
        self.assertIn("no symbol matching 'zebra'", self.q("find", "zebra"))


class FakeRedis:
    """Just enough of a Redis server (RPUSH, LTRIM, LRANGE over RESP) to test the sink without one."""

    def __init__(self):
        import socketserver
        import threading
        lists = self.lists = {}

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                while True:
                    head = self.rfile.readline()
                    if not head:
                        return
                    words = []
                    for _ in range(int(head[1:])):
                        n = int(self.rfile.readline()[1:])
                        words.append(self.rfile.read(n + 2)[:-2].decode())
                    cmd, key, rest = words[0].upper(), words[1], words[2:]
                    if cmd in ("SELECT", "AUTH"):
                        self.wfile.write(b"+OK\r\n")
                        continue
                    items = lists.setdefault(key, [])
                    if cmd == "RPUSH":
                        items.extend(rest)
                        self.wfile.write(b":%d\r\n" % len(items))
                    elif cmd == "LTRIM":
                        lists[key] = items[int(rest[0]):][:None if int(rest[1]) == -1 else int(rest[1]) + 1]
                        self.wfile.write(b"+OK\r\n")
                    elif cmd == "LRANGE":
                        self.wfile.write(b"*%d\r\n" % len(items) + b"".join(
                            b"$%d\r\n%s\r\n" % (len(x.encode()), x.encode()) for x in items))

        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"redis://127.0.0.1:{self.server.server_address[1]}/0"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class FakeHTTPSink:
    """POST stores a trace, GET ?repo= lists them: the HTTP sink contract from the README."""

    def __init__(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from urllib.parse import parse_qs, urlparse
        store = self.store = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                store.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(204)
                self.end_headers()

            def do_GET(self):
                repo = parse_qs(urlparse(self.path).query).get("repo", [""])[0]
                body = json.dumps([t for t in store if t["repo"] == repo]).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/traces"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class SharedTraces(unittest.TestCase):
    """CTXH_TRACE_SINK: traces go to a shared store as well, and `ctxh signals` reads it back."""

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.git("remote", "add", "origin", "https://user:tok@github.com/acme/shop.git")
        self.repo.ctxh("build-index")
        self.tp = self.repo.root / "t.jsonl"
        transcript(self.tp, [("Read", {"file_path": str(self.repo.root / "app/common/retry.py")}),
                             ("Bash", {"command": "make tset"})])
        lines = self.tp.read_text().splitlines()
        result = json.loads(lines[3])
        result["message"]["content"][0].update(is_error=True, content="SECRET_TOKEN=abc in output")
        lines[3] = json.dumps(result)
        self.tp.write_text("\n".join(lines))

    def tearDown(self):
        self.repo.cleanup()

    def stop(self, session, sink):
        self.repo.ctxh("hook-stop", stdin=json.dumps({"session_id": session, "transcript_path": str(self.tp)}),
                       env={"CTXH_TRACE_SINK": sink, "CTXH_REVIEW_GATE": "0"})

    def check_sink(self, sink, stored):
        for s in ("s1", "s2", "s3"):
            self.stop(s, sink)
        items = stored()
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["repo"], "github.com_acme_shop")  # credentials stripped from the key
        self.assertEqual(items[0]["failed_commands"], [{"cmd": "make tset"}])  # command output never leaves
        self.assertNotIn("SECRET_TOKEN", json.dumps(items))
        local = json.loads((self.repo.root / ".ctx/traces/s1.json").read_text())
        self.assertIn("SECRET_TOKEN", json.dumps(local))  # local traces are unchanged
        for f in (self.repo.root / ".ctx/traces").glob("*.json"):
            f.unlink()  # as if these sessions ran on teammates' machines
        out = self.repo.ctxh("signals", env={"CTXH_TRACE_SINK": sink}).stdout
        self.assertIn("3 traces (3 from the shared sink)", out)
        self.assertIn("3x app/common/retry.py", out)
        self.assertIn("3x make tset", out)
        self.assertIn("no traces yet", self.repo.ctxh("signals").stdout)  # unset: local only, as before

    def test_directory_sink(self):
        d = Path(tempfile.mkdtemp(prefix="ctxh-sink-"))
        try:
            self.check_sink(str(d), lambda: [json.loads(p.read_text())
                                             for p in sorted((d / "github.com_acme_shop").glob("*.json"))])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_http_sink(self):
        srv = FakeHTTPSink()
        try:
            self.check_sink(srv.url, lambda: srv.store)
        finally:
            srv.close()

    def test_redis_sink(self):
        srv = FakeRedis()
        try:
            self.check_sink(srv.url, lambda: [json.loads(x) for x in srv.lists["ctxh:traces:github.com_acme_shop"]])
        finally:
            srv.close()

    def test_unreachable_sink_warns_and_keeps_local(self):
        r = self.repo.ctxh("hook-stop", stdin=json.dumps({"session_id": "x", "transcript_path": str(self.tp)}),
                           env={"CTXH_TRACE_SINK": "redis://127.0.0.1:1/0", "CTXH_REVIEW_GATE": "0"})
        self.assertIn("could not send the trace to CTXH_TRACE_SINK", r.stderr)
        self.assertTrue((self.repo.root / ".ctx/traces/x.json").exists())


class ToolLabels(unittest.TestCase):
    """Metrics carry the agent that produced them; gateway logs import usage for agents without transcripts."""

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.ctxh("build-index")

    def tearDown(self):
        self.repo.cleanup()

    def test_metrics_are_labeled_and_stats_group_by_tool(self):
        tp = self.repo.root / "t.jsonl"
        transcript(tp, [("Read", {"file_path": "app/common/retry.py"})])
        self.repo.ctxh("usage", str(tp), "--label", "harness", "--task", "t1")
        self.assertEqual(json.loads((self.repo.root / ".ctx/metrics/t.json").read_text())["tool"], "claude")
        log = self.repo.root / "gateway.jsonl"
        log.write_text("\n".join(json.dumps(x) for x in [
            {"metadata": {"session_id": "cx-1"}, "usage": {"prompt_tokens": 1000, "completion_tokens": 50,
                                                           "prompt_tokens_details": {"cached_tokens": 800}}},
            {"metadata": {"session_id": "cx-1"}, "usage": {"prompt_tokens": 1200, "completion_tokens": 70}},
            {"session_id": "cx-2", "input_tokens": 300, "output_tokens": 30, "cache_read_input_tokens": 100},
            {"usage": {"prompt_tokens": 5}},  # no session id: skipped
            "not json",
        ]))
        out = self.repo.ctxh("usage", "--gateway", str(log), "--tool", "codex", "--label", "baseline",
                             "--task", "t1").stdout
        self.assertIn("codex baseline t1 cx-1: 2320 tokens total (1520 uncached), 2 requests", out)
        m = json.loads((self.repo.root / ".ctx/metrics/cx-1.json").read_text())
        self.assertEqual((m["tool"], m["source"], m["steps"]), ("codex", "gateway", None))
        self.assertEqual(m["tokens_main"], {"input_tokens": 1400, "output_tokens": 120,
                                            "cache_read_input_tokens": 800, "cache_creation_input_tokens": 0})
        stats = self.repo.ctxh("stats").stdout
        self.assertIn("codex     baseline       2", stats)
        self.assertIn("claude    harness        1", stats)
        self.assertNotIn("paired tasks", stats)  # claude/harness vs codex/baseline is not a pair
        bad = self.repo.ctxh("usage", "--gateway", str(tp), "--tool", "codex", check=False)
        self.assertIn("carries a session id", bad.stderr)


class ReviewRecord(unittest.TestCase):
    """The opt-in review gate outside the agent: .ctx/reviews.json, review-check, the pre-commit hook."""

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.ctxh("build-index")
        self.repo.commit("ctx")
        self.svc = self.repo.root / "app/orders/service.py"

    def tearDown(self):
        self.repo.cleanup()

    def check(self, *args):
        return self.repo.ctxh("review-check", *args, check=False)

    def test_record_then_edit_again(self):
        self.svc.write_text(self.svc.read_text() + "# change\n")
        (self.repo.root / "README.txt").write_text("not code\n")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("  app/orders/service.py", r.stdout)
        self.assertNotIn("README.txt", r.stdout)
        self.assertIn("1 code files", self.repo.ctxh("review-record").stdout)
        self.assertEqual(self.check().returncode, 0)
        self.svc.write_text(self.svc.read_text() + "# again\n")
        self.assertEqual(self.check().returncode, 1)
        self.assertEqual(self.repo.ctxh("review-check", env={"CTXH_REVIEW_GATE": "0"}).returncode, 0)  # off switch

    def test_staged_and_base_modes_and_the_pre_commit_hook(self):
        self.assertIn("installed .git/hooks/pre-commit", self.repo.ctxh("review-check", "--install-hook").stdout)
        self.assertEqual(json.loads((self.repo.root / ".ctx/reviews.json").read_text()), {})
        self.repo.git("checkout", "-q", "-b", "feature")
        self.svc.write_text(self.svc.read_text() + "# change\n")
        self.repo.git("add", "-A")
        self.assertEqual(self.check("--staged").returncode, 1)
        blocked = subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-qm", "unreviewed"],
                                 cwd=self.repo.root, env=self.repo.env(), capture_output=True, text=True)
        self.assertNotEqual(blocked.returncode, 0)
        self.repo.ctxh("review-record", "app/orders/service.py")
        self.repo.commit("reviewed")  # passes the hook
        self.assertEqual(self.check("--base", "main").returncode, 0)
        self.svc.write_text(self.svc.read_text() + "# sneaky\n")
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "bypass")
        r = self.check("--base", "main")
        self.assertEqual(r.returncode, 1)
        self.assertIn("app/orders/service.py", r.stdout)

    def test_hook_refuses_to_overwrite_a_foreign_pre_commit(self):
        hook = self.repo.root / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nmake lint\n")
        r = self.repo.ctxh("review-check", "--install-hook", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(hook.read_text(), "#!/bin/sh\nmake lint\n")

    def test_stop_hook_records_after_a_reviewer_only_when_opted_in(self):
        self.svc.write_text(self.svc.read_text() + "# change\n")
        tp = self.repo.root / "t.jsonl"
        transcript(tp, [("Edit", {"file_path": str(self.svc)}), ("Task", {"subagent_type": "ctx-harness:reviewer"})])
        stop = lambda sid: self.repo.ctxh("hook-stop", stdin=json.dumps({"session_id": sid, "transcript_path": str(tp)}))
        stop("a")
        self.assertFalse((self.repo.root / ".ctx/reviews.json").exists())  # not opted in: nothing written
        (self.repo.root / ".ctx/reviews.json").write_text("{}\n")
        stop("b")
        self.assertEqual(self.check().returncode, 0)
        transcript(tp, [("Edit", {"file_path": str(self.svc)})])  # no reviewer after the edit: no record
        self.svc.write_text(self.svc.read_text() + "# more\n")
        stop("c")
        self.assertEqual(self.check().returncode, 1)


TOY_ADAPTER = """
import json
from pathlib import Path

NAME, LABEL = "toy", "Toy Agent"
TOOLS = {"read": ("view",), "edit": ("str_replace_editor",), "shell": ("run",), "subagent": ("delegate",)}
KIND_OF = {n: k for k, names in TOOLS.items() for n in names}


def project_dir():
    return None


def child_env(root):
    return {}


def read_event(stream):
    e = json.load(stream)
    return {"session": e.get("id"), "transcript": Path(e["log"]) if e.get("log") else None}


def emit_context(text):
    print("CTX:" + text)


def emit_block(reason):
    print("BLOCK:" + reason)


def read_session(path):
    calls = []
    for i, line in enumerate(path.read_text().splitlines()):
        tool, arg = line.split(" ", 1)
        calls.append({"id": str(i), "side": "main", "tool": tool, "kind": KIND_OF.get(tool), "path": arg,
                      "command": arg, "agent": arg, "error": False, "output": ""})
    return {"tool_version": "9", "assistant_messages": len(calls),
            "usage": [{"side": "main", "input_tokens": 10, "output_tokens": 5}], "calls": calls}
"""


class Adapters(unittest.TestCase):
    """The engine is tool-neutral: everything agent-specific comes from plugins/ctx-harness/adapters/."""

    def test_core_holds_no_claude_code_specifics(self):
        core = CTXH.read_text()
        for needle in ("CLAUDE_", "isSidechain", "tool_use", '"decision"', '"Bash"', '"Edit"', "subagent_type"):
            self.assertNotIn(needle, core)

    def test_unknown_adapter_names_the_available_ones(self):
        repo = Repo()
        try:
            r = repo.ctxh("version", env={"CTXH_TOOL": "nope"}, check=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("available: claude", r.stderr)
            self.assertIn("adapter: claude", repo.ctxh("version").stdout)
        finally:
            repo.cleanup()

    def test_another_adapter_drives_hooks_metrics_and_gates(self):
        repo = Repo()
        plugin = Path(tempfile.mkdtemp(prefix="ctxh-plugin-")) / "ctx-harness"
        try:
            shutil.copytree(CTXH.parents[1], plugin, ignore=shutil.ignore_patterns("__pycache__"))
            (plugin / "adapters" / "toy.py").write_text(TOY_ADAPTER)
            python_app(repo)
            repo.ctxh("build-index")
            log = repo.root / "toy.log"
            log.write_text(f"view app/orders/service.py\nstr_replace_editor {repo.root}/app/orders/service.py\n"
                           "run ctxh q find OrderService\n")
            run = lambda cmd, stdin="": subprocess.run(
                [sys.executable, str(plugin / "bin" / "ctxh"), cmd], cwd=repo.root, input=stdin, text=True,
                capture_output=True, env=repo.env({"CTXH_TOOL": "toy"}))
            self.assertTrue(run("hook-start", "{}").stdout.startswith("CTX:"))
            stop = run("hook-stop", json.dumps({"id": "toy1", "log": str(log)}))
            self.assertTrue(stop.stdout.startswith("BLOCK:ctx-harness review gate"), stop.stdout + stop.stderr)
            m = json.loads((repo.root / ".ctx" / "metrics" / "toy1.json").read_text())
            self.assertEqual((m["tokens_total"], m["steps"], m["tool_version"]), (15, 3, "9"))
            t = json.loads((repo.root / ".ctx" / "traces" / "toy1.json").read_text())
            self.assertEqual(t["files_edited"], ["app/orders/service.py"])
            self.assertEqual(t["ctx_queries"], ["ctxh q find OrderService"])
            log.write_text(log.read_text() + "delegate ctx-harness:reviewer\n")
            self.assertEqual(run("hook-stop", json.dumps({"id": "toy2", "log": str(log)})).stdout, "")
        finally:
            repo.cleanup()
            shutil.rmtree(plugin.parent, ignore_errors=True)


GEMINI = Path(__file__).parent / "fixtures" / "gemini"


class GeminiAdapter(unittest.TestCase):
    """Gemini CLI hooks (SessionStart, BeforeAgent, AfterAgent) on recorded payloads and a session log."""

    def setUp(self):
        self.repo = Repo()
        python_app(self.repo)
        self.repo.ctxh("build-index")
        self.chats = Path(tempfile.mkdtemp(prefix="ctxh-gemini-")) / "chats"
        self.log = self.chats / "session-2026-10-07T10-00-5f1c2a90.jsonl"
        sid = json.loads((GEMINI / "session.jsonl").read_text().splitlines()[0])["sessionId"]
        self.fill("session.jsonl", self.log)
        self.fill("subagent.jsonl", self.chats / sid / "sub-7a1.jsonl")

    def tearDown(self):
        self.repo.cleanup()
        shutil.rmtree(self.chats.parent, ignore_errors=True)

    def fill(self, name, dest=None):
        text = (GEMINI / name).read_text().replace("{ROOT}", str(self.repo.root)).replace("{TRANSCRIPT}", str(self.log))
        if dest:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
        return text

    def hook(self, cmd, payload):
        """Run a hook the way the settings.json block in the README does: adapter on the command line,
        root from GEMINI_PROJECT_DIR."""
        return self.repo.ctxh(cmd, "--tool", "gemini", stdin=self.fill(payload),
                              env={"GEMINI_PROJECT_DIR": str(self.repo.root)})

    def test_start_and_prompt_hooks_answer_with_one_json_object(self):
        start = json.loads(self.hook("hook-start", "session-start.json").stdout)
        self.assertIn("Working protocol", start["hookSpecificOutput"]["additionalContext"])
        prompt = json.loads(self.hook("hook-prompt", "before-agent.json").stdout)
        self.assertIn("run ctx-harness-reviewer", prompt["hookSpecificOutput"]["additionalContext"])

    def test_stop_hook_measures_the_session_and_gates_unreviewed_edits(self):
        stop = self.hook("hook-stop", "after-agent.json")
        out = json.loads(stop.stdout)
        self.assertEqual(out["decision"], "deny")
        self.assertIn("review gate", out["reason"])
        sid = json.loads(self.fill("after-agent.json"))["session_id"]
        m = json.loads((self.repo.root / ".ctx" / "metrics" / f"{sid}.json").read_text())
        # 4 model turns in the main log (the rewound one was still paid for) and 1 in the subagent log;
        # Gemini's input includes cached tokens and thoughts count as output.
        self.assertEqual((m["tokens_total"], m["tool"]), (1300 + 1460 + 1540 + 1630 + 550, "gemini"))
        self.assertEqual(m["tokens_main"]["cache_read_input_tokens"], 1000 + 1200 + 1400 + 1500)
        t = json.loads((self.repo.root / ".ctx" / "traces" / f"{sid}.json").read_text())
        self.assertEqual(t["files_edited"], ["app/orders/service.py", "notes.txt"])  # retry.py was rewound
        self.assertEqual(t["ctx_queries"], ["ctxh q find OrderService"])
        self.assertEqual(self.hook("hook-stop", "after-agent.json").stdout, "")  # blocks once per edit

        with self.log.open("a") as f:
            f.write(self.fill("review.jsonl"))
        fresh = {**json.loads(self.fill("after-agent.json")), "session_id": "another-session"}
        r = self.repo.ctxh("hook-stop", "--tool", "gemini", stdin=json.dumps(fresh),
                           env={"GEMINI_PROJECT_DIR": str(self.repo.root)})
        self.assertEqual(r.stdout, "")  # a new session would be blocked too, but the reviewer ran after the edit

    def test_legacy_single_json_session_file(self):
        msgs = [json.loads(l) for l in self.fill("session.jsonl").splitlines()]
        legacy = {**msgs[0], "messages": [m for m in msgs[1:] if "id" in m and m["id"] != "g4"]}
        self.log.write_text(json.dumps(legacy))
        self.assertEqual(json.loads(self.hook("hook-stop", "after-agent.json").stdout)["decision"], "deny")
        sid = msgs[0]["sessionId"]
        m = json.loads((self.repo.root / ".ctx" / "metrics" / f"{sid}.json").read_text())
        self.assertEqual(m["steps"], 4)


class Prompts(unittest.TestCase):
    """Agent and skill prompts are written once in prompts/ and generated per agent (`ctxh export`)."""

    def test_claude_files_are_generated_byte_identical(self):
        r = subprocess.run([sys.executable, str(CTXH), "export", "--tool", "claude", "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_gemini_export_is_a_complete_extension(self):
        out = Path(tempfile.mkdtemp(prefix="ctxh-gemini-ext-")) / "ctx-harness"
        repo = Repo()
        try:
            subprocess.run([sys.executable, str(CTXH), "export", "--tool", "gemini", "--out", str(out)], check=True,
                           capture_output=True)
            manifest = json.loads((out / "gemini-extension.json").read_text())
            self.assertEqual(manifest["name"], "ctx-harness")
            hooks = json.loads((out / "hooks" / "hooks.json").read_text())["hooks"]
            self.assertEqual(sorted(hooks), ["AfterAgent", "BeforeAgent", "SessionStart"])
            self.assertIn("hook-stop --tool gemini", hooks["AfterAgent"][0]["hooks"][0]["command"])
            agents = sorted(p.name for p in (out / "agents").iterdir())
            self.assertEqual(agents, ["ctx-harness-card-writer.md", "ctx-harness-planner.md",
                                      "ctx-harness-reviewer.md", "ctx-harness-scout.md"])
            scout = (out / "agents" / "ctx-harness-scout.md").read_text()
            self.assertIn("  - run_shell_command\n", scout)
            self.assertIn("Targeted grep_search, then read_file", scout)
            self.assertNotIn("write_file", scout)
            # Manual skills become commands only; build is also a model-invocable skill.
            self.assertEqual(sorted(p.name for p in (out / "skills").iterdir()), ["build"])
            build = (out / "skills" / "build" / "SKILL.md").read_text()
            self.assertIn("~/.gemini/policies/", build)
            self.assertNotIn(".claude/settings.json", build)
            self.assertIn("`ctx-harness-card-writer`", build)
            try:
                import tomllib
            except ImportError:
                tomllib = None
            for name in ("build", "curate", "status"):
                toml = (out / "commands" / "ctx-harness" / f"{name}.toml").read_text()
                if tomllib:
                    self.assertTrue(tomllib.loads(toml)["prompt"].startswith("#"))
            for p in out.rglob("*"):  # protocol.md stays a source: the engine fills it at hook time
                if p.is_file() and p.suffix in (".md", ".toml", ".json") and p.name != "protocol.md":
                    self.assertNotIn("{{", p.read_text(), p)
            # The extension carries its own engine, which names Gemini's agents at hook time.
            self.assertTrue(os.access(out / "bin" / "ctxh", os.X_OK))
            (repo.root / ".ctx").mkdir()
            r = subprocess.run([sys.executable, str(out / "bin" / "ctxh"), "hook-prompt", "--tool", "gemini"],
                               cwd=repo.root, input="{}", capture_output=True, text=True,
                               env=repo.env({"GEMINI_PROJECT_DIR": str(repo.root)}))
            ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("call ctx-harness-planner first", ctx)
            self.assertNotIn("run_in_background", ctx)  # a Claude Code tool parameter
            r = subprocess.run([sys.executable, str(out / "bin" / "ctxh"), "hook-start", "--tool", "gemini"],
                               cwd=repo.root, input="{}", capture_output=True, text=True,
                               env=repo.env({"GEMINI_PROJECT_DIR": str(repo.root)}))
            ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("`ctx-harness-reviewer`", ctx)
            self.assertNotIn("{{", ctx)
        finally:
            repo.cleanup()
            shutil.rmtree(out.parent, ignore_errors=True)

    def test_claude_hooks_still_name_claude_agents(self):
        repo = Repo()
        try:
            (repo.root / ".ctx").mkdir()
            self.assertIn("call ctx-harness:planner first", repo.ctxh("hook-prompt", stdin="{}").stdout)
            start = repo.ctxh("hook-start", stdin="{}").stdout
            self.assertIn("`ctx-harness:scout`", start)
            self.assertIn("`/ctx-harness:curate`", start)
        finally:
            repo.cleanup()


if __name__ == "__main__":
    unittest.main()
