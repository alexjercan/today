# Review: Release mechanism for v0.1.0: CHANGELOG, CI, tag-triggered GitHub release

- TASK: 20260731-152711
- BRANCH: feat/release-v0.1.0

## Round 1

- REVIEWER: out-of-context
- VERDICT: REQUEST_CHANGES

- [x] R1.1 (MAJOR) README.md:20 - `# (planned - parity port, see tasks/)` above
  the `task`/`habit`/`weight`/`macros`/`note` examples is contradicted by
  `CHANGELOG.md:23-30`, which this same diff adds and which declares those
  commands shipped in `0.1.0`. This branch cuts v0.1.0; the README the release
  links to must not call its own shipped surface planned. Delete the
  `# (planned - parity port, see tasks/)` line, and rewrite `README.md:50-54`
  ("Bootstrapped: ... are the parity-port work tracked in `tasks/`") to
  describe the actual shipped state.
  - Response: fixed - dropped the `(planned - parity port)` marker from
    README.md's usage block and rewrote the Status section to say the parity
    port ships as of v0.1.0.
- [x] R1.2 (MINOR) .github/workflows/release.yml:47 - the awk range ends only
  on the next `^## \[`, so the oldest section in the file (for v0.1.0, the only
  one) runs to EOF and drags the link-reference block into the notes. Confirmed
  in-session: the extraction ends with `[unreleased]: .../compare/v0.1.0...HEAD`
  and `[0.1.0]: .../releases/tag/v0.1.0`. Add `seen && /^\[/ { exit }` (or trim
  link definitions) so the body is the section only.
  - Response: fixed - the awk range now also exits on `/^\[/`, so the link
    block stays out of the notes; re-extracted, the body now ends at
    `- `today --version`.`
- [x] R1.3 (MINOR) README.md:26 - `--version` is a new user-visible flag (added
  at `today/cli.py:520`) and `AGENTS.md:10` makes `README.md` the CLI-surface
  doc, but the Usage block never mentions it. Add
  `today --version            # print the declared version` to the block.
  - Response: fixed - `today --version` is listed in README.md's usage block.
- [x] R1.4 (NIT) .github/workflows/release.yml:32 - `grep -qx "version =
  \"${version}\""` treats the tag as a basic regex, so the `.` separators match
  any character. Use `grep -qxF` on both guards (line 32 and line 36).
  - Response: fixed - both guards use `grep -qxF`; checked that a `0!1!0`
    pattern no longer matches `0.1.0`.
- [x] R1.5 (NIT) CHANGELOG.md:32 - `` - `nix flake check` runs the whole check
  suite (ruff, mypy, pytest). `` is a developer-facing entry that `AGENTS.md:16`
  ("Internal refactors, test-only changes and task records do not") excludes.
  Delete the line.
  - Response: fixed - the `nix flake check` line is out of the 0.1.0 section.

Verified by the out-of-context reviewer, spot-checked in-session:

- `nix flake check -L` green (ruff, mypy, 89 pytest, rc=0); rerun in-session,
  still green.
- DoD 1/2: `pytest -k version` and `-k version_matches_pyproject` pass;
  `today --version` prints `today 0.1.0`. DoD 4: both `CHANGELOG.md` greps
  rc=0. DoD 6: `tatr check --ledger LESSONS.md` rc=0.
- Mutation-checked both new tests: deleting the `--version` `add_argument`
  fails the flag test; a one-sided version bump fails the drift test. No
  existing test weakened or deleted.
- Guard behaviour reproduced: `0.1.0` accepted on both greps; `9.9.9` rejected
  on both and extracts empty notes; `## [Unreleased]` extracts empty, so the
  empty-section check fires as documented.
- Re-derived in-session (load-bearing): R1.2's link-block leak, and R1.1's
  README/CHANGELOG contradiction.
- Tag glob, `workflow_call` wiring, `needs: check` and job-scoped
  `permissions: contents: write` read as described.

Pending user checks:

- DoD 5 is `manual:` (read both workflow files) - the user's to resolve.
- The workflow shell is first executed by the real tag push; no CI run exists
  to observe (scope trimmed by the user).

## Round 2

- REVIEWER: out-of-context
- VERDICT: APPROVE

All five round-1 findings fixed and re-verified: the notes extraction stops
before the link block, both version guards are `grep -qxF`, README documents
`--version` and no longer calls the shipped surface planned, and the
developer-facing changelog line is gone. `nix flake check` green (ruff, mypy,
89 pytest); `tatr check --ledger LESSONS.md` rc=0. No regressions introduced by
the fixes, and no new findings.

Pending user checks (do not block APPROVE):

- DoD 5 `manual:` - read `.github/workflows/check.yml` and `release.yml`.
- The workflow shell is first executed by the real `v0.1.0` tag push.
