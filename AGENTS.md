# AGENTS.md

Global `~/AGENTS.md` applies.

## Project

- `today` is the only reader and writer for the-den journal Markdown.
- Bare `today` opens an editor. Agents use non-interactive subcommands.
- The runtime uses Python 3.13 and the standard library only.

## Agent workflow

- Work directly on `master` unless the user requests an isolated worktree.
- Use tatr for tracked work. Create a task only when the user requests one.
- Use one task for one user request and its follow-up work. Create dependent
  tasks only when the user requests decomposition.
- Store task records under `tasks/`. See `tasks/EXEMPTIONS.md` for legacy schema
  exceptions.
- Keep runnable task-specific examples and evidence with the task. Do not add a
  top-level examples or scripts directory.
- Treat `README.md` as the CLI contract. Treat `today/model.py` and golden
  fixtures as the Markdown format contract.
- Work offline. New runtime dependencies require user approval.

## Conventions

- Match real the-den Markdown exactly. Capture real entries as fixtures before
  parser changes.
- Mutations use parse -> transform -> atomic write. Never half-write.
- Preserve non-interactive `--json` behavior for agent callers.
- Use type hints for public functions and non-obvious data structures.
- Use `snake_case` for modules, functions, and variables and `PascalCase` for
  classes.
- Format and lint with Ruff. Type-check with mypy.
- Keep runtime dependencies empty unless the user approves a concrete need.
- Add one short Unreleased changelog line for user-visible changes. Skip
  internal refactors, tests, and task records.
- Put durable rationale and worked examples in `README.md`. Keep transient
  evidence with the task.

## Verification

Run the relevant checks:

```bash
ruff check .
mypy .
pytest
nix flake check
```

## Release

- Keep `pyproject.toml` version equal to `today/__init__.py::__version__`.
- Promote Unreleased, add a fresh section, and update compare links.
- Run `nix flake check`, then commit only version and changelog files.
- Tag `vX.Y.Z`. Push only when requested; release CI publishes the changelog
  section.
