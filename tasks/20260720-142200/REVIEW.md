# Review: today habit toggle/list (20260720-142200)

- VERDICT: APPROVE
- ROUNDS: 1 (out-of-context reviewer)

## Summary

`today habit toggle <name>` and `today habit list` (both `--json`). Toggling is
scoped to the Habits section via a new `edit._section_region` (`_notes_region`
now delegates to it), matching by name ignoring a leading emoji and case.
Reviewer verdict APPROVE; all findings minor/nit.

## Findings and disposition

1. [minor] Empty/emoji-only query normalized to "" could false-match the first
   such habit. FIXED: `toggle_habit` now raises `KeyError` on an empty key;
   test `test_toggle_habit_empty_name_never_matches`.
2. [minor] First-match-on-duplicate was undocumented. FIXED: docstring notes
   "the first in document order is toggled"; test
   `test_toggle_habit_first_of_duplicates_wins`.
3. [nit] `if updated != text` guard in `_cmd_habit` is technically dead. KEPT:
   mirrors the existing `_cmd_task` pattern for consistency.
4. [nit] `_habit_key` strips a leading non-word run, broader than "emoji".
   FIXED: docstring reworded to "a leading run of non-word characters".
   Reviewer confirmed `\W` correctly handles multi-emoji / no-space / ZWJ
   prefixes.
5. [minor] Missing no-trailing-newline + duplicate coverage. FIXED: added
   `test_toggle_habit_no_trailing_newline_preserved` and the duplicate test.

## Confirmed correct

- Section scoping: a Today/Tomorrow checkbox named like a habit is not toggled
  (`test_toggle_habit_ignores_todo_checkboxes_outside_habits`).
- `_notes_region` refactor is behavior-preserving (returns `(len, len)` when
  Notes is absent).
- CRLF / no-trailing-newline byte preservation; unknown-habit -> rc 1 with the
  file untouched; `--json` matches `Habit.to_dict()`; required `haction`
  subaction; command-surface test stays green.

## Proof

`nix develop -c "ruff check . && mypy . && pytest"`: 41 passed, green.
`nix flake check`: all checks passed. Manual e2e (list/toggle/unknown) verified.
