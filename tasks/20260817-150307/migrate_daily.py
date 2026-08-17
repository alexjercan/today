#!/usr/bin/env python3
"""One-time best-effort migration to canonical daily sections."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

H1 = re.compile(r"^#\s+(.+?)\s*$")
H3 = re.compile(r"^###\s+(.+?)\s*$")
H4 = re.compile(r"^####\s+(.+?)\s*$")
CHECK = re.compile(r"^\s*-\s+\[[ xX~]\]\s+")
BULLET = re.compile(r"^\s*-\s+")
OLD_WEIGHT = re.compile(r"^\s*weight\s*::\s*([0-9]+(?:\.[0-9]+)?)(?:\s*kg)?\s*$", re.I)
NEW_WEIGHT = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s+kg\s*$", re.I)
OLD_NOTE = re.compile(r"^\s*note\s*::\s*(\S.*?)\s*$", re.I)
KNOWN = {"tasks", "habits", "macros", "weight", "notes"}


def section_name(heading: str) -> str | None:
    last = heading.strip().lower().split()[-1]
    return last if last in KNOWN else None


def split_sections(lines: list[str]) -> tuple[str, dict[str, list[str]], list[str]]:
    title = next((line for line in lines if H1.match(line)), "# Untitled")
    sections: dict[str, list[str]] = {}
    extras: list[str] = []
    current: str | None = None
    seen_title = False
    for line in lines:
        if line == title and not seen_title:
            seen_title = True
            current = None
            continue
        match = H3.match(line)
        if match:
            name = section_name(match.group(1))
            if name is None:
                current = None
                extras.append(line)
            else:
                current = name
                sections.setdefault(name, [])
            continue
        if current is None:
            if line.strip():
                extras.append(line)
        else:
            sections[current].append(line)
    return title, sections, extras


def take_marker_block(lines: list[str], marker: str) -> tuple[list[str], list[str]]:
    kept: list[str] = []
    items: list[str] = []
    index = 0
    target = marker.lower()
    while index < len(lines):
        if lines[index].strip().lower() != target:
            kept.append(lines[index])
            index += 1
            continue
        index += 1
        while index < len(lines) and not lines[index].strip():
            index += 1
        while index < len(lines) and (
            CHECK.match(lines[index]) or BULLET.match(lines[index])
        ):
            items.append(lines[index])
            index += 1
    return kept, items


def structured_notes(
    lines: list[str], extras: list[str], tomorrow: list[str]
) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        if OLD_WEIGHT.match(line):
            continue
        marker = OLD_NOTE.match(line)
        cleaned.append(f"#### {marker.group(1)}" if marker else line)
    if extras:
        safe_extras = [
            re.sub(r"^###\s+", "##### ", line) if H3.match(line) else line
            for line in extras
        ]
        cleaned.extend(["", "#### Imported content", "", *safe_extras])
    if tomorrow:
        cleaned.extend(["", "#### Historical Tomorrow", "", *tomorrow])

    output: list[str] = []
    loose: list[str] = []

    def flush_loose() -> None:
        nonlocal loose
        while loose and not loose[0].strip():
            loose.pop(0)
        while loose and not loose[-1].strip():
            loose.pop()
        if loose:
            if output and output[-1].strip():
                output.append("")
            output.extend(["#### Imported", "", *loose])
        loose = []

    in_note = False
    for line in cleaned:
        if H4.match(line):
            flush_loose()
            if output and output[-1].strip():
                output.append("")
            output.append(line)
            in_note = True
        elif in_note:
            output.append(line)
        else:
            loose.append(line)
    flush_loose()
    while output and not output[-1].strip():
        output.pop()
    return output


def migrate(source: str) -> str:
    lines = source.splitlines()
    title, sections, extras = split_sections(lines)
    notes = sections.get("notes", [])
    notes, tasks = take_marker_block(notes, "Today")
    notes, tomorrow = take_marker_block(notes, "Tomorrow")
    if sections.get("tasks"):
        tasks = [*sections["tasks"], *tasks]

    weight = sections.get("weight", [])
    if not any(NEW_WEIGHT.match(line) for line in weight):
        old_values = [
            match.group(1) for line in lines if (match := OLD_WEIGHT.match(line))
        ]
        if old_values:
            weight = [f"{old_values[0]} kg"]

    extras = [line for line in extras if not OLD_WEIGHT.match(line)]
    canonical = {
        "Tasks": tasks,
        "Habits": sections.get("habits", []),
        "Macros": sections.get("macros", []),
        "Weight": weight,
        "Notes": structured_notes(notes, extras, tomorrow),
    }
    output = [title]
    for heading, body in canonical.items():
        output.extend(["", f"### {heading}", ""])
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        output.extend(body)
    return "\n".join(output).rstrip() + "\n"


def atomic_write(path: Path, text: str) -> None:
    fd, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".migrate"
    )
    try:
        os.fchmod(fd, path.stat().st_mode & 0o777)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("den", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    records: list[dict[str, object]] = []
    for path in sorted((args.den / "Daily").glob("*.md")):
        try:
            source = path.read_text(encoding="utf-8")
            updated = migrate(source)
            if args.write and updated != source:
                atomic_write(path, updated)
            records.append(
                {"file": path.name, "changed": updated != source, "error": None}
            )
        except Exception as exc:  # Best effort leaves the original file untouched.
            records.append({"file": path.name, "changed": False, "error": str(exc)})
    report = {
        "files": len(records),
        "changed": sum(record["changed"] is True for record in records),
        "errors": [record for record in records if record["error"] is not None],
        "records": records,
    }
    rendered = json.dumps(report, indent=2)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: report[key] for key in ("files", "changed", "errors")}, indent=2
        )
    )
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
