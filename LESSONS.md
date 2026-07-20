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
- `devshell-env-not-in-checks` (x1): env a tool needs that is set only in the
  devShell shellHook (e.g. `REPO_ROOT` for the editable `.pth`) is absent in
  check/CI/`nix build` sandboxes; replicate it in `mkCheck`. 20260720-172833
- `normalizer-empty-result-edge` (x1): when a matcher normalizes input
  (strip/casefold/regex), test the degenerate empty/all-stripped result as a
  first-class case - it can silently match the wrong item. 20260720-142200
- `writer-must-honor-reader-grammar` (x1): a writer must validate input against
  the reader's exact grammar (not a looser stdlib parse like `float()`) and scan
  the same span the reader scans, or it silently writes lines the parser reads
  back as empty/stale; pin it with a write->parse round-trip test over
  adversarial inputs. 20260720-142201

## Pending promotions (3+ occurrences, user decides)

(none yet)
