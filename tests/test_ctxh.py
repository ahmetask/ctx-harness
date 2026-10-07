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


if __name__ == "__main__":
    unittest.main()
