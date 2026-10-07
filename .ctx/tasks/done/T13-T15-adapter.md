# T13 + T15 · Tool-neutral core with a Claude Code adapter

## Goal
Everything Claude-specific in `ctxh` (where the project root comes from, hook payloads, the block reply, transcript parsing and tool names) moves behind one adapter, so the index, queries, cards, checks, stats and gates are tool-neutral and another agent needs only a new adapter file.

## Scope
- New `plugins/ctx-harness/adapters/claude.py`, stdlib only, imports nothing from `ctxh`. Interface (documented in `adapters/README.md`):
  - `NAME`, `LABEL`, `TOOLS` (read / edit / shell / subagent -> that tool's names; T15).
  - `project_dir()` and `child_env(root)`: the root the tool hands its hooks, and how a background re-index inherits it.
  - `read_event(stream)`: hook payload in, `{"session", "transcript"}` out.
  - `emit_context(text)` and `emit_block(reason)`: hook replies.
  - `read_session(path)`: transcript in, normalized trace out (`tool_version`, `assistant_messages`, deduplicated `usage` per main/sub side, ordered `calls` with `kind`, `path`, `command`, `agent`, `error`, `output`).
- `bin/ctxh` loads the adapter named by `CTXH_TOOL` (default `claude`) from `adapters/`. `parse_transcript` and `session_edits` work on the normalized trace; hooks use `read_event` / `emit_*`; `find_root` and `refresh_in_background` use `project_dir` / `child_env`. No `CLAUDE_*` name, JSONL field or Claude tool name stays in the core.
- Docs: engine docstring, README (environment table, engine section), the module card.

## Acceptance criteria
- `python3 -m unittest discover -s tests` passes with the tests unchanged (T13 "behavior and all tests unchanged").
- `grep -n "CLAUDE_\|isSidechain\|tool_use\|\"decision\"" bin/ctxh` finds nothing.
- `CTXH_TOOL=nope ctxh version` fails with the list of available adapters.
- `python3 bench/sandbox.py` smoke checks pass, and `bench/run.py --agent fake` still parses transcripts.
- Still one plugin, stdlib only.

## Risks
- Tests load `ctxh` as a module and set `m.ROOT`; core helpers must keep reading module globals, so the adapter gets no core state.
- Adapter load must work both when `ctxh` runs as a script and when imported by path (tests, bench): resolve it from `__file__`.

## Steps
1. Adapter file + loader.
2. Move transcript parsing behind `read_session`; rewrite `parse_transcript` / `session_edits` over normalized calls.
3. Hooks and root through the adapter.
4. Tests for the loader and the normalized trace; docs; task status.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md. T15 grouped in: once tool names come from the adapter, it is done.
- Steps 1-3 done: `adapters/claude.py` holds `TOOLS`, `project_dir`, `child_env`, `read_event`, `emit_context`, `emit_block` and `read_session`. `bin/ctxh` loads it via `load_adapter(CTXH_TOOL)` before computing `ROOT`; `parse_transcript` and `session_edits` read the normalized trace; hooks read events and reply through the adapter.
- Decision: one adapter module per agent, loaded by file path from `adapters/`, rather than a package. Tests and `bench/run.py` load `bin/ctxh` by path, and the plugin stays a copy-and-run directory.
- Decision: the adapter imports nothing from the engine and gets no core state, so tests that set `m.ROOT` keep working and an adapter can be tested alone.
- Small behavior change: a `NotebookEdit` now records its `notebook_path` in `files_edited` (it recorded "" before); the gate already did this.
- Step 4 done: `Adapters` tests (core has no Claude names, unknown adapter lists the available ones, a toy adapter with other tool names and log format drives hook-start, metrics, traces and both outcomes of the review gate). Docs in `adapters/README.md`, README, the module card.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session). Checked the main/sub split and dedup match the old parser (fixture token counts unchanged), `CTXH_DISABLED` paths, and that an unreadable hook payload still exits quietly. No findings.
- Verification: `python3 -m unittest discover -s tests` passes 47 tests (44 before, existing ones unchanged). `python3 bench/sandbox.py` smoke checks pass; two live `--prompt` sessions recorded metrics through the adapter, and the edit session hit the review gate once (`.ctx/tmp/gates/<session>.json` holds `blocked_edit`). `bench/run.py --agent fake` parses its transcripts.
