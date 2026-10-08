# Benchmark

This folder measures whether ctx-harness saves tokens without costing correctness. It runs the same coding tasks on a demo repo twice, once with the harness and once without, and checks every result with hidden tests.

## Quick start

```bash
python3 bench/run.py --agent fake                      # offline, about 1 minute, synthetic numbers
python3 bench/run.py --agent claude --repeats 3        # real runs with your Claude Code login
python3 bench/run.py --agent claude --tasks t2,t4 --repeats 1 --model <model-id>
python3 bench/report.py bench/results/<run>            # re-render a report
python3 bench/sandbox.py [--prompt "<task>"]           # one demo repo to try a change in, not a measurement
```

Requirements: git, Python 3.10+ and Go 1.22+. Real runs also need the `claude` CLI on `PATH`.

**Cost.** A full real run is 6 tasks × 2 modes × repeats sessions, plus one bootstrap session. With the default 3 repeats that is 37 sessions. Use `--tasks` and `--repeats 1` while iterating.

## What a run does

1. **Bootstrap (harness only, once).** It materializes the demo repo and runs `/ctx-harness:build` in it. It records the cost as the `bootstrap` row and saves `.ctx/` to `bench/results/<run>/ctx`. Pass `--ctx-from <dir>` to reuse a saved context.
2. **For each repeat × task × mode:**
   - It materializes a fresh repo. Harness runs also get the saved `.ctx/`, committed.
   - It runs the agent. The order of the two modes alternates between runs, so neither mode always goes first.
   - It copies the task's hidden tests in and runs the task's checks plus `go test ./...`. A run passes only if every check passes.
   - It reads token usage from the session transcript with the plugin's own parser, the same one the Stop hook uses.
3. **Report.** `report.md` shows:
   - pass rate per mode
   - median tokens with the interquartile range
   - uncached tokens and steps
   - tokens per passing run, which charges failed runs to the mode that produced them
   - the change against baseline per task and per category
   - the bootstrap cost and break-even point
   - a list of failed runs

Modes:
- **harness:** `claude -p --plugin-dir plugins/ctx-harness`, with the repo's `.ctx/` present.
- **baseline:** `claude -p` with `CTXH_DISABLED=1` and no `.ctx/`. It stays inert even if the plugin is installed user-wide, but its agents may still be listed in that case. For the cleanest baseline, run from a user config without ctx-harness installed.

In both modes the prompt ends with a note that the run is non-interactive and any plan counts as approved. Without it, the harness protocol would wait for plan approval that never comes. `--no-review-gate` turns the Stop-hook review check off, if you want to measure the gate's cost separately. Each real run is killed after `--timeout` seconds (default 3600). `--max-turns` also passes each task's `max_turns` to `claude --max-turns`, if your CLI supports it.

Real runs use `--permission-mode acceptEdits` and allow `Bash`, so the agent can run `go test` and `ctxh`. Each run happens in a throwaway directory under the system temp dir. Pass `--keep` to keep the per-run repos for inspection.

## Agents

| agent | what it does | use |
|---|---|---|
| `claude` | Real Claude Code sessions | The actual measurement |
| `fake` | Applies each task's reference solution and writes a synthetic transcript | Tests the whole pipeline offline; its numbers mean nothing |
| `noop` | Changes nothing | Every check must fail, which proves the checks aren't vacuous |

## The demo repo: shopd

`demo/template/` is a Go order service with 43 source files in 18 packages (money, catalog, inventory, pricing, payments, orders, notify, httpapi, ...), using only the standard library. `demo/materialize.py` copies it and rebuilds a deterministic git history of 10 commits (fixes, a hotfix, a revert, three authors). That history gives the index real signals:

- risk: `internal/orders/service.go`, `internal/pricing/tax.go`, `internal/catalog/search.go`
- co-change with no import link: `internal/orders/state.go` ↔ `internal/notify/templates.go`
- owners per file

`demo/ctx/` is the demo's `.ctx/` as `/ctx-harness:build` produces it: the deterministic index output, a filled-in map and cards for the five central modules (orders, pricing, payments, money, httpapi). `sandbox.py` installs it in every sandbox, and `python3 bench/run.py --ctx-from bench/demo/ctx` uses it instead of paying for a bootstrap session. Its cards are anchored to template files, so `tests/test_bench.py` fails when an edit leaves them stale; refresh them by re-running the build in a sandbox and copying `.ctx/` back without `graph.json`.

To change the demo, edit `template/` (the final state). If an edit touches text that a `HISTORY` entry in `materialize.py` mentions, update that entry too. `tests/test_bench.py` checks that the history replays exactly to the template.

## Tasks

| id | category | what it takes |
|---|---|---|
| t1-locate-idempotency | locate | Find where double charges are prevented and write it to `ANSWER.md` |
| t2-fixed-coupon-tax | bugfix | Fixed coupons are applied after tax; the policy says before |
| t3-cancel-releases-stock | bugfix | Cancelling an order never releases its reserved stock |
| t4-refunds | cross-module | New `refunded` state: lifecycle, payment refund, email template (no import link to find it) and HTTP endpoint |
| t5-price-filter | feature | `min_price` / `max_price` on `GET /products` |
| t6-jpy | feature | A currency without minor units: formatting and parsing |

Each task folder holds:
- `task.json`: prompt, category, check commands, hidden test mapping and turn limit
- `hidden/`: tests copied in only after the agent finishes
- `solution/`: a reference solution, overlaid as whole files

`tests/test_bench.py` asserts that each hidden check fails on the untouched repo and passes with the solution.

To add a task, create `bench/tasks/<id>/` with those three parts. Name hidden tests `TestHidden...` so `-run Hidden` selects them. Run `python3 -m unittest tests.test_bench`.

Keep the suite balanced: include tasks the map, cards and index should help with (locate, cross-module) and tasks they shouldn't (local edits). The per-category table exists so one kind of task can't decide the result.
