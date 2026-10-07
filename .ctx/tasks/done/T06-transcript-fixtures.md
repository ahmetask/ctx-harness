# T06 · Transcript parser fixtures and version guard

## Goal
Make the dependency on Claude Code's transcript JSONL format visible and testable: checked-in fixtures pin the parse, and a format change says so instead of silently recording zeros and disabling the review gate.

## Scope
- `tests/fixtures/transcripts/`: checked-in JSONL in Claude Code's real shape (`type`, `message.id`, `message.usage`, `tool_use`/`tool_result`, `isSidechain`, a `subagents/` directory).
  - `session-edit.jsonl` (+ `session-edit/subagents/scout.jsonl`): main session with reads, a `ctxh q`, a subagent, a failed command, an empty-index query and an unreviewed edit.
  - `session-reviewed.jsonl`: the same edit with a `ctx-harness:reviewer` call after it.
  - `drift-no-usage.jsonl`: known tool names, `usage` moved under another key.
  - `drift-unknown-tools.jsonl`: usage intact, tool names renamed.
  - `__ROOT__` in file paths is replaced with the test repo path, so absolute-path handling is covered.
- `plugins/ctx-harness/bin/ctxh`:
  - `TOOLS`/`KNOWN_TOOLS`: the Claude tool-name mapping (read, edit, shell, subagent) in one place, used by `parse_transcript` and `unreviewed_edit` (groundwork for T15).
  - `parse_transcript` also returns `assistant_messages`, `usage_messages`, `known_tool_calls`, `unknown_tools`, `tool_version`.
  - `transcript_warning(data)`: the one sentence saying what did not parse.
  - `warn_once(kind, message)`: stderr, once per state, in `.ctx/tmp/warnings.json`.
  - Stop hook: warn once, record metrics only when usage was found (no zero rows), gate unchanged.
  - `ctxh usage`: exit non-zero with the warning when there is no usage (an explicit invocation should fail loudly); warn once and still record when only the tool names are unrecognized.
  - Metrics records carry `tool_version`.
- README: a line in the measurement section about the guard and the fixtures.

## Acceptance criteria
- Fixture tests assert exact `tokens_total`, `tokens_uncached`, `steps`, `files_read`, `files_edited`, `commands`, `failed_commands`, `ctx_queries`, `ctx_misses`, `subagents` and the gate decision (block, then pass after a reviewer run).
- A transcript with no `usage` makes the Stop hook warn once and write no metrics file; a second identical run is silent.
- A transcript with unrecognized tool names warns once, still records tokens, and does not block.
- `ctxh usage` on an unparseable transcript exits non-zero with the reason.
- `python3 -m unittest discover -s tests` passes.

## Risks
- Fixtures drift from the real format over time: they are a snapshot, so the README says to refresh them from a real session when Claude Code's format changes. A stale fixture that still parses is the cost of the guard.
- Not recording zero-token sessions slightly changes `ctxh stats` input (a broken session no longer counts as a run). That is the intent.

## Steps
1. Fixtures + loader helper in the tests.
2. Tool-name constants and the extra parse fields.
3. `transcript_warning` / `warn_once`, wired into `cmd_usage` and `cmd_hook_stop`.
4. Tests, README, task statuses.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Step 1 done: four fixtures plus `session-edit/subagents/scout.jsonl`, in Claude Code's real entry shape (`parentUuid`, `sessionId`, `version`, `requestId`, `toolUseResult`). `session-edit` also repeats one assistant line, the way a stream retry does, so the id-keyed usage dedupe is covered.
- Step 2 done: `TOOLS`/`KNOWN_TOOLS` replace the inline tool-name tuples in `parse_transcript` and `unreviewed_edit`; the parser also returns `assistant_messages`, `usage_messages`, `known_tool_calls`, `unknown_tools` and `tool_version` (the Claude Code version the transcript was written by, now also stored on each metrics record).
- Step 3 done: `transcript_warning` names the drift and `warn_once` keeps it to one line per state in `.ctx/tmp/warnings.json`. The Stop hook warns and skips the record when no usage parsed; it still records tokens when only the tool names are foreign (the numbers are real, the traces and the gate are not). `ctxh usage` exits non-zero in the no-usage case, since an explicit invocation should not be silent.
- Decision: tool names are centralized but not yet injectable. The adapter seam is T13/T15; this only removes the duplication so that change stays small.
- Review: reviewed the diff myself (the `ctx-harness:reviewer` subagent is not loaded in this cloud session). Checked that `steps` is still main-session-only, that unknown names are counted main-side only, and that a sidechain read stays out of `files_read`. No findings.
- Verification: `python3 -m unittest discover -s tests` passes 37 tests (32 before). `ctxh usage` on `drift-no-usage.jsonl` exits 1 and writes no metrics; the second Stop-hook run on it is silent.
