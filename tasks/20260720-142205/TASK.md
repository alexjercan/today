# today: finalize nix packaging + swap dotfiles (uv.lock, overlay, delete today.nix/daily.nix)

- STATUS: CLOSED
- PRIORITY: 20
- TAGS: infra, nix

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

## Done (in-repo)

- uv.lock made consistent with pyproject: the declared dev deps over-listed the
  lock (respx / pytest-asyncio / types-psutil / types-requests were never
  imported by this stdlib-only project). Trimmed the dev group to ruff + mypy +
  pytest; `uv lock --check` now passes and uv.lock is unchanged (already minimal).
- Verified `nix develop`, `nix flake check` (ruff+mypy+pytest all green), and
  `nix run .` work; full e2e smoke test through the packaged binary
  (create/habit/weight/macros/note/task/show) against a temp den.
- Exported `flake.overlays.default` (the tatr pattern) providing `pkgs.today`;
  verified it evaluates and resolves the app (mainProgram "today").

## Deferred to the user (outward-facing, cross-repo)

The dotfiles swap is NOT done here: it edits a DIFFERENT repo (nix.dotfiles),
deletes the live `today`/`daily` scripts, and rebuilds the home environment, and
it depends on THIS repo being pushed so nix.dotfiles can add it as a flake input
(`github:alexjercan/today`) - flow does not push. Batched as a manual-acceptance
follow-up (see GOAL.md): add `inputs.today` + `inputs.today.overlays.default`,
set `home.packages = [pkgs.today]`, point `$DEN_PATH` at the-den, and delete
`nix.dotfiles/home/modules/scripts/{today,daily}.nix` + their config. Best filed
as a nix.dotfiles task (that repo has its own tatr tracker).
