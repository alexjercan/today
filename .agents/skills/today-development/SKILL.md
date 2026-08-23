---
name: today-development
description: Change Today's journal parser, CLI, atomic mutations, JSON contract, dashboard widget, or Python tests.
---

# Today development

Treat `README.md` as the CLI contract. Treat `today/model.py` and golden fixtures
as the Markdown format contract.

- Capture representative real the-den Markdown as a fixture before parser
  changes. Preserve unknown content and exact supported formatting.
- Mutate through parse -> transform -> atomic write. Validate all input before
  replacing a daily file.
- Preserve non-interactive `--json` output. Never use bare `today` in agent work;
  it opens the editor.
- Keep runtime dependencies empty unless the user approves a concrete need.
- Use type hints for public functions and non-obvious data structures. Use
  `snake_case` for modules, functions, and variables and `PascalCase` for
  classes.
- Keep widget backend behavior aligned with the CLI and journal model. Validate
  frontend and backend payloads at their boundaries.
- Add or update golden and focused behavioral tests with the first changed
  behavior.

Use the narrowest relevant checks:

```bash
pytest tests/<focused-test>.py
ruff check .
ruff format --check .
mypy .
nix flake check
```

Run the focused pytest case first. Use `nix flake check` only for broad Python,
widget, packaging, or release integration.
