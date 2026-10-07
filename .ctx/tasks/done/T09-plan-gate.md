# T09 · Hook-enforced plan gate

## Goal
"Plan before touching 3+ files" is the rule the harness repeats most and enforces least. Make the Stop hook check it, the same way it already checks that a reviewer ran.

## Scope
- Stop hook, not PreToolUse: the same place as the review gate, so the two share one state file and one block-once rule. A PreToolUse gate would have to guess at the third edit before it happens and would fire mid-thought; at Stop the session's whole edit set is known.
- `plugins/ctx-harness/bin/ctxh`:
  - `session_edits(path)`: one pass over the transcript returning the distinct code files edited in the main session, the last code edit's id, whether a reviewer ran after it, and whether a planner subagent ran. `unreviewed_edit` becomes a thin wrapper on it.
  - `plan_gate_reason(info)`: a reason when 3+ distinct code files changed and there is no plan, where a plan is a non-empty `.ctx/tasks/active.md` or a `ctx-harness:planner` call in this session (a finished task moves its plan to `done/`).
  - `gate_once(session, key, value)`: the review gate's block-once rule, now shared, both keys in one `.ctx/tmp/gates/<session>.json`.
  - Order in `cmd_hook_stop`: plan gate first, then the review gate. Each is keyed on the last edit id, so the sequence is block for the plan, then block for the review, then finish. Neither can loop.
  - `CTXH_PLAN_GATE=0` turns it off, like `CTXH_REVIEW_GATE=0`.
- Docs: the engine docstring, the README environment table and the one line in the limits that says the planner rule is unenforced.

## Acceptance criteria
- 3 code files edited with no plan: the hook blocks once; the second Stop on the same state is silent.
- The same session with a non-empty `.ctx/tasks/active.md`, or with a planner subagent call, does not hit the plan gate.
- 2 edited files never hit it.
- `CTXH_PLAN_GATE=0` disables it and leaves the review gate alone.
- Edits under `.ctx/` and to files `lang_of` does not recognize are not counted, as in the review gate.
- `python3 -m unittest discover -s tests` passes.

## Risks
- Two gates in a row cost the agent two extra turns on a large unplanned change. That is the point, but it is also why each is keyed on the same edit id rather than firing repeatedly.
- A session that legitimately spreads a trivial change over 3 files (a rename) gets asked for a plan. The block says to say so and finish, and the env var is the escape hatch.

## Steps
1. `session_edits` + `gate_once` refactor, review gate unchanged in behavior.
2. Plan gate and the env switch.
3. Tests (block, once, plan present, planner ran, 2 files, off switch).
4. Docs and task statuses.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Step 1 done: `session_edits` replaces the single-purpose scan in `unreviewed_edit` (now a wrapper on it) and also returns the distinct code files and whether a planner ran. `gate_once` holds the block-once rule for both gates in one state file.
- Step 2 done: `plan_gate_reason` + `PLAN_GATE_FILES = 3`, wired into `cmd_hook_stop` ahead of the review gate, behind `CTXH_PLAN_GATE`.
- Decision: Stop hook, not PreToolUse. A PreToolUse gate would have to block the third edit as it happens, which interrupts a change mid-way and fires on edits the agent then abandons; at Stop the whole edit set is known and the cost is one turn.
- Decision: a `ctx-harness:planner` call in the session counts as a plan even with no `active.md`, because a session that finishes its task moves the plan to `tasks/done/` before stopping.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session). Checked that the two gates cannot loop (each keyed on the last edit id, separate keys, state merged rather than overwritten) and that `CTXH_DISABLED=1` still skips both. No findings.
- Verification: `python3 -m unittest discover -s tests` passes 42 tests (37 before). The new tests cover block-once, two files, an active plan, a planner call, the off switch, and both gates firing in turn.
