# Adopt flow v2: root LESSONS.md, clean tatr check, AGENTS.md flow section

- STATUS: CLOSED
- PRIORITY: 90
- TAGS: chore, process

## Story

As a repo in the flow ecosystem, I want the v2 /flow conventions in place -
root LESSONS.md ledger, clean tatr check, AGENTS.md pointing at /flow - so
development here compounds the same way as everywhere else. Part of the
six-repo adoption goal (umbrella: nix.dotfiles tasks/20260720-171807).

## Steps

- [x] Ledger at the root: move docs/LESSONS.md to LESSONS.md (git mv) - or
      create it from the lessons-skill format if the repo has none - then
      run the doc-surface sweep for every reference to the old path
      (AGENTS.md, README, scripts, CI guards, wiki pages) and update them.
      Bring the ledger to format: bare counts until promotion, a
      "## Pending promotions (3+ occurrences, user decides)" section;
      move unpromoted (x3)+ entries there; keep existing PROMOTED/absorbed
      annotations as they are.
- [x] Fix tatr check findings best-effort, assuming recorded work was done
      properly where the record supports it:
      - closed-unchecked: tick Steps boxes whose close-out notes or landed
        commits evidence the work shipped; genuinely unshipped steps stay
        unticked and go on the residue list;
      - closed-not-approved: normalize nonstandard-but-approving verdict
        lines (e.g. "Verdict: APPROVE", "**APPROVE**") to
        "- VERDICT: APPROVE"; a review that really ended unapproved goes on
        the residue list untouched;
      - bad-severity: map to the nearest of BLOCKER/MAJOR/MINOR/NIT
        (LOW -> MINOR, NOTE/INFO/OBSERVATION -> NIT, FIXED -> the severity
        it had, keeping any "fixed in-review" note in the text), recording
        the mapping in the close-out.
- [x] AGENTS.md: add or refresh a "Development flow" section stating: /flow
      drives development here (plan/work/review/compound via tatr tasks,
      sprout worktrees, out-of-context round-1 reviews, DoD proofs with
      test:/cmd:/manual: notation); LESSONS.md at the repo root is the
      lessons ledger, read before starting any task; `tatr check` (plus
      `--ledger LESSONS.md`) is the conformance gate. Keep the section
      short; do not restructure the rest of the file.
- [x] Verify: tatr check exit 0 (or residue listed in the close-out),
      tatr check --ledger LESSONS.md exit 0, and the repo's own check
      suite still green.

## Definition of Done

- LESSONS.md at the repo root, old docs/ path gone, no stale references
  (cmd: test -f LESSONS.md && test ! -f docs/LESSONS.md && ! grep -rn "docs/LESSONS" --include="*.md" --include="*.sh" .)
- tatr check clean or residue documented (cmd: /home/alex/personal/tatr/tatr check;
  manual: user reviews the residue list at the goal's Finish)
- ledger lints clean (cmd: /home/alex/personal/tatr/tatr check --ledger LESSONS.md)
- AGENTS.md names /flow and LESSONS.md (cmd: grep -n "flow\|LESSONS.md" AGENTS.md)

## Notes

- Use the tatr binary at /home/alex/personal/tatr/tatr (the installed one
  may predate the check subcommand).
- Preserve history honestly: normalizations keep meaning; ticks record
  verifiably shipped work only (linter-adoption cleanup, per the precedent
  in tatr's own 20260720-152503).

## Close-out

Changes:
- git mv docs/LESSONS.md -> LESSONS.md (docs/ removed; it held only the
  ledger). The ledger already had the "## Pending promotions (3+ occurrences,
  user decides)" section and no unpromoted (x3)+ entries, so no content
  reshuffle was needed.
- Doc-surface sweep: tasks/20260720-142159/RETRO.md action item updated from
  docs/LESSONS.md to LESSONS.md. AGENTS.md, README.md, scripts, and CI had no
  references to the old path.
- tatr check severity fix (the mapping applied): tasks/20260720-142159/REVIEW.md
  R1.5 "(MAJOR, tests)" -> "(MAJOR) tests:" - severity was genuinely MAJOR
  with a "tests" category qualifier baked into the tag; the qualifier moved
  into the finding text, meaning unchanged. That was the only finding.
- AGENTS.md: added a short "## Development flow" section (/flow, tatr tasks,
  sprout worktrees, out-of-context round-1 reviews, DoD proofs with
  test:/cmd:/manual:, root LESSONS.md ledger read before any task,
  /home/alex/personal/tatr/tatr check + --ledger LESSONS.md as the gate).

Residue: none. All findings were honestly mappable; no closed-unchecked or
closed-not-approved findings existed.

Check results:
- /home/alex/personal/tatr/tatr check -> exit 0
- /home/alex/personal/tatr/tatr check --ledger LESSONS.md -> exit 0
- DoD ledger cmd: test -f LESSONS.md and test ! -f docs/LESSONS.md both pass.
  The "docs/LESSONS" grep now matches only this task's own TASK.md (the step
  text describing the move and the DoD command string itself) - inherently
  self-matching spec text, not stale references.
- Repo check suite: checks.ruff and checks.mypy build green; `nix develop -c
  pytest -q` -> 30 passed. Pre-existing failure (NOT fixed, per spec): the
  checks.pytest flake derivation fails with "ModuleNotFoundError: No module
  named 'today'" in the nix sandbox - identical failure on the clean base
  commit 5aa6805, so unrelated to this change; the check derivation runs
  pytest without installing/pointing at the package.
