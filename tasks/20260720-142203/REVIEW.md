# Review: today note add/list with tags (20260720-142203)

- VERDICT: APPROVE
- ROUNDS: 1 (out-of-context reviewer) + reviewer-suggested minor hardening

## Summary

`today note add "text" [--tag TAG]` and `today note list [--tag TAG]`, both
`--json`. A note is any non-structural Notes-body line (not a Today/Tomorrow
marker, list item, or weight line); `iter_notes` splits out an inline
`note :: <tag>` marker so an untagged note can still carry one. Reviewer verdict
APPROVE, no blockers.

## Findings and disposition

1. [minor] `_structural_note_lines` used `_find_marker` (first marker only), so a
   hand-edited *second* Today/Tomorrow block leaked its marker/items as notes.
   FIXED: scan every marker line and collect each one's list. Test
   `test_iter_notes_excludes_every_today_block_not_just_the_first`.
2. [minor] Freeform prose `- ` bullets (not under a marker) are listed as
   individual notes. INTENTIONAL and documented: a note is any freeform Notes
   line with no marker to attach it to; `--tag` gives clean filtered output. See
   RETRO.
3. [minor] Empty/whitespace note text with `--tag` stored an empty-body note.
   FIXED: `_cmd_note` rejects empty text on add. Test
   `test_note_add_rejects_empty_text`.
4. [nit] If a den template lacks a Notes section, `add_note` appends at EOF but
   `iter_notes` (fallback span) would not list it. Defensive-only - the shipped
   template always has Notes. Noted in RETRO; not actioned.
5. [nit] `note list` is day-scoped (old `-n` searched all files). INTENTIONAL:
   the CLI is day-centric like every other subcommand; the DoD does not require
   cross-day. Noted in RETRO.

Added the reviewer's requested tests: two-marker exclusion, inline-marker-in-
untagged-text round-trip, empty-text rejection, and empty `note list` on a fresh
entry (`normalizer-empty-result-edge`).

## Confirmed correct

- Tag round-trip (incl. `a:b`, `work,`, `note`); `--tag`-with-text-marker
  rejection keeps the appended marker the single source of truth.
- Byte preservation via the shared `_append_notes_block` (CRLF, no-final-newline).
- Scaffold (`_cmd_planned`/`_PLANNED`) fully removed, no dangling refs; command
  surface test still green.

## Proof

`nix develop -c "ruff check . && mypy . && pytest"`: green. `nix flake check`:
all checks passed. Manual e2e (add/tag/list/filter/inline-marker) verified.
