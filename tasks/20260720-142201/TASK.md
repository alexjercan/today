# today: weight (log + show/trend)

- PRIORITY: 40
- TAGS: feature, cli
- KIND: TASK
- ACTIVITY: COMPOUNDING
- GATES: REVIEW RETRO
- RESOLUTION: DONE

## Goal

`today weight <value>` logs the day's weight (as `weight :: <value> Kg`); bare
`today weight` shows the weight (and a trend improvement). `--json` output.

## Notes

- The parser already reads `weight :: N Kg`. Decide where the line lives (a
  `### Weight` section or inline) - match the old `daily --weight-entry` placement.
- Improvement (from the spike): `today weight` with no value prints recent weights /
  a simple trend across the last N days (read multiple entries).
- Test against a temp den + multi-day fixtures.
