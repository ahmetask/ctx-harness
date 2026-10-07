# T07 · Benchmark platform with a demo repo

## Goal
Measure whether ctx-harness actually saves tokens without losing correctness. Run the same coding tasks on a realistic demo repo with the harness on and off, check each result with hidden acceptance tests, and report tokens, steps and pass rate per task. Today `ctxh stats` compares tokens only and has no repo or tasks to run against.

## Scope
- New `bench/`:
  - `demo/`: a template for a multi-module Python app (stdlib only). It includes scripted git history with fix/revert commits and files that change together, plus hidden rules that live in one place in the code.
  - `tasks/`: task specs (prompt, category, acceptance check, turn limit).
  - `run.py`: materializes a fresh repo per run, runs the agent in harness or baseline mode, runs the hidden checks and records results.
  - `report.py`: aggregates results.
- `bench/agents/`: a pluggable agent command. The default is `claude -p` with `--plugin-dir ./plugins/ctx-harness`. A `fake` agent replays scripted transcripts so the platform runs without API cost.
- `tests/`: index tests against the demo repo (correct `q find`, `impact`, `cochange` and `risk` answers), plus platform tests in fake mode.
- CI: add platform tests in fake mode. The real benchmark stays manual (API key, cost).
- Touches `ctxh` `usage`/`record` only if the runner needs extra fields; no index-logic changes. Co-change partners: `tests/test_ctxh.py`, README "Measuring against a baseline", `docs/flow.md`.

## Acceptance criteria
- `python3 bench/run.py --agent fake --repeats 2` finishes offline in under a minute and writes `bench/results/<run>/results.jsonl` and `report.md`.
- The demo repo has at least 6 modules and at least 40 source files, its own passing tests, and history that makes `ctxh q cochange` and `ctxh q risk` non-empty.
- The suite has at least 6 tasks covering locate/explain, bug fix, small feature, and a cross-module change (3+ files). Each has a hidden check that fails on the untouched repo and passes on a reference solution, and a test asserts both.
- The report shows per task, for harness and baseline: pass rate, median and IQR of total and uncached tokens, median steps, and tokens per successful run. It also shows the one-time bootstrap cost and the break-even point.
- The harness condition uses a `.ctx/` built once per benchmark run and copied into each harness run. Its build cost is recorded as `bootstrap`.
- `python3 -m unittest discover -s tests` passes, and CI runs the fake-mode platform tests.

## Risks
- The suite's design favors one side. Mix tasks the map/cards help with and tasks they don't (pure local edits), and report per category.
- Noise: single runs mean little. Default to 3 repeats and always show spread.
- Hidden checks leaking into the agent's view. Keep them outside the materialized repo and copy them in only after the agent finishes.
- Claude transcript format coupling (T06). The runner reads transcripts through `ctxh usage`, so a format change breaks both in the same place.
- Cost: a full real run is roughly 6 tasks × 2 modes × 3 repeats = 36 sessions. The runner supports `--tasks` and `--repeats` to keep runs small.

## Steps
1. Demo repo template and a history script that commits code in stages with fix/revert/co-change commits. Add demo index tests.
2. Task spec format, 6 tasks with hidden checks and reference patches, and a test that checks each hidden check fails before and passes after its patch.
3. Runner: materialize, prebuild `.ctx/` once, run the agent per mode and repeat, run the checks, record results. Include the `fake` agent.
4. Report: aggregation, markdown output and break-even.
5. CI job for fake mode, plus README "Benchmark" section and `tasks.md` status.

## Progress log
- Plan approved with changes from the user: Go demo (not Python); real runs manual only via `claude -p`.
- Step 1 done: `bench/demo/template/` (shopd, 43 source files in 18 packages, stdlib Go 1.22) and `bench/demo/materialize.py` (10 scripted commits, 3 authors, fix/hotfix/revert, state.go <-> templates.go co-change with no import link). `go vet`, `gofmt` and `go test` are clean. Replay is byte-identical to the template, and the HEAD hash is deterministic.
- Step 2 done: 6 tasks (locate, 2 bugfix, 2 feature, 1 cross-module) with hidden `TestHidden*` checks plus `go test ./...` as regression. Solutions for changed files are derived from the template with exact replacements. Verified: every check fails untouched (`noop` agent) and passes with its solution.
- Step 3 done: `bench/run.py` and `bench/agents.py` (`claude` / `fake` / `noop`). Token usage comes from ctxh's own `parse_transcript`. Modes alternate order; harness runs get a committed `.ctx/` snapshot. A headless note is added to every prompt, since in `-p` mode nobody can approve a plan.
- Step 4 done: `bench/report.py` (overall, per task with IQR, by category, tokens per pass, bootstrap and break-even, failed runs).
- Step 5 done: CI `engine` job sets up Go 1.22. Added `tests/test_bench.py` (10 tests, including a stub `claude` CLI that checks flags, per-mode env and transcript discovery), `bench/README.md`, the README section and `.gitignore` for `bench/results/`.
- Deviation: `--max-turns` is opt-in. The installed CLI (2.1.292) doesn't list it in `--help`, and a test with `--version` couldn't confirm it is accepted. Runs are bounded by `--timeout` (default 3600s) instead.
- Found: the demo dominates this repo's own index (`ctxh q hot`, `q find`, plus nested `go.mod` commands). Logged as T21; derived `commands.json` reverted.
- Review: the `ctx-harness:reviewer` subagent isn't loaded in this cloud session, so I reviewed the diff myself. Fixed: run-dir collision when two runs start in the same second; transcripts of real runs are now copied into the run dir. Accepted: the baseline may still list ctx-harness agents if the plugin is installed user-wide (hooks are inert via `CTXH_DISABLED=1`; documented).
- Not done: real (`claude`) benchmark numbers. That is T20.
- Verification: `python3 -m unittest discover -s tests` passes 25 tests in about 45s. `ctxh check` is ok. `ctxh stale` reports everything fresh, but `.ctx/map.md` doesn't mention `bench/` yet, so `/ctx-harness:curate` is due.
