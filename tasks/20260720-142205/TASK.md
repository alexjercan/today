# today: finalize nix packaging + swap dotfiles (uv.lock, overlay, delete today.nix/daily.nix)

- STATUS: OPEN
- PRIORITY: 20
- TAGS: infra,nix

## Goal

Finalize nix packaging and swap the dotfiles over to this CLI.

## Notes

- Generate `uv.lock` (interrupted during bootstrap) and verify `nix develop`,
  `nix flake check` (ruff+mypy+pytest), and `nix run .` all work from the flake.
- Export the overlay so nix.dotfiles can consume it (the tatr pattern): add `today`
  to `home.packages` via the flake input, and DELETE
  `nix.dotfiles/home/modules/scripts/{today,daily}.nix` + their `programs.today`/
  `daily` config. Point `$DEN_PATH`/`--den` at the-den in the home config.
- This is the LAST step - do it once the CLI has parity (tasks above). Then the
  scufris den MCP tools (scufris tasks/20260720-122514) wrap the subcommands.
