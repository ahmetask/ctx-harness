# Repo map  <!-- generated @ 9fd53c7; keep under 60 lines -->

Stack: python (stdlib only, 3.10+) plus markdown agent/skill prompts. Manifests: .github/workflows/ci.yml, .claude-plugin/marketplace.json.
Entry point: `plugins/ctx-harness/bin/ctxh` (extensionless Python script, indexed by its shebang).
Verified commands: `python3 -m unittest discover -s tests` (37 tests, ~80s; the benchmark tests need Go). CI also runs `claude plugin validate .` and `claude plugin validate ./plugins/ctx-harness`.

## Modules (most central first)

| module | purpose | key files | depends on |
|---|---|---|---|
| plugins/ctx-harness/bin | `ctxh` engine: index, queries, cards, freshness, metrics, hook entry points | ctxh | - |
| plugins/ctx-harness (prompts) | protocol, hooks wiring, agents (scout, planner, reviewer, card-writer), skills (build, curate, status) | protocol.md, hooks/hooks.json, agents/, skills/ | ctxh |
| tests | engine tests: throwaway git repos, ctxh run as a subprocess; checked-in transcript fixtures | test_ctxh.py, test_bench.py, fixtures/transcripts/ | ctxh |
| bench | harness-vs-baseline benchmark: demo Go repo, tasks with hidden checks, runner, report (`bench/demo/` and `bench/tasks/` are .ctxignored) | run.py, agents.py, report.py | ctxh |
| (root) | marketplace manifest, README, flow diagrams, gap backlog | .claude-plugin/marketplace.json, README.md, docs/flow.md, tasks.md | - |

## Finding things
- Ask the index first: `ctxh q find|rdeps|impact|cochange|tests|owner|module <arg>`
- Module cards: `.ctx/cards/<module-with-dashes>.md` (open only for the module you touch)
- Gotchas learned from past tasks: `.ctx/learned.md`
- Gap backlog and its status: `tasks.md`
