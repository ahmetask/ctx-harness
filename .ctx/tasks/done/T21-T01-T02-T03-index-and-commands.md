# T21 + T01 + T02 + T03 · Dogfooding: what the index sees and which commands it keeps

## Goal
Make `ctxh` useful on this repo: index the engine (an extensionless script), keep the benchmark fixture out of the index, verify the repo's real test command from CI, and stop re-index from dropping commands an agent fixed or added.

## Scope
- `plugins/ctx-harness/bin/ctxh`:
  - T21: `.ctxignore` (gitignore-style patterns, `!` negation, last match wins) read by `list_files`; `index_lag` respects it too, so fixture edits don't trigger a background re-index. `testdata` joins `SKIP_DIRS`.
  - T01: `lang_of(path)`: suffix in `LANGS`, else (no suffix) the shebang's interpreter (python, node, ruby, bash/sh). Used by `build-index`, `index_lag` and `unreviewed_edit`. Shell gets a small symbol regex, and `.sh`/`.bash` suffixes map to it too. Shebang scripts count as entry points.
  - T02: CI `run:` lines (including `run: |` blocks) that look like test/lint/build commands become candidates with `source: ci`, `in_ci: true`. Install/deploy/publish lines and lines with `${{ }}` expressions are skipped.
  - T03: commands with `source: manual` survive re-index with their verification; `replaces: <cmd>` drops the detected command it fixes. New `ctxh add-command <kind> <cmd> [--replaces <old>]` writes and verifies one. `--verify` re-verifies manual commands.
- `.ctxignore` for this repo: `bench/demo/`, `bench/tasks/`.
- Tests in `tests/test_ctxh.py` for each task.
- Docs: README (engine, `.ctxignore`), build skill (use `add-command`), `tasks.md` statuses.

## Acceptance criteria
- `ctxh q find cmd_hook_stop` answers `plugins/ctx-harness/bin/ctxh:<line>`; `index_lag` and the review gate count edits to `ctxh`.
- `ctxh q hot` here lists engine and bench code, no `bench/demo` files; no `cd bench/demo/template && go ...` commands.
- `build-index --verify` here verifies `python -m unittest discover -s tests -v` (source `ci`); `npm install -g ...` is not a candidate.
- A `manual` command survives `build-index`, is re-verified by `--verify`, and `ctxh skeleton` lists it.
- `python3 -m unittest discover -s tests` passes.

## Risks
- Reading the first line of every extensionless tracked file: bounded to 128 bytes each, cheap.
- CI classification false positives: keep the keyword list conservative, skip anything with installs or GitHub expressions.
- Verifying the CI unittest command runs the whole suite (~45s, needs Go) during `--verify` on this repo. Acceptable; it is the real check.
- Module grouping of `plugins/ctx-harness/bin/ctxh` stays `plugins` until T04.

## Steps
1. T21 `.ctxignore` + test.
2. T01 shebang languages + tests (index, gate).
3. T02 CI candidates + test.
4. T03 manual commands, `add-command` + test.
5. Docs, rebuild this repo's index with `--verify`, check acceptance on this repo.

## Progress log
- Plan written by the coder (planner subagent not loaded in this cloud session); user asked to implement.
- Step 1 (T21) done: `ignore_rules`/`ignored` (gitignore subset: globs, `**`, `[]`, trailing `/`, leading or middle `/` anchors, `!` negation, last match wins) applied in `list_files` and `index_lag`. `testdata` added to `SKIP_DIRS`. This repo's `.ctxignore`: `bench/demo/template/` (not `bench/demo/`, so `materialize.py` stays indexed) and `bench/tasks/`.
- Step 2 (T01) done: `shebang_lang`/`lang_of` (python, node, ruby, bash/sh/zsh; `env -S` handled). Shell symbols (`function f`, `f() {`) and `.sh`/`.bash` suffixes added. Extensionless scripts count as entry points. Used in `build-index`, `index_lag` (also counts deleted files that were indexed) and `unreviewed_edit`.
- Found and fixed: symbol regexes for python, java, rust, ruby and kotlin started with `^\s*`, which also matches newlines, so `q find` reported the line of the first blank line above a definition. Now `[ \t]`. Covered by the shebang test (`bin/tool:5`).
- Step 3 (T02) done: `ci_run_lines` (single-line and `run: |` blocks, `\` continuations, a bare `cd X` carried into later lines) and `ci_kind` (conservative keyword lists; installs, deploys, docker and `${{ }}` lines skipped). CI candidates get `source: ci`.
- Step 4 (T03) done: `merge_commands` keeps `source: manual` entries and their results, drops detected commands named by `replaces`. `verify_command` shared by `--verify` and the new `ctxh add-command <kind> <cmd> [--replaces X] [--no-verify]`. Build skill now uses it.
- Step 5 done: README (what gets indexed, `.ctxignore`, commands), build skill, `tasks.md` statuses. This repo: `ctxh q find cmd_hook_stop` -> `plugins/ctx-harness/bin/ctxh:1178`; `q hot` lists engine and bench code only; `build-index --verify` verified `python -m unittest discover -s tests -v` (source ci, ~60s); no `go` commands from the demo.
- Behavior change to note: edits to `.sh`/`.bash` files and shebang scripts now count for the review gate.
- Review: the `ctx-harness:reviewer` subagent isn't loaded in this cloud session, so I reviewed the diff myself. Fixed: leading-`/` anchoring lost in `ignore_rules` (caught before tests), a duplicated assignment in `cmd_add_command`, Java's `|\s` and Kotlin's `\w+\s+` still spanning lines. Accepted: `python` (not `python3`) in a CI line may fail verification on machines without `python`; the tail says why and `add-command --replaces` fixes it.
- Verification: `python3 -m unittest discover -s tests` passes 32 tests. `ctxh check` ok. `ctxh stale`: card `plugins-ctx-harness.md` is stale (ctxh changed, and its invariants about `LANGS`-only indexing and dropped hand-added commands are now false); `.ctx/map.md` still says the index doesn't see `ctxh`. `/ctx-harness:curate` is due.
- T20 note: rerun the benchmark after this lands (T01–T03 change what the harness indexes and verifies).
