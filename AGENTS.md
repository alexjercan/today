# AGENTS.md

Repository guidance. Global `~/AGENTS.md` applies.

## Project

- `today`: the only reader and writer for the-den journal Markdown.
- Bare `today` opens an editor. Agents must use non-interactive subcommands.
- Runtime uses the Python standard library only.

## Agent workflow

- Tracker/epics: tatr records under `tasks/`; see `tasks/EXEMPTIONS.md` for
  legacy schema exceptions.
- Examples/retention: keep runnable examples in the owning task; no top-level
  examples or scripts directory.
- Domain docs: `README.md` for the CLI; `today/model.py` and golden fixtures for
  the Markdown format.
- Research/network: work offline; new dependencies require user approval.
- Checks/records: run `nix flake check`; keep records and RETRO with the task.

## Rules

- Match real the-den Markdown exactly. Capture real entries as fixtures before
  parser changes.
- Mutations use parse -> transform -> atomic write. Never half-write.
- Preserve non-interactive `--json` behavior for agent callers.
- User-visible changes need one short Unreleased changelog line. Skip internal
  refactors, tests, and task records.
- Put rationale and worked examples in README or the task record.

## Release

- Keep `pyproject.toml` version equal to `today/__init__.py::__version__`.
- Promote Unreleased, add a fresh section, and update compare links.
- Run `nix flake check`, then commit only version and changelog files.
- Tag `vX.Y.Z`. Push only when requested; release CI publishes the changelog
  section.
