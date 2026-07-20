# Bootstrap the today project (repo, model+parser, read/create/editor CLI)

- STATUS: CLOSED
- PRIORITY: 50
- TAGS: setup

## Goal

Bootstrap the `today` project (DONE - recorded for the trail).

## What shipped

- Repo scaffold: `pyproject.toml` (stdlib-only, `today = today.cli:main`),
  `flake.nix` (pyproject-nix + uv2nix, same as scufris; exports package + overlay-
  ready + devShell + `nix flake check`), README.md, AGENTS.md, `.gitignore`,
  `tasks/`, `tests/`.
- `today/model.py`: the `Day` model + markdown parser/serializer. `Day.to_dict()`
  mirrors the old `daily --json` shape and is GOLDEN-TESTED against 3 real
  `Daily/*.md` entries paired with their live `daily --json` output (habits, tasks,
  tomorrow, macros, weight all match).
- `today/cli.py`: bare `today` -> create-from-template + `$EDITOR`; `today path`,
  `today create`, `today show [--json]`; `-N/--offset`, `--den`. Mutation
  subcommands (task/habit/weight/macros/note) are scaffolded (visible in --help,
  exit 2 with a "planned" message).
- 11 tests pass.

## Open loose end

- `uv.lock` was NOT yet generated / the nix flake build was NOT yet verified end to
  end (interrupted). Do that as part of the nix-packaging task.

## Design source

scufris tasks/20260720-140800/SPIKE.md (the questionnaire decisions): command
`today` + subcommands; bare opens editor; targets the-den; parity + a few
improvements; its own repo + overlay replacing today.nix/daily.nix.
