# Retro: Release mechanism for v0.1.0: CHANGELOG, CI, tag-triggered GitHub release

- TASK: 20260731-152711
- BRANCH: feat/release-v0.1.0
- REVIEW ROUNDS: 2

## What went well

- Copying two working precedents (macros.nvim's reusable-workflow + tag guard,
  tatr's changelog-sourced notes) rather than designing from scratch made the
  plan short and the disagreements between them explicit enough to settle in
  DECISION.md before any code.
- The version-drift pytest was written red first and mutation-checked by the
  reviewer, so the one invariant that CI can only catch at tag time is pinned
  locally.
- Running the workflow's own `grep`/`awk` against the working tree before
  committing caught nothing, but the reviewer running the same extraction and
  reading its OUTPUT caught the link-block leak.

## What went wrong

- The release notes dragged the changelog's link-reference block into the
  published body. The awk range ended only on the next `## [` heading, which is
  correct for every section except the oldest - and the first release is
  precisely the oldest section. The extraction was checked for "non-empty",
  not for what it contained.
- Both version guards used `grep -qx` with an unescaped version string, so the
  `.` separators matched any character. Harmless in practice, wrong in kind.
- The diff declared the mutation subcommands shipped in `CHANGELOG.md` while
  `README.md` still labelled them "(planned - parity port)". The doc sweep
  looked for stale mentions of what the diff CHANGED (`--version`), and missed
  that publishing a changelog re-dates every "planned" claim in the repo.

## What to improve next time

- When a script extracts a slice of a file, assert on the slice's content
  (first and last line), not just that it is non-empty.
- A first-of-its-kind record (first changelog section, first row, first entry)
  sits at a boundary the general case never exercises; test the extremes, not
  the middle.
- Backfilling status into a new document (a changelog, a release note) is a
  claim about the whole repo: sweep for contradicting status prose, not only
  for renamed symbols.

## Action items

- None requiring a follow-up task; all findings were fixed in round 2.
- Ledger: `extraction-assert-on-content` and
  `status-doc-backfill-sweeps-status-prose` appended to `LESSONS.md`.
