# T19 · Review gate outside the agent (pre-commit / CI)

## Goal
An opt-in check, outside any agent session, that fails when code changes reach a commit or a PR without a review record. It covers other agents, humans, and the in-session blind spot the T20 pilot found (edits made through the shell never reach the Stop-hook gate).

## Scope
- Review record: `.ctx/reviews.json`, committed, mapping each reviewed code file to the git blob id of the content that was reviewed (`git hash-object`). Blob ids are the same in the working tree, the index and a commit, so a record made before committing matches in pre-commit and in CI, and any later edit invalidates it.
- `ctxh review-record [paths...]`: record the given code files, or by default every code file changed against HEAD (staged, unstaged, untracked). Creating the file is the opt-in.
- `ctxh review-check [--staged | --base REF]`: the code files changed (`--staged`: index vs HEAD; `--base REF`: `REF...HEAD`; default: working tree vs HEAD), compared against their blob at that point. Unreviewed files are listed and the exit status is 1. Deleted files and files `lang_of` doesn't treat as code are ignored, matching the in-session gate. `CTXH_REVIEW_GATE=0` skips it.
- `ctxh review-check --install-hook`: writes `.git/hooks/pre-commit` running `review-check --staged` (refuses to overwrite a hook it didn't write) and creates `.ctx/reviews.json` if missing.
- Stop hook: when `.ctx/reviews.json` exists and a reviewer ran after the session's last code edit, record the changed code files automatically, so Claude sessions that follow the protocol produce the record with no extra step.
- Docs: README (opt-in section with a CI snippet), engine docstring, card.

## Acceptance criteria
- An edit without a record fails `review-check`; `review-record` makes it pass; editing the file again fails it.
- `--staged` checks the staged blob; `--base main` in a branch checks the committed blobs.
- The pre-commit hook blocks an unreviewed commit and lets a reviewed one through.
- The Stop hook records only with `.ctx/reviews.json` present and a reviewer after the last edit.
- Existing tests unchanged; `python3 -m unittest discover -s tests` and `python3 bench/sandbox.py` pass.

## Risks
- `.ctx/reviews.json` is a shared file across branches; it holds one sorted key per path, so concurrent branches conflict only on the same file, which they'd conflict on anyway.
- A record proves someone ran `review-record`, not that the review was good. It is an audit trail, documented as such.

## Steps
1. Blob helpers, `review-record`, `review-check`, `--install-hook`.
2. Stop-hook auto-record.
3. Tests, docs, task status.

## Progress log
- Plan written by the coder (the planner subagent is not loaded in this cloud session); user asked to continue tasks.md.
- Steps 1-3 done: `changed_code`, `record_reviews`, `cmd_review_record`, `cmd_review_check` (with `--install-hook`) and the Stop-hook auto-record in `bin/ctxh`; `ReviewRecord` tests; README opt-in section with a CI snippet; card line.
- Decision: the record is git blob ids, not a reviewer entry in the progress log. A blob id is the same in the working tree, the index and a commit, so a record made before committing matches in pre-commit and in CI, and any edit after the review invalidates it. A progress-log line can't tell which content was reviewed.
- Decision: opt-in by the file's existence. The Stop hook writes a committed file only in repos that created `.ctx/reviews.json`, so nobody gets a new tracked file by default.
- Review: reviewed the diff myself (the reviewer subagent is not loaded in this cloud session). Found and fixed `--install-hook` recording every changed file (`record_reviews([])` was treated as "all"). Checked that deletions, non-code and ignored files are skipped, matching the in-session gate.
- Verification: `python3 -m unittest discover -s tests` passes 59 tests; `python3 bench/sandbox.py` smoke checks pass; scratch repo: unreviewed commit blocked by the hook, reviewed one let through, `--no-verify` bypass caught by `--base main`.
