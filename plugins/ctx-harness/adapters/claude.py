"""Claude Code adapter for ctxh: everything that knows how Claude Code talks to its hooks.

The engine (bin/ctxh) is tool-neutral. It asks this module where the project root is, what a hook
event carries, how to answer it, and what a session transcript says, and gets plain data back.
See adapters/README.md for the interface. Stdlib only; nothing here imports the engine.
"""
import json
import os
from pathlib import Path

NAME = "claude"
LABEL = "Claude Code"

# Tool names by role. The engine counts reads, edits, shell commands and subagent calls by role,
# so another agent's adapter maps its own names here and the gates and traces work unchanged.
TOOLS = {
    "read": ("Read", "NotebookRead"),
    "edit": ("Edit", "Write", "MultiEdit", "NotebookEdit"),
    "shell": ("Bash",),
    "subagent": ("Task", "Agent"),
}
KIND_OF = {name: kind for kind, names in TOOLS.items() for name in names}

# How prompts name things (bin/ctxh render_prompt fills {{agent:X}}, {{command:X}} and {{tool:ROLE}}).
AGENT_REF = "ctx-harness:{}"
COMMAND_REF = "/ctx-harness:{}"
PROMPT_TOOLS = {"read": "Read", "search": "Grep", "shell": "Bash", "write": "Write"}
EXPORT_IN_PLACE = True  # the plugin directory is what Claude Code installs: export writes agents/ and skills/ there

USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def project_dir():
    """The repo root Claude Code hands to hooks and plugin commands, or None."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or None


def child_env(root):
    """Environment additions so a detached re-index resolves the same root."""
    return {"CLAUDE_PROJECT_DIR": str(root)}


def read_event(stream):
    """A hook's stdin payload -> {"session", "transcript", "source", "prompt"}, or None if unreadable.

    source is why a session started: startup, resume, clear or compact (SessionStart only, else None)."""
    try:
        payload = json.load(stream)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    tp = payload.get("transcript_path")
    return {"session": payload.get("session_id"), "transcript": Path(tp).expanduser() if tp else None,
            "source": payload.get("source"),
            "prompt": payload.get("prompt")}


def emit_context(text):
    """SessionStart / UserPromptSubmit: stdout is added to the model's context."""
    print(text)


def emit_block(reason):
    """Stop: this reply keeps the session going with the reason as its next instruction."""
    print(json.dumps({"decision": "block", "reason": reason}))


def read_session(path: Path):
    """A session transcript -> the normalized trace the engine works on, or None if there is none.

    {"tool_version": str, "assistant_messages": int,
     "usage": [{"side": "main"|"sub", <USAGE_KEYS>: int}, ...]   one per model message, deduplicated,
     "calls": [{"id", "side", "tool", "kind", "path", "command", "agent", "error", "output"}, ...],
     "prompts": [{"text", "after"}, ...]   the user's own messages; after = number of calls before it}
    calls are in first-seen order; kind is a TOOLS role or None for a tool this adapter doesn't map.
    Subagent transcripts (a sibling <session>/subagents/ directory, or sidechain entries) are side "sub".
    """
    if not path.exists():
        return None
    usage, calls, results, prompts = {}, {}, {}, []
    seen = {"assistant": 0, "version": ""}

    def ingest(p, bucket):
        for line in p.read_text(errors="ignore").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            msg = e.get("message") or {}
            content = msg.get("content") if isinstance(msg.get("content"), list) else []
            side = bucket if bucket == "sub" or not e.get("isSidechain") else "sub"
            if e.get("version"):
                seen["version"] = str(e["version"])
            if e.get("type") == "user" and side == "main" and not e.get("isMeta") and msg.get("role") == "user":
                text = msg["content"] if isinstance(msg.get("content"), str) else " ".join(
                    c.get("text", "") for c in content if c.get("type") == "text")
                text = text.strip()
                if text and not text.startswith(("<", "This session is being continued")):  # harness wrappers, summaries
                    prompts.append({"text": text, "after": len(calls)})
            if e.get("type") == "assistant":
                seen["assistant"] += 1
                if msg.get("usage"):  # a stream retry writes the same message twice: key on its id
                    usage[(side, msg.get("id") or e.get("uuid"))] = msg["usage"]
            for c in content:
                if c.get("type") == "tool_use":
                    name, inp = c.get("name"), c.get("input") or {}
                    calls[c.get("id")] = {
                        "id": c.get("id"), "side": side, "tool": name, "kind": KIND_OF.get(name),
                        "path": inp.get("file_path") or inp.get("notebook_path") or "",
                        "command": inp.get("command", ""), "agent": inp.get("subagent_type"),
                    }
                elif c.get("type") == "tool_result":
                    body = c.get("content")
                    if isinstance(body, list):
                        body = " ".join(x.get("text", "") for x in body if isinstance(x, dict))
                    results[c.get("tool_use_id")] = (bool(c.get("is_error")), str(body or "")[:300])

    ingest(path, "main")
    subdir = path.with_suffix("") / "subagents"
    if subdir.is_dir():
        for p in subdir.glob("*.jsonl"):
            ingest(p, "sub")
    for cid, call in calls.items():
        call["error"], call["output"] = results.get(cid, (False, ""))
    return {
        "tool_version": seen["version"], "assistant_messages": seen["assistant"],
        "usage": [{"side": side, **{k: u.get(k) or 0 for k in USAGE_KEYS}} for (side, _), u in usage.items()],
        "calls": list(calls.values()),
        "prompts": prompts,
    }


AGENT_TOOLS = {"read": "Read", "search": "Grep, Glob", "shell": "Bash", "write": "Write"}
SKILL_TOOLS = {"ctxh": "Bash(ctxh *)", "read": "Read", "search": "Grep Glob", "shell": "Bash"}
MODELS = {"fast": "haiku", "inherit": "inherit"}


def render_agent(meta, body):
    """A neutral agent prompt -> {path in the plugin: Claude Code subagent file}."""
    head = (f"name: {meta['name']}\ndescription: {meta['description']}\n"
            f"tools: {', '.join(AGENT_TOOLS[t] for t in meta['tools'])}\nmodel: {MODELS[meta.get('model', 'inherit')]}\n")
    return {f"agents/{meta['name']}.md": f"---\n{head}---\n{body}"}


def render_skill(meta, body):
    """A neutral skill prompt -> {path in the plugin: SKILL.md}; manual skills are slash commands only."""
    head = f"name: {meta['name']}\ndescription: {meta['description']}\n"
    if meta["manual"]:
        head += "disable-model-invocation: true\n"
    head += f"allowed-tools: {' '.join(SKILL_TOOLS[t] for t in meta['tools'])}\n"
    return {f"skills/{meta['name']}/SKILL.md": f"---\n{head}---\n{body}"}
