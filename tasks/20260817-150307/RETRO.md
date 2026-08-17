# Retrospective

## Result

- Replaced mixed legacy daily syntax with five canonical sections.
- Migrated 1,134 real entries without missing source content.
- Added structured multi-line note operations and a tall 3x5 Notes widget.
- Deployed and verified the strict parser against the migrated den.

## What worked

- A committed pre-migration entry and temporary-copy validation reduced data risk.
- Per-file atomic writes and error reports made the migration recoverable.
- Semantic counts plus line-preservation checks caught migration omissions.
- Browser checks covered normal writes, Focus editing, and phone overflow.

## Problems and fixes

- The first migration retained some old weight markers in imported content.
  Expanded weight detection and filtered structural lines before note import.
- Unknown H3 headings could make migration non-idempotent. Demoted them to H5
  inside imported notes.
- Interpreted 5x3 as width 5 and height 3 despite the stated tall requirement.
  Corrected it to width 3 and height 5 and added exact package assertions.

## Next time

- Convert natural-language dimensions to explicit width and height acceptance
  criteria before implementation.
- Require a zero-change second migration pass before touching real data.
