# AGENTS.md

Global `~/AGENTS.md` applies. This file defines project-specific instructions.

## Project

- `today` is the only reader and writer for the-den journal Markdown.
- Bare `today` opens an editor. Agents use non-interactive subcommands.
- The Python 3.13 runtime uses only the standard library.
- `README.md` defines the CLI. `today/model.py` and golden fixtures define the
  Markdown format.

## Workflow

- Work directly on `master` unless the user requests an isolated worktree.
- Use Tatr for requested tracked work. Keep one task for one request and its
  follow-up work.
- Keep task records and evidence under `tasks/<id>/`. Follow
  `tasks/EXEMPTIONS.md` for legacy records.
- Use Sprout only when the user requests an isolated worktree.
- Keep task-specific examples with the task. Do not add top-level example or
  script directories.
- Work offline. New runtime dependencies require user approval.

## Conventions

- Match real the-den Markdown. Capture real entries as fixtures before parser
  changes.
- Mutate through parse -> transform -> atomic write. Never half-write.
- Preserve non-interactive `--json` behavior for agent callers.
- Use type hints for public and non-obvious interfaces. Format and lint with
  Ruff and type-check with mypy.
- Add one short Unreleased changelog line for user-visible changes. Skip
  internal refactors, tests, and task records.
- Put durable rationale and worked examples in `README.md`.
- Run the cheapest relevant check. Use focused pytest cases first and
  `nix flake check` for broad integration.
- Keep `pyproject.toml` and `today/__init__.py` versions equal during releases.
  Promote Unreleased, create a fresh section, and push tags only when requested.
