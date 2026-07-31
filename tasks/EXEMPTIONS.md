# Historical schema exemptions

`tatr check` validates every sibling record against its schema, and `tatr flow`
gates its transitions on the same rules. The records below were written before
the rule they now trip, and the flow trail is append-only history: a task
record is not rewritten to satisfy a rule invented after it landed. Each line
classifies one such record explicitly.

Format, one exemption per line:

```
- <task-id> <rule>: <why this record is exempt>
```

An entry suppresses that rule for that task only. An entry that never fires is
reported as `unused-exemption` on a full `tatr check`, so the list cannot rot:
when a record is legitimately rewritten, its exemption must go with it.

New work does not get exemptions. Scaffold the record with
`tatr scaffold <id> <RECORD>` and it is schema-clean from the first byte.

## Pre-v2 records

- 20260720-142158 bad-record-schema: pre-v2 record, free-form headings
- 20260720-142158 bad-review-round: pre-v2 REVIEW.md, no round structure
- 20260720-142159 bad-record-schema: pre-v2 record, free-form headings
- 20260720-142159 missing-reviewer: pre-v2 REVIEW.md, reviewer not recorded
- 20260720-142200 bad-record-schema: pre-v2 record, free-form headings
- 20260720-142200 bad-review-round: pre-v2 REVIEW.md, no round structure
- 20260720-142201 bad-record-schema: pre-v2 record, free-form headings
- 20260720-142201 missing-reviewer: pre-v2 REVIEW.md, reviewer not recorded
- 20260720-142201 bad-verdict: pre-v2 REVIEW.md, verdict not per round
- 20260720-142202 bad-record-schema: pre-v2 record, free-form headings
- 20260720-142202 missing-reviewer: pre-v2 REVIEW.md, reviewer not recorded
- 20260720-142202 bad-verdict: pre-v2 REVIEW.md, verdict not per round
- 20260720-142203 bad-record-schema: pre-v2 record, free-form headings
- 20260720-142203 bad-review-round: pre-v2 REVIEW.md, no round structure
- 20260720-142204 bad-record-schema: pre-v2 record, free-form headings
- 20260720-142204 bad-review-round: pre-v2 REVIEW.md, no round structure
- 20260720-142205 bad-record-schema: pre-v2 record, free-form headings
- 20260720-142205 bad-review-round: pre-v2 REVIEW.md, no round structure
- 20260720-171855 bad-record-schema: pre-v2 record, free-form headings
- 20260720-172833 bad-record-schema: pre-v2 record, free-form headings
- 20260720-172833 bad-review-round: pre-v2 REVIEW.md, no round structure
