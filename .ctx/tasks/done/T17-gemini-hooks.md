# T17 · Hook adapter for Gemini CLI

## Goal
Automatic context injection, freshness notices, metrics and the plan and review gates work in a second agent, Gemini CLI, through the adapter interface from T13.

## Scope
- `adapters/gemini.py`, built from Gemini CLI's current hook reference and session-recording source (main branch, read 2026-10-07):
  - Hooks: SessionStart → `hook-start`, BeforeAgent → `hook-prompt`, AfterAgent → `hook-stop`. Context goes out as `hookSpecificOutput.additionalContext`; the gates answer `{"decision": "deny", "reason": ...}`, which makes Gemini retry with the reason as the next prompt.
  - Root: `GEMINI_PROJECT_DIR`.
  - Session log: JSONL records keyed by message id (metadata line, message records, `$set`, `$patch`, `$rewindTo`), plus the older single-JSON format. Token counts: `input` includes `cached`, and `thoughts` are output.
  - Subagents: `invoke_agent` calls (`agent_name`), and subagent logs under `chats/<session id>/`.
- `ctxh hook-start|hook-prompt|hook-stop --tool <name>`: Gemini runs hooks with a sanitized environment, so the adapter is picked on the command line.
- Recorded payloads and a session log under `tests/fixtures/gemini/`; tests for the hooks, metrics and both gates.
- README "Other agents" with the `.gemini/settings.json` hooks block; adapters README; card.

## Out of scope
- Gemini-format agent and skill prompts (T16). Until then, `hook-prompt` names `ctx-harness:planner` and `ctx-harness:reviewer`, which a Gemini user must define as subagents named `planner` and `reviewer`.
- Gemini has no compaction SessionStart (PreCompress is advisory), so the T08 resume note only fires on `resume`.

## Acceptance criteria
- With `--tool gemini`, the start and prompt hooks print a single JSON object with the context; the stop hook records metrics with the right token totals and steps, and denies once on an unreviewed code edit.
- A reviewer subagent run after the edit lets the session finish.
- Patches, removals and rewinds in the log are applied before counting.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Done: `adapters/gemini.py`, `adapter_name()` (`--tool` on hook commands; the background re-index inherits the adapter through `CTXH_TOOL`), fixtures in `tests/fixtures/gemini/`, `GeminiAdapter` tests, README section with the settings.json block, adapters README, card.
- Decision: `--tool` only on the hook commands. Gemini cleans the hook environment, so `CTXH_TOOL` cannot be set there, and `usage --gateway` already uses `--tool` as a metrics label.
- Decision: usage counts rewound turns (the tokens were spent), while calls come from the conversation as it stands, so a rewound edit does not trip the gates.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session).
- Verification: `python3 -m unittest discover -s tests` passes 72 tests (1 skipped without tree-sitter); `python3 bench/sandbox.py` smoke checks pass. Not run against a live Gemini CLI: there is no Gemini API key here, so the fixtures are assembled from the hook reference and the recorder source.
