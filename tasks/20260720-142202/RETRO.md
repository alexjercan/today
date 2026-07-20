# Retro: today macros add + aggregate

- TASK: 20260720-142202
- BRANCH: feature/macros
- REVIEW ROUNDS: 2 (REQUEST_CHANGES -> APPROVE)

## What went well

- Went in already holding the `writer-must-honor-reader-grammar` lesson from the
  weight task, so I deliberately validated macro cells with `float()` because
  that is what `_parse_macros` aggregates with, and guarded the `what,` header
  collision. That reasoning was correct as far as it went.
- Reused `_section_region` for the Macros scan and kept placement/CRLF/no-final
  -newline tests up front; the reviewer confirmed those all correct first pass.
- The comma-in-food-name worry turned out safe by construction (the name's
  trailing text fails `float()`, so the row is loudly rejected, not corrupted).

## What went wrong

- Applied the lesson one level too shallow. I matched the reader's *surface*
  grammar (`float()`) but the reader's *effective* grammar is `float()` composed
  with `round()`: `round(inf)`/`round(nan)` throw, so `x,inf,1,1` passed the
  writer, was persisted, and then crashed `parse_day` on every later read -
  permanently poisoning the day file. Root cause: I checked what the reader
  *parses* but not what it *does with the parsed value* downstream.
- A second, deeper rung (finite cells summing past DBL_MAX to inf) survived even
  the round-2 cell guard; only guarding the summed total before `round()` fully
  closed it.

## What to improve next time

- "Honor the reader's grammar" means the reader's WHOLE pipeline, not just its
  parse step: trace the parsed value through every operation that can throw
  (round, int, division, index) and validate/guard against each. When the writer
  cannot know a downstream aggregate (a sum over other rows), the reader itself
  must be made total (never crash on file contents) - the writer guards inputs,
  the reader guards results.

## Action items

- [x] LESSONS.md: bumped `writer-must-honor-reader-grammar` to x2 with the
      "whole pipeline, not just parse; make the reader total" nuance.
