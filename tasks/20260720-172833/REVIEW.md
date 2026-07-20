# Review: Fix checks.pytest sandbox import (20260720-172833)

- VERDICT: APPROVE
- ROUNDS: 1 (out-of-context reviewer)

## Summary

One-line fix in `flake.nix` `mkCheck`: `export REPO_ROOT=$PWD` after `cd work`,
plus an accurate comment. Reviewer confirmed the exact root cause and approved.

## Root cause (confirmed)

The editable install writes a literal code-exec `.pth`
(`_editable_impl_today.pth`):

    import sys; import os.path; sys.path.append(os.path.expandvars(("$REPO_ROOT")))

It re-expands `$REPO_ROOT` from the environment on every interpreter start. In
the check sandbox `REPO_ROOT` was unset (only the devShell shellHook set it), so
`expandvars` returned the literal `'$REPO_ROOT'` and appended a nonexistent
relative path -> `ModuleNotFoundError: No module named 'today'`. ruff/mypy passed
because they analyze files by path and never import the package.

## Assessment

- `$PWD` = `/build/work` (after `cp -r $src work; cd work`), the flat-layout root
  that directly contains `today/`. Imports resolve to the copied source.
- Hermetic: REPO_ROOT resolves sandbox-local; the `.pth` stores only the
  unexpanded literal, so no host/build path is baked into any store output.
- ruff/mypy unaffected; all three checks now share the identical mechanism, so a
  future `mkCheck`-based check inherits the fix.
- PYTHONPATH alternative rejected: the line above deliberately clears PYTHONPATH;
  using the editable mechanism's own variable is the faithful fix.

## Non-blocking nits (not actioned)

- Could note REPO_ROOT + emptied PYTHONPATH are the two halves of "clean but
  importable".
- `$PWD` relies on `cd work` immediately preceding; capture `work=$PWD` if the
  recipe ever grows intermediate `cd`s. Purely defensive.

## Proof

`nix flake check` fully green (ruff, mypy, pytest 30/30). The green check is the
regression pin (a build-sandbox path defect cannot be pinned by a unit test).
