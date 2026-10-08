# Working protocol (context harness)

You are the coder: work directly, with the repo map below and the module card in place of exploring. Subagents cost a full extra context each, so they are opt-in (last bullet).

Finding things, cheapest first:
1. The repo map below and `ctxh q ...` (symbols, importers, impact, co-change, tests, owners; `ctxh q search <words>` for concepts). Only the answer enters your context.
2. The card for the module you are changing: `.ctx/cards/<module-with-dashes>.md`. Do not open cards for modules you are not touching.
3. Raw grep/read, targeted. Read file ranges, not whole large files. Batch the reads you already know you need into one command.

Task flow:
- If `.ctx/tasks/active.md` exists, read it first and continue from its progress log.
- Read the card, then the files it and the map point to, and edit. Do not re-read what you just wrote.
- Validate with the verified commands in the map. Send long output to `.ctx/tmp/` and read it with tail/grep.
- If something cost you real exploration and is not inferable from code (a hidden rule, a misleading name, a command quirk), append one line to `.ctx/tasks/notes.md`. The curator decides whether it becomes durable context.
- Do not edit `.ctx/map.md`, `.ctx/cards/` or `.ctx/learned.md` during a task; the curator owns them (`{{command:curate}}` after merge; staleness is reported at session start).
- Subagents, only when they pay for themselves: `{{agent:scout}}` for an open question that would take 5+ reads; `{{agent:planner}}` when the user asks for a plan, or the design is open and no reasonable default exists; `{{agent:reviewer}}` when the user asks for a review, or the change touches 6+ files or a file the map lists as fragile. Run them in the foreground and use their answer; never poll or redo their work.
{{only:claude}}  Pass `run_in_background: false`.
