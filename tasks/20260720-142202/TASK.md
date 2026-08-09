# today: macros (add row + aggregate)

- STATUS: CLOSED
- PRIORITY: 40
- TAGS: feature, cli

## Goal

`today macros add "what,protein,carbs,fat"` appends a macros CSV row; `today macros`
(or `today show`) reports the aggregate. `--json` output.

## Notes

- Macros live under `### Macros` as CSV rows after the `what,protein,carbs,fat`
  header; the parser already aggregates them (protein/carbs/fat + Atwater calories).
  This task adds the WRITE side (append a row). Mirror old `daily --macros-entry`.
- Uses the write-back helper. Test round-trip via `parse_day` (aggregate updates).
