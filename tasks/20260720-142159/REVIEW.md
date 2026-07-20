# Review: today task mutations + safe write-back foundation

- TASK: 20260720-142159
- BRANCH: today-task-mutations

## Round 1

- VERDICT: REQUEST_CHANGES

Reviewed by an independent fresh-eyes pass (out-of-context agent) plus a manual
re-derivation of the index geometry. Index-to-line mapping and atomic-write
safety verified CORRECT. Two byte-preservation bugs found, both uncaught by the
current tests.

- [x] R1.1 (MAJOR) today/edit.py `_split`/`_join` - `text.splitlines()` splits on
  `\r\n`/`\r`/`\x0b`/`\x0c`/`\x1c`-`\x1e`/` `/... and `_join` re-emits only
  `\n`, so a CRLF file has every line ending rewritten on a single edit -
  violates "preserve the rest byte-for-byte". Switch to `splitlines(keepends=True)`
  and `"".join(...)` so untouched lines (and any terminator) round-trip exactly.
  - Response: Fixed. Rewrote edit.py to keep each line's own terminator via
    `splitlines(keepends=True)`; `_join` is now `"".join`. Untouched lines
    (LF, CRLF, or exotic separators) are preserved byte-for-byte; only inserted
    lines use the file's detected newline. Added `test_crlf_file_preserves_line_endings`
    and `test_no_trailing_newline_is_preserved`.

- [x] R1.2 (MAJOR) today/edit.py `_append_section` - appends a new Today/Tomorrow
  list at absolute EOF, so if any `### ` section follows Notes the list lands under
  the wrong section. Insert relative to the Notes section boundary instead.
  - Response: Fixed. New-section insertion is now bounded to the Notes section:
    it finds the Notes header and the next `### ` header, and inserts after the
    last non-blank line of that region (reusing the section's blank spacer when
    Notes is the last section, so template output stays clean; otherwise adding
    one blank and preserving the blank before the following header). Added
    `test_add_lands_inside_notes_when_a_section_follows`.

- [x] R1.3 (MINOR) today/edit.py `_append_section` collapsed ALL pre-existing
  trailing blank lines. Preserve them.
  - Response: Fixed by R1.2's rewrite - it no longer pops trailing blanks; it
    inserts at the end of the Notes content and leaves surrounding blanks intact.

- [x] R1.4 (NIT) today/edit.py `atomic_write` does not fsync the containing
  directory after `os.replace`, so the rename could be lost on a crash (content
  integrity already holds).
  - Response: Fixed. Added a best-effort directory fsync after `os.replace`
    (guarded for platforms that cannot fsync a directory).

- [x] R1.5 (MAJOR) tests: No test exercises a mixed list (a plain bullet
  interleaved with Today checkboxes) - the trickiest part of the index contract.
  - Response: Added `test_mixed_list_index_matches_parser`, which asserts the
    physical line `task done N` / `task rm N` touches is exactly the item
    `show --json` prints as index N, for a checkbox/plain/checkbox list.

## Round 2

- VERDICT: APPROVE

All five findings verified resolved against the new diff; full check suite green
(ruff, ruff format, mypy, 30 pytest tests).

- R1.1 confirmed: `test_crlf_file_preserves_line_endings` and
  `test_no_trailing_newline_is_preserved` pass; CRLF and no-final-newline files
  round-trip byte-for-byte, inserted lines use the detected newline.
- R1.2 / R1.3 confirmed: `test_add_lands_inside_notes_when_a_section_follows`
  pass; a new list lands inside Notes with the following section's blank spacer
  preserved. Template output stays clean (`test_add_creates_a_today_section_when_missing`).
- R1.4 confirmed: directory fsync added; `test_atomic_write_replaces_the_file`
  still green (no stray temp files).
- R1.5 confirmed: `test_mixed_list_index_matches_parser` pins the index contract
  for a checkbox/plain/checkbox list (done 3 -> b, index 2 -> IndexError).
