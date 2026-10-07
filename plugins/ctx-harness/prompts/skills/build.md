---
name: build
description: Bootstraps ctx-harness repository context (.ctx/) from zero, in any repo and language. Use when the user asks to build, rebuild, or initialize harness context, when the session start says this repo has no harness context and the user wants it, or after large refactors. Deterministic indexing first, LLM only for what code analysis cannot say.
tools: ctxh, read, search
---
# Build repository context

Goal: the smallest context that saves more tokens than it costs. Everything an agent could cheaply rediscover stays out.

## 1. Deterministic index (no LLM tokens)
Run `ctxh build-index --verify`.
It creates `.ctx/` (this is what opts the repo in), scans tracked code files, resolves internal imports, ranks files by centrality, mines git history (churn, owners, co-change, fix/revert commits), detects build/lint/test commands from Makefiles, manifests and CI, and runs them to verify. Report the one-line summary it prints.

If a detected command fails, read its `tail` in `.ctx/commands.json`. Fix the invocation only if the cause is obvious (missing flag, wrong runner): record it with `ctxh add-command <kind> "<fixed cmd>" --replaces "<failing cmd>"`, which verifies it and keeps it across re-index. Otherwise leave it unverified. Never install software or change the repo to make a command pass.

If the index is dominated by fixtures, vendored samples or test data (`ctxh q hot` lists them), suggest a `.ctxignore` at the repo root (gitignore syntax) and re-run `ctxh build-index --verify`.

## 2. Map
Run `ctxh skeleton`, then turn `.ctx/map.draft.md` into `.ctx/map.md`:
- Fill each `TODO(llm)` purpose cell with one line. Base it on the module's central files (`ctxh q hot`, then read only the top file or two per module). Use the `{{agent:scout}}` agent for modules where that is not enough.
- Keep the generated sections. You may drop co-change or fragile lines that are noise, but do not invent new ones.
- Delete the draft. The map stays under 60 lines because it is injected into every session.

## 3. Cards for central modules only
Pick the top modules by centrality, at most 5, skipping ones with fewer than about 3 source files. Invoke the `{{agent:card-writer}}` agent once per module, in parallel when possible. Smaller modules get no card; the index and the code are enough.

## 4. Verify and prune
- Run `ctxh check` and fix everything it reports.
- Probe: write 5 questions a new engineer would ask about this repo whose answers you can confirm with `ctxh q` (where X is enforced, what breaks if Y changes, which tests cover Z). Ask the `{{agent:scout}}` agent each one. Wrong or low-confidence answers point to a missing or misleading card line: fix that line. Remove lines that no probe needed and that only restate code.

## 5. Permissions and sharing
{{only:claude}}- If `.claude/settings.json` does not allow `Bash(ctxh *)`, offer to add it under `permissions.allow`, so agents can query the index without an approval prompt each time.
{{only:gemini}}- If Gemini CLI asks before each `ctxh` call, offer to add a policy rule (a `.toml` file in `~/.gemini/policies/`: `[[rule]]` with `commandPrefix = "ctxh"`, `decision = "allow"`), so agents can query the index without an approval prompt each time.
- `.ctx/.gitignore` already excludes derived and per-machine files (graph.json, tmp, traces, metrics). Suggest committing the rest of `.ctx/` so the whole team shares the context. Do not commit unless the user asks.

## 6. Report
Summarize: files indexed, verified commands, map line count, cards written, probe results, anything left unverified.
