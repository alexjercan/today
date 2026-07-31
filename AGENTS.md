# AGENTS.md - today

The-den journal CLI. One command (`today`) with non-interactive subcommands +
`--json`, so agents call subcommands and never the editor. `the-den` is data
only; this CLI is the sole reader/writer of its markdown.

## Agent workflow
- Tracker/epics: tatr records in `tasks/`; `/flow` drives plan/work/review/compound. See `tasks/EXEMPTIONS.md` for the schema-exemption rule.
- Examples/retention: runnable examples live in the owning task folder (`tasks/<id>/`) and are retained with that record; no top-level `examples/` or `scripts/`.
- Domain docs: `README.md` for CLI surface; the-den markdown format is defined by `today/model.py` + the golden fixtures in `tests/fixtures/`.
- Research/network: offline only - stdlib at runtime, no runtime deps, no network in code or checks; new deps need explicit user approval.
- Checks/records: `nix flake check` (ruff + mypy + pytest) plus `tatr check --ledger LESSONS.md`; read `LESSONS.md` before starting and write a retro into the task folder after.

## Layout
- `today/model.py` - the `Day` model + markdown parser/serializer. `Day.to_dict()`
  mirrors the old `daily --json` shape (the golden contract).
- `today/cli.py` - argparse CLI (bare -> $EDITOR; path/create/show + mutation
  scaffolds).
- `today/edit.py` - mutation ops (parse -> transform -> atomic write).
- `tests/fixtures/` - real `Daily/*.md` entries paired with the live `daily --json`
  output; the parser is golden-tested against them.

## Conventions
- Match the existing the-den markdown format exactly (read real entries; capture
  real `daily --json` as fixtures before changing the parser).
- Mutations must never half-write: parse -> transform -> write atomically.
- DoD proofs use `test:` / `cmd:` / `manual:` notation.
