"""In-place, atomic edits to a day entry's Today/Tomorrow task lists.

This is the write-back foundation the other mutations (habits, weight, macros,
notes) build on: parse the raw markdown, transform only the lines that change,
and write the whole file back atomically so a crash never leaves a half-write.

Every untouched line is preserved byte-for-byte - the file is split with
``splitlines(keepends=True)`` so each line keeps its own terminator, only the
few lines that change are touched, and the whole thing is rejoined with a bare
``"".join``. LF, CRLF, and even exotic separators round-trip exactly; only
lines we insert use the file's detected newline. The list geometry (which line
a 1-based task index maps to) mirrors ``today.model.parse_day`` exactly, so an
index printed by ``show --json`` refers to the same item these functions edit.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from today.model import _BULLET, _CHECK, _H1, _H3, _section_of

TODAY = "Today"
TOMORROW = "Tomorrow"

_CHECKBOX = re.compile(r"\[[ xX]\]")


def atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (temp file in the same dir + rename).

    The rename is atomic on POSIX, so readers see either the old file or the new
    one, never a partial write. ``newline=""`` keeps the newlines we put in
    ``text`` verbatim (no platform translation). The directory is fsynced after
    the rename so it survives a crash.
    """
    directory = path.parent
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _fsync_dir(directory)


def _fsync_dir(directory: Path) -> None:
    """Best-effort fsync of a directory so a rename survives a crash."""
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _newline(lines: list[str]) -> str:
    """The file's line terminator, inferred from the first terminated line."""
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
        if line.endswith("\r"):
            return "\r"
    return "\n"


def _join(lines: list[str]) -> str:
    """Rejoin keepends lines - each already carries its own terminator."""
    return "".join(lines)


def _body_start(lines: list[str]) -> int:
    """First line after the H1 title - where the parser starts scanning markers."""
    for i, line in enumerate(lines):
        if _H1.match(line):
            return i + 1
    return 0


def _find_marker(lines: list[str], marker: str) -> int | None:
    """Index of the ``Today``/``Tomorrow`` marker line, or None if absent.

    Matched the same way the parser does: a full line equal to the marker word
    (case-insensitive), anywhere after the title.
    """
    target = marker.strip().lower()
    for i in range(_body_start(lines), len(lines)):
        if lines[i].strip().lower() == target:
            return i
    return None


def _item_lines(lines: list[str], marker_idx: int) -> list[int]:
    """Line indices of the contiguous bullet list directly after ``marker_idx``.

    Mirrors ``model._collect_list``: stops at the first blank or non-bullet line.
    """
    result: list[int] = []
    i = marker_idx + 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            break
        if _CHECK.match(line) or _BULLET.match(line):
            result.append(i)
            i += 1
            continue
        break
    return result


def _target_line(lines: list[str], marker: str, index: int) -> int | None:
    """Physical line index for 1-based task ``index`` under ``marker``.

    Reproduces the parser's index assignment: a Tomorrow item's index is its
    position among all bullets; a Today task's index is its position among all
    bullets *and* it must be a checkbox (plain bullets are not tasks).
    """
    marker_idx = _find_marker(lines, marker)
    if marker_idx is None:
        return None
    items = _item_lines(lines, marker_idx)
    if index < 1 or index > len(items):
        return None
    line_no = items[index - 1]
    if marker.strip().lower() == TODAY.lower() and not _CHECK.match(lines[line_no]):
        return None
    return line_no


def _notes_region(lines: list[str]) -> tuple[int, int]:
    """The ``[start, end)`` line range of the Notes section's body.

    ``start`` is the line after the ``### ... Notes`` header; ``end`` is the next
    ``### `` header (or EOF). Falls back to ``(len, len)`` - append at EOF - when
    there is no Notes section at all.
    """
    header = None
    for i, line in enumerate(lines):
        h3 = _H3.match(line)
        if h3 and _section_of(h3.group(1)) == "notes":
            header = i
            break
    if header is None:
        return len(lines), len(lines)
    end = len(lines)
    for i in range(header + 1, len(lines)):
        if _H3.match(lines[i]):
            end = i
            break
    return header + 1, end


def _insert_section(lines: list[str], marker: str, bullet: str) -> None:
    """Create a missing ``marker`` list at the end of the Notes section body.

    Bounded to the Notes section so the new list never lands under a later
    section. Separated from the preceding content by exactly one blank line: the
    section's existing blank spacer is reused when Notes is the last section (so
    template output stays clean), otherwise a blank is added and the blank before
    the following header is preserved.
    """
    newline = _newline(lines)
    start, end = _notes_region(lines)
    content_end = start
    for i in range(start, end):
        if lines[i].strip() != "":
            content_end = i + 1
    block = [marker + newline, bullet + newline]

    reuse_spacer = (
        content_end < end and lines[content_end].strip() == "" and end == len(lines)
    )
    if reuse_spacer:
        insert_at = content_end + 1
    else:
        insert_at = content_end
        if insert_at > 0:
            block = [newline] + block

    if insert_at > 0 and not lines[insert_at - 1].endswith(("\n", "\r")):
        lines[insert_at - 1] += newline
    lines[insert_at:insert_at] = block


def add_item(text: str, item: str, marker: str) -> str:
    """Return ``text`` with a new item appended to the ``marker`` list.

    Today items are checkboxes (``- [ ] item``); Tomorrow items are plain
    bullets (``- item``). Creates the section if it does not exist yet.
    """
    lines = text.splitlines(keepends=True)
    is_today = marker.strip().lower() == TODAY.lower()
    bullet = f"- [ ] {item}" if is_today else f"- {item}"
    marker_idx = _find_marker(lines, marker)
    if marker_idx is None:
        _insert_section(lines, marker, bullet)
        return _join(lines)
    items = _item_lines(lines, marker_idx)
    insert_at = items[-1] + 1 if items else marker_idx + 1
    newline = _newline(lines)
    if insert_at > 0 and not lines[insert_at - 1].endswith(("\n", "\r")):
        lines[insert_at - 1] += newline
    lines.insert(insert_at, bullet + newline)
    return _join(lines)


def remove_item(text: str, index: int, marker: str) -> str:
    """Return ``text`` with the 1-based ``index`` item removed from ``marker``.

    Raises ``IndexError`` if no task with that index exists.
    """
    lines = text.splitlines(keepends=True)
    line_no = _target_line(lines, marker, index)
    if line_no is None:
        raise IndexError(f"no {marker.lower()} task #{index}")
    del lines[line_no]
    return _join(lines)


def toggle_item(text: str, index: int, marker: str = TODAY) -> str:
    """Return ``text`` with the 1-based Today task ``index`` checkbox toggled.

    Raises ``IndexError`` if no task with that index exists.
    """
    lines = text.splitlines(keepends=True)
    line_no = _target_line(lines, marker, index)
    if line_no is None:
        raise IndexError(f"no {marker.lower()} task #{index}")
    lines[line_no] = _toggle_checkbox(lines[line_no])
    return _join(lines)


def _toggle_checkbox(line: str) -> str:
    """Flip the first ``[ ]``/``[x]`` on a line, preserving everything else."""
    if re.search(r"\[[xX]\]", line):
        return _CHECKBOX.sub("[ ]", line, count=1)
    return _CHECKBOX.sub("[x]", line, count=1)
