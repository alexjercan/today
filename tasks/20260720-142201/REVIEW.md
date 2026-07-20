# Review: today weight log + show/trend (20260720-142201)

- VERDICT: APPROVE
- ROUNDS: 2 (out-of-context reviewer)

## Summary

`today weight <value>` logs `weight :: <value> Kg` (Notes section, update-in-place
or append), bare `today weight` shows the recent trend over `--days`. Round 1
found two blockers; both fixed in round 2 and re-verified APPROVE.

## Round 1: REQUEST_CHANGES (both blockers fixed)

1. [blocker] `_normalize_weight` validated with `float()`, which accepts `inf`,
   `nan`, `1e3`, `-3`, `+5`, `1_000`, `.5`, `1.` - appending `.0` then wrote a
   line (e.g. `1e3.0`) the parser's `[0-9]+(\.[0-9]+)?` regex cannot read back,
   silently losing the value (logged as weight=None). FIXED: validate the
   normalized value against the parser's exact grammar and reject the rest.
   Test: `test_weight_rejects_values_the_parser_cannot_read`.
2. [blocker] `parse_day` reads the first `weight ::` occurrence globally, but
   `set_weight` scanned only the Notes region - a stale weight line elsewhere
   (e.g. under Macros) left a duplicate and the parser read the stale value.
   FIXED: `set_weight` updates the first `weight ::` line document-wide, appending
   in Notes only when none exists. Test:
   `test_set_weight_updates_a_line_outside_notes_in_place`.

Minor/nit from round 1 (change semantics with gaps, leading-zero canonicalization,
trend float formatting) judged acceptable and left as-is.

## Round 2: APPROVE

Both blockers confirmed resolved; every accepted input round-trips through the
parser, all bad inputs rejected, the Macros-line duplicate is gone, append
fallback intact. 54 tests, ruff/mypy/pytest green.

Residual nit (non-blocking, not actioned): the writer's `_WEIGHT_LINE` is
line-anchored while the parser's `_WEIGHT` is an unanchored `.search`, so a
hand-typed prose line like `My weight :: 60 Kg` would be read by the parser but
missed by the writer. The app never emits that pattern, so it is an unrealistic
edge. A future hardening could anchor `_WEIGHT` to line-start to make reader and
writer perfectly congruent (noted in RETRO for follow-up).

## Proof

`nix develop -c "ruff check . && mypy . && pytest"`: 54 passed, green.
`nix flake check`: all checks passed. Manual e2e (log/update/show) verified.
