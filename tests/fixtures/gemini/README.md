Gemini CLI hook payloads and a session log for `Adapters` tests in `tests/test_ctxh.py`.

Assembled from Gemini CLI's hook reference (`docs/hooks/reference.md`) and its session recorder (`packages/core/src/services/chatRecordingService.ts`, `chatRecordingTypes.ts`) on the main branch, October 2026, not captured from a live run. `{ROOT}` and `{TRANSCRIPT}` are filled in by the test.

- `session.jsonl`: a main session with a rewritten message (same id twice), a `$patch` that fills a tool result, and a `$rewindTo` that drops the last turn.
- `subagent.jsonl`: a subagent log, which Gemini writes to `chats/<parent session id>/`.
- `review.jsonl`: one more turn that calls the `reviewer` subagent through `invoke_agent`.
