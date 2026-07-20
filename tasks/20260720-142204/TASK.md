# today: parity + templating hardening (more golden fixtures, carry-forward)

- STATUS: CLOSED
- PRIORITY: 30
- TAGS: feature, cli

## Goal

Harden parity + templating fidelity so the CLI is a safe drop-in for the two bash
scripts across REAL entries (not just the 3 golden fixtures).

## Notes

- Capture more real `Daily/*.md` + live `daily --json` pairs as fixtures (varied:
  populated macros, weight logged, multiple tasks/tomorrow, tagged notes) and
  golden-test the parser against all of them (capture-real-cli-output-for-parser).
- Templating: the bare-`today` create must match the old `today` - fill `{{title}}`
  AND carry yesterday's "Tomorrow" list forward into today's "Today" list (verify
  against the real behavior, incl. edge cases: no previous entry, empty tomorrow).
- Ensure every mutation is a clean round-trip (write then parse == expected) and
  preserves unrelated file content.
