---
name: today
description: Read and edit the daily journal with the today CLI. Use for journal, tasks, habits, macros, notes, or weight.
disable-model-invocation: true
---

# Today

Read and edit the den with the `today` CLI. Never run bare `today`; it opens `$EDITOR`. Prefer `--json`.

## Commands

```bash
today path
today create
today show --json
today task add "<text>"
today task done <index>
today task rm <index>
today habit list
today habit toggle "<name>"
today weight [<number>]
today weight --days <N> --json
today macros
today macros add "what,protein,carbs,fat"
today macros query "<food>" --json
today macros calculate --food "<id>" --amount <quantity> --json
today macros insert "<food> <quantity><unit>,<protein>,<carbs>,<fat>" --json
today note add "<body>" [--title <title>]
today note list --json
today note edit <index> "<body>" [--heading <heading>]
today note rm <index>
today -N <offset> <subcommand>
today --help
```

## Rules

* Default target: today. `-N` selects a relative day.
* Prefer JSON for reads and mutations. Parse stdout only.
* Task indices are 1-based.
* After removing a task, re-read before another indexed edit.
* One mutation per invocation.
* Food IDs and canonical units come from `macros query`; quantities must be positive and finite.
* Food database commands use `MACROS_DATABASE`, then `~/.local/share/nvim/macros.csv`.
* `path` does not create an entry; other journal subcommands may.
* Use `today --help` for details.
