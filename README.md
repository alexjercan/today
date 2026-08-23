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
today show [--json]         # read tasks, habits, macros, weight, and notes
today -N -1 show            # select a day by offset
today --date 2026-08-20 show # select an exact date
today upcoming [--json]     # incomplete tasks in future daily files
today --version             # print the declared version

today task add "go to gym"  # add a task; task done/rm
today --date 2026-08-20 task add "prepare release"
today habit toggle Gym
today weight 80
today macros add "eggs,12,1,10"
today macros query chick --json
today macros calculate --food "chicken breast:g" --amount 150 --json
today macros insert "apple 1pc,0.3,25,0.2" --json
today note add "idea..." --title project
today note list --json      # structured #### notes
today note edit 1 "replacement body"
today note rm 1
```

- Den path: `--den PATH`, else `$DEN_PATH`, else `~/personal/the-den`.
- `--date YYYY-MM-DD` and `-N/--offset` are mutually exclusive.
- Scheduled tasks live directly in the target date's `### Tasks` section.
- Daily files use plain Tasks, Habits, Macros, Weight, and Notes sections.
- Notes are multi-line Markdown blocks delimited by `####` headings.
- Missing sections read as empty domain defaults.

### Food database commands

`today macros query` provides deterministic, case-insensitive fuzzy search.
Prefix matches rank first, followed by food ID. `search` is a compatibility
alias for `query`. Results contain stable IDs, display names, and canonical
units (`g` or `pc`). `calculate` accepts a selected ID and a positive finite
quantity, then scales protein, carbohydrates, and fat from the database row.
`insert` validates and atomically appends one canonical row.

The commands reuse the macros.nvim CSV format:

```csv
chicken breast 100g,31,0,3.6
egg 1pc,6,0,5
```

The database defaults to `~/.local/share/nvim/macros.csv`, which keeps
macros.nvim as the Neovim data source. Set `MACROS_DATABASE` or pass
`--database PATH` after `query`, `calculate`, or `insert`. Use `--json` for the
stable machine contract:

```json
{"results":[{"id":"chicken breast:g","name":"chicken breast","unit":"g"}]}
{"food":"chicken breast","amount":150.0,"unit":"g","protein":46.5,"carbs":0.0,"fat":5.4}
```

## dashboardd widgets

The flake exports `packages.dashboardd-widget`, an external runtime bundle with
six writable variants: Tasks, Habits, Macros, Weight, Upcoming, and Notes.

```bash
nix build .#dashboardd-widget
dashboardd-widget check result/share/dashboardd/widgets/today
```

Compose it with dashboardd without merging package trees:

```nix
lib.makeSearchPath "share/dashboardd/widgets" [
  inputs.dashboardd.packages.${pkgs.system}.bundled-widgets
  inputs.today.packages.${pkgs.system}.dashboardd-widget
]
```

The Python backend inherits `DEN_PATH`; otherwise it uses
`~/personal/the-den`. Starting a Today widget ensures the current daily entry
exists. Dated Upcoming writes create the selected future entry. Macros food
entry uses Today's food database implementation for fuzzy autocomplete, gram
or piece quantities, and automatic nutrient calculation. The widget package
has no macros.nvim CLI runtime dependency and uses the same `MACROS_DATABASE`
selection described above.

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
