# Normalize daily sections and add structured Notes

- STATUS: IN_PROGRESS
- PRIORITY: 100
- TAGS: markdown,notes,dashboardd,migration

Replace the legacy daily Markdown layout with independent Tasks, Habits, Macros, Weight, and Notes sections, then add a 5x3 structured Notes widget.

## Accepted format

- Plain `### Tasks`, `### Habits`, `### Macros`, `### Weight`, and `### Notes` headings.
- Tasks are checkboxes directly under Tasks.
- Weight is empty or one `<number> kg` line.
- Every note starts with `####`; its body continues until the next `####` or section.
- New notes use `#### HH:MM` with an optional ` - title` suffix.
- No runtime support for `Today`, `Tomorrow`, `weight ::`, `note ::`, emoji section names, or loose notes.
- Missing sections produce domain defaults instead of parse failures.

## Migration

- One task-local Python migration script rewrites the-den before the strict parser is deployed.
- Best effort is allowed for ambiguous old notes, but no source content may be deleted.
- Unknown or ambiguous content is retained in an imported structured note or an explicit historical section.
- Migration is atomic per file and produces a validation report.

## Definition of Done

- New parser and all writers use only the canonical sections.
- Tomorrow is removed from the model and JSON output.
- Notes support list, add, edit, and remove with revisions.
- Notes dashboard variant is 5x3 with normal append and Focus edit/remove.
- Migration preserves old source text semantically and validates task, weight, and food counts.
- Template and all daily entries use the canonical structure.
- Today, browser, migration, and Home Manager checks pass.

## Implementation notes

- Replaced the parser with strict plain sections and domain defaults for every
  missing or malformed section.
- Removed Tomorrow from `Day` and JSON output.
- Replaced embedded task and weight writes with section-scoped transforms.
- Added structured note list/add/edit/remove operations and backend commands.
- Added a 5x3 Notes widget with normal quick append and Focus editing/removal.
- Added the task-local atomic migration script. It converts old task and weight
  structures, wraps ambiguous content in `#### Imported`, converts standalone
  old note markers to H4 titles, and preserves Tomorrow data under
  `#### Historical Tomorrow`.

## Pre-migration evidence

- `nix flake check -L`: passed all 11 checks and 74 pytest tests.
- Dry run: 1,134 files, 1,134 changes, zero errors.
- Temporary-copy migration: 1,134 strict-parser reads, zero errors.
- Content audit: every non-structural source line remained verbatim in the
  migrated file; zero missing content lines.
- Migration is idempotent in its integration test.

## Actual migration

- Stopped dashboardd before touching the-den.
- Captured the untracked current entry in the-den commit `0b794d0`.
- Migrated 1,134 files and the daily template in commit `2bc80b9`.
- Final strict-parser sweep: 1,134 successful reads.
- Preserved all 676 standard task checkboxes and all 681 weight values.
- Content audit found zero missing non-structural source lines.
- Final dry run reports zero changes and zero errors.
- Removed all old Today, standalone note, and weight markers. Ambiguous old
  headings in note bodies were demoted to H5 under imported note blocks so
  they remain content instead of becoming sections.
