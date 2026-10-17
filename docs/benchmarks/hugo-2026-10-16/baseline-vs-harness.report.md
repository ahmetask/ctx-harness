# Benchmark 20261015-224947-claude

Agent: claude · tasks: 5 · repeats: 5 · plan/review gates: off

## Overall

| mode | runs | pass rate | median tokens | median uncached | median steps | tokens per pass | median time | cost | cost per pass |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 25 | 100% | 210.9k | 14.6k | 5 | 249.3k | 33s | $2.40 | $0.096 |
| harness | 25 | 96% | 218.8k | 16.2k | 4 | 235.8k | 36s | $2.40 | $0.100 |

## Per task

| task | category | mode | pass | median tokens (IQR) | uncached | steps | time | Δ tokens vs baseline |
|---|---|---|---|---|---|---|---|---|
| t1-locate-permalink-error | locate | baseline | 5/5 | 201.5k (201.3k–201.8k) | 11.1k | 4 | 15s |  |
| t1-locate-permalink-error | locate | harness | 4/5 | 212.9k (212.9k–213.7k) | 13.3k | 4 | 16s | +6% |
| t2-escaped-colons | bugfix | baseline | 5/5 | 168.0k (168.0k–210.9k) | 13.4k | 4 | 33s |  |
| t2-escaped-colons | bugfix | harness | 5/5 | 218.1k (171.2k–218.8k) | 15.1k | 5 | 36s | +30% |
| t3-strings-reverse | cross-module | baseline | 5/5 | 305.5k (259.7k–350.5k) | 18.9k | 7 | 89s |  |
| t3-strings-reverse | cross-module | harness | 5/5 | 222.7k (222.2k–224.3k) | 17.6k | 4 | 85s | -27% |
| t4-isoweek-permalink | feature | baseline | 5/5 | 370.4k (306.4k–396.7k) | 20.3k | 12 | 61s |  |
| t4-isoweek-permalink | feature | harness | 5/5 | 275.1k (271.2k–321.5k) | 19.7k | 9 | 61s | -26% |
| t5-locate-pagersize | locate | baseline | 5/5 | 171.1k (170.0k–171.8k) | 14.6k | 4 | 15s |  |
| t5-locate-pagersize | locate | harness | 5/5 | 178.5k (178.2k–179.0k) | 16.2k | 3 | 16s | +4% |

## By category

| category | baseline pass | harness pass | median Δ tokens vs baseline |
|---|---|---|---|
| bugfix | 5/5 | 5/5 | harness +30% |
| cross-module | 5/5 | 5/5 | harness -27% |
| feature | 5/5 | 5/5 | harness -26% |
| locate | 10/10 | 9/10 | harness +5% |

## Harness overhead

- Reused context from `/home/user/ctx-harness/bench/results/20261015-220103-claude/ctx`; bootstrap cost not measured in this run.

## Failed runs

- t1-locate-permalink-error · harness · r4: d: no such file or directory)
