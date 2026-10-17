# Benchmark 20261017-095824-claude

Agent: claude · tasks: 5 · repeats: 5 · plan/review gates: off

## Overall

| mode | runs | pass rate | median tokens | median uncached | median steps | tokens per pass | median time | cost | cost per pass |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 25 | 100% | 250.3k | 14.1k | 6 | 246.1k | 23s | $2.23 | $0.089 |
| harness | 25 | 96% | 262.0k | 16.0k | 6 | 259.2k | 25s | $2.37 | $0.099 |

## Per task

| task | category | mode | pass | median tokens (IQR) | uncached | steps | time | Δ tokens vs baseline |
|---|---|---|---|---|---|---|---|---|
| s1-grouped-pagination | bugfix | baseline | 5/5 | 250.9k (250.3k–292.8k) | 13.4k | 6 | 32s |  |
| s1-grouped-pagination | bugfix | harness | 4/5 | 270.2k (262.0k–310.0k) | 16.0k | 6 | 32s | +8% |
| s2-delimit-two | bugfix | baseline | 5/5 | 207.5k (207.0k–210.0k) | 12.1k | 5 | 18s |  |
| s2-delimit-two | bugfix | harness | 5/5 | 172.6k (172.4k–172.9k) | 13.4k | 4 | 18s | -17% |
| s3-absurl-root | bugfix | baseline | 5/5 | 213.0k (211.2k–259.1k) | 15.5k | 6 | 26s |  |
| s3-absurl-root | bugfix | harness | 5/5 | 265.8k (264.7k–314.3k) | 16.9k | 7 | 58s | +25% |
| s4-toc-end-level | bugfix | baseline | 5/5 | 257.1k (255.7k–309.0k) | 14.8k | 6 | 26s |  |
| s4-toc-end-level | bugfix | harness | 5/5 | 263.0k (221.2k–354.9k) | 16.9k | 6 | 30s | +2% |
| s5-getenv-patterns | bugfix | baseline | 5/5 | 250.2k (250.0k–250.7k) | 13.3k | 6 | 19s |  |
| s5-getenv-patterns | bugfix | harness | 5/5 | 221.6k (218.5k–223.4k) | 15.7k | 6 | 21s | -11% |

## By category

| category | baseline pass | harness pass | median Δ tokens vs baseline |
|---|---|---|---|
| bugfix | 25/25 | 24/25 | harness +2% |

## Harness overhead

- Bootstrap (`/ctx-harness:build`, once per repo): 679.0k tokens, $0.18, 1048s.
- No net token saving on these tasks: the harness does not pay for its bootstrap here.

## Failed runs

- s1-grouped-pagination · harness · r1: go test -count=1 -run Hidden ./resources/page/ (exit 1)
