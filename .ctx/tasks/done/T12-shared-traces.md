# T12 · Shared trace store

## Goal
Let the curator learn from the whole team's sessions: traces can also go to a shared store, and `ctxh signals` reads them back. Nothing changes when it isn't configured.

## Scope
- `CTXH_TRACE_SINK`: a directory, an `http(s)://` endpoint (POST a trace; GET `?repo=` lists them) or `redis://` (RPUSH + LTRIM to 2000, LRANGE to read; a small RESP client on a socket, so no package is needed).
- `CTXH_TRACE_REPO`, else the `origin` URL with scheme and credentials stripped, keys the repo.
- `shared_trace`: what leaves the machine has no command output (`failed_commands` keep only `cmd`).
- `record` pushes after the local write; `signals` merges `sink_pull()` with local traces, deduplicated by session.
- A 3-second timeout; failures `warn_once` and never fail a session.
- Privacy section in the README.

## Acceptance criteria
- Unset: local behavior is unchanged (existing tests).
- Each sink kind: 3 sessions arrive, credentials are stripped from the repo key, command output is absent, and `signals` counts them as shared once local traces are gone.
- An unreachable sink warns and the local trace is still written.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Done: sink code in `bin/ctxh`, `SharedTraces` tests with in-process fakes for HTTP and Redis plus a directory sink, README section, env table, limits line, card.
- Decision: implement Redis over a raw socket (RESP2) instead of requiring `redis-py`, to keep the engine stdlib-only; it needs only AUTH, SELECT, RPUSH, LTRIM and LRANGE.
- Decision: drop command output from shared traces. The task says traces hold "commands and paths, not code", and failure output often quotes code or secrets. Local traces keep it for the local curator, as before.
- Live check: against a real `redis-server` (7.x from apt) on db 2, two Stop-hook runs created `ctxh:traces:ctxh-sandbox` with 2 entries, and `ctxh signals` read them back.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session).
- Verification: `python3 -m unittest discover -s tests` passes 68 tests (1 skipped without tree-sitter); `python3 bench/sandbox.py` smoke checks pass.
