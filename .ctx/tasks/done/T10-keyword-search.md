# T10 · Keyword retrieval fallback for `ctxh q`

## Goal
Concept questions ("where is the retry policy?", "double charge") get a `file:line` answer from the index even when no symbol is named that way, instead of an empty result and a grep.

## Scope
- `ctxh q search <terms...>`: BM25 (k1 1.2, b 0.75) over units built at query time from the indexed files, stdlib only:
  - one unit per symbol: its name (split on camelCase/snake_case, counted 3x), the comment block right above it, and comments/docstrings in the first lines of its body;
  - one unit per standalone comment block (3+ comment lines not attached to a symbol);
  - for markdown docs, one unit per heading with the lines under it.
  Terms are lowercased, split on identifier boundaries, light-stemmed (plural/-ing/-ed), with a small stopword list. Results: up to 8 `path:line  name  (score)` lines, code before tests at equal score.
- `ctxh q find <x>` with no symbol match falls back to the same search and prints `no symbol named 'x'; keyword matches:` followed by hits, so a concept query isn't an empty answer. The original `no symbol matching` message stays when search finds nothing too.
- `ctxh signals`: print the empty-result rate (`ctx_misses / ctx_queries`) so before/after can be compared on real traces.
- Prompts: scout and protocol mention `ctxh q search`.
- Docs: README engine section, card.

## Acceptance criteria
- On a test repo, `q search retry policy` finds the retry function by its docstring, and `q search double charge` finds the idempotency code by a comment, with names that share no token with the query.
- `q find` on a concept falls back to keyword matches; with nothing to match, the old message is unchanged (existing tests unchanged).
- On the shopd sandbox: a fixed set of concept queries, compared as `q find` empty rate before vs `q find`/`q search` after (recorded in the progress log).
- `signals` prints the empty-result rate.

## Steps
1. Tokenizer, unit extraction, BM25, `q search`.
2. `q find` fallback; `signals` rate.
3. Tests, sandbox comparison, prompts, docs.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Steps 1-3 done: `terms`, `search_units`, `keyword_search`, `q search`, the `q find` fallback, the `signals` empty-result rate; `KeywordSearch` tests; scout prompt, protocol and README mention `q search`.
- Decision: units are built at query time from the indexed files, not stored in `graph.json`. That costs nothing at index time and keeps the graph small; the query reads only indexed files.
- Decision: BM25 score times the fraction of query words a unit covers. Plain BM25 ranked `def charge` (name counted 3x) above a comment saying "double charge"; coverage fixes that without tuning weights per repo.
- Decision: the `q find` fallback header ("keyword matches for ... (not a symbol name)") avoids the words trace parsing counts as a miss, and `no keyword matches` is counted as one.
- Measurement (shopd sandbox, 13 concept queries such as "double charge", "retry policy", "release reserved stock", "order state transition"): `q find` empty before 11/13, after 0/13. A useful file in the top 3 for about 9 of 13; misses: "double charge" (the idempotency comment says "one charge", not "double"), "tax before discount", "price filter" (the feature doesn't exist yet), "low stock alert" partly.
- Live check: `sandbox.py --prompt "Where does this service prevent charging a customer twice...?"` answered correctly (`internal/payments/idempotency.go:5`) but went straight to Grep for "idempot", not `q search`. The agent knew the term; whether agents reach for `q search` on vaguer questions needs real traces (`ctxh signals` now prints the empty-result rate to compare).
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session).
- Verification: `python3 -m unittest discover -s tests` passes 62 tests; `python3 bench/sandbox.py` smoke checks pass.
