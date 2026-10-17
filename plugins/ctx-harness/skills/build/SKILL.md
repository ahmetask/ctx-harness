---
name: build
description: Bootstraps ctx-harness context (.ctx/) in any repo: a deterministic index, then a short map. Use when asked to build, rebuild or initialize harness context, or after large refactors.
allowed-tools: Bash(ctxh *) Read Grep Glob
---
# Build repository context

Goal: the smallest context that saves more tokens than it costs. Everything an agent could cheaply rediscover stays out. Sessions pay for the map every time they start, so keep it short.

## 1. Deterministic index (no LLM tokens)
Run `ctxh build-index --verify`.
It creates `.ctx/` (this is what opts the repo in), scans tracked code files, resolves internal imports, ranks files by centrality, mines git history (churn, owners, co-change, fix/revert commits), detects build/lint/test commands from Makefiles, manifests and CI, and runs them to verify. Report the one-line summary it prints.

If a detected command fails, read its `tail` in `.ctx/commands.json`. Fix the invocation only if the cause is obvious (missing flag, wrong runner): record it with `ctxh add-command <kind> "<fixed cmd>" --replaces "<failing cmd>"`, which verifies it and keeps it across re-index. Otherwise leave it unverified. Never install software or change the repo to make a command pass.

If the index is dominated by fixtures, vendored samples or test data (`ctxh q hot` lists them), suggest a `.ctxignore` at the repo root (gitignore syntax) and re-run `ctxh build-index --verify`.

## 2. Map
Run `ctxh skeleton`, then turn `.ctx/map.draft.md` into `.ctx/map.md`:
- Fill each `TODO(llm)` purpose cell with one line. Base it on the module's central files (`ctxh q hot`, then read only the top file or two per module). Use the `ctx-harness:scout` agent for modules where that is not enough.
- Keep the generated sections. You may drop co-change or fragile lines that are noise, but do not invent new ones.
- Delete the draft. The map stays under 60 lines because it is injected into every session.

## 3. Cards (optional, off by default)
Skip this step unless the user asks for cards. On a large repo they measured no better than the map alone, and each is a file-by-file description that costs context every session. If asked: run `ctxh ready` (it lists the central modules with 3+ source files that lack a card), then invoke the `ctx-harness:card-writer` agent once per module, at most 5, in parallel when possible; each starts from `ctxh card-draft <module>` and only adds invariants.

## 4. Verify and prune
- Run `ctxh ready` and fix every `FAIL` line (it includes `ctxh check`). Treat each `warn` line as a question to settle, not noise: a `.ctxignore` for fixtures, an unverified test command, an uncommitted `.ctx/`.
- Only if you wrote cards, probe: write 3 questions a new engineer would ask about this repo whose answers you can confirm with `ctxh q` (where X is enforced, what breaks if Y changes, which tests cover Z). Ask the `ctx-harness:scout` agent each one. Wrong or low-confidence answers point to a missing or misleading card line: fix that line. Remove lines that no probe needed and that only restate code.

## 5. Permissions and sharing
- If `.claude/settings.json` does not allow `Bash(ctxh *)` and `mcp__plugin_ctx-harness_ctx` (the `ctx_query` tool this plugin provides), offer to add them under `permissions.allow`, so agents can query the index without an approval prompt each time.
- `.ctx/.gitignore` already excludes derived and per-machine files (graph.json, tmp, traces, metrics). Suggest committing the rest of `.ctx/` so the whole team shares the context. Do not commit unless the user asks.

## 6. Report
Summarize with the final `ctxh ready` output: files indexed, verified commands, map line count, anything left unverified (and cards written and probe results, if you wrote any).
