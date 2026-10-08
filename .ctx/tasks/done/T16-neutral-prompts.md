# T16 · Tool-neutral agent and skill prompts

## Goal
Write the scout, planner, reviewer and card-writer agents and the build, curate and status skills once, and generate each agent's own files from them: Claude Code's (byte-identical to today's) and Gemini CLI's.

## Scope
- Sources in `plugins/ctx-harness/prompts/agents/` and `prompts/skills/`: neutral front matter (`name`, `description`, `tools` as roles, `model: fast|inherit`, `manual` for skills) and bodies with placeholders: `{{agent:X}}`, `{{command:X}}`, `{{tool:ROLE}}`, and lines prefixed `{{only:TOOL}}` that only one tool gets.
- Engine: `render_prompt(text)` fills placeholders from the adapter (`AGENT_REF`, `COMMAND_REF`, `PROMPT_TOOLS`, defaults when an adapter has none). The protocol and the engine's own hook messages go through it, so Gemini sessions hear `ctx-harness-planner` instead of `ctx-harness:planner`.
- `ctxh export --tool <name> [--out DIR] [--check]`: renders every source through the adapter's `render_agent` / `render_skill` and writes the adapter's `package()` files. Claude writes into the plugin itself; `--check` fails when the committed files differ (tests run it).
- Gemini adapter: agents as `agents/ctx-harness-<name>.md` (Gemini subagent front matter), skills as `skills/<name>/SKILL.md` unless manual, a `commands/ctx-harness/<name>.toml` per skill (so `/ctx-harness:build` works the same), plus `gemini-extension.json`, `hooks/hooks.json` and copies of `bin/ctxh`, `adapters/`, `protocol.md`: a complete extension for `gemini extensions link`.
- README, adapters README, card, tasks.md.

## Acceptance criteria
- `ctxh export --tool claude --check` passes on the committed agents and skills (byte-identical).
- `ctxh export --tool gemini --out DIR` writes a valid extension: JSON parses, TOML parses (`tomllib`), front matter has the fields Gemini's docs require, and no `{{` placeholder survives.
- Claude's hook-start and hook-prompt output is unchanged; with `--tool gemini` they name `ctx-harness-planner` and `ctx-harness-reviewer`.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Done: neutral sources in `prompts/` (generated from today's files, then placeholders), `render_prompt`, `prompt_sources`, `cmd_export`; Claude adapter `render_agent`/`render_skill`; Gemini adapter `render_agent`/`render_skill`/`package`; protocol and engine hook/gate messages rendered per adapter; `Prompts` tests; CI steps (`export --tool claude --check`, `gemini extensions validate`); README, adapters README, card.
- Decision: Gemini agents are `ctx-harness-<name>` (subagent names allow no colon; the prefix avoids clashes, and the gates' `endswith("reviewer")` still matches). Skills become `/ctx-harness:<name>` commands (Gemini namespaces extension commands by folder) and, unless manual, agent skills. `model: fast` is not pinned for Gemini: model ids change too often.
- Decision: the Gemini extension is generated on demand (`--out`), not committed, so the engine is not duplicated in the repo.
- Live check (Gemini CLI 0.63.0, installed locally): `gemini extensions validate` passes; `extensions link` loads it with the `build` skill; a `gemini -p` run in the sandbox repo with a fake API key fired the extension's SessionStart and BeforeAgent hooks, and the prompt Gemini recorded carries the protocol and the prompt-hook line naming `ctx-harness-planner`/`ctx-harness-reviewer`. The captured payloads and the session file's opening records match the T17 fixtures. AfterAgent did not fire (the model call failed).
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session). Claude output: `export --tool claude --check` byte-identical, rendered protocol identical to the old file, `claude plugin validate` passes.
- Verification: `python3 -m unittest discover -s tests` passes 75 tests (1 skipped without tree-sitter); `python3 bench/sandbox.py` smoke checks pass.
