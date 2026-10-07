# T14 · `ctxh init --target` instruction files for other agents

## Goal
One command points another coding agent at the harness: it writes the agent's own instructions file with a short, tool-neutral version of the protocol, so Codex, Copilot, Cursor, Gemini CLI or Aider read `.ctx/map.md` and query `ctxh q` before grepping.

## Scope
- `ctxh init --target agents-md|gemini|cursor|aider` (comma-separated for several):
  - `agents-md` -> `AGENTS.md` (Codex, GitHub Copilot's coding agent, and others that read it)
  - `gemini` -> `GEMINI.md`
  - `cursor` -> `.cursor/rules/ctx-harness.mdc` (a rule with `alwaysApply: true`; the file is ctxh's own)
  - `aider` -> `CONVENTIONS.md`, plus `read: CONVENTIONS.md` in `.aider.conf.yml` when that file has no `read:` key yet (otherwise it says what to add, rather than editing YAML it can't parse)
- The block sits between `<!-- ctx-harness:begin -->` / `<!-- ctx-harness:end -->`. Re-running replaces only the block, so text around it is kept, and a second run with no changes leaves the file untouched.
- Block content: read `.ctx/map.md` and any `.ctx/tasks/active.md` first; `ctxh q ...` before grep; the module card; plan to `.ctx/tasks/active.md` before 3+ files; verified commands; review the diff and run `ctxh stale` before finishing; leave map/cards/learned to the curator; how to get `ctxh` on PATH; a link to the full protocol. No Claude-only names (subagents, slash commands) as instructions.
- Not opted in yet (no `.ctx/`): still writes, and prints how to build the context.
- README "Other agents" section; engine docstring.

## Acceptance criteria
- Each target writes its file; a second run reports "unchanged" and the bytes are identical.
- Existing content outside the markers survives; an edited block is replaced.
- An unknown target fails with the list of targets.
- Aider: `.aider.conf.yml` gets `read: CONVENTIONS.md` when it has no `read:` key; with an existing `read:` key it is left alone and a note is printed.
- `python3 -m unittest discover -s tests` and `python3 bench/sandbox.py` pass.

## Steps
1. Block template + `cmd_init`.
2. Tests.
3. Docs and task status.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Steps 1-3 done: `INIT_TARGETS`, `INIT_BLOCK`, `upsert_block` and `cmd_init` in `bin/ctxh`; tests in `InitTargets`; README "Other agents"; card line.
- Decision: the block is a short, tool-neutral restatement of the protocol plus a link to the full one, not a copy of `protocol.md`. That file names Claude-only subagents and is injected by Claude's hook, and copying it into `.ctx/protocol.md` would turn it into a frozen override for Claude sessions too. T16 can later generate both from one source.
- Decision: Cursor gets a file of its own under `.cursor/rules/` with `alwaysApply: true` front matter. Aider's `.aider.conf.yml` is edited only when it has no `read:` key, because ctxh can't parse YAML with the stdlib; otherwise it prints what to add.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session). Checked that re-runs are byte-identical, that text outside the markers survives, and that `init` never creates `.ctx/`.
- Verification: `python3 -m unittest discover -s tests` passes 54 tests (50 before). `python3 bench/sandbox.py` smoke checks pass. Tried all four targets in a scratch repo, twice: the second run reported 4 x unchanged. Not tried inside the other agents themselves, since none is installed here.
