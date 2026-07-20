# Review: parity + templating hardening (20260720-142204)

- VERDICT: APPROVE
- ROUNDS: 1 (out-of-context reviewer, verified against the real daily/today)

## Summary

Fix title zero-padding, add 2 real golden fixtures, carry-forward edge tests,
and document the user-approved `[~]` divergence. Reviewer verified every claim
against the live `daily`/`today` binaries; APPROVE, no blockers.

## Verified by the reviewer

1. Title fix direction correct: real titles are zero-padded ("January 02"), old
   today used `date +%d`; the old `%-d` was the bug. `test_title_pads_day_of_
   month_to_two_digits` sweeps 40 offsets so a single-digit day is always hit.
2. Both new fixtures are byte-faithful to real `daily --json` (title, habits,
   tasks, tomorrow, 2781 kcal, weights) - confirmed by re-running the binary.
   They add genuine coverage (single-digit title, populated macros, weight,
   multi-task Today, multi-item Tomorrow).
3. `[~]` divergence correctly implemented and self-consistent: `parse_day` and
   `edit._target_line` both index among all bullets and both skip the `[~]`
   position, so `show` indices and `task done N` stay in lockstep. daily returns
   `tasks: []` for the same file (data loss); the new tool surfaces the real
   tasks. Documented by `test_only_standard_checkboxes_are_tasks`.
4. Carry-forward matches old today byte-for-byte (append at EOF), incl. all three
   edge cases (no previous entry, empty Tomorrow, blank-split list).

## Findings (non-blocking, not actioned)

- [nit] New carry-forward tests import `parse_day` in-body; matches the existing
  test locality style. No change.
- [minor] No real `[~]` golden fixture - correct by design, since it is a
  deliberate divergence from daily (a golden equality assertion would be wrong);
  coverage lives in `test_model.py` where it belongs.

## Proof

`nix develop -c "ruff check . && mypy . && pytest"`: 87 passed, green.
`nix flake check`: all checks passed. Reviewer cross-checked against live
`daily`/`today` binaries.
