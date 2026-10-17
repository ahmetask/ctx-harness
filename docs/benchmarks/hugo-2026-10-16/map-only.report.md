# Benchmark 20261015-234950-claude

Agent: claude · tasks: 5 · repeats: 5 · plan/review gates: off

## Overall

| mode | runs | pass rate | median tokens | median uncached | median steps | tokens per pass | median time | cost | cost per pass |
|---|---|---|---|---|---|---|---|---|---|
| harness | 25 | 100% | 213.3k | 15.9k | 4 | 218.6k | 34s | $2.34 | $0.094 |

## Per task

| task | category | mode | pass | median tokens (IQR) | uncached | steps | time | Δ tokens vs baseline |
|---|---|---|---|---|---|---|---|---|
| t1-locate-permalink-error | locate | harness | 5/5 | 213.3k (213.2k–213.3k) | 13.4k | 4 | 16s |  |
| t2-escaped-colons | bugfix | harness | 5/5 | 172.0k (171.0k–172.5k) | 14.0k | 4 | 34s |  |
| t3-strings-reverse | cross-module | harness | 5/5 | 227.2k (220.4k–265.5k) | 17.4k | 4 | 84s |  |
| t4-isoweek-permalink | feature | harness | 5/5 | 317.0k (269.3k–319.3k) | 19.1k | 6 | 47s |  |
| t5-locate-pagersize | locate | harness | 5/5 | 177.2k (176.2k–177.7k) | 15.9k | 5 | 18s |  |

## Harness overhead

- Reused context from `/tmp/ctxmaponly/ctx`; bootstrap cost not measured in this run.
