# Retro: today weight log + show/trend

- TASK: 20260720-142201
- BRANCH: feature/weight
- REVIEW ROUNDS: 2 (REQUEST_CHANGES -> APPROVE)

## What went well

- Read the old `daily.nix add_weight_entry` before implementing, so the
  placement (bare `weight ::` line in Notes, update-in-place else append with a
  blank line before) was a deliberate parity match, not a guess.
- Refactored the inline `_insert_section` body into a shared
  `_append_notes_block` so the weight-append reused the already-vetted Notes
  spacer logic instead of reinventing it (the reviewer confirmed the refactor
  byte-identical).

## What went wrong

- Two real blockers shipped to review, both of the same root cause: I did not
  hold the writer to the reader's contract.
  - `_normalize_weight` validated with `float()`, which is a wider grammar than
    the parser's `[0-9]+(\.[0-9]+)?` - so `inf`/`nan`/`1e3`/`-3` normalized to
    lines the parser reads back as None (silent data loss).
  - `set_weight` scanned only the Notes region for an existing weight line, but
    `parse_day` reads the first `weight ::` globally - a stale line elsewhere
    would win and a duplicate get written.
  Root cause: I treated "valid input" and "where the line lives" from the
  writer's convenience instead of deriving both from exactly what the parser
  accepts and where it looks.

## What to improve next time

- For any write that a parser later reads, make the writer's accept-set and
  scan-scope provably equal to the parser's. Concretely: validate input against
  the *parser's* regex (not a looser stdlib parse), and search the same span the
  parser searches. A round-trip test (write value -> parse_day -> assert equal)
  over adversarial inputs would have caught blocker 1 before review.

## Action items

- [x] LESSONS.md: `writer-must-honor-reader-grammar`.
- [ ] tatr (optional, minor): anchor `model._WEIGHT` to line-start so the parser
      and the line-anchored writer scan are perfectly congruent (a hand-typed
      mid-line `weight ::` in prose is currently read by the parser but missed
      by the writer). Unrealistic edge; deferred, not filed as a task yet.
