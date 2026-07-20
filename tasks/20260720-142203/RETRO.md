# Retro: today note add/list with tags

- TASK: 20260720-142203
- BRANCH: feature/notes
- REVIEW ROUNDS: 1 (APPROVE + minor hardening)

## What went well

- Read the old `daily` `add_notes_entry` and `run_note` first, so the
  `note :: <tag>` convention was reused deliberately (an untagged note can carry
  its own inline marker - a small but nice parity feature, and it earned a test).
- The writer-honors-reader lesson was applied up front this time: with `--tag`,
  a text already carrying a `note ::` marker is rejected so the appended marker
  is the single source of truth. No round-2 needed on that axis.
- iter_notes reused the existing structural machinery (`_find_marker`,
  `_item_lines`, `_notes_region`, `_WEIGHT_LINE`) rather than re-parsing.

## What went wrong

- One genuine bug caught in-session (before review): `add_note` initially
  conflated the document and the note text into a single `text` parameter (mypy
  flagged "multiple values for keyword argument tag" from the test). Root cause:
  I pattern-matched the other one-arg-ish edit signatures without noticing a note
  needs BOTH the document and the content. Fixed to `add_note(text, note, tag)`.
- Two edges shipped to review: `_structural_note_lines` only excluded the first
  Today/Tomorrow marker, and empty note text with `--tag` stored an empty-body
  note. Root cause: I scoped "structure" and "valid input" to the common case
  and did not enumerate the degenerate ones (duplicate markers, empty text).

## Decisions recorded (intentional, per review)

- `note list` is day-scoped (the old `-n` searched all files). Kept day-scoped
  to match every other subcommand; `--tag` is the search. Cross-day search is a
  possible future task, not a DoD requirement.
- Freeform prose (including prose `- ` bullets not under a marker) is listed as
  notes. Intentional: a note is any freeform Notes line; `--tag` filters. Listing
  a real prose-heavy entry is noisy but correct.
- No-Notes-section write/read asymmetry (a note appended at EOF would not be
  listed) is defensive-only; the shipped template always has a Notes section.

## What to improve next time

- When a function takes "the thing" plus "where it goes", check the signature has
  a slot for BOTH before reusing a sibling's shape - a type error is the cheap
  version of that catch; enumerate degenerate inputs (duplicate/empty) alongside
  the happy path.

## Action items

- No new ledger entry (reinforces existing `writer-must-honor-reader-grammar` and
  `normalizer-empty-result-edge`; both already ticked). No follow-up code.
