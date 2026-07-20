# today: task mutations + safe write-back foundation (task add/done/rm, --tomorrow)

- STATUS: OPEN
- PRIORITY: 50
- TAGS: feature,cli

## Goal

Implement the task mutations and the safe write-back mechanism the other mutations
reuse: `today task add "text"`, `today task done <idx>`, `today task rm <idx>`, and
a `--tomorrow` variant (or `today tomorrow add/rm`). Each supports `--json` to
return the updated slice.

## Notes

- This is the FOUNDATION for all mutations: a parse -> transform -> write helper
  that edits the "Today"/"Tomorrow" bullet lists in the Notes section IN PLACE and
  writes atomically (never a half-write). Preserve the rest of the file byte-for-
  byte where possible.
- Tasks are `- [ ]`/`- [x]` items under a "Today" marker; tomorrow items are plain
  `- ` bullets under "Tomorrow". `done` toggles the checkbox. Match the format the
  parser already reads (today/model.py) - round-trip: write then parse == expected.
- Mirror the old `daily` behavior: `--task-entry`, `--task-remove`,
  `--task-tomorrow-entry`, `--task-tomorrow-remove`, plus a done/toggle.
- Test against a temp den + assert via `parse_day`.
