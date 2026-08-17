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
today -N -1 show            # select a day by offset
today --date 2026-08-20 show # select an exact date
today upcoming [--json]     # incomplete tasks in future daily files
today --version             # print the declared version

today task add "go to gym"  # add a task; task done/rm
today --date 2026-08-20 task add "prepare release"
today habit toggle Gym
today weight 80
today macros add "eggs,12,1,10"
today note add "idea..." --tag ideas
```

- Den path: `--den PATH`, else `$DEN_PATH`, else `~/personal/the-den`.
- `--date YYYY-MM-DD` and `-N/--offset` are mutually exclusive.
- Scheduled tasks live in the target date's `Today` list. New `Tomorrow` writes
  and automatic carry-forward are not supported.

## Agent skill

The flake exports `skills.today` for agent workspaces that support external
Agent Skills sources:

```nix
programs.agents.extraSkills.today = inputs.today.skills.today;
```

The skill documents the non-interactive command surface and prevents agents
from opening the editor through bare `today`.

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

CI runs the same `nix flake check` on `master` and every PR. Releases are
tag-driven: pushing a `vX.Y.Z` tag re-runs the checks, verifies the tag against
the declared version, and publishes a GitHub Release from that version's
`CHANGELOG.md` section - see `AGENTS.md` for the procedure.

## Status

The parity port is complete as of v0.1.0: the day model + markdown parser
(golden parity with the old `daily --json`), the read/create/editor commands
and every mutation subcommand (task/habit/weight/macros/note) ship. Next:
nix.dotfiles swaps `today.nix`/`daily.nix` for this package, and scufris wraps
the subcommands as MCP tools. Ongoing work is tracked in `tasks/`.
