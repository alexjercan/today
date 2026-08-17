"""Precise atomic edits for canonical daily Markdown sections."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from today.model import _CHECK, _H3, _H4, _parse_food_row

_CHECKBOX = re.compile(r"\[[ xX~]\]")


def atomic_write(path: Path, text: str) -> None:
    directory = path.parent
    fd, temporary = tempfile.mkstemp(
        dir=directory, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    _fsync_dir(directory)


def _fsync_dir(directory: Path) -> None:
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
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
        if line.endswith("\r"):
            return "\r"
    return "\n"


def _section_region(lines: list[str], name: str) -> tuple[int, int]:
    header: int | None = None
    target = name.lower()
    for index, line in enumerate(lines):
        match = _H3.match(line.strip())
        if match and match.group(1).strip().lower() == target:
            header = index
            break
    if header is None:
        raise LookupError(f"no {name.title()} section")
    end = len(lines)
    for index in range(header + 1, len(lines)):
        if _H3.match(lines[index].strip()):
            end = index
            break
    return header + 1, end


def _content_end(lines: list[str], start: int, end: int) -> int:
    while end > start and not lines[end - 1].strip():
        end -= 1
    return end


def _insert_section_line(lines: list[str], name: str, value: str) -> None:
    start, end = _section_region(lines, name)
    newline = _newline(lines)
    position = _content_end(lines, start, end)
    if position > start and not lines[position - 1].endswith(("\n", "\r")):
        lines[position - 1] += newline
    lines.insert(position, value + newline)


def _checkbox_lines(lines: list[str], section: str) -> list[int]:
    start, end = _section_region(lines, section)
    return [index for index in range(start, end) if _CHECK.match(lines[index])]


def add_task(text: str, item: str) -> str:
    lines = text.splitlines(keepends=True)
    _insert_section_line(lines, "tasks", f"- [ ] {item}")
    return "".join(lines)


def toggle_task(text: str, index: int) -> str:
    lines = text.splitlines(keepends=True)
    targets = _checkbox_lines(lines, "tasks")
    if index < 1 or index > len(targets):
        raise IndexError(f"task {index} not found")
    target = targets[index - 1]
    match = _CHECK.match(lines[target])
    assert match is not None
    replacement = " " if match.group(1) in "xX" else "x"
    lines[target] = _CHECKBOX.sub(f"[{replacement}]", lines[target], count=1)
    return "".join(lines)


def remove_task(text: str, index: int) -> str:
    lines = text.splitlines(keepends=True)
    targets = _checkbox_lines(lines, "tasks")
    if index < 1 or index > len(targets):
        raise IndexError(f"task {index} not found")
    del lines[targets[index - 1]]
    return "".join(lines)


def toggle_habit(text: str, name: str) -> str:
    lines = text.splitlines(keepends=True)
    targets = _checkbox_lines(lines, "habits")
    normalized = name.strip().lower()
    for target in targets:
        match = _CHECK.match(lines[target])
        assert match is not None
        candidate = match.group(2).strip()
        without_emoji = candidate.split(maxsplit=1)[-1] if candidate else candidate
        if normalized not in {candidate.lower(), without_emoji.lower()}:
            continue
        replacement = " " if match.group(1) in "xX" else "x"
        lines[target] = _CHECKBOX.sub(f"[{replacement}]", lines[target], count=1)
        return "".join(lines)
    raise LookupError(f"habit not found: {name}")


def set_weight(text: str, value: str) -> str:
    lines = text.splitlines(keepends=True)
    start, end = _section_region(lines, "weight")
    newline = _newline(lines)
    replacement = value + " kg" + newline
    nonblank = [index for index in range(start, end) if lines[index].strip()]
    if nonblank:
        lines[nonblank[0]] = replacement
        for index in reversed(nonblank[1:]):
            del lines[index]
    else:
        lines.insert(start, newline)
        lines.insert(start + 1, replacement)
    return "".join(lines)


def remove_macros_row(text: str, index: int) -> str:
    lines = text.splitlines(keepends=True)
    start, end = _section_region(lines, "macros")
    rows = [line for line in range(start, end) if _parse_food_row(lines[line])]
    if index < 1 or index > len(rows):
        raise IndexError(f"food {index} not found")
    del lines[rows[index - 1]]
    return "".join(lines)


def add_macros_row(text: str, row: str) -> str:
    lines = text.splitlines(keepends=True)
    _insert_section_line(lines, "macros", row)
    return "".join(lines)


def _note_ranges(lines: list[str]) -> list[tuple[int, int]]:
    start, end = _section_region(lines, "notes")
    headings = [index for index in range(start, end) if _H4.match(lines[index].strip())]
    return [
        (heading, headings[position + 1] if position + 1 < len(headings) else end)
        for position, heading in enumerate(headings)
    ]


def add_note(text: str, heading: str, body: str) -> str:
    lines = text.splitlines(keepends=True)
    newline = _newline(lines)
    start, end = _section_region(lines, "notes")
    position = _content_end(lines, start, end)
    block = [f"#### {heading}{newline}", newline]
    block.extend(line + newline for line in body.splitlines())
    if body and not body.splitlines():
        block.append(newline)
    if position > start and lines[position - 1].strip():
        block.insert(0, newline)
    lines[position:position] = block
    return "".join(lines)


def edit_note(text: str, index: int, heading: str, body: str) -> str:
    lines = text.splitlines(keepends=True)
    ranges = _note_ranges(lines)
    if index < 1 or index > len(ranges):
        raise IndexError(f"note {index} not found")
    start, end = ranges[index - 1]
    newline = _newline(lines)
    block = [f"#### {heading}{newline}", newline]
    block.extend(line + newline for line in body.splitlines())
    if end < len(lines) and block and block[-1].strip():
        block.append(newline)
    lines[start:end] = block
    return "".join(lines)


def remove_note(text: str, index: int) -> str:
    lines = text.splitlines(keepends=True)
    ranges = _note_ranges(lines)
    if index < 1 or index > len(ranges):
        raise IndexError(f"note {index} not found")
    start, end = ranges[index - 1]
    del lines[start:end]
    return "".join(lines)
