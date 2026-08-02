# today: notes with tags + search (note add/list --tag)

- PRIORITY: 40
- TAGS: feature, cli
- KIND: TASK
- ACTIVITY: COMPOUNDING
- GATES: REVIEW RETRO
- RESOLUTION: DONE

## Goal

`today note add "text" [--tag TAG]` appends a note; `today note list [--tag TAG]`
lists/searches notes (the notes tags + search improvement). `--json` output.

## Notes

- Notes go in the `### Notes` section. The old `daily` used a `note :: <tag>`
  convention and `-n <tag>` to filter - reuse it (a note can carry `note :: tag`).
- `note list --tag` filters by tag; without a tag, list all (search improvement).
- Uses the write-back helper. Test against a temp den.
