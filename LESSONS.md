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
- `writer-must-honor-reader-grammar` (x2): a writer must honor the reader's
  WHOLE pipeline (parse AND every downstream op that can throw - round/int/div),
  not just its surface parse, and scan the same span; where the writer can't know
  a downstream aggregate, make the reader total so file contents never crash it.
  Pin with a write->parse round-trip over adversarial inputs. 20260720-142201,
  20260720-142202
- `sample-fixtures-span-formatting-axes` (x1): pick golden/sample fixtures to
  span FORMATTING axes (single vs double-digit day, empty vs populated, CRLF/LF,
  first-of-month), not just content; consecutive real days share formatting and
  hid a zero-padding title bug for two tasks. 20260720-142204
- `pipefail-on-passfail-commands` (x1): for any command whose exit code is the
  signal (build/test/lint/`uv lock --check`), run it bare or `set -o pipefail`
  before reading a piped tail - `cmd | tail` reports tail's rc 0 and hid a stale
  lock. 20260720-142205

## Pending promotions (3+ occurrences, user decides)

(none yet)
