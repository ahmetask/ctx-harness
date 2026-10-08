# T04 · Module grouping and markdown-only modules

## Goal
Modules match how a repo is actually split: a directory that holds a package manifest is a module, so `plugins/ctx-harness` (and `services/api`, `svc/` with its own `go.mod`) stop collapsing into their first path segment. Cards whose `module:` matches nothing get flagged instead of silently never going stale.

## Scope
- `package_roots(files)`: directories holding a package manifest (`package.json`, `pyproject.toml`, `setup.py`, `setup.cfg`, `go.mod`, `pom.xml`, `build.gradle(.kts)`, `Cargo.toml`, `Gemfile`, `composer.json`, `Chart.yaml`, or a plugin manifest `.claude-plugin/plugin.json`), excluding the repo root. Build/CI files (Makefile, Dockerfile, CI configs, tsconfig) do not make a module.
- `module_of(path, roots=())`: the deepest package root containing the file, then the existing rule applied below it (a container dir like `src/`, `internal/` adds one level). With no root, behavior is unchanged. Roots go into `graph.json` (`package_roots`) for `q module`.
- Decision on markdown: index `.md`/`.mdx` files as `lang: markdown`, `role: docs`, with headings as symbols and no imports. That makes `q find` answer for prompt and doc sections, puts prompt files into git co-change (`q cochange ctxh` shows the agents and skills that change with it), and lets a prompt-only module exist. Docs stay out of everything code-only: `lang_of` (so edits to them never hit the review/plan gates or make the index lag), PageRank/`q hot`, the stack's language counts, skeleton key files, and card "new files" staleness (all filter `role == "src"`).
- `card_module_problems()`: cards whose `module:` is not a graph module. `build-index` prints them (not with `--quiet`); `ctxh check` reports them as problems.
- This repo: the `plugins-ctx-harness` card now matches a graph module.
- Docs: README engine section, the card.

## Acceptance criteria
- A file under `plugins/x/` with `plugins/x/.claude-plugin/plugin.json` is in module `plugins/x`; `svc/internal/store/store.go` with `svc/go.mod` is in `svc/internal/store`; repos without nested manifests group exactly as before (existing tests unchanged).
- `ctxh q find <heading words>` finds a markdown section; editing a `.md` file does not trigger the review gate.
- A card with an unknown module is reported by `build-index` and fails `ctxh check`.
- Here: `ctxh q module plugins/ctx-harness/bin/ctxh` says `module plugins/ctx-harness` and names the card.
- `python3 -m unittest discover -s tests` and `python3 bench/sandbox.py` pass.

## Risks
- Large doc trees add graph size; `.ctxignore` covers that, and symbols stay capped at 200 per file.
- Changing module names renames modules in existing maps and cards; the new check reports any card left behind.

## Steps
1. `package_roots` + `module_of` + graph field.
2. Markdown docs nodes.
3. Card-module check in build-index and check.
4. Tests, docs, task status.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Steps 1-3 done: `package_roots` + `module_of(path, roots)`, roots saved as `graph.json` `package_roots` and used by `q module`; markdown nodes (`role: docs`, headings as symbols, fenced code blanked so `# comment` lines are not headings and line numbers hold); `card_module_problems` printed by `build-index` and counted by `check`.
- Decision: only package manifests make a module. Makefiles, Dockerfiles, CI files and tsconfig often sit in folders that are not packages (`docker/`, `scripts/`), and would fragment modules.
- Decision: markdown is indexed but is not a code language. Keeping it out of `lang_of` means edits to prompts or READMEs never trigger the plan or review gate or mark the index stale; they are picked up at the next re-index.
- Here: `ctxh q module plugins/ctx-harness/bin/ctxh` now says `module plugins/ctx-harness` and names its card; `q cochange ctxh` lists README, tests and tasks.md; `q find "review gate"` lands on the tasks.md heading.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session). Caught and fixed a heading line-number shift after removing fenced blocks (test now pins line 7). Checked that repos without nested manifests group exactly as before (existing tests and the shopd sandbox give the same 19 modules).
- Verification: `python3 -m unittest discover -s tests` passes 50 tests (47 before, existing ones unchanged). `python3 bench/sandbox.py --fresh` smoke checks pass.
