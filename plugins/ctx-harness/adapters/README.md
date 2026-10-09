# Agent adapters

`bin/ctxh` is tool-neutral: the index, queries, cards, checks, stats and both Stop-hook gates never name a coding agent. Everything that depends on how an agent runs its hooks and writes its session log lives in one module here, picked by `CTXH_TOOL` (default `claude`).

| Adapter | Agent |
|---|---|
| `claude.py` | Claude Code |
| `gemini.py` | Gemini CLI (SessionStart, BeforeAgent and AfterAgent hooks; see the main README) |

## Interface

An adapter is a stdlib-only Python module that imports nothing from the engine. It defines:

| Name | What it is |
|---|---|
| `NAME`, `LABEL` | Adapter id (`ctxh version` prints it) and the agent's display name (used in drift warnings) |
| `TOOLS` | Tool names by role: `read`, `edit`, `shell`, `subagent`. Calls with a name outside these count as unknown, and a session where none is known triggers the drift warning |
| `project_dir()` | The repo root the agent hands its hooks, or `None` to let the engine search for `.ctx/` and `.git` |
| `child_env(root)` | Environment additions so the detached background re-index resolves the same root |
| `read_event(stream)` | A hook's stdin payload, as `{"session": id or None, "transcript": Path or None, "source": str or None}`; `None` if unreadable. `source` says why a session (re)started: `startup`, `resume`, `clear` or `compact` |
| `emit_context(text)` | How a start or prompt hook adds text to the model's context |
| `emit_block(reason)` | How the Stop hook refuses to finish and hands the agent the reason |
| `read_session(path)` | A session log as the normalized trace below, or `None` if there is no log at `path` |

Optional, for prompts (`ctxh export --tool <name>` and `render_prompt`; without them prompts get bare names and export refuses):

| Name | What it is |
|---|---|
| `AGENT_REF`, `COMMAND_REF` | Format strings for `{{agent:X}}` and `{{command:X}}` in prompts and hook messages, e.g. `"ctx-harness:{}"` |
| `PROMPT_TOOLS` | The tool name a prompt says for `{{tool:read}}`, `search`, `shell`, `write` |
| `render_agent(meta, body)` | `{path: text}` for one agent from `prompts/agents/` (`meta`: `name`, `description`, `tools` roles, `model` `fast` or `inherit`) |
| `render_skill(meta, body)` | `{path: text}` for one skill from `prompts/skills/` (`meta` also has `manual`: user-invoked only) |
| `package(plugin_root)` | Other files the agent installs, as `{path: text or source Path}` (Gemini: manifest, hooks, the engine) |
| `EXPORT_IN_PLACE` | `True` when export writes into the plugin itself (Claude Code); otherwise `--out` is required |

The normalized trace:

```python
{
  "tool_version": "2.0.14",        # agent version that wrote the log, "" if unknown
  "assistant_messages": 12,        # model turns seen, with or without usage
  "usage": [                       # one entry per model message, already deduplicated
    {"side": "main", "input_tokens": 0, "output_tokens": 0,
     "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
  ],
  "prompts": [                     # optional: the user's own messages, in order
    {"text": "no, tax is computed in pricing", "after": 7},   # after = number of calls made before it
  ],
  "calls": [                       # tool calls in first-seen order
    {"id": "…", "side": "main",    # "sub" for subagent work, which is not the session's own steps
     "tool": "Edit", "kind": "edit",   # kind is a TOOLS role, or None for an unmapped tool
     "path": "/abs/or/rel/file", "command": "", "agent": None,   # agent: subagent type for subagent calls
     "error": False, "output": "first 300 chars of the result"},
  ],
}
```

The gates key on `calls[].id` and look for subagent types ending in `planner` and `reviewer`, so an agent without subagents can still pass the review gate by reporting a reviewer run under that name.

## Adding one

1. Copy `claude.py` to `<tool>.py` and replace each piece from the agent's current hook and log documentation.
2. Point the agent's hooks at `ctxh hook-start`, `hook-prompt` and `hook-stop` with `--tool <tool>` (or `CTXH_TOOL=<tool>` in their environment).
3. Add recorded payloads and a session log under `tests/fixtures/`, and a test like `Adapters.test_another_adapter_drives_hooks_metrics_and_gates` in `tests/test_ctxh.py`.
