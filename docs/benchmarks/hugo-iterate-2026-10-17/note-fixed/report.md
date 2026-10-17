# Iterative benchmark 20261017-161035-iterate-claude

Suite `hugo-iterate`, 5 repeats, chain: i1-chunk -> i2-chunk-pad -> i3-window -> i4-maps. Medians per step.

| arm | passes | total tokens | median steps/session | median files read | cost |
|---|---|---|---|---|---|
| harness | 20/20 | 5189.9k | 8 | 2 | $2.50 |

## By step (median tokens, steps, files read; passes)

| step | harness |
|---|---|
| 1 i1-chunk | 218.6k, 8 steps, 2 reads; 5/5 |
| 2 i2-chunk-pad | 217.7k, 9 steps, 3 reads; 5/5 |
| 3 i3-window | 222.4k, 6 steps, 2 reads; 5/5 |
| 4 i4-maps | 319.4k, 8 steps, 3 reads; 5/5 |
