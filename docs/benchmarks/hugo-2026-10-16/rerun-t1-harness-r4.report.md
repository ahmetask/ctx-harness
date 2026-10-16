# Benchmark 20261016-002127-claude

Agent: claude · tasks: 1 · repeats: 1 · plan/review gates: off

## Overall

| mode | runs | pass rate | median tokens | median uncached | median steps | tokens per pass | median time | cost | cost per pass |
|---|---|---|---|---|---|---|---|---|---|
| harness | 1 | 100% | 170.8k | 13.5k | 3 | 170.8k | 15s | $0.07 | $0.075 |

## Per task

| task | category | mode | pass | median tokens (IQR) | uncached | steps | time | Δ tokens vs baseline |
|---|---|---|---|---|---|---|---|---|
| t1-locate-permalink-error | locate | harness | 1/1 | 170.8k (170.8k–170.8k) | 13.5k | 3 | 15s |  |

## Harness overhead

- Reused context from `/home/user/ctx-harness/bench/results/20261015-220103-claude/ctx`; bootstrap cost not measured in this run.
