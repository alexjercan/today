# Fix checks.pytest: package not importable in the nix sandbox

- STATUS: OPEN
- PRIORITY: 60
- TAGS: bug

## Goal

The flake check derivation checks.pytest fails in the nix sandbox with
ModuleNotFoundError: No module named 'today' (3 collection errors) while
the same tests pass in the devShell (30/30). The check derivation runs
pytest without making the package importable. Reproduced on 5aa6805
(pre-existing; found during the flow-v2 adoption, 20260720-171855).
Fix the derivation so checks.pytest is green in CI/sandbox.
