# T05 · Document the dogfooding setup

## Goal
Say, from observed behavior, which copy of the plugin runs when this repo's settings enable the published plugin and a contributor passes `--plugin-dir ./plugins/ctx-harness`, and how to run local changes without double hooks.

## Scope
- Measure on the current Claude Code: published only, published + `--plugin-dir`, and published disabled per session.
- README "Development": which copy runs, how to run local changes, how to refresh the cached release.
- `.claude/settings.json`: change only if the measurement shows a problem.

## Acceptance criteria
- The README states the behavior with the version it was checked on.
- No double hooks in the documented workflow.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Setup: a copy of the shopd sandbox with this repo's `.claude/settings.json`, marked trusted, with `ctx-harness@ctx-harness` installed at project scope from GitHub (the state a contributor reaches after accepting the trust prompt; `claude -p` alone does not install project-declared plugins). The local copy was a plugin copy with `LOCAL-COPY-MARKER` appended to `protocol.md` and to the scout agent's description. Each run was a `claude -p` with `CLAUDE_CODE_SESSION_ID` stripped, which nested sessions otherwise inherit and which makes runs share one transcript. Hook runs were counted from the transcript's `hook_success` attachments and `stop_hook_summary` entries.
- Results on Claude Code 2.1.292:
  - published only: 1 SessionStart injection (published protocol), 1 UserPromptSubmit, 1 Stop hook, published scout description, `command -v ctxh` = `~/.claude/plugins/cache/ctx-harness/ctx-harness/0.1.0/bin/ctxh`.
  - published + `--plugin-dir <local>`: 1 SessionStart injection (local protocol), 1 UserPromptSubmit, 1 Stop hook, local scout description, `command -v ctxh` = the local `bin/ctxh`.
  - `--settings '{"enabledPlugins":{"ctx-harness@ctx-harness":false}}'` with no `--plugin-dir`: no ctx-harness hooks, so the per-session disable works too, though it isn't needed.
- Decision: keep `.claude/settings.json` as is. `--plugin-dir` already replaces the installed copy cleanly, and a local directory marketplace would still install a cached copy that needs `claude plugin update` after each edit, which is worse for development.
- Review: reviewed the README text myself against the measurements (the reviewer subagent is not loaded in this cloud session).
- Verification: the measurements above; `python3 -m unittest discover -s tests` passes (no code change).
