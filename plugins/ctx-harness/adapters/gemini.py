"""Gemini CLI adapter for ctxh: everything that knows how Gemini CLI talks to its hooks.

Built from Gemini CLI's hook reference (docs/hooks/reference.md) and its session recorder
(packages/core/src/services/chatRecordingService.ts and chatRecordingTypes.ts), main branch, 2026-10.
Hook mapping: SessionStart -> hook-start, BeforeAgent -> hook-prompt, AfterAgent -> hook-stop.
See adapters/README.md for the interface. Stdlib only; nothing here imports the engine.
"""
import json
import os
from pathlib import Path

NAME = "gemini"
LABEL = "Gemini CLI"

TOOLS = {
    "read": ("read_file", "read_many_files"),
    "edit": ("write_file", "replace"),
    "shell": ("run_shell_command",),
    "subagent": ("invoke_agent",),
}
KIND_OF = {name: kind for kind, names in TOOLS.items() for name in names}


def project_dir():
    """Gemini CLI sets GEMINI_PROJECT_DIR (and CLAUDE_PROJECT_DIR as an alias) for hooks."""
    return os.environ.get("GEMINI_PROJECT_DIR") or None


def child_env(root):
    return {"GEMINI_PROJECT_DIR": str(root)}


def read_event(stream):
    """A hook's stdin payload -> {"session", "transcript", "source"}, or None if unreadable.

    source (SessionStart only) is startup, resume or clear; Gemini CLI has no compaction start."""
    try:
        payload = json.load(stream)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    tp = payload.get("transcript_path")
    return {"session": payload.get("session_id"), "transcript": Path(tp).expanduser() if tp else None,
            "source": payload.get("source")}


def emit_context(text):
    """SessionStart and BeforeAgent: stdout must be one JSON object; the text goes in additionalContext."""
    print(json.dumps({"hookSpecificOutput": {"additionalContext": text}}))


def emit_block(reason):
    """AfterAgent: deny rejects the reply and Gemini retries with the reason as the next prompt."""
    print(json.dumps({"decision": "deny", "reason": reason}))


def _text(part):
    """Plain text from a tool result (a string, a Part, or a list of Parts)."""
    if isinstance(part, str):
        return part
    if isinstance(part, list):
        return " ".join(filter(None, (_text(p) for p in part)))
    if isinstance(part, dict):
        if isinstance(part.get("text"), str):
            return part["text"]
        resp = (part.get("functionResponse") or {}).get("response")
        if isinstance(resp, dict):
            return " ".join(str(resp[k]) for k in ("output", "error") if resp.get(k))
    return ""


def _records(path):
    """Replay a session file into ({id: final message}, [every message id ever written], metadata).

    JSONL: a metadata line, message records keyed by id (a later record with the same id replaces it),
    {"$set": {"messages": [...]}}, {"$patch": {...}} and {"$rewindTo": id}. The older format is one JSON
    ConversationRecord with "messages"."""
    text = path.read_text(errors="ignore")
    msgs, ever, meta = {}, {}, {}
    try:
        whole = json.loads(text)
    except ValueError:
        whole = None
    lines = [json.dumps(whole)] if isinstance(whole, dict) else text.splitlines()

    def put(m):
        if isinstance(m, dict) and isinstance(m.get("id"), str) and "type" in m:
            msgs[m["id"]] = m
            ever[m["id"]] = m

    def patch(p):
        m = msgs.get(p.get("id"))
        if not m:
            return
        if p.get("content") is not None:
            m["content"] = p["content"]
        for tp in p.get("toolCalls") or []:
            for tc in m.get("toolCalls") or []:
                if tc.get("id") == tp.get("id") and "result" in tp:
                    tc["result"] = tp["result"]

    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict):
            continue
        if "$rewindTo" in r:
            ids = list(msgs)
            cut = ids.index(r["$rewindTo"]) if r["$rewindTo"] in ids else 0
            for i in ids[cut:]:
                del msgs[i]
        elif isinstance(r.get("$patch"), dict):
            p = r["$patch"]
            patch(p)
            for u in p.get("updates") or []:
                if isinstance(u, dict):
                    patch(u)
            for i in p.get("removeIds") or []:
                msgs.pop(i, None)
            order = [i for i in p.get("orderIds") or [] if i in msgs]
            if order:
                rest = {i: m for i, m in msgs.items() if i not in order}
                msgs = {**rest, **{i: msgs[i] for i in order}}
        elif isinstance(r.get("$set"), dict):
            if isinstance(r["$set"].get("messages"), list):
                msgs.clear()
                for m in r["$set"]["messages"]:
                    put(m)
            meta.update({k: v for k, v in r["$set"].items() if k != "messages"})
        elif "id" in r and "type" in r:
            put(r)
        else:
            meta.update({k: v for k, v in r.items() if k != "messages"})
            for m in r.get("messages") or []:
                put(m)
    return msgs, list(ever.values()), meta


def read_session(path: Path):
    """A session file -> the normalized trace (see adapters/README.md), or None if there is none.

    Usage counts every model message ever written, rewound ones included, since those tokens were spent;
    calls come from the conversation as it stands. Gemini's input count includes cached tokens and its
    thought tokens are billed as output, so they are split and added to match the engine's fields.
    Subagent sessions are written to chats/<parent session id>/ next to the session file."""
    if not path.exists():
        return None
    usage, calls, seen = [], [], {"assistant": 0}

    def ingest(p, side):
        msgs, ever, meta = _records(p)
        if meta.get("kind") == "subagent":
            side = "sub"
        for m in ever:
            if m.get("type") != "gemini":
                continue
            seen["assistant"] += 1
            t = m.get("tokens") or {}
            if t:
                cached = t.get("cached") or 0
                usage.append({"side": side, "input_tokens": max((t.get("input") or 0) - cached, 0),
                              "output_tokens": (t.get("output") or 0) + (t.get("thoughts") or 0),
                              "cache_read_input_tokens": cached, "cache_creation_input_tokens": 0})
        for m in msgs.values():
            if m.get("type") != "gemini":
                continue
            for tc in m.get("toolCalls") or []:
                args, name = tc.get("args") or {}, tc.get("name")
                calls.append({
                    "id": tc.get("id"), "side": "sub" if tc.get("agentId") else side,
                    "tool": name, "kind": KIND_OF.get(name),
                    "path": args.get("file_path") or "", "command": args.get("command") or "",
                    "agent": args.get("agent_name"), "error": tc.get("status") == "error",
                    "output": _text(tc.get("result"))[:300],
                })
        return meta

    meta = ingest(path, "main")
    sid = meta.get("sessionId")
    subdir = path.parent / sid if isinstance(sid, str) and sid and "/" not in sid else None
    if subdir and subdir.is_dir():
        for p in sorted(subdir.glob("*.jsonl")):
            ingest(p, "sub")
    return {"tool_version": "", "assistant_messages": seen["assistant"], "usage": usage, "calls": calls}
