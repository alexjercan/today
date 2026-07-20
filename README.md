# today

A single command for [the-den](../the-den) journal - merges the old `today`
(open/create) and `daily` (read/mutate) bash scripts into one agentic-friendly
Python CLI. Bare `today` opens today's entry in `$EDITOR`; every data operation is
a non-interactive subcommand with machine-readable (`--json`) output, so tools and
agents call subcommands and never the editor.

`the-den` is just data; this CLI is the only thing that parses/writes its markdown.

## Usage

```
today                       # open/create today's entry in $EDITOR
today path                  # print today's entry path (no create)
today create                # create from the template, print the path
today show [--json]         # read the day: habits/tasks/tomorrow/macros/weight
today -N -1 show            # operate on another day (offset in days)

# (planned - parity port, see tasks/)
today task add "go to gym"  # add a task; task done/rm; --tomorrow variant
today habit toggle Gym
today weight 80
today macros add "eggs,12,1,10"
today note add "idea..." --tag ideas
```

- Den path: `--den PATH`, else `$DEN_PATH`, else `~/personal/the-den`.

## Development

Python via `pyproject-nix` + `uv2nix` (same setup as scufris):

```
nix develop        # dev shell (venv + uv)
pytest             # tests (golden-tested against real `daily --json` output)
ruff check .
mypy .
nix flake check    # runs ruff + mypy + pytest
nix run .          # run the CLI
```

## Status

Bootstrapped: the day model + markdown parser (golden parity with the old
`daily --json`), and the read/create/editor commands. The mutation subcommands
(task/habit/weight/macros/note) and a few improvements are the parity-port work
tracked in `tasks/`. Then nix.dotfiles swaps `today.nix`/`daily.nix` for this
package, and scufris wraps the subcommands as MCP tools.
