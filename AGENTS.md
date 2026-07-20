# AGENTS.md - today

The-den journal CLI. One command (`today`) with non-interactive subcommands +
`--json`, so agents call subcommands and never the editor. `the-den` is data
only; this CLI is the sole reader/writer of its markdown.

## Layout
- `today/model.py` - the `Day` model + markdown parser/serializer. `Day.to_dict()`
  mirrors the old `daily --json` shape (the golden contract).
- `today/cli.py` - argparse CLI (bare -> $EDITOR; path/create/show + mutation
  scaffolds).
- `tests/fixtures/` - real `Daily/*.md` entries paired with the live `daily --json`
  output; the parser is golden-tested against them.

## Conventions
- Match the existing the-den markdown format exactly (read real entries; capture
  real `daily --json` as fixtures before changing the parser).
- Mutations must never half-write: parse -> transform -> write atomically.
- Stdlib only (no runtime deps). ruff + mypy + pytest all green (`nix flake check`).
- Records live in `tasks/` (tatr). After meaningful changes, write a short retro
  note there: what changed, why, and any gotcha.

## Development flow
- /flow drives development here: plan/work/review/compound via tatr tasks,
  sprout worktrees, out-of-context round-1 reviews, and DoD proofs using
  test:/cmd:/manual: notation.
- `LESSONS.md` at the repo root is the lessons ledger; read it before starting
  any task.
- `/home/alex/personal/tatr/tatr check` (plus `--ledger LESSONS.md`) is the
  conformance gate.
