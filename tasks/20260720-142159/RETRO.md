# Retro: today task mutations + safe write-back foundation

- TASK: 20260720-142159
- BRANCH: today-task-mutations
- REVIEW ROUNDS: 2 (R1 REQUEST_CHANGES, R2 APPROVE)

See TASK.md for what/why and REVIEW.md for the findings. Process notes only.

## What went well

- Read the old `daily` bash/awk implementation before writing, so the new
  Python mirrored its exact insertion/toggle/remove semantics instead of
  guessing the format.
- Independently re-derived the parser's index geometry (the `enumerate(items)`
  numbering) rather than trusting my own code, and confirmed `_target_line`
  matches it. The load-bearing claim held.
- Spawned an out-of-context reviewer to counter the shared-session blind spot.
  It caught two real byte-preservation bugs (CRLF collapse, misplaced section
  append) that my LF-only tests sailed past - exactly the kind of thing an
  in-session review rationalizes away.

## What went wrong

- Byte-preservation was under-tested in round 1: `_split`/`_join` used
  `splitlines()` + `"\n".join`, silently rewriting a CRLF file's every line.
  Root cause: I tested only the LF happy path, though the spec said
  "byte-for-byte". A "preserve exactly" requirement demands adversarial-input
  tests (CRLF, no trailing newline) up front.
- `git stash -u` in the sprout worktree wiped the untracked `uv.lock` (needed
  for `nix develop` to evaluate) and my new files; the pop was then blocked by
  a staged `flake.lock` and left everything stashed while reporting success.
  Root cause: stashing in a flake worktree whose nix eval depends on untracked
  files, and not verifying the pop landed. Cost ~2 recovery steps.
- The lock artifacts got swept into a task commit. Root cause: I `git add -f`'d
  `uv.lock`/`flake.lock` repeatedly so `nix develop` could see them (flakes
  only read tracked files), leaving them in the index; a later bare
  `git commit` committed everything staged. Had to `git rm --cached` + amend.

## What to improve next time

- For any "preserve byte-for-byte" task, write the CRLF / no-final-newline /
  exotic-separator tests before the happy-path ones.
- Never `git stash` in a flake worktree that depends on untracked lock files;
  if unavoidable, verify the pop actually restored (`git status`, not the exit
  message).
- When force-staging a file only to satisfy nix eval, commit with an explicit
  pathspec (`git commit -- <files>`) or unstage it immediately after; never let
  a bare `git commit` decide what a force-add left in the index.

## Action items

- [x] Proposed ledger entries in LESSONS.md (nix-flake-untracked-eval,
  byte-preservation-needs-adversarial-tests, independent-review-blindspot).
- Note: the root of the lock-file pain is now resolved upstream - master commit
  3e9be36 tracks `uv.lock`/`flake.lock`, so future sprout worktrees get them
  without `git add -f`. No follow-up task needed.
