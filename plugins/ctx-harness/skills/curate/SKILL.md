---
name: curate
description: Keeps ctx-harness context true and lean after code changes. Run after merges, on a schedule or in CI, when a reviewer reports context drift, or when the user asks to refresh, update, or clean up the context.
disable-model-invocation: true
allowed-tools: Bash(ctxh *) Read Grep Glob
---
# Curate repository context

The curator is the only writer of `.ctx/map.md`, `.ctx/cards/` and `.ctx/learned.md`. Prefer deleting over adding.

If `.ctx/` does not exist, stop and point the user to `/ctx-harness:build`.

## 1. Re-index (cheap, deterministic)
`ctxh build-index --verify`, then `ctxh stale`.

## 2. Refresh what changed
- For each stale card: invoke the `ctx-harness:card-writer` agent for that module. It rewrites the card and re-anchors it.
- If modules, entry points, verified commands, co-change or fragile files changed, run `ctxh skeleton` and update only the affected map lines. Keep existing purpose lines that are still true, then delete `.ctx/map.draft.md`.

## 3. Learn from usage
Run `ctxh signals` and read `.ctx/tasks/notes.md` if present. Promote a fact into `.ctx/learned.md` (or into the relevant card) only when:
- it recurred (a file needed in 3+ tasks, a command that failed 2+ times, a repeated empty index query), or a reviewer or coder note gives concrete evidence, and
- it cannot be cheaply inferred from code.
Write each as one factual line with its evidence, starting with a scope tag: `[*]` when it applies to the whole repo (loaded at every session start, so keep those few, at most 5), or `[<module>]` with a module name from the map (shown only when a request matches that module). Then remove the notes you processed.

Empty index queries mean either a gap in `ctxh` (report it to the plugin maintainers) or a misleading name in the code; a card line can fix the latter.

## 4. Prune and verify
- Remove learned lines that no recent trace touched and that a probe no longer needs. `ctxh signals` lists each learned line that names a path or command with how many traces used it, and the prune candidates; a line with no backticked path or command is not listed, so judge it yourself.
- `ctxh check` must pass. Budgets are hard limits: consolidate rather than exceed them.

## 5. Report
List what changed in `.ctx/` and why, in a few lines.
