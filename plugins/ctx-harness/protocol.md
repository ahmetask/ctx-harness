# Working protocol (context harness)

You are the coder: work directly, starting from the repo map below. Subagents cost a full extra context each, so they are opt-in (last bullet).

- Ask the index before searching wide: the `ctx_query` tool, or `ctxh q <kind> <arg>` in a shell (kinds: find, search, rdeps, impact, cochange, tests, owner, module). Only the answer enters your context. Then read file ranges, not whole files, and batch the reads you already know you need.
- If a request leaves the outcome or how to check it open and the code can't answer it, ask the user a few short questions (with your suggested defaults) before editing; if a guess is cheap, state it in one line and go.
- If `.ctx/tasks/active.md` exists, read it first and continue from its progress log.
- Validate with the verified commands in the map. Send long output to `.ctx/tmp/` and read it with tail/grep.
- If something cost you real exploration and is not inferable from code (a hidden rule, a misleading name, a command quirk), append one line to `.ctx/tasks/notes.md`. The curator owns `.ctx/map.md`, `.ctx/cards/` and `.ctx/learned.md` (`{{command:curate}}` after merge); do not edit them during a task.
- Subagents, only when they pay for themselves: `{{agent:scout}}` for an open question that would take 5+ reads; `{{agent:planner}}` when the user asks for a plan; `{{agent:reviewer}}` when the user asks for a review or the change touches 6+ files. Run them in the foreground and use their answer; never poll or redo their work.
{{only:claude}}  Pass `run_in_background: false`.
