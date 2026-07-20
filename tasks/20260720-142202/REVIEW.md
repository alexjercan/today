# Review: today macros add + aggregate (20260720-142202)

- VERDICT: APPROVE
- ROUNDS: 2 (out-of-context reviewer)

## Summary

`today macros add "what,protein,carbs,fat"` appends a CSV row at the end of the
Macros table; bare `today macros` reports the aggregate. Both `--json`. Round 1
found one blocker; fixed in round 2 and re-verified APPROVE, plus a follow-on
one-line reader hardening applied.

## Round 1: REQUEST_CHANGES (blocker fixed)

1. [blocker] The reader's grammar is `float()` *composed with* `round()`:
   `_parse_macros` sums the cells then does `round(protein*4+carbs*4+fat*9)`, and
   `round()` throws OverflowError on inf / ValueError on nan - which `float()`
   accepts. `_normalize_macros_row` validated with `float()` alone, so
   `today macros add "x,inf,1,1"` wrote the row and then crashed `parse_day` on
   every subsequent read, permanently poisoning the file. FIXED: writer rejects
   non-finite cells (`math.isfinite`); reader skips non-finite cells so a
   hand-edited file cannot crash it. Tests: `test_macros_rejects_non_finite_cells`
   (round-trip, file untouched, still parses), `test_parse_macros_survives_non_finite_row`.
2. [minor] Reader hardening against hand-edited inf/nan - addressed by the reader
   skip above.
3. [nit] Capital `What,` is data (parser skips only lowercase `what,`) - added
   `test_macros_capital_what_is_data_not_header` confirming writer+parser agree.

Verified correct in round 1: comma-in-food-name is loudly rejected (not silent
corruption) since the name's remainder fails `float()`; placement/CRLF/no-trailing
-newline preservation; the `--json` SUPPRESS argparse trick across all orderings.

## Round 2: APPROVE

Blocker and both lesser items confirmed resolved, 67 tests green, no regression.

Residual (reviewer, out of scope): finite cells can still sum past DBL_MAX to inf,
and `round(inf)` throws. Though unrealistic (two hand-edited ~1e308 values),
FIXED anyway as a one-line hardening: `_parse_macros` guards the summed total
with `math.isfinite` and degrades to 0 calories. Test:
`test_parse_macros_survives_finite_sum_overflow`. 68 tests green.

## Proof

`nix develop -c "ruff check . && mypy . && pytest"`: 68 passed, green.
`nix flake check`: all checks passed. Manual e2e (add/aggregate/reject) verified.
