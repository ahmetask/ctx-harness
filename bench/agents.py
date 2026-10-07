"""Agents the benchmark can drive.

Each agent prepares harness context once (bootstrap) and runs single tasks.
Both return an AgentResult whose transcript is in Claude Code's JSONL format,
so token accounting goes through the same parser as the plugin's Stop hook.

  claude  real `claude -p` runs; the harness mode loads the plugin from this checkout
  fake    offline: applies the reference solution and writes a synthetic transcript
  noop    offline: changes nothing; every check must fail (proves checks are not vacuous)
"""
import json
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

BENCH = Path(__file__).resolve().parent
PLUGIN_DIR = BENCH.parent / "plugins" / "ctx-harness"
CTXH = PLUGIN_DIR / "bin" / "ctxh"

# Appended to every task prompt in both modes: in -p mode nobody can approve a plan or answer a question.
HEADLESS_NOTE = ("\n\n(This is a non-interactive run: nobody will answer questions or approve plans. "
                 "Treat any plan as approved and carry the task through to the end.)")
ALLOWED_TOOLS = ["Bash", "Read", "Edit", "MultiEdit", "Write", "Grep", "Glob", "Task", "Agent", "TodoWrite"]


@dataclass
class AgentResult:
    transcript: Path | None
    seconds: float
    error: str = ""
    cost_usd: float | None = None
    num_turns: int | None = None
    extra: dict = field(default_factory=dict)


def clean_env(**overrides):
    """The caller's environment without harness switches, so runs don't inherit them."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CTXH_", "CTX_", "CLAUDE_PROJECT_DIR"))}
    # Launched from inside a Claude Code session, a child `claude` would otherwise reuse the parent's
    # session id, and find_transcript could pick the parent's transcript.
    for k in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_REMOTE_SESSION_ID"):
        env.pop(k, None)
    env.setdefault("GOTOOLCHAIN", "local")
    env.update(overrides)
    return env


def ctxh(repo: Path, *args, check=True):
    r = subprocess.run([sys.executable, str(CTXH), *args], cwd=repo, env=clean_env(), text=True,
                       capture_output=True, timeout=900)
    if check and r.returncode != 0:
        raise RuntimeError(f"ctxh {' '.join(args)} failed: {r.stderr or r.stdout}")
    return r.stdout


# ---------------------------------------------------------------- real runs
class ClaudeAgent:
    name = "claude"

    def __init__(self, model=None, review_gate=True, max_turns=False, claude_bin="claude", timeout=3600):
        self.model, self.review_gate, self.bin, self.timeout = model, review_gate, claude_bin, timeout
        self.max_turns = max_turns  # pass each task's turn limit as --max-turns (not every CLI build lists it)
        if not shutil.which(claude_bin):
            raise SystemExit(f"'{claude_bin}' not found on PATH; install Claude Code or use --agent fake")

    def bootstrap(self, repo: Path, scratch: Path) -> AgentResult:
        return self._invoke(repo, "/ctx-harness:build", "bootstrap", "bootstrap", 120, scratch)

    def run(self, repo: Path, task, mode: str, repeat: int, scratch: Path) -> AgentResult:
        return self._invoke(repo, task.prompt + HEADLESS_NOTE, mode, task.id, task.max_turns, scratch)

    def _invoke(self, repo, prompt, mode, label, max_turns, scratch):
        cmd = [self.bin, "-p", prompt, "--output-format", "json",
               "--permission-mode", "acceptEdits", "--allowedTools", ",".join(ALLOWED_TOOLS)]
        if self.max_turns:
            cmd += ["--max-turns", str(max_turns)]
        if self.model:
            cmd += ["--model", self.model]
        env = clean_env(CTXH_TASK=label)
        if mode in ("harness", "bootstrap"):
            cmd += ["--plugin-dir", str(PLUGIN_DIR)]
            env["PATH"] = f"{PLUGIN_DIR / 'bin'}{os.pathsep}{env.get('PATH', '')}"
            if not self.review_gate:
                env["CTXH_REVIEW_GATE"] = "0"
        else:
            env["CTXH_DISABLED"] = "1"  # inert even if the plugin is installed user-wide
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=repo, env=env, text=True, capture_output=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return AgentResult(None, time.time() - t0, error=f"timeout after {self.timeout}s")
        seconds = time.time() - t0
        out = _last_json(p.stdout)
        if out is None:
            return AgentResult(None, seconds, error=f"exit {p.returncode}: {(p.stderr or p.stdout)[-500:]}")
        transcript = find_transcript(out.get("session_id", ""))
        error = ""
        if out.get("is_error") or out.get("subtype") not in (None, "success"):
            error = f"{out.get('subtype')}: {str(out.get('result', ''))[:300]}"
        return AgentResult(transcript, seconds, error=error, cost_usd=out.get("total_cost_usd"),
                           num_turns=out.get("num_turns"), extra={"session_id": out.get("session_id")})


def _last_json(text):
    for line in reversed((text or "").strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    try:
        return json.loads(text)
    except ValueError:
        return None


def find_transcript(session_id: str):
    if not session_id:
        return None
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects"
    hits = sorted(base.glob(f"*/{session_id}.jsonl"))
    return hits[0] if hits else None


# ---------------------------------------------------------------- offline stand-ins
def write_transcript(path: Path, calls, sub_calls=(), tokens=(30_000, 2_000), rng=None):
    """Write a Claude Code style JSONL transcript.

    calls / sub_calls are (tool_name, input) pairs for the main session and for
    subagents (sidechain). tokens is (input-ish context per step, output per step);
    usage is spread over the steps with some noise.
    """
    rng = rng or random.Random(0)
    lines = []
    for side, seq in (("main", calls), ("sub", sub_calls)):
        for i, (name, inp) in enumerate(seq):
            ctx, out = tokens
            usage = {"input_tokens": int(ctx * 0.02 * rng.uniform(0.8, 1.2)),
                     "cache_read_input_tokens": int(ctx * (1 + i * 0.15) * rng.uniform(0.9, 1.1)),
                     "cache_creation_input_tokens": int(ctx * 0.05 * rng.uniform(0.8, 1.2)),
                     "output_tokens": int(out * rng.uniform(0.7, 1.3))}
            tid = f"{side}-{i}"
            lines.append({"type": "assistant", "isSidechain": side == "sub",
                          "message": {"id": f"msg-{tid}", "usage": usage,
                                      "content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}})
            lines.append({"type": "user", "isSidechain": side == "sub",
                          "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": "ok"}]}})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return path


def fake_bootstrap(repo: Path) -> None:
    """Deterministic part of the build skill, with placeholder purposes instead of an LLM."""
    ctxh(repo, "build-index", "--verify")
    ctxh(repo, "skeleton")
    draft = repo / ".ctx" / "map.draft.md"
    (repo / ".ctx" / "map.md").write_text(draft.read_text().replace("TODO(llm)", "demo module"))
    draft.unlink()


class FakeAgent:
    """Applies each task's reference solution and writes a plausible transcript.

    It exercises materialize -> context -> run -> check -> record -> report end to
    end without an API key. Harness runs get fewer, cheaper steps by construction,
    so its numbers say nothing about the real harness.
    """
    name = "fake"
    apply_solution = True

    def bootstrap(self, repo: Path, scratch: Path) -> AgentResult:
        t0 = time.time()
        fake_bootstrap(repo)
        calls = [("Bash", {"command": "ctxh build-index --verify"}), ("Bash", {"command": "ctxh skeleton"})]
        calls += [("Read", {"file_path": str(repo / f)}) for f in
                  ("internal/orders/service.go", "internal/pricing/pricing.go", "internal/payments/client.go")]
        calls += [("Write", {"file_path": str(repo / ".ctx/map.md")}), ("Bash", {"command": "ctxh check"})]
        sub = [("Read", {"file_path": str(repo / "internal/orders/state.go")})] * 6
        tr = write_transcript(scratch / "bootstrap.jsonl", calls, sub, tokens=(25_000, 3_000))
        return AgentResult(tr, time.time() - t0)

    def run(self, repo: Path, task, mode: str, repeat: int, scratch: Path) -> AgentResult:
        t0 = time.time()
        rng = random.Random(f"{task.id}/{mode}/{repeat}")
        touched = []
        if self.apply_solution and task.solution.is_dir():
            for src in sorted(p for p in task.solution.rglob("*") if p.is_file()):
                rel = src.relative_to(task.solution)
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, repo / rel)
                touched.append(rel.as_posix())
        size = 1 + len(touched)
        if mode == "harness":
            calls = [("Bash", {"command": f"ctxh q find {task.id.split('-')[1]}"})]
            calls += [("Read", {"file_path": str(repo / f)}) for f in touched[:2]]
            sub = [("Bash", {"command": "git diff HEAD"}), ("Read", {"file_path": str(repo / "go.mod")})]
            calls += [("Agent", {"subagent_type": "ctx-harness:reviewer", "prompt": "review HEAD"})]
            tokens = (int(22_000 * size ** 0.5), 1_500)
        else:
            calls = [("Grep", {"pattern": task.id.split("-")[1]}), ("Bash", {"command": "ls -R internal"})]
            calls += [("Read", {"file_path": str(repo / f)}) for f in
                      ["internal/orders/service.go", "internal/app/app.go", *touched]]
            sub = []
            tokens = (int(26_000 * size ** 0.5), 1_800)
        calls += [("Edit", {"file_path": str(repo / f)}) for f in touched]
        calls += [("Bash", {"command": "go test ./..."})] * rng.randint(1, 3)
        tr = write_transcript(scratch / f"{task.id}-{mode}-{repeat}.jsonl", calls, sub, tokens, rng)
        return AgentResult(tr, time.time() - t0)


class NoopAgent(FakeAgent):
    """Like FakeAgent but changes nothing, so every task check must fail."""
    name = "noop"
    apply_solution = False


def make_agent(name, model=None, review_gate=True, max_turns=False, timeout=3600):
    if name == "claude":
        return ClaudeAgent(model=model, review_gate=review_gate, max_turns=max_turns, timeout=timeout)
    if name == "fake":
        return FakeAgent()
    if name == "noop":
        return NoopAgent()
    raise SystemExit(f"unknown agent {name!r} (claude, fake, noop)")
