# T08 · Mid-session context management (compaction)

## Goal
A session that gets compacted mid-task resumes from its plan: after compaction the agent again has the protocol, the map, the active plan's path and where its progress log left off.

## Scope
- Measured first (Claude Code 2.1.292, sandbox, `claude -p "/compact" --resume <id>`): compaction fires `SessionStart` with source `compact` (`hookName: SessionStart:compact`), and since `hooks.json` registers `hook-start` with no matcher, the protocol and map are already re-injected. So the hook to extend is `hook-start`, not a new `PreCompact` hook (whose output does not reach the model's context).
- Adapter: `read_event` also returns `source` (`startup`, `resume`, `clear`, `compact`; Claude's `source` field).
- `cmd_hook_start`: when the source is `compact` or `resume` and `.ctx/tasks/active.md` is non-empty, the plan line becomes a resume note: the plan's title, its path, and the last `PLAN_TAIL` (8) entries of its `## Progress log`, with an instruction to continue from there rather than re-plan. Startup keeps the one-line pointer.
- Docs: README (how it works / hooks), the card.

## Acceptance criteria
- `hook-start` with `{"source": "compact"}` and an active plan prints the protocol, the map and a resume note with the plan title and the last 8 progress entries.
- With `startup` the output is as before.
- Without an active plan, `compact` output equals `startup` output.
- `python3 -m unittest discover -s tests` and `python3 bench/sandbox.py` pass; a live compaction in the sandbox shows the resume note in the `SessionStart:compact` hook output.

## Steps
1. Adapter `source`; `plan_resume_note()`; wire into `cmd_hook_start`.
2. Tests; live check.
3. Docs and task status.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Step 1 done: the adapter's `read_event` returns `source`; `plan_resume_note` builds the title and progress tail; `cmd_hook_start` uses it for `compact` and `resume`.
- Decision: extend `hook-start` instead of adding a `PreCompact` hook. Measured: `claude -p "/compact" --resume <id>` writes a `compact_boundary` and then a `SessionStart:compact` hook run whose output is injected, so the existing unmatched SessionStart hook is the re-injection point. PreCompact runs before the summary and does not add to the model's context.
- Step 2 done: test `CardsAndHooks.test_compaction_resumes_from_the_active_plan` (same output with no plan; resume note with the last 8 of 10 entries; resume wording; startup unchanged). Live: in the sandbox with an active plan, the transcript's `SessionStart:compact` output carried the note with both progress entries.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session). Checked that an unreadable payload still yields the startup output (`read_event` None -> `{}`) and that a plan without a progress log gets the re-read hint.
- Verification: `python3 -m unittest discover -s tests` passes 55 tests; `python3 bench/sandbox.py` smoke checks pass.
