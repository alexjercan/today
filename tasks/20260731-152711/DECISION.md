# Decision: Release mechanism for v0.1.0: CHANGELOG, CI, tag-triggered GitHub release

- DATE: 20260731-152836
- STATUS: ACCEPTED
- TASK: 20260731-152711
- TAGS: release, ci, changelog

## Context

`today` had no CI and no changelog, so the release mechanism has to be built
from nothing. Two sibling projects already solved this and disagree on the
details: macros.nvim publishes with `gh release create --generate-notes` and
guards two version literals; tatr extracts the matching `CHANGELOG.md` section
with awk and uses it as the release body. The version here lives in
`pyproject.toml` and `today/__init__.py`; `flake.nix` derives it from the uv
workspace and declares none.

## Decision

1. Release notes come from the `CHANGELOG.md` section for the tagged version
   (tatr's awk extraction), and an empty section fails the release.
2. The version stays declared twice (`pyproject.toml`, `today/__init__.py`),
   with drift caught by a pytest that reads `pyproject.toml` via `tomllib`,
   and by the CI tag guard.
3. `today --version` is added, so the declared version is observable from the
   shipped artifact and not only from source files.
4. CI is a single reusable `check.yml` running `nix flake check -L`, called by
   `release.yml`, with its push trigger filtered to `master` so a tag does not
   run the suite twice.
5. The guard and the notes extraction live inline in `release.yml`, reviewed
   by reading the workflow; no local mirror script (user's call - keep the
   proofs to ordinary code checks).

## Alternatives considered

- `--generate-notes` (macros.nvim): needs no changelog discipline, but the
  notes become a commit list. Rejected: the changelog contract is part of what
  this task is introducing, and the empty-section failure makes forgetting it
  loud.
- Single-source the version via `importlib.metadata.version("today")`:
  removes the drift entirely, but raises `PackageNotFoundError` when the
  package is not installed and would need a fallback. Rejected as more moving
  parts than a three-line test.
- Extract the workflow shell into a checked-in `scripts/release-guard.sh`, or
  mirror it in a task-folder verify script, so the guard is locally provable.
  Rejected: `AGENTS.md` declares this repo has no top-level `scripts/`, the
  precedent projects keep the guard inline, and a hand-mirrored script drifts.
  The cost is that the guard is first exercised by the real tag.

## Consequences

- Every user-visible change must add a `[Unreleased]` line, or the next
  release fails at the empty-section check.
- Bumping a version means editing two files; the test fails immediately if
  only one is edited.
- CI runs a full `nix flake check` on every push to `master` and every PR;
  cold-cache runs may be slow, and adding a binary cache is a follow-up.
