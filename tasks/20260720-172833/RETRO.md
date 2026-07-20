# Retro: Fix checks.pytest sandbox import

- TASK: 20260720-172833
- BRANCH: bug/pytest-sandbox-import
- REVIEW ROUNDS: 1 (APPROVE)

## What went well

- Reproduce-first paid off immediately: building `.#checks.pytest` before
  touching anything gave the exact 3-error trace, and the fix was aimed rather
  than guessed.
- The root cause was pinned by mechanism (the editable `.pth` re-expands
  `$REPO_ROOT` at import time), not by symptom, so the one-line fix was
  obviously correct. The out-of-context reviewer independently reached the same
  mechanism and even inspected the realized `.pth`, confirming it.

## What went wrong

- Nothing in this cycle. The defect itself was a devShell/sandbox parity gap:
  `REPO_ROOT` was set only in the devShell shellHook, so the editable install
  worked interactively but not in any sandboxed check. It slipped in originally
  because the check suite had never been run green in the sandbox (found during
  the flow-v2 adoption, 20260720-171855).

## What to improve next time

- When a tool depends on an env var provided by the devShell shellHook, assume
  every non-devShell context (checks, CI, `nix build`) lacks it and replicate
  it there. The devShell is not the sandbox.

## Action items

- [x] LESSONS.md: `devshell-env-not-in-checks`.
- No follow-up code work; `nix flake check` is now fully green.
