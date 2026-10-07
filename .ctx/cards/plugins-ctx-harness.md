---
module: plugins/ctx-harness
updated: 2026-10-07
anchors:
  plugins/ctx-harness/bin/ctxh: e5914051ee7f
  plugins/ctx-harness/protocol.md: f1a70dd90a28
  plugins/ctx-harness/hooks/hooks.json: 4291e4081215
---
Owns the plugin: the `ctxh` engine (single stdlib Python file) and the prompts that drive agents around it.

Invariants in code:
- Repo root: `CLAUDE_PROJECT_DIR` wins, else nearest dir with `.ctx/`, else nearest `.git` (`find_root`).
- A repo is opted in only if `.ctx/` exists (`opted_in`); every hook is a no-op otherwise, so hooks never create files.
- Env vars are read through `env()`: `CTXH_*` first, legacy `CTX_*` accepted.
- `build-index` rewrites `commands.json` from `detect_commands` and keeps only earlier `verified` results for commands it re-detects; hand-added commands are dropped.
- `index_lag` and indexing consider only files whose suffix is in `LANGS`, so extensionless scripts (including `ctxh` itself) never trigger a re-index.
- Background re-index is guarded by .ctx/tmp/index.lock, treated as held for 600s.
- Review gate (`cmd_hook_stop`): blocks once per last code-edit tool_use id, state in .ctx/tmp/gates/<session>.json; a review is any `Task`/`Agent` call whose `subagent_type` ends in `reviewer`. Edits under `.ctx/` or to non-`LANGS` files do not count.
- A repo-level .ctx/protocol.md overrides the plugin `protocol.md` in `cmd_hook_start`.
- Metrics/traces keep the newest `KEEP_RECORDS` (300) files; traces are written only for `harness` runs.
- `ctxh check` limits: map 60 lines / 4000 bytes, card body 45 lines, learned 40 lines; flags `IMPERATIVE` phrasing and unfilled LLM placeholders from the skeleton.

Coupling to Claude Code (non-obvious):
- `parse_transcript` and `unreviewed_edit` read Claude JSONL fields (`usage`, `isSidechain`, `subagents/`) and tool names `Read`, `Edit`, `Write`, `Bash`, `Task`.
- Hook replies use Claude's formats: stdout is injected context, `{"decision":"block"}` stops finishing.

Tests: `tests/test_ctxh.py` (strips `CLAUDE_PROJECT_DIR` and `CTXH_*` from the env per run).
