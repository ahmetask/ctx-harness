# Iterative benchmark hugo-iterate-2026-10-17

Suite `hugo-iterate`, 5 repeats, chain: i1-chunk -> i2-chunk-pad -> i3-window -> i4-maps. Medians per step.

| arm | passes | total tokens | median steps/session | median files read | cost |
|---|---|---|---|---|---|
| baseline | 20/20 | 4818.7k | 6 | 3 | $2.34 |
| harness | 20/20 | 5321.2k | 9 | 3 | $2.59 |

harness vs baseline: tokens +10%, cost +11%

## By step (median tokens, steps, files read; passes)

| step | baseline | harness | change |
|---|---|---|---|
| 1 i1-chunk | 209.0k, 4 steps, 0 reads; 5/5 | 220.2k, 4 steps, 0 reads; 5/5 | +5% |
| 2 i2-chunk-pad | 213.0k, 9 steps, 3 reads; 5/5 | 261.5k, 10 steps, 3 reads; 5/5 | +23% |
| 3 i3-window | 207.5k, 5 steps, 2 reads; 5/5 | 224.1k, 6 steps, 2 reads; 5/5 | +8% |
| 4 i4-maps | 313.0k, 9 steps, 3 reads; 5/5 | 323.6k, 10 steps, 3 reads; 5/5 | +3% |
