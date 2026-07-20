"""The journal day model + a parser/serializer for the-den's markdown format.

`the-den` stores one file per day under `Daily/YYYY-MM-DD-Weekday.md` with a fixed
set of `### ` sections (Habits, Macros, Notes) plus, inside Notes, "Today" and
"Tomorrow" task lists, and an optional `weight :: N Kg` line. `Day.to_dict()`
mirrors the JSON the old `daily` script emitted, so the agent/tools get a stable,
machine-readable shape.

This CLI is the source of truth for the format; it reads existing entries and is
the only writer (so nothing else has to parse the markdown).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_H1 = re.compile(r"^#\s+(.*)$")
_H3 = re.compile(r"^###\s+(.*)$")
_CHECK = re.compile(r"^\s*-\s+\[( |x|X)\]\s+(.*)$")
_BULLET = re.compile(r"^\s*-\s+(.*)$")
_WEIGHT = re.compile(r"weight\s*::\s*([0-9]+(?:\.[0-9]+)?)\s*Kg", re.IGNORECASE)
# Section headers are matched by the trailing word, not the emoji, so a changed
# icon does not break parsing.
_HABITS = "habits"
_MACROS = "macros"
_NOTES = "notes"


@dataclass
class Habit:
    name: str
    done: bool

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "done": self.done}


@dataclass
class Task:
    index: int
    text: str
    done: bool

    def to_dict(self) -> dict[str, object]:
        return {"index": self.index, "text": self.text, "done": self.done}


@dataclass
class TomorrowTask:
    index: int
    text: str

    def to_dict(self) -> dict[str, object]:
        return {"index": self.index, "text": self.text}


@dataclass
class Macros:
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    calories: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
            "calories": self.calories,
        }


@dataclass
class Day:
    date: str  # "2026-07-20-Monday" (the filename stem)
    file: str
    title: str
    habits: list[Habit] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    tomorrow: list[TomorrowTask] = field(default_factory=list)
    macros: Macros = field(default_factory=Macros)
    weight: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "file": self.file,
            "title": self.title,
            "habits": [h.to_dict() for h in self.habits],
            "tasks": [t.to_dict() for t in self.tasks],
            "tomorrow": [t.to_dict() for t in self.tomorrow],
            "macros": self.macros.to_dict(),
            "weight": self.weight,
        }


def _section_of(header: str) -> str | None:
    """Map a `### ...` header to a section key by its trailing word."""
    words = header.strip().lower().split()
    if not words:
        return None
    last = words[-1]
    if last in (_HABITS, _MACROS, _NOTES):
        return last
    return None


def _parse_habits(lines: list[str]) -> list[Habit]:
    habits: list[Habit] = []
    for line in lines:
        m = _CHECK.match(line)
        if m:
            habits.append(Habit(name=m.group(2).strip(), done=m.group(1) in "xX"))
    return habits


def _parse_macros(lines: list[str]) -> Macros:
    protein = carbs = fat = 0.0
    for line in lines:
        row = line.strip()
        if not row or row.startswith("what,"):  # skip the CSV header
            continue
        cells = [c.strip() for c in row.split(",")]
        if len(cells) < 4:
            continue
        try:
            protein += float(cells[1])
            carbs += float(cells[2])
            fat += float(cells[3])
        except ValueError:
            continue
    # Atwater factors: protein/carbs 4 kcal/g, fat 9 kcal/g.
    calories = round(protein * 4 + carbs * 4 + fat * 9)
    return Macros(protein=protein, carbs=carbs, fat=fat, calories=calories)


def _collect_list(
    lines: list[str], start: int
) -> tuple[list[tuple[str, bool | None]], int]:
    """From `lines[start]` (a marker like 'Today'), collect the bullet list that
    immediately follows. Returns [(text, done|None)] and the index after it.

    ``done`` is True/False for a `- [ ]` checkbox, None for a plain `- ` bullet.
    Stops at the first blank line or non-bullet line.
    """
    items: list[tuple[str, bool | None]] = []
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            break
        check = _CHECK.match(line)
        if check:
            items.append((check.group(2).strip(), check.group(1) in "xX"))
            i += 1
            continue
        bullet = _BULLET.match(line)
        if bullet:
            items.append((bullet.group(1).strip(), None))
            i += 1
            continue
        break
    return items, i


def parse_day(path: Path) -> Day:
    """Parse a Daily entry file into a `Day`."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    title = ""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    body_start = 0
    for idx, line in enumerate(lines):
        h1 = _H1.match(line)
        if h1 and not title:
            title = h1.group(1).strip()
            body_start = idx + 1
            continue
        h3 = _H3.match(line)
        if h3:
            current = _section_of(h3.group(1))
            if current is not None:
                sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)

    habits = _parse_habits(sections.get(_HABITS, []))
    macros = _parse_macros(sections.get(_MACROS, []))

    # Tasks ("Today") and Tomorrow lists live inside the Notes section as bullet
    # lists under a "Today"/"Tomorrow" marker line.
    notes_lines = lines[body_start:]
    tasks: list[Task] = []
    tomorrow: list[TomorrowTask] = []
    i = 0
    while i < len(notes_lines):
        marker = notes_lines[i].strip().lower()
        if marker == "today":
            items, i = _collect_list(notes_lines, i)
            tasks = [
                Task(index=n + 1, text=t, done=bool(d))
                for n, (t, d) in enumerate(items)
                if d is not None
            ]
            continue
        if marker == "tomorrow":
            items, i = _collect_list(notes_lines, i)
            tomorrow = [
                TomorrowTask(index=n + 1, text=t) for n, (t, _) in enumerate(items)
            ]
            continue
        i += 1

    weight_match = _WEIGHT.search(text)
    weight = float(weight_match.group(1)) if weight_match else None

    return Day(
        date=path.stem,
        file=str(path),
        title=title,
        habits=habits,
        tasks=tasks,
        tomorrow=tomorrow,
        macros=macros,
        weight=weight,
    )
