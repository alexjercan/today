# today: habit mutations (habit toggle/list)

- STATUS: OPEN
- PRIORITY: 40
- TAGS: feature,cli

## Goal

`today habit toggle <name>` (check/uncheck a habit) and `today habit list`
(show habits + done state). `--json` returns the updated habits.

## Notes

- Habits are `- [ ] <name>` / `- [x] <name>` under the `### Habits` section.
  Toggle flips the checkbox for the matching habit (match by name, emoji-insensitive
  if practical). Mirror the old `daily --toggle-habit`.
- Uses the write-back helper from the task-mutations task.
- Test against a temp den; round-trip via `parse_day`.
