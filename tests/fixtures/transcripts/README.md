# Transcript fixtures

Token accounting (`ctxh usage`, `ctxh stats`) and the review gate both read Claude Code's
session transcript (`~/.claude/projects/<slug>/<session>.jsonl`). These files pin that format
so a change to it fails a test instead of silently zeroing metrics.

| File | What it pins |
|---|---|
| `session-edit.jsonl` | a normal session: `ctxh q` calls, a read, a subagent, a failed command, an empty-index query and an edit nobody reviewed. One assistant message is written twice (a stream retry), so usage must be deduplicated by `message.id`. |
| `session-edit/subagents/scout.jsonl` | the sibling directory newer versions write; its tokens count as `tokens_sub` and its reads stay out of `files_read`. |
| `session-reviewed.jsonl` | the same edit with a `ctx-harness:reviewer` call after it, so the Stop hook must not block. |
| `drift-no-usage.jsonl` | `usage` moved to another key: the parser must warn, not record zeros. |
| `drift-unknown-tools.jsonl` | tool names from another agent: tokens are still real, but traces and the gate are blind, so it warns. |

`__ROOT__` stands for the repo root; the tests replace it with the temporary repo they build, which
is how absolute-path handling gets covered. Keep it in any fixture you add.

Refreshing them: run a real session, copy its JSONL (and `subagents/` directory) here, replace the
repo path with `__ROOT__`, strip anything private, and update the expected numbers in
`tests/test_ctxh.py`. A fixture that no longer looks like a real transcript is worse than none.
