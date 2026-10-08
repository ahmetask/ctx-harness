# T11 · Optional tree-sitter parsing

## Goal
Use tree-sitter for import and symbol extraction when it is installed, keeping the stdlib-only regex path as the default, with results identical or better.

## Scope
- `ts_parser` / `ts_extract` in `bin/ctxh`: lazy, cached parsers for Python, Go, JavaScript, TypeScript/TSX, Java, Rust and Ruby, from the `tree_sitter` package plus each grammar package. Missing package or grammar, an incompatible API, or a parse error all mean `None`, and the regex path runs.
- Output in the regex path's shape (import specs fed to `resolve_import`, `[name, line]` symbols), so the rest of the index is unchanged. Definitions include nested functions and types and class methods. JS/TS `const`/`let` stay module-level only, as the regex has it.
- `CTXH_PARSER=regex` forces regexes. `graph.json` `stack.parsers` records which parser ran per language.
- CI: a job installs tree-sitter and the grammars and runs the full suite.

## Acceptance criteria
- Without tree-sitter, behavior is unchanged (all tests, sandbox).
- With tree-sitter, all tests pass, and outputs on real repos are identical or better.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Done: `ts_extract`, `parsers` in the stack, `Parsers` tests (one forced-regex test; one tree-sitter test, skipped when it is not installed, for nested Python defs, string content ignored, multi-line JS import, `require`, methods, Go nested type, and a language with no grammar falling back), CI job `engine-tree-sitter`, README and card.
- Decision: keep the regex path's output format rather than adding a call graph. The task asks for identical or better extraction; a call graph would change `graph.json` consumers and needs its own task.
- Comparison (scratch venv with tree-sitter 0.25 and the 7 grammars, `CTXH_PARSER=regex` vs auto):
  - shopd demo (Go): imports identical (173 edges); symbols 198 -> 199, the one addition is `key`, a type declared inside `SalesByDay` (internal/reports/sales.go:24).
  - this repo (Python): imports identical; symbols 262 -> 252, all 10 removed are `def`/`class` lines inside triple-quoted fixture strings in tests/test_ctxh.py (e.g. `OrderService`, `emit_block`), which the regex wrongly indexed.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session).
- Verification: `python3 -m unittest discover -s tests` passes 64 tests without tree-sitter (1 skipped) and with it in the venv (0 skipped); `python3 bench/sandbox.py` smoke checks pass.
