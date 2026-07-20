# Retro: Adopt flow v2 (today)

- TASK: 20260720-171855
- BRANCH: chore/flow-v2-adoption (landed as 3e9836a via sprout land)
- REVIEW ROUNDS: 1 (out-of-context APPROVE, zero findings)

## What went well

- Cleanest migration of the six: one finding, honestly mapped; ledger was
  already v2-shaped; the work agent verified the pre-existing
  checks.pytest failure against the BASE commit before claiming it was
  not its breakage - exactly the baseline discipline the ledger teaches.

## What went wrong

- Nothing in this cycle; the repo's checks.pytest derivation was already
  broken (filed as its own bug task).

## Action items

- [x] Filed the checks.pytest sandbox bug as a task in this repo.
