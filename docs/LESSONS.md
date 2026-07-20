# Lessons ledger

One line per recurring lesson; /compound appends or bumps counts.

- `byte-preservation-needs-adversarial-tests` (x1): for any "preserve
  byte-for-byte" requirement, write CRLF / no-final-newline / exotic-separator
  tests before the LF happy path. 20260720-142159
- `independent-review-blindspot` (x1): a same-session review rationalizes away
  edge cases; an out-of-context reviewer catches them (found CRLF + misplaced
  append here). 20260720-142159
- `nix-flake-untracked-eval` (x1): nix flakes only read git-tracked files, so
  force-staging untracked lock files for `nix develop` leaves them in the index
  where a bare commit sweeps them, and `git stash -u` wipes them; scope-commit
  or unstage after, and never stash them. 20260720-142159

## Pending promotions (3+ occurrences, user decides)

(none yet)
