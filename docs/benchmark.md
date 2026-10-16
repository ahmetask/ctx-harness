# Benchmark results

## Large repo, symptom-only bug reports, full history (2026-10-16)

Follow-up to the Hugo run below, built to remove its two biggest caveats: the prompts named greppable identifiers, and the checkout had one commit. Same repo and pinned commit (Hugo v0.140.2, 852 Go files), but with full git history (8,752 commits; the miner reads the latest 500, so churn, co-change and owners exist this time), and five new bug-fix tasks in the suite `hugo-symptom` whose prompts describe only what a user sees. Each is a one-line bug planted by `setup.patch` in a different package: group headings merged in a grouped paginator (`resources/page`), `delimit` ignoring its last separator for two items (`tpl/collections`), `absURL ""` losing the base URL's trailing slash (`common/paths`), table-of-contents end level one too low (`markup/tableofcontents`), and an allowlist that drops its last pattern, which blocks `getenv "CI"` (`config/security`). Every task has a hidden test that fails on the planted state and passes with the fix (`tests/test_bench.py::HugoSuite`). 5 repeats, baseline vs harness, plan and review gates off. One bootstrap build ($0.41, 2.1M tokens, 22 minutes), reused for every harness run. Raw rows, reports, the context used and `aggregate.py` are in `docs/benchmarks/hugo-symptom-2026-10-16/`.

| arm | pass | total tokens | median tokens | median steps | median uncached | cost |
|---|---|---|---|---|---|---|
| baseline | 25/25 | 6.24M | 247.6k | 6 | 14.3k | $2.23 |
| harness (map + cards) | 25/25 | 6.55M (+5%) | 268.4k | 5 | 17.3k | $2.57 (+15%) |

| task | baseline | harness | change |
|---|---|---|---|
| s1 grouped pagination | 287.5k, 7 steps | 277.3k, 5 steps | -4% |
| s2 `delimit`, two items | 207.9k, 5 steps | 223.9k, 4 steps | +8% |
| s3 `absURL ""` | 301.9k, 8 steps | 276.0k, 6 steps | -9% |
| s4 table-of-contents end level | 251.8k, 7 steps | 313.0k, 6 steps | +24% |
| s5 `getenv` allowlist | 247.6k, 6 steps | 178.5k, 4 steps | -28% |

Reading it:
- **Still no saving, and a cost increase.** The harness took one fewer step at the median (139 steps against 152 in total), but each session carries the injected map and protocol (uncached tokens +21%), so tokens went up 5% and cost 15%. The per-task spread (-28% to +24%) is as large as the effect; with 5 repeats this reads as noise around zero, not as a win or a loss on any one task.
- **The agent did not use the index.** In 25 harness sessions Claude ran `ctxh q` zero times. It read the injected map, then used grep and `go test` as in the baseline. So the history signals (churn, co-change, owners) were available but never consulted; this run says nothing about whether they would help if used.
- **Symptom-only prompts were still easy.** Both arms fixed 25 of 25. Baseline needed 5 to 8 steps, about 25 seconds per task (not comparable with the first Hugo run: this suite sets `-trimpath`, which lets Go reuse its build cache across clones). My reading, not tested, is that a one-line bug in a well-tested package falls to the package's own tests once grep points at the package, and the prompts gave enough words to grep.
- **The combined result of both Hugo runs:** ctx cut tokens on tasks that touch several places (-26% and -27%) and cost 5 to 15% more on single-spot fixes. It has not yet saved money on any large-repo run.

What this does not show: harder tasks (a failing integration test far from the cause, a regression introduced a few commits ago, a change that needs 15+ files), a model told to use the index before searching, or a different agent. Those are where a map should pay off, and none has been measured.

## Large repo, greppable tasks, 2026-10-16: Hugo (852 Go files), baseline vs harness vs map-only

The demo repo (43 files) is too small for a map to replace much search, so this run uses a real project: [Hugo](https://github.com/gohugoio/hugo) v0.140.2 (852 Go files, 44 modules), vendored as the submodule `bench/repos/hugo`. Run it with `python3 bench/run.py --suite hugo --agent claude ...` (see `bench/README.md`). Raw rows, per-run reports, the context that was used and `aggregate.py` are in `docs/benchmarks/hugo-2026-10-16/`.

Setup: 5 tasks (2 locate, 1 bugfix with a planted bug, 1 cross-module, 1 feature), 5 repeats, Claude Code's default model, plan and review gates off. Every task has hidden tests that fail on the untouched repo and pass with a reference solution (`tests/test_bench.py::HugoSuite`). Context: one `/ctx-harness:build` run on the repo (map of 27 lines and 5 cards; $0.41, 570s, 2.1M tokens), reused for every harness run. The map-only arm is the same context with `cards/` deleted. 76 task sessions plus the bootstrap, about $7.5 in total.

| arm | pass | total tokens (sum of 25 runs) | median tokens | median steps | median uncached | cost |
|---|---|---|---|---|---|---|
| baseline | 25/25 | 6.23M | 210.9k | 5 | 14.6k | $2.40 |
| harness (map + cards) | 25/25 | 5.62M (-10%) | 218.8k | 4 | 16.2k | $2.39 |
| map only | 25/25 | 5.47M (-12%) | 213.3k | 4 | 15.9k | $2.34 |

Median tokens per task (cost of the 5 runs in brackets):

| task | baseline | harness | map only |
|---|---|---|---|
| t1 locate: permalink error | 201.5k ($0.34) | 212.9k ($0.39) | 213.3k ($0.39) |
| t2 bugfix: escaped colons | 168.0k ($0.39) | 218.1k ($0.42) | 172.0k ($0.39) |
| t3 cross-module: `strings.Reverse` | 305.5k, 7 steps ($0.58) | 222.7k, 4 steps ($0.53) | 227.2k, 4 steps ($0.53) |
| t4 feature: ISO week permalink tokens | 370.4k, 12 steps ($0.67) | 275.1k, 9 steps ($0.61) | 317.0k, 6 steps ($0.60) |
| t5 locate: pager size | 171.1k ($0.41) | 178.5k ($0.44) | 177.2k ($0.44) |

Reading it:
- **Cost is a tie** ($2.40 vs $2.39 vs $2.34), as on the demo repo. Uncached tokens are 8-11% higher with context (the injected map and protocol), and cheaper cache reads from fewer steps pay that back and little more.
- **The saving is concentrated in tasks that touch several places.** t3 and t4 used 26-27% fewer tokens with the harness and about 40% fewer steps in t3 (7 to 4); the agent was told where the registry and the docs live instead of searching. On the locate tasks and the one-file bugfix the context added 4-30% (see below), because Claude's own grep finds the answer in 4 steps either way.
- **Cards did not help here either.** Map only matched the harness within noise on every task, and was cheaper in total ($2.34 vs $2.39). The t2 gap (218k vs 172k) is the harness reading a card for a one-line fix; the card is the only difference between those arms.
- **Claude finds things fast even in 852 files.** Baseline medians are 4 steps on locate and bugfix tasks, 7 and 12 on the two multi-file tasks. All of these are tasks whose prompts name identifiers an agent can grep (`permalink`, `paginate`, `strings`). That is the ceiling for what a map can save; it says nothing about tasks described only by symptom in an unfamiliar area.
- **One infrastructure failure, rerun.** The first pass had one harness failure (t1, r4) caused by my clearing the Go build cache while the check ran. Its rerun passed and replaces it in the tables (`rerun-t1-harness-r4.*`). Excluding it, 75 of 75 runs passed.

What this does and does not show:
- 5 repeats and one repo: per-task differences under about 15% are inside the run-to-run spread (the t4 baseline ranged 306k to 397k).
- The submodule is a shallow checkout, so the index mined **one commit**: no churn, owners, co-change or fix/revert risk. The map and hints are the content-only half of ctx; history-based signals were not tested.
- The tasks were written for this benchmark. Larger or less greppable work (a vague bug report, a refactor, a task needing 20+ files) is untested.
- Building the context on Hugo exposed a real bug, now fixed with a test: `ctxh build-index` crashed with a `KeyError` when code imported a tracked non-code file (a CSS file here). The bootstrap agent patched `plugins/ctx-harness/bin/ctxh` mid-run; that patch is the one in this commit, and it is what every harness run used.

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
