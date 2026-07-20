# Retro: finalize nix packaging (in-repo half)

- TASK: 20260720-142205
- BRANCH: infra/finalize-nix
- REVIEW ROUNDS: 1 (APPROVE)

## What went well

- Followed the flow discipline on the outward-facing boundary: did the safe,
  verifiable in-repo half (overlay export, uv.lock consistency, e2e smoke test)
  and deferred the cross-repo dotfiles swap to the user rather than editing
  nix.dotfiles / deleting the live tools / rebuilding home autonomously.
- Caught the real uv.lock issue by checking the exit code correctly: the first
  `uv lock --check` in a pipe reported rc 0 (the pipe ate the exit code - the
  exact AGENTS.md trap); re-running with `set -o pipefail` showed rc 1 and the
  stale lock. The `| tail` habit nearly hid a failure.
- Turned "generate uv.lock" into the more correct fix: the lock was already
  minimal; pyproject over-declared unused template deps. Trimming pyproject (not
  padding the lock) made them consistent AND removed cruft.

## What went wrong

- Nearly trusted the piped `rc=0`. Root cause: reflexively appending `| tail` to
  a check command, which discards the real exit status. This is precisely the
  AGENTS.md "never end a build/test command with a pipe that eats its exit code"
  rule - I caught it on the second look, but should apply pipefail (or run bare)
  the first time on any pass/fail command.

## Decisions recorded

- The dotfiles swap is an outward-facing, cross-repo change that also depends on
  this repo being pushed (nix.dotfiles adds `github:alexjercan/today` as a flake
  input). It belongs as a nix.dotfiles task after the push, not something flow
  should do autonomously. Batched as the single manual-acceptance item.

## What to improve next time

- For any command whose exit code is the signal (build/test/lint/lock --check),
  run it bare or `set -o pipefail` BEFORE reading a piped tail - never infer
  pass/fail from a message line.

## Action items

- [x] LESSONS.md: `pipefail-on-passfail-commands`.
- [ ] User: complete the nix.dotfiles swap (see TASK.md "Deferred to the user").
