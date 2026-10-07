# T18 · Tool label and vendor-neutral token counting

## Goal
Record which agent produced each metric, compare harness and baseline within one agent, and count tokens for agents whose own logs don't expose usage.

## Scope
- `record(..., tool=None)`: every metric record gets `tool` (the adapter's `NAME`, or an explicit one) and `source` when it isn't a transcript.
- `ctxh stats`: rows by (tool, label); paired tasks only within a tool (prefixed `tool/` when several tools are paired). Records written before this change have no `tool` and count as `claude`, since only the Claude adapter existed.
- `ctxh usage --gateway <requests.jsonl> --tool <agent> [--label] [--task]`: sums per-request usage by session id from a gateway's JSONL export. Accepts Anthropic names and OpenAI names; with OpenAI names, cached tokens are subtracted from `prompt_tokens`, because there they are a subset. Steps are unknown (`None`, shown as `-`).
- README section; card.

## Acceptance criteria
- A transcript import is labeled `claude`; a gateway import with `--tool codex` is labeled `codex` with `source: gateway`.
- Mixed Anthropic and OpenAI lines sum correctly per session; lines without a session id are skipped; a log with none fails loudly.
- `stats` shows one row per tool and label, and doesn't pair across tools.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Done: `record` tool/source fields, `gateway_sessions` + `GATEWAY_KEYS`, `usage --gateway`, tool-aware `stats`, `ToolLabels` test, README and card.
- Decision: a generic JSONL contract with field aliases instead of an adapter per gateway. Gateway export formats differ and change; the documented field names cover the Anthropic and OpenAI usage objects that gateways pass through, and anything else maps to them with a one-line `jq`.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session). Caught the OpenAI cached-token double count while writing the test (cached tokens are inside `prompt_tokens`).
- Verification: `python3 -m unittest discover -s tests` passes 69 tests (1 skipped without tree-sitter); `python3 bench/sandbox.py` smoke checks pass. Not run against a real gateway log here.
