"""Strict parser for the canonical the-den daily Markdown format."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

_H1 = re.compile(r"^#\s+(.+?)\s*$")
_H3 = re.compile(r"^###\s+(.+?)\s*$")
_H4 = re.compile(r"^####\s+(.+?)\s*$")
_CHECK = re.compile(r"^\s*-\s+\[([ xX])\]\s+(.+?)\s*$")
_WEIGHT = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s+kg$", re.IGNORECASE)
_SECTIONS = {"tasks", "habits", "macros", "weight", "notes"}


@dataclass(frozen=True)
class Habit:
    name: str
    done: bool

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "done": self.done}


@dataclass(frozen=True)
class Task:
    index: int
    text: str
    done: bool

    def to_dict(self) -> dict[str, object]:
        return {"index": self.index, "text": self.text, "done": self.done}


@dataclass(frozen=True)
class Food:
    index: int
    name: str
    protein: float
    carbs: float
    fat: float

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "name": self.name,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
        }


@dataclass(frozen=True)
class Note:
    index: int
    heading: str
    body: str

    def to_dict(self) -> dict[str, object]:
        return {"index": self.index, "heading": self.heading, "body": self.body}


@dataclass(frozen=True)
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
    date: str
    file: str
    title: str
    habits: list[Habit] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    foods: list[Food] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    macros: Macros = field(default_factory=Macros)
    weight: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "file": self.file,
            "title": self.title,
            "habits": [habit.to_dict() for habit in self.habits],
            "tasks": [task.to_dict() for task in self.tasks],
            "notes": [note.to_dict() for note in self.notes],
            "macros": self.macros.to_dict(),
            "weight": self.weight,
        }


def _sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        match = _H3.match(line)
        if match:
            name = match.group(1).strip().lower()
            current = name if name in _SECTIONS else None
            if current is not None:
                sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def _parse_checkboxes(lines: list[str]) -> list[tuple[str, bool]]:
    result: list[tuple[str, bool]] = []
    for line in lines:
        match = _CHECK.match(line)
        if match:
            result.append((match.group(2).strip(), match.group(1) in "xX"))
    return result


def _parse_food_row(line: str) -> tuple[str, float, float, float] | None:
    row = line.strip()
    if not row or row.startswith("what,"):
        return None
    cells = [cell.strip() for cell in row.split(",")]
    if len(cells) != 4:
        return None
    try:
        values = [float(cell) for cell in cells[1:]]
    except ValueError:
        return None
    if not all(math.isfinite(value) for value in values):
        return None
    return cells[0], values[0], values[1], values[2]


def _parse_macros(lines: list[str]) -> tuple[list[Food], Macros]:
    foods: list[Food] = []
    protein = carbs = fat = 0.0
    for line in lines:
        parsed = _parse_food_row(line)
        if parsed is None:
            continue
        name, row_protein, row_carbs, row_fat = parsed
        foods.append(
            Food(
                index=len(foods) + 1,
                name=name,
                protein=row_protein,
                carbs=row_carbs,
                fat=row_fat,
            )
        )
        protein += row_protein
        carbs += row_carbs
        fat += row_fat
    total = protein * 4 + carbs * 4 + fat * 9
    calories = round(total) if math.isfinite(total) else 0
    return foods, Macros(protein, carbs, fat, calories)


def _parse_weight(lines: list[str]) -> float | None:
    values = [line.strip() for line in lines if line.strip()]
    if len(values) != 1:
        return None
    match = _WEIGHT.fullmatch(values[0])
    return float(match.group(1)) if match else None


def _parse_notes(lines: list[str]) -> list[Note]:
    notes: list[Note] = []
    heading: str | None = None
    body: list[str] = []

    def append() -> None:
        if heading is None:
            return
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        notes.append(Note(len(notes) + 1, heading, "\n".join(body)))

    for line in lines:
        match = _H4.match(line)
        if match:
            append()
            heading = match.group(1).strip()
            body = []
        elif heading is not None:
            body.append(line)
    append()
    return notes


def parse_day(path: Path) -> Day:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = next(
        (match.group(1).strip() for line in lines if (match := _H1.match(line))),
        "",
    )
    sections = _sections(lines)
    task_values = _parse_checkboxes(sections.get("tasks", []))
    habit_values = _parse_checkboxes(sections.get("habits", []))
    foods, macros = _parse_macros(sections.get("macros", []))
    return Day(
        date=path.stem,
        file=str(path),
        title=title,
        tasks=[
            Task(index + 1, text, done)
            for index, (text, done) in enumerate(task_values)
        ],
        habits=[Habit(name, done) for name, done in habit_values],
        foods=foods,
        notes=_parse_notes(sections.get("notes", [])),
        macros=macros,
        weight=_parse_weight(sections.get("weight", [])),
    )
