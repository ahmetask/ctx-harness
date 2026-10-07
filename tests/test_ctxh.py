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


if __name__ == "__main__":
    unittest.main()
