---
name: status
description: Shows the state of this repo's ctx-harness context and token metrics. Use when the user asks whether the context is fresh, what is stale, or whether the harness is saving tokens.
tools: ctxh
manual: true
---
# Context status

Run these and summarize the results in a few lines, without changing anything:

1. `ctxh version`
2. `ctxh stale`: stale cards mean `{{command:curate}}` is due.
3. `ctxh check`: budget or dead-path problems.
4. `ctxh stats`: harness vs baseline token medians and break-even, if any sessions were recorded with `CTXH_DISABLED=1` for comparison.

If `.ctx/` does not exist, say so and point to `{{command:build}}`.
