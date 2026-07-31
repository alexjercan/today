# AGENTS.md - today

The-den journal CLI. One command (`today`) with non-interactive subcommands +
`--json`, so agents call subcommands and never the editor. `the-den` is data
only; this CLI is the sole reader/writer of its markdown.

## Agent workflow
- Tracker/epics: tatr records in `tasks/`; `/flow` drives plan/work/review/compound. See `tasks/EXEMPTIONS.md` for the schema-exemption rule.
- Examples/retention: runnable examples live in the owning task folder (`tasks/<id>/`) and are retained with that record; no top-level `examples/` or `scripts/`.
- Domain docs: `README.md` for CLI surface; the-den markdown format is defined by `today/model.py` + the golden fixtures in `tests/fixtures/`.
- Research/network: offline only - stdlib at runtime, no runtime deps, no network in code or checks; new deps need explicit user approval.
- Checks/records: `nix flake check` (ruff + mypy + pytest) plus `tatr check --ledger LESSONS.md`; read `LESSONS.md` before starting and write a retro into the task folder after. CI (`.github/workflows/check.yml`) runs the same `nix flake check` on master and every PR.

## Changelog
- Every user-visible change adds one short line under `## [Unreleased]` in `CHANGELOG.md`, in `Added` / `Changed` / `Fixed`.
- Internal refactors, test-only changes and task records do not.
- Rationale and worked examples belong in `README.md` or the task record, not the changelog.
- The release refuses to publish a version whose changelog section is empty.

## Cutting a release
The version is declared in two places and CI refuses a tag that disagrees with
either: `version` in `pyproject.toml` and `__version__` in `today/__init__.py`
(`today --version` prints it; a pytest keeps the two equal). `flake.nix` reads
the version from the uv workspace, so it needs no bump.

On `master`, for version `X.Y.Z`:
1. Bump `version` in `pyproject.toml` and `__version__` in `today/__init__.py`.
2. In `CHANGELOG.md`, promote `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`, leave a fresh empty `## [Unreleased]` above it, and merge any duplicate section headings that grew during the cycle.
3. Repoint the link block at the bottom: `[unreleased]` compares `vX.Y.Z...HEAD`, and add `[X.Y.Z]` (a compare against the previous tag, or `releases/tag/vX.Y.Z` for the first one).
4. `nix flake check`, then commit exactly those files as `chore(release): vX.Y.Z`.
5. `git tag vX.Y.Z`, then `git push origin master && git push origin vX.Y.Z`.
6. `release.yml` runs the checks, verifies the tag against both declared versions, and publishes a GitHub Release whose notes are that changelog section.

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
