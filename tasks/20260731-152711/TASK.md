# Release mechanism for v0.1.0: CHANGELOG, CI, tag-triggered GitHub release

- STATUS: CLOSED
- PRIORITY: 1
- TAGS: release, ci

Give `today` the release mechanism macros.nvim and tatr already have: a
changelog contract, CI that runs the flake checks, and a `vX.Y.Z` tag that
gates on the declared version and publishes a GitHub Release. Target the
first tag, `v0.1.0` (the version already declared in `pyproject.toml` and
`today/__init__.py`).

Today the repo has no `.github/` at all and no `CHANGELOG.md`, so this task
creates CI and the release path together.

## Context

- Version literals: `pyproject.toml` `version = "0.1.0"`, `today/__init__.py`
  `__version__ = "0.1.0"`. `flake.nix` derives the version from the uv
  workspace, so it declares none and needs no guard.
- The CLI has no `--version` flag; `build_parser()` in `today/cli.py:514`.
- Checks: `nix flake check` (ruff, mypy, pytest via `mkCheck`).
- Remote `git@github.com:alexjercan/today.git`, default branch `master`.
- Precedent: `~/personal/macros.nvim/.github/workflows/{lint-test,release}.yml`
  (reusable check workflow + tag guard) and `~/personal/tatr`'s `release.yml`
  (awk-extracted changelog section as the release body).

## Steps

1. `today/cli.py`: add `parser.add_argument("--version", action="version",
   version=f"today {__version__}")` in `build_parser()`, importing
   `__version__` from `today`. Keep it before the subparsers.
2. `tests/test_cli.py`: assert `today --version` exits 0 and prints
   `today 0.1.0` (argparse's `version` action raises `SystemExit`), and assert
   `today.__version__` equals the `project.version` parsed out of
   `pyproject.toml` with `tomllib`, so the two literals cannot drift.
3. `CHANGELOG.md`: Keep a Changelog 1.1.0 header, an empty `## [Unreleased]`,
   and `## [0.1.0] - 2026-07-31` backfilling the pre-tagging history from
   `git log` (bare `today`/`path`/`create`/`show --json`, `task add/done/rm`
   with `--tomorrow`, `habit toggle/list`, `weight`, `macros add`,
   `note add/list --tag`, `-N/--offset`, `--den`/`$DEN_PATH`, the nix package
   and overlay). Link block at the bottom: `[unreleased]` comparing
   `v0.1.0...HEAD`, `[0.1.0]` pointing at `releases/tag/v0.1.0`.
4. `.github/workflows/check.yml`: name `check`; triggers `push` filtered to
   `master`, `pull_request`, and `workflow_call` (so the release can call it);
   `actions/checkout@v4`, `cachix/install-nix-action@v31` with flakes enabled,
   then `nix flake check -L`.
5. `.github/workflows/release.yml`: trigger on tags matching
   `v[0-9]+.[0-9]+.[0-9]+`; job `check` uses `./.github/workflows/check.yml`;
   job `release` needs it, `permissions: contents: write`, and
   (a) guards `grep -qx 'version = "<v>"' pyproject.toml` and
   `grep -qx '__version__ = "<v>"' today/__init__.py`,
   (b) awk-extracts the `## [<v>]` section of `CHANGELOG.md` into a body file
   and fails when it is empty, (c) `gh release create "$tag" --title "today
   v<v>" --notes-file "$body"`.
6. `AGENTS.md`: a `## Changelog` section (one short line per user-visible
   change under `[Unreleased]`; internal refactors and task records excluded)
   and a `## Cutting a release` procedure (bump both literals, promote
   `[Unreleased]`, repoint links, `chore(release): vX.Y.Z`, tag, push both).
   Point the `Checks/records` workflow line at CI.
7. `README.md`: one line under Development naming CI and the tag-driven
   release.

## Definition of Done

1. `today --version` prints `today 0.1.0`.
   test: `pytest tests/test_cli.py -k version`
2. `today/__init__.py` and `pyproject.toml` declare the same version, enforced
   by a test rather than by review.
   test: `pytest tests/test_cli.py -k version_matches_pyproject`
3. The full check suite still passes.
   cmd: `nix flake check -L`
4. `CHANGELOG.md` has an empty `## [Unreleased]` above `## [0.1.0] -
   2026-07-31`, and a link block resolving both.
   cmd: `grep -qx '## \[Unreleased\]' CHANGELOG.md && grep -qx '## \[0.1.0\] - 2026-07-31' CHANGELOG.md`
5. Both workflows are wired as described (tag filter, `workflow_call`,
   `contents: write`, version guard, changelog-sourced notes).
   manual: read `.github/workflows/check.yml` and `release.yml`.
6. Task records are clean.
   cmd: `tatr check --ledger LESSONS.md`

## Notes

- The tag is pushed by the user during landing, not by this task; the release
  run itself is the final evidence and is out of this task's scope.
- `nix flake check` only sees git-tracked files (LESSONS.md
  `nix-flake-untracked-eval`); the new workflow files must be staged before
  the local check proof means anything.
- Run pass/fail commands bare, not piped (LESSONS.md
  `pipefail-on-passfail-commands`).
- Assumption: the GitHub runner can build the flake within the default
  timeout; if `nix flake check` proves too slow, keeping the same workflow but
  adding a cache is a follow-up, not a redesign.

## Close-out

What and why: `today` had no CI and no release path. This adds
`.github/workflows/check.yml` (`nix flake check -L` on master, PRs and via
`workflow_call`) and `release.yml`, which a `vX.Y.Z` tag triggers: it re-runs
the checks, refuses to publish when the tag disagrees with `pyproject.toml` or
`today/__init__.py`, and publishes a GitHub Release whose notes are that
version's `CHANGELOG.md` section. `CHANGELOG.md` backfills the pre-tagging
history under `[0.1.0]`. `today --version` makes the declared version
observable from the shipped artifact, and a pytest reads `pyproject.toml` with
`tomllib` so the two literals cannot drift. `AGENTS.md` gained the changelog
contract and the cutting-a-release procedure; `README.md` names both.

Alternatives: `--generate-notes` (macros.nvim's choice) and single-sourcing
the version through `importlib.metadata` - both rejected in DECISION.md. The
plan also carried a `verify-release.sh` mirroring the workflow shell; the user
trimmed it, so the guard is proved by reading the workflow plus a throwaway
local run of the same `grep`/`awk` against the working tree (v0.1.0 accepted,
v9.9.9 rejected on both greps and extracting empty notes).

Difficulties: none material. `ruff format` wanted the new `add_argument` on one
line (`ruff check` alone would have passed). The empty `[Unreleased]` section
is what the release guard would reject, so the guard is exercised against
`[0.1.0]` only.

Evidence: `nix flake check -L` all green (ruff, mypy, 89 pytest);
`pytest -k version` red before the flag (`SystemExit(2)`,
`unrecognized arguments: --version`) and green after; the changelog greps;
`today --version` prints `today 0.1.0`; `tatr check --ledger LESSONS.md` rc=0.

Reflection: the changelog-sourced notes make the changelog load-bearing rather
than decorative - the first release that forgets an entry fails loudly. The
one gap left by design is that the workflow shell itself is first executed by
the real tag push.
