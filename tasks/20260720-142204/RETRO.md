# Retro: parity + templating hardening

- TASK: 20260720-142204
- BRANCH: feature/parity-hardening
- REVIEW ROUNDS: 1 (APPROVE)

## What went well

- Capturing real fixtures immediately earned its keep: the very first single-
  digit-day entry (2026-01-02) exposed a real title bug (`%-d` non-padded vs the
  den's zero-padded `%d`) that the 3 original two-digit-day fixtures could never
  have caught. "Capture real CLI output" is the lesson that paid here.
- Diffing the parser against the freshly captured `daily --json` BEFORE committing
  surfaced the `[~]` divergence as data, not theory - so the conversation with
  the user was concrete (daily returns tasks=[], new tool surfaces the [x] tasks).
- Reading the old daily.nix / today.nix awk directly (today_tasks, carry-forward
  grep, add_weight/macros/notes) meant every parity claim was checked against the
  reference implementation, not guessed.

## What went wrong

- Nothing broke, but the title bug had been latent since the bootstrap task -
  the original fixtures were all two-digit days, a classic sampling blind spot.
  Root cause: the bootstrap chose 3 consecutive days (all >= 10) as fixtures, so
  the padding branch was never exercised.

## Decisions recorded

- `[~]` handling: the old `daily` drops the whole Today list at the first
  non-`[ ]`/`[x]` line (data loss). The user confirmed `[~]` was a retired
  "won't do" marker and only `[ ]`/`[x]` are used going forward, with non-standard
  markers simply skipped. So the new tool deliberately diverges from daily and
  surfaces the real tasks. Saved as a project memory (den-task-checkbox-convention)
  and pinned by `test_only_standard_checkboxes_are_tasks`. Not a golden fixture,
  because asserting equality with daily here would be asserting the bug.

## What to improve next time

- When picking golden/sample fixtures, deliberately span the FORMATTING axes, not
  just content: single- vs double-digit day, empty vs populated section, CRLF vs
  LF, first-of-month, etc. Consecutive real days share formatting and hide
  padding/boundary bugs.

## Action items

- [x] LESSONS.md: `sample-fixtures-span-formatting-axes`.
- [x] Memory: den-task-checkbox-convention (the `[~]` decision).
