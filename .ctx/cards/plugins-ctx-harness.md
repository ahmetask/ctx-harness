---
module: plugins/ctx-harness
updated: 2026-10-07
anchors:
  plugins/ctx-harness/bin/ctxh: fc6095aa27a9
  plugins/ctx-harness/protocol.md: f1a70dd90a28
  plugins/ctx-harness/hooks/hooks.json: 4291e4081215
---
Owns the plugin: the `ctxh` engine (single stdlib Python file) and the prompts that drive agents around it.

Invariants in code:
- Repo root: `CLAUDE_PROJECT_DIR` wins, else nearest dir with `.ctx/`, else nearest `.git` (`find_root`).
- A repo is opted in only if `.ctx/` exists (`opted_in`); every hook is a no-op otherwise, so hooks never create files.
- Env vars are read through `env()`: `CTXH_*` first, legacy `CTX_*` accepted.
- `build-index` rewrites `commands.json` from `detect_commands`, keeps earlier `verified` results, and carries `source: manual` commands (from `add-command`) across re-index; `replaces` drops the detected command a manual one fixes.
- Indexing and `index_lag` use `lang_of`: a suffix in `LANGS`, else a known shebang on an extensionless file (so `ctxh` itself is indexed). `.ctxignore` and `SKIP_DIRS` exclude paths from both indexing and command detection.
- Background re-index is guarded by .ctx/tmp/index.lock, treated as held for 600s.
- Gates (`cmd_hook_stop`, both from one `session_edits` pass, both via `gate_once` keyed on the last code-edit tool_use id in .ctx/tmp/gates/<session>.json, so neither can loop): the plan gate runs first and blocks when `PLAN_GATE_FILES` (3) distinct code files changed with no non-empty plan at .ctx/tasks/active.md and no `planner` call; then the review gate, where a review is any subagent whose `subagent_type` ends in `reviewer`. Edits under `.ctx/` or to files `lang_of` does not recognize count for neither. `CTXH_DISABLED=1` skips both.
- A repo-level .ctx/protocol.md overrides the plugin `protocol.md` in `cmd_hook_start`.
- Metrics/traces keep the newest `KEEP_RECORDS` (300) files; traces are written only for `harness` runs.
- `ctxh check` limits: map 60 lines / 4000 bytes, card body 45 lines, learned 40 lines; flags `IMPERATIVE` phrasing and unfilled LLM placeholders from the skeleton.

Coupling to Claude Code (non-obvious):
- `parse_transcript` and `unreviewed_edit` read Claude JSONL fields (`usage`, `isSidechain`, `subagents/`); tool names live only in `TOOLS`. Usage is deduplicated by `message.id`, and only main-session tool calls count as steps.
- Format drift: `transcript_warning` + `warn_once` (state in .ctx/tmp/warnings.json) report a transcript with no `usage` or no known tool name; such a session is not recorded. Fixtures pin the format in `tests/fixtures/transcripts/`.
- Hook replies use Claude's formats: stdout is injected context, `{"decision":"block"}` stops finishing.

Tests: `tests/test_ctxh.py` (strips `CLAUDE_PROJECT_DIR` and `CTXH_*` from the env per run).
