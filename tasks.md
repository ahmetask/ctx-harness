# ctx-harness gap backlog

Known gaps, one task each. We work through them with the harness itself (this repo has `.ctx/`).

## How to work a task

1. Pick the next `todo` task below and tell the coder: "work on T0x from tasks.md".
2. The coder asks `ctx-harness:planner` for a plan. The plan goes to `.ctx/tasks/active.md`, built from the task's **Problem** and **Done when**. Approve it before any code is written.
3. Implement, run `python3 -m unittest discover -s tests`, then run `ctx-harness:reviewer` (the Stop hook enforces this). For behavior a unit test can't show (hooks in a live session, indexing a real repo), also try it in the demo: `python3 bench/sandbox.py`, then the interactive command it prints or `--prompt "<task>"`.
4. Move `active.md` to `.ctx/tasks/done/T0x-<name>.md`, set the status here to `done`, and run `/ctx-harness:curate` if `ctxh stale` reports cards.

Status: `todo` · `planned` · `in progress` · `done` · `dropped`. Priority: P1 (blocks dogfooding or measurement), P2 (core value), P3 (nice to have).

## Summary

| ID | Task | Area | Priority | Status |
|---|---|---|---|---|
| T01 | Index extensionless scripts by shebang | dogfooding | P1 | done |
| T02 | Promote CI `run:` test commands to candidates | dogfooding | P1 | done |
| T03 | Keep hand-verified commands across re-index | dogfooding | P1 | done |
| T04 | Module grouping and markdown-only modules | dogfooding | P2 | done |
| T05 | Document the dogfooding setup (installed plugin vs working tree) | dogfooding | P2 | done |
| T06 | Transcript parser fixtures and version guard | measurement | P1 | done |
| T07 | Benchmark platform with a demo repo | measurement | P1 | done |
| T08 | Mid-session context management (compaction) | context | P2 | done |
| T09 | Hook-enforced plan gate for 3+ file changes | enforcement | P2 | done |
| T10 | Semantic/keyword retrieval fallback for `ctxh q` | retrieval | P3 | done |
| T11 | Optional tree-sitter parsing | retrieval | P3 | done |
| T12 | Shared trace store for team-wide curation | learning | P3 | done |
| T13 | Split `ctxh` into tool-neutral core + Claude adapter | portability | P2 | done |
| T14 | `ctxh init --target` instruction files for other agents | portability | P2 | done |
| T15 | Configurable tool names for traces and the review gate | portability | P2 | done |
| T16 | Tool-neutral agent/skill prompts with per-tool generators | portability | P3 | done |
| T17 | Hook adapters for other agents | portability | P3 | done |
| T18 | Tool label in metrics and vendor-neutral token counting | portability | P3 | done |
| T19 | Review gate outside the agent (pre-commit / CI) | enforcement | P3 | done |
| T20 | Run the real benchmark and publish results (pilot in docs/benchmark.md) | measurement | P1 | done |
| T21 | Exclude fixture dirs from indexing (`.ctxignore`) | dogfooding | P1 | done |
| T22 | Don't repeat prompt hints within a session | context | P3 | done |
| T23 | Session ledger on compaction when there is no plan | context | P2 | done |
| T24 | Scoped learned lines, delivered with the hint | learning | P2 | done |
| T25 | Usage evidence for pruning learned lines | learning | P3 | done |
| T26 | User redirects as a learning signal | learning | P3 | done |
| T27 | Screen shared traces before the curator reads them | learning | P3 | done |

Suggested order: T21 → T01 → T02 → T03 → T20 (baseline numbers before changing behavior) → T06 → T13 → T15 → T09 → T04 → T05 → T14 → the rest. For T22–T27: T22 → T23 → T24 (uses T22's per-session state) → T25 → T26 → T27.

---

## Dogfooding (found by enabling the harness on this repo)

### T01 · Index extensionless scripts by shebang
- **Problem:** `list_files` and `index_lag` keep only files whose suffix is in `LANGS`. In this repo, `build-index` indexed 1 file (`tests/test_ctxh.py`) and missed the engine `plugins/ctx-harness/bin/ctxh`. So `ctxh q` knows nothing about the engine, and edits to it never trigger a background re-index. The review gate also ignores edits to it.
- **Done when:** files without a suffix whose first line is a known shebang (python, node, ruby, bash optional) are indexed with the right language. `ctxh q find cmd_hook_stop` answers with `plugins/ctx-harness/bin/ctxh:<line>`. `index_lag` and `unreviewed_edit` count those files. A test covers it.

### T02 · Promote CI `run:` test commands to candidates
- **Problem:** `detect_commands` collects CI `run:` lines into `ci_runs` but only proposes commands from Makefile, package.json, go.mod, Cargo.toml and pytest metadata. This repo's `python -m unittest discover -s tests -v` was never proposed or verified, so the map has no verified command.
- **Done when:** CI run lines that look like test, lint or build commands (unittest, pytest, go test, npm test, make targets and so on) become candidates with `source: ci` and `in_ci: true`. Install or deploy lines (`npm install -g`, `pip install`, `docker push`) are skipped. `build-index --verify` verifies the unittest command here. A test covers it.

### T03 · Keep hand-verified commands across re-index
- **Problem:** `build-index` rebuilds `commands.json` from detection and keeps earlier verification results only for commands it detects again. The build skill tells agents to fix a failing invocation, but any fixed or added command disappears on the next (background) re-index.
- **Done when:** a command added or fixed by an agent (for example marked `source: manual`) survives re-index and is re-verified with `--verify`. `ctxh skeleton` lists it. A test covers it.

### T04 · Module grouping and markdown-only modules (done)
A directory holding a package manifest (including a plugin's `.claude-plugin/plugin.json`) is a module, so this repo's card for `plugins/ctx-harness` now matches. Markdown is indexed as `role: docs` (headings as symbols, in co-change, outside the gates, `q hot` and staleness). `build-index` warns and `ctxh check` fails on a card whose module is not in the index. See `.ctx/tasks/done/T04-module-grouping.md`.

### T21 · Exclude fixture dirs from indexing
- **Problem:** `list_files` indexes everything git tracks outside `SKIP_DIRS`. Since `bench/demo/template/` landed, the demo's 43 Go files dominate this repo's own index: `ctxh q hot` lists only demo files, `q find IdempotencyKey` answers from the fixture, and the nested `go.mod` adds `cd bench/demo/template && go ...` as this repo's commands. Any repo with fixtures, vendored samples or test data has the same problem.
- **Done when:** a `.ctxignore` (gitignore-style patterns, read by `list_files` and `detect_commands`) excludes paths from the index and command detection. `testdata/` is skipped by default (Go convention). This repo ignores `bench/demo/` and `bench/tasks/`. `ctxh q hot` here lists engine and bench code, and a test covers it.

### T05 · Document the dogfooding setup (done)
Checked on Claude Code 2.1.292: `--plugin-dir ./plugins/ctx-harness` replaces the installed `ctx-harness@ctx-harness` for the session (hooks run once, and the agents and `bin/ctxh` are the local copy), so there are no double hooks and the settings stay as they are. The README "Development" section explains it. See `.ctx/tasks/done/T05-dogfooding-setup.md`.

## Measurement

### T06 · Transcript parser fixtures and version guard (done)
Fixtures in `tests/fixtures/transcripts/` (a session with a subagent, a reviewed session, and two drifted formats) pin tokens, files, commands and the gate decision. Tool names live in one `TOOLS` table, and a transcript with no `usage` or no known tool name makes `ctxh usage` fail and the Stop hook warn once instead of recording zeros. See `.ctx/tasks/done/T06-transcript-fixtures.md`.

### T07 · Benchmark platform with a demo repo (done)
- Built `bench/`: a Go demo repo (`shopd`) with scripted history, 6 tasks with hidden checks and reference solutions, a runner (`claude`, `fake` and `noop` agents) and a report. See `bench/README.md` and `.ctx/tasks/done/T07-benchmark-platform.md`.

### T20 · Run the real benchmark and publish results (done 2026-10-09; see docs/benchmark.md)
- **Problem:** the platform exists, but no real harness-vs-baseline numbers do yet. The README's claim that the harness is cheaper is still unproven.
- **Pilot (2026-10-07):** 2 tasks × 1 repeat in `docs/benchmark.md`. All passed; harness −7% on t2, +129% on t4 (planner + reviewer overhead), bootstrap 2.2M tokens. It also found that shell edits bypass the review gate. The full run is still to do.
- **Done when:** `python3 bench/run.py --agent claude --repeats 3` has run on at least one model, and its `report.md` plus a short reading (where the harness wins or loses, and why) is in `docs/benchmark.md`. Rerun after T01–T03, since they change what the harness indexes on Go repos. Optional later: a second demo repo in another language, or a public repo with tasks.

## Context management and enforcement

### T08 · Mid-session context management (done)
Compaction fires `SessionStart` with source `compact`, which already re-ran `hook-start` (protocol and map). With an active plan, `hook-start` now adds the plan's title, path and the last 8 progress-log entries on `compact` and `resume`. This was checked live with `/compact` in the sandbox, and tests cover it. See `.ctx/tasks/done/T08-compaction.md`.

### T09 · Hook-enforced plan gate (done)
The Stop hook blocks once when 3+ distinct code files changed with no plan (`.ctx/tasks/active.md`, or a planner call in the session), before the review gate; both share `gate_once` and `.ctx/tmp/gates/<session>.json`. Opt-in since 0.4.0: `CTXH_PLAN_GATE=1` turns it on (the gates cost a subagent and a turn; see `docs/benchmark.md`). See `.ctx/tasks/done/T09-plan-gate.md`.

### T19 · Review gate outside the agent (done)
Opt-in `.ctx/reviews.json` (code path -> reviewed blob id), `ctxh review-record`, `ctxh review-check [--staged | --base REF]`, `--install-hook` for pre-commit, and auto-recording from the Stop hook when the reviewer ran after the last edit. See `.ctx/tasks/done/T19-review-gate-outside.md`.
- **Problem:** the review gate only exists inside Claude Code sessions. Other agents and humans bypass it. Inside a session it is also blind to edits made through the shell: in the T20 pilot, an agent edited a file with `cat >>` and the gate never fired (see `docs/benchmark.md`). Checking `git diff` instead of edit-tool calls would cover both.
- **Done when:** an optional pre-commit or CI check flags code changes that have no reviewer record (for example a review entry in the task's progress log or a gate state file), documented as opt-in.

## Retrieval

### T10 · Semantic or keyword retrieval fallback (done)
`ctxh q search <words>` (BM25 over split names, nearby comments, docstrings and doc sections), and `q find` falls back to it for concepts. `ctxh signals` prints the empty-result rate. On 13 concept queries in the shopd sandbox, empty answers went from 11/13 to 0/13, with a useful file in the top 3 for about 9. See `.ctx/tasks/done/T10-keyword-search.md`.
- **Problem:** `ctxh q` is structural (imports, symbols, history). Questions phrased in domain terms ("where is the retry policy?") come back empty when names don't match, and the scout falls back to grep.
- **Done when:** a zero-dependency fallback, for example `ctxh q search <terms>` using BM25 over symbols, docstrings and comments, answers concept queries with `file:line`. Empty-result rates in `ctxh signals` are compared before and after.

### T11 · Optional tree-sitter parsing (done)
When `tree_sitter` and a grammar are importable, Python, Go, JS/TS, Java, Rust and Ruby are parsed from the syntax tree (`ts_extract`); otherwise the regexes run. The full suite passes both ways (a new CI job installs the grammars). On this repo and the shopd demo, the only differences are improvements: a nested Go type found, and fixture code inside test strings no longer indexed. See `.ctx/tasks/done/T11-tree-sitter.md`.
- **Problem:** import and symbol extraction is regex-based. It misses nested definitions and multi-line imports, and has no call graph.
- **Done when:** if `tree_sitter` is importable, it is used for supported languages, otherwise the regex path is used. Results on the existing tests are identical or better, and the stdlib-only default is preserved.

## Learning

### T12 · Shared trace store (done)
`CTXH_TRACE_SINK` (a directory, an http(s) URL or `redis://`) receives each harness trace, minus command output. `ctxh signals` merges it with local traces. Unset means unchanged behavior, and privacy is documented in the README. See `.ctx/tasks/done/T12-shared-traces.md`.
- **Problem:** traces live in each machine's `.ctx/traces/`, so the curator only learns from one developer's sessions.
- **Done when:** an optional sink (env-configured: a directory, an HTTP endpoint or Redis) receives traces, and `ctxh signals` can read from it. Local behavior is unchanged when it isn't configured. Privacy is documented: traces hold commands and paths, not code.

## Portability (other coding agents)

### T13 · Split `ctxh` into core + Claude adapter (done)
`bin/ctxh` is tool-neutral and loads `plugins/ctx-harness/adapters/<CTXH_TOOL>.py` (default `claude`). The adapter owns the project root, hook events in, context and block replies out, and a normalized trace out of the transcript; the interface is in `adapters/README.md`. Existing tests pass unchanged, and a toy adapter test drives hooks, metrics and both gates. See `.ctx/tasks/done/T13-T15-adapter.md`.

### T14 · `ctxh init --target` (done)
`ctxh init --target agents-md|gemini|cursor|aider[,...]` writes a marked block into `AGENTS.md`, `GEMINI.md`, `.cursor/rules/ctx-harness.mdc` or `CONVENTIONS.md` (plus `read:` in `.aider.conf.yml`). Re-runs replace only the block, and the README has an "Other agents" section. See `.ctx/tasks/done/T14-init-targets.md`.

### T15 · Configurable tool names (done)
The read / edit / shell / subagent mapping is the adapter's `TOOLS`; the engine only sees each call's role. Done with T13.

### T16 · Tool-neutral agent and skill prompts (done)
Prompts live once in `plugins/ctx-harness/prompts/` with placeholders for agent names, commands and tool names. `ctxh export --tool claude` regenerates `agents/` and `skills/` byte-identically (CI checks it); `ctxh export --tool gemini --out DIR` writes a complete Gemini CLI extension (subagents, commands, the build skill, hooks, the engine), which `gemini extensions validate` accepts. See `.ctx/tasks/done/T16-neutral-prompts.md`.

### T17 · Hook adapters for other agents (done)
Gemini CLI gets `adapters/gemini.py`: SessionStart, BeforeAgent and AfterAgent run `ctxh hook-start|hook-prompt|hook-stop --tool gemini`, with JSON replies and a session-log reader that replays patches and rewinds. Tested on payloads assembled from Gemini's hook reference and recorder source. Gemini CLI 0.63.0 ran the start and prompt hooks live (no API key, so no model turn reached the stop hook). Tools without a stop hook use the T19 review record. See `.ctx/tasks/done/T17-gemini-hooks.md`.

### T18 · Tool label and vendor-neutral token counting (done)
Metric records carry `tool`. `ctxh stats` groups by tool and label, and pairs harness and baseline runs only within a tool. `ctxh usage --gateway <requests.jsonl> --tool <agent>` imports per-session usage from an LLM gateway log, with either Anthropic or OpenAI field names. See `.ctx/tasks/done/T18-tool-label.md`.

## Ideas from Kiro Crew (2026-10-09)

Kiro Crew (`kirodotdev/KiroCrew`) is a persistent agent gateway with its own context assembly and memory. These are the parts that fit a repo-scoped, stdlib-only harness. Left out on purpose: embeddings and vector memory (BM25 already answers concept queries, and Kiro's own code says its cosine admission threshold is not calibrated), user-preference consolidation (that is the agent's own memory, not repo context), and a budget table of shares (the injection is about 1.5k tokens and `ctxh check` already caps every file; revisit if T24 grows it).

### T22 · Don't repeat prompt hints within a session (done)
- **Problem:** `prompt_hint` keeps no state. A follow-up prompt that matches the same module re-sends the same leads and card path, about 100 tokens each time, while they are still in context. Kiro Crew keeps a per-session record of the skill bodies it injected and sends a body again only after compaction (`ContextBuilder._dedup_triggered_bodies`).
- **Done when:** `hook-prompt` records the leads and card it showed in `.ctx/tmp/hints/<session>.json`, leaves out leads already shown, and stays silent when nothing is new. `hook-start` clears the record on source `compact` and `clear`. Tests: the same prompt twice gives a silent second run; after a `compact` start it fires again.

### T23 · Session ledger on compaction when there is no plan (done)
- **Problem:** after compaction, `hook-start` restores the protocol and the map, and the plan's progress tail only when `.ctx/tasks/active.md` exists. Since 0.4.0 plans are opt-in, so most compacted sessions get no task state from the harness and rely on the compaction summary, which loses exact details such as which files were already edited and which validation command last failed. Kiro Crew prepends a work-ledger snapshot (goal, phase, next step, last 3 attempts) to each long-running cycle so it starts from durable state, not transcript memory (`session_ledger.render_snapshot`).
- **Done when:** on source `compact` or `resume`, `hook-start` reads the event's transcript through the adapter and adds a ledger of at most 10 lines: code files edited (in order), the last run of a verified command from `commands.json` and whether it failed (first output line), the last 3 failed commands, and subagents called. It is a pure function of the trace, with no model call. It is shown only when the session edited files or ran commands, next to the plan note when one exists, without repeating it. Startup output is unchanged. A live `/compact` in the sandbox confirmed (2026-10-09, Claude Code 2.1.x, ~$0.40) that the transcript passed on `compact` still holds the pre-compaction tool calls, and a fixture test covers the rendering. The bench tasks are too short to compact, so measuring this needs a long task.

### T24 · Scoped learned lines, delivered with the hint (done; the bench measurement is not run, it costs money)
- **Problem:** `.ctx/learned.md` holds the facts that cost real exploration, but nothing in a Claude Code session loads it. The protocol doesn't mention it, and only a generated map line points at it, so whether an agent reads it is luck. Kiro Crew gives each lesson an optional `repo_scope` and injects lessons ranked against the request, whole entries only, inside a budget, naming what it left out.
- **Done when:** a learned line can start with a scope tag, `[<module>]` (a graph module) or `[*]`. `hook-start` injects the `[*]` lines, at most 5; over that, it names how many were left out and the file. When `prompt_hint` fires, it adds up to 2 lines scoped to the top hit's module, deduplicated per session with T22's record. `ctxh check` fails on a tag that is not a module. The curate prompt writes the tag. A test covers each path. Measure with a bench run where one learned line answers a task's gotcha.

### T25 · Usage evidence for pruning learned lines (done)
- **Problem:** curate step 4 says to remove learned lines that no recent trace touched, but nothing tells the curator which lines those are, so the step is a guess. Kiro Crew records when memories were accessed and decays them by age.
- **Done when:** `ctxh signals` lists each learned line with the number of traces, and the latest date, that read or edited a path, or ran a command, named in backticks on that line. Lines with no such trace among the newest N are listed as prune candidates. The curate prompt points at that section. A test covers it.

### T26 · User redirects as a learning signal (done)
- **Problem:** `signals` learns from files read, failed commands, empty index queries and coder notes, which the coder may skip. It misses the strongest signal: the user correcting the agent ("no, tax is computed in pricing, not orders"). Kiro Crew's consolidator extracts these implicit corrections into lessons, separately from explicit "remember this" requests.
- **Done when:** the adapter's `read_session` also returns user prompt text with its position. The local trace keeps up to 5 user prompts that follow a code edit in the same session (first 200 characters each) as `redirects`. `shared_trace` drops them, as it drops command output. `signals` prints them under "user redirects after an edit", and the curator applies the existing promotion rule. A fixture test covers it, and the README privacy section says what is kept locally.

### T27 · Screen shared traces before the curator reads them (done)
- **Problem:** with `CTXH_TRACE_SINK` set, `signals` prints commands, queries and paths from other machines straight into the curator's context, and the curator writes committed files from them. A command line can carry instruction-like text. Kiro Crew screens third-party text, drops matches with an audit record, and rewrites forged block markers before injecting anything.
- **Done when:** `signals` drops shared-trace strings that match `IMPERATIVE` or a small injection pattern (for example "ignore previous instructions", "system prompt"), and prints how many it dropped. Local traces are not screened. A test covers it.
