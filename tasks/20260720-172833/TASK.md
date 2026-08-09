# Fix checks.pytest: package not importable in the nix sandbox

- STATUS: CLOSED
- PRIORITY: 60
- TAGS: bug

## Goal

The flake check derivation checks.pytest fails in the nix sandbox with
ModuleNotFoundError: No module named 'today' (3 collection errors) while
the same tests pass in the devShell (30/30). The check derivation runs
pytest without making the package importable. Reproduced on 5aa6805
(pre-existing; found during the flow-v2 adoption, 20260720-171855).
Fix the derivation so checks.pytest is green in CI/sandbox.

## Fix

The editable dev venv writes a code-exec `.pth` that re-expands `$REPO_ROOT`
at interpreter startup; only the devShell shellHook set REPO_ROOT, so in the
check sandbox it expanded to the literal `'$REPO_ROOT'` and `import today`
failed. Set `export REPO_ROOT=$PWD` in `mkCheck` (after `cd work`) so the
editable install resolves to the copied source. `nix flake check` is now fully
green (ruff, mypy, pytest 30/30) - the green check is the regression pin.
Reviewed out-of-context: APPROVE, 1 round.
