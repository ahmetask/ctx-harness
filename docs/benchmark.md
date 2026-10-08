# Benchmark results

## Pilot, 2026-10-07: a small sample only

**This is not the T20 result.** It is 4 task sessions plus 1 bootstrap: 2 tasks, 1 repeat each, run to check that the real pipeline works before spending about 37 sessions on a full run. One run per cell can't separate the harness from session noise, so treat the numbers below as a direction to check, not a finding.

- Command: `python3 bench/run.py --agent claude --tasks t2,t4 --repeats 1`
- Model: `claude-sonnet-5-5` (the CLI default), Claude Code 2.1.292, review gate on.
- Cost: about $1.59 in total, of which $0.71 was the bootstrap.
- The engine was being refactored (T13) in the same checkout while the pilot ran. That refactor doesn't change behavior (the tests are unchanged), but it is a caveat.

### Report (`bench/report.py` output)

Agent: claude · tasks: 2 · repeats: 1 · review gate: on

#### Overall

| mode | runs | pass rate | median tokens | median uncached | median steps | tokens per pass | cost |
|---|---|---|---|---|---|---|---|
| harness | 2 | 100% | 434.1k | 48.2k | 7.0 | 434.1k | $0.57 |
| baseline | 2 | 100% | 275.4k | 20.8k | 7.0 | 275.4k | $0.30 |

#### Per task

| task | category | mode | pass | median tokens (IQR) | uncached | steps | Δ tokens vs baseline |
|---|---|---|---|---|---|---|---|
| t2-fixed-coupon-tax | bugfix | harness | 1/1 | 268.4k (268.4k–268.4k) | 23.0k | 5 | -7% |
| t2-fixed-coupon-tax | bugfix | baseline | 1/1 | 288.5k (288.5k–288.5k) | 19.0k | 9 |  |
| t4-refunds | cross-module | harness | 1/1 | 599.7k (599.7k–599.7k) | 73.3k | 9 | +129% |
| t4-refunds | cross-module | baseline | 1/1 | 262.3k (262.3k–262.3k) | 22.7k | 5 |  |

#### By category

| category | harness pass | baseline pass | median Δ tokens |
|---|---|---|---|
| bugfix | 1/1 | 1/1 | -7% |
| cross-module | 1/1 | 1/1 | +129% |

#### Harness overhead

- Bootstrap (`/ctx-harness:build`, once per repo): 2201.0k tokens, $0.71, 115s.
- No net token saving on these tasks: the harness does not pay for its bootstrap here.

### Reading

- **Correctness:** all 4 runs passed their hidden checks, in both modes.
- **t2 (bugfix, 1 file): harness 7% cheaper, 5 steps vs 9.** The baseline opened 4 files with the Read tool before editing. The harness run went straight to `internal/pricing` (the map names it), read the package with one `cat` and edited.
- **t4 (cross-module, 4 files): harness 129% more expensive, 600k vs 262k tokens.** The protocol did what it says: a change to 3+ files called `ctx-harness:planner`, and the edit called `ctx-harness:reviewer`. Those two subagents and their extra turns are the whole difference. The baseline solved it in 5 steps without them. On a task the model can already do in one pass, the planner and reviewer are pure overhead.
- **Bootstrap: 2.2M tokens (147k uncached), $0.71.** It ran 5 card-writer and 5 scout subagent calls. The paired savings here don't pay it back.
- **Gate blind spot:** in t2 the harness run edited `discount.go` with a shell heredoc (`cat >> ...`) and with a tool named `bash` (lowercase), not `Edit`/`Write`. So the review gate never saw a code edit and never fired. Edits through the shell are invisible to `session_edits`. Making the gate check `git diff` instead of the edit tools would close this. It belongs with T19 (a review gate outside the agent).

### What to run for T20

Run `python3 bench/run.py --agent claude --repeats 3` over all 6 tasks: 37 sessions, roughly $10–15 at these prices. Also worth measuring:
- `--no-review-gate`, to separate the gate's cost from the context's
- a run where the planner threshold is higher, since t4 suggests the 3-file rule is the expensive part
