# Benchmark 20261016-071035-claude

Agent: claude · tasks: 5 · repeats: 5 · plan/review gates: off

## Overall

| mode | runs | pass rate | median tokens | median uncached | median steps | tokens per pass | median time | cost | cost per pass |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 25 | 100% | 247.6k | 14.3k | 6 | 249.5k | 23s | $2.23 | $0.089 |
| harness | 25 | 100% | 268.4k | 17.3k | 5 | 261.9k | 26s | $2.57 | $0.103 |

## Per task

| task | category | mode | pass | median tokens (IQR) | uncached | steps | time | Δ tokens vs baseline |
|---|---|---|---|---|---|---|---|---|
| s1-grouped-pagination | bugfix | baseline | 5/5 | 287.5k (247.2k–288.3k) | 13.1k | 7 | 29s |  |
| s1-grouped-pagination | bugfix | harness | 5/5 | 277.3k (224.6k–323.1k) | 18.1k | 5 | 28s | -4% |
| s2-delimit-two | bugfix | baseline | 5/5 | 207.9k (207.3k–208.0k) | 12.7k | 5 | 22s |  |
| s2-delimit-two | bugfix | harness | 5/5 | 223.9k (178.3k–268.4k) | 16.1k | 4 | 24s | +8% |
| s3-absurl-root | bugfix | baseline | 5/5 | 301.9k (212.7k–351.8k) | 16.2k | 8 | 65s |  |
| s3-absurl-root | bugfix | harness | 5/5 | 276.0k (269.7k–277.3k) | 18.4k | 6 | 38s | -9% |
| s4-toc-end-level | bugfix | baseline | 5/5 | 251.8k (250.3k–253.0k) | 14.7k | 7 | 25s |  |
| s4-toc-end-level | bugfix | harness | 5/5 | 313.0k (268.8k–370.5k) | 18.1k | 6 | 26s | +24% |
| s5-getenv-patterns | bugfix | baseline | 5/5 | 247.6k (207.3k–252.4k) | 13.1k | 6 | 20s |  |
| s5-getenv-patterns | bugfix | harness | 5/5 | 178.5k (177.6k–223.8k) | 16.0k | 4 | 22s | -28% |

## By category

| category | baseline pass | harness pass | median Δ tokens vs baseline |
|---|---|---|---|
| bugfix | 25/25 | 25/25 | harness -4% |

## Harness overhead

- Bootstrap (`/ctx-harness:build`, once per repo): 2078.5k tokens, $0.41, 1338s.
- Mean saving per task (paired medians): 5.6k tokens; break-even after ~371.0 tasks.
