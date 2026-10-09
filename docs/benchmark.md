# Benchmark results

## Full run, 2026-10-09: all six tasks, plus a cards ablation and a learned-line check

Model `claude-sonnet-5-5`, harness with gates off, the committed `bench/demo/ctx`, 3 repeats per task. Same demo repo as below (43 Go files), engine at main after T22-T27.

Command: `python3 bench/run.py --agent claude --repeats 3 --modes baseline,harness --ctx-from bench/demo/ctx`. 36 sessions, $4.72.

| mode | pass | median tokens | uncached | median steps | cost | cost per passing task |
|---|---|---|---|---|---|---|
| baseline | 18/18 | 230.2k | 18.1k | 6.0 | $2.44 | $0.136 |
| harness | 17/18 | 217.3k | 18.0k | 4.5 | $2.28 | $0.134 |

| task | baseline (median tokens, steps) | harness | change |
|---|---|---|---|
| t1 locate | 156.8k, 4 | 123.3k, 2 | -21% |
| t2 fixed coupon | 292.9k, 9 | 222.1k, 4 | -24% |
| t3 cancel stock | 164.2k, 6 | 213.1k, 5 | +30% |
| t4 refunds | 368.9k, 7 | 388.5k, 7 | +5% |
| t5 price filter | 390.1k, 13 | 306.3k, 6 | -21% |
| t6 JPY | 206.0k, 4 | 172.2k, 4 (2/3 passed) | -16% |

Reading it:
- **On cost the harness is about break-even** (-1% per passing task), and it takes fewer steps (4.5 vs 6.0 median; 81 vs 123 summed over the 18 runs each). It saves tokens on locate, bugfix-with-a-clear-pointer and feature tasks, and costs more on t3 and t4, where the cards and map point at the right module but the agent still has to find the second place (stock release, the email template).
- **The one harness failure** was a t6 run whose hidden money test failed (`go test -run Hidden ./internal/money/`). With 3 repeats that is one run; I did not investigate whether the context contributed.
- **Uncached tokens are the same** in both modes, so the saving is in cached reads from fewer steps, which bill at a lower rate. Cost per passing task is the fairer headline.

### Cards ablation

Same protocol, harness only, with `cards/` deleted from the context (the map stays). 18 sessions, $2.21.

| context | pass | median tokens | median steps | cost | cost per passing task |
|---|---|---|---|---|---|
| map + cards | 17/18 | 217.3k | 4.5 | $2.28 | $0.134 |
| map only | 18/18 | 193.2k | 3.5 | $2.21 | $0.123 |

Per task, map only was cheaper on t3 (168k vs 213k), t4 (334k vs 389k) and t5 (218k vs 306k), the same on t1 and t6, and dearer on t2 (265k vs 222k). At three repeats these gaps are within the run-to-run spread (t4 and t5 IQRs overlap), so the honest reading is: **on a 43-file repo the cards do not pay for themselves yet, and they might cost a little.** I would not drop them on this evidence (the map alone is enough to find things in a repo this small), but the case for cards rests on larger repos, which this run does not cover.

### Learned line check (T24)

t2 x3, map only plus one scoped learned line that states the answer (`[internal/pricing]` fixed coupons apply before tax, `Engine.Quote` subtracts after). The prompt hint delivered it in all three sessions (found in the transcripts). 3/3 passed at 265.1k median tokens and 5 steps, $0.40, the same as map-only without the line (265.2k, 5 steps). So delivery works, but on this task the agent already finds the fix in about five steps and the line saved nothing. A task where the gotcha is hard to infer from the code would be a fairer test.

### Caveats
- 3 repeats per cell, one model, one small repo. Differences under about 15% are noise here (see the t4 spread in the earlier runs).
- The baseline ran with `CTXH_DISABLED=1`; the plugin's agents may still be listed if it is installed user-wide.
- Not run: a large-repo benchmark, which is where a map and retrieval hints should matter most.

## Four arms, 2026-10-08: baseline, Graphify, harness, harness + Graphify

Same protocol as the rerun below (t1, t2, t4 × 3 repeats, harness 0.4.0 with gates off and the committed `bench/demo/ctx`), now with four arms. 36 sessions, about $4.83 in total, model `claude-sonnet-5-5`, Claude Code 2.1.294, Graphify 0.9.80 (PyPI `graphifyy`). All 36 passed their hidden checks and the regression suite.

- **Graphify setup.** As its docs describe for Claude Code: `graphify update .` (AST-only graph, no LLM, about 1s, 291 nodes on the demo repo) and `graphify claude install` (a `CLAUDE.md` section plus `PreToolUse` hooks that steer search and reads to `graphify query`). I did not run the `/graphify` skill, whose semantic pass uses the model. A live session confirmed the agent calls `graphify query` first.
- Command: `python3 bench/run.py --agent claude --tasks t1,t2,t4 --repeats 3 --modes baseline,graphify,harness,harness+graphify --ctx-from bench/demo/ctx`.

Totals over the 9 runs per arm (all passed, so cost per pass is cost / 9):

| arm | total tokens | uncached | steps | wall time | billed cost | per passing task |
|---|---|---|---|---|---|---|
| baseline | 2.13M | 168.6k | 53 | 259s | $1.19 | $0.132 |
| baseline + Graphify | 2.42M (+14%) | 184.9k (+10%) | 45 | 272s (+5%) | $1.30 (+9%) | $0.144 |
| harness | 2.05M (-4%) | 174.0k (+3%) | 38 | 253s (-2%) | $1.18 (-1%) | $0.131 |
| harness + Graphify | 1.83M (-14%) | 180.6k (+7%) | 32 | 219s (-15%) | $1.16 (-3%) | $0.129 |

Medians per task (tokens, steps, time):

| task | baseline | + Graphify | harness | harness + Graphify |
|---|---|---|---|---|
| t1 locate | 159.5k, 4, 16s | 161.6k, 3, 25s | 123.7k, 3, 12s | 124.4k, 2, 14s |
| t2 bugfix | 292.4k, 9, 37s | 349.1k, 7, 32s | 175.0k, 3, 27s | 178.5k, 3, 26s |
| t4 cross-module | 270.0k, 5, 37s | 341.0k, 6, 39s | 386.6k, 7, 38s | 288.9k, 5, 34s |

What this shows:
- **Graphify alone did not help on this repo.** It cut steps (53 → 45) but cost more tokens, time and money. Its query output is large (the t1 query returned 83 nodes, truncated), and the agent still read the files afterwards. A 43-file repo is small enough that grep is already cheap.
- **The harness on its own is about break-even on cost** (-1%) and saves tokens mainly through fewer steps. Uncached tokens are slightly higher in every arm that adds context.
- **The best arm was harness + Graphify**, mostly because of t4 (289k vs 387k for the harness alone). I would not read that as synergy: t4 harness runs were 383–387k in all three repeats here, but 184k–333k in the earlier rerun (which gave -10% on cost overall). t4 is the noisy task, and the 9-run arms differ by single-digit percent on cost.
- **Differences of a few percent in cost, time or uncached tokens are inside run-to-run noise** at 3 repeats per cell. The solid findings are Graphify-alone being worse than baseline (consistent on t2 and t4) and the harness saving 22–40% of tokens on t1 and t2.
- Limits: one small repo, three tasks, Graphify's AST graph only (no semantic extraction, no wiki, no MCP server).

## Rerun, 2026-10-08: lean default flow (plugin 0.4.0)

After the pilot below, the harness still cost more than the baseline on t4: 80k uncached tokens vs 28k, and 86s vs 37s. The cause was not the context (the map and card are about 1.5k tokens). It was the planner and reviewer subagents, plus the turns the plan and review gates forced. 0.4.0 makes both gates and both subagents opt-in, and keeps the protocol to working from the map and the module card.

- Command: `python3 bench/run.py --agent claude --tasks t4,t2,t1 --repeats 3 --ctx-from bench/demo/ctx --keep` (gates off, the new default). Model `claude-sonnet-5-5`, Claude Code 2.1.292, demo repo with the committed `bench/demo/ctx`. 18 sessions, all 18 passed their hidden checks and the regression suite.
- Medians of 3 runs per cell; cost is the sum of the 3 runs. "Tokens" include cache reads, which grow with every model call; "uncached" is fresh input plus output plus cache writes.

| task | mode | tokens | uncached | steps | time | cost |
|---|---|---|---|---|---|---|
| t1 locate | harness | 123.7k | 13.4k | 3 | 16s | $0.24 |
| t1 locate | baseline | 159.7k | 13.1k | 4 | 15s | $0.26 |
| t2 bugfix | harness | 176.8k | 19.9k | 3 | 28s | $0.38 |
| t2 bugfix | baseline | 333.1k | 18.2k | 9 | 32s | $0.46 |
| t4 cross-module | harness | 284.3k | 25.6k | 5 | 31s | $0.49 |
| t4 cross-module | baseline | 318.2k | 25.4k | 6 | 36s | $0.53 |
| **all 9 runs per mode** | harness | 1.74M | 172.6k | | 229s | $1.11 |
| | baseline | 2.36M | 170.6k | | 253s | $1.24 |

- **Total tokens -26%, wall time -9%, cost -10%** against the baseline. The saving comes from fewer steps: the map and card name the files, so the agent skips the discovery turns (t2: 3 steps vs 9).
- **Uncached tokens are a tie (+1%).** The injected protocol and map add about 1.5k tokens of cache writes up front, and that is what the saved turns repay. On a 43-file repo with 3-to-6-step tasks there isn't more to win; the gap should widen on larger repos, which this benchmark doesn't cover.
- **t1 is a wash on time** (16s vs 15s, within run-to-run spread of 12–24s).
- t4 varies most (harness 184k–333k tokens): it is the only task where the agent sometimes reads extra files.
- Before this change, the same t4 run cost 80k uncached tokens and 86s with the old defaults (the planner and reviewer ran in the background). With `--gates` the harness arm turns the plan and review gates back on, to measure what they cost.

## Pilot, 2026-10-07: a small sample only

Run with plugin 0.1.0 defaults (planner for 3+ files, reviewer before finishing, review gate on); kept for history.

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
- `--gates` (harness arm with the plan and review gates on; they are off by default since 0.4.0), to measure what the gates cost
- a run where the planner threshold is higher, since t4 suggests the 3-file rule is the expensive part
