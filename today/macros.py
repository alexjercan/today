"""Food database operations compatible with macros.nvim's CSV format."""

from __future__ import annotations

import fcntl
import math
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from today import edit

DEFAULT_DATABASE = Path.home() / ".local" / "share" / "nvim" / "macros.csv"
_UNIT_ALIASES = {
    "g": "g",
    "gr": "g",
    "gram": "g",
    "grams": "g",
    "p": "pc",
    "pc": "pc",
    "pcs": "pc",
    "piece": "pc",
    "pieces": "pc",
}
_FOOD = re.compile(
    r"^(?P<name>.+?)\s+(?P<amount>(?:\d+(?:\.\d*)?|\.\d+))(?P<unit>[A-Za-z]+)$"
)


@dataclass(frozen=True)
class FoodItem:
    name: str
    amount: float
    unit: str
    protein: float
    carbs: float
    fat: float

    @property
    def id(self) -> str:
        return f"{self.name.lower()}:{self.unit}"

    def candidate(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "unit": self.unit}

    def to_dict(self) -> dict[str, str | float]:
        return {
            "food": self.name,
            "amount": self.amount,
            "unit": self.unit,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
        }

    def to_row(self) -> str:
        return (
            f"{self.name} {_number(self.amount)}{self.unit},"
            f"{_number(self.protein)},{_number(self.carbs)},{_number(self.fat)}"
        )


def resolve_database(value: str | None = None) -> Path:
    """Resolve an explicit path, MACROS_DATABASE, or the Neovim data default."""
    selected = value or os.environ.get("MACROS_DATABASE")
    return Path(selected).expanduser() if selected else DEFAULT_DATABASE


def _number(value: float) -> str:
    return format(value, ".15g")


def _positive(value: float, label: str) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return value


def _parse_number(
    value: str, label: str, *, positive: bool = False, nonnegative: bool = False
) -> float:
    try:
        number = float(value)
    except ValueError:
        requirement = "a positive finite number" if positive else "a finite number"
        raise ValueError(f"{label} must be {requirement}") from None
    if positive:
        return _positive(number, label)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number")
    if nonnegative and number < 0:
        raise ValueError(f"{label} must be a non-negative finite number")
    return number


def parse_row(row: str) -> FoodItem:
    """Parse one macros.nvim food row and normalize its unit."""
    if "\n" in row or "\r" in row:
        raise ValueError("food row must be one line")
    cells = row.split(",")
    if len(cells) != 4:
        raise ValueError("food row must contain food,protein,carbs,fat")
    food = _FOOD.fullmatch(cells[0].strip())
    if food is None:
        raise ValueError("food must end with a quantity and unit")
    name = food.group("name").strip()
    if not name or "," in name:
        raise ValueError("food name must not be empty or contain a comma")
    unit_value = food.group("unit").lower()
    unit = _UNIT_ALIASES.get(unit_value)
    if unit is None:
        raise ValueError(f"unknown unit: {unit_value}")
    amount = _parse_number(food.group("amount"), "food quantity", positive=True)
    protein, carbs, fat = (
        _parse_number(value.strip(), label, nonnegative=True)
        for value, label in zip(cells[1:], ("protein", "carbs", "fat"), strict=True)
    )
    return FoodItem(name, amount, unit, protein, carbs, fat)


class Database:
    def __init__(self, foods: dict[str, FoodItem] | None = None) -> None:
        self.foods = foods or {}

    @classmethod
    def load(cls, path: Path) -> Database:
        """Load valid rows. As in macros.nvim, later duplicate IDs replace earlier ones."""
        try:
            rows = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            raise ValueError(f"food database not found: {path}") from None
        database = cls()
        for row in rows:
            try:
                item = parse_row(row)
            except ValueError:
                continue
            database.foods[item.id] = item
        return database

    def query(self, query: str) -> list[dict[str, str]]:
        """Return deterministic subsequence matches, with prefix matches first."""
        normalized = query.strip().lower()
        if not normalized:
            raise ValueError("query must not be empty")
        matches = [
            item
            for food_id, item in self.foods.items()
            if _is_subsequence(normalized, food_id)
        ]
        matches.sort(key=lambda item: (not item.id.startswith(normalized), item.id))
        return [item.candidate() for item in matches]

    def calculate(self, food_id: str, amount: float) -> FoodItem:
        quantity = _positive(amount, "amount")
        item = self.foods.get(food_id.lower())
        if item is None:
            raise ValueError(f"unknown food ID: {food_id}")
        ratio = quantity / item.amount
        nutrients = (
            item.protein * ratio,
            item.carbs * ratio,
            item.fat * ratio,
        )
        if not all(math.isfinite(value) for value in nutrients):
            raise ValueError("calculated macros are not finite")
        return FoodItem(item.name, quantity, item.unit, *nutrients)


def _is_subsequence(query: str, candidate: str) -> bool:
    position = 0
    for character in query:
        position = candidate.find(character, position)
        if position < 0:
            return False
        position += 1
    return True


@contextmanager
def _database_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.parent / f".{path.name}.lock"
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def insert(path: Path, row: str) -> FoodItem:
    """Validate and atomically append one canonical row to the database."""
    item = parse_row(row)
    with _database_lock(path):
        try:
            source = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            source = ""
        separator = "" if not source or source.endswith(("\n", "\r")) else "\n"
        edit.atomic_write(path, f"{source}{separator}{item.to_row()}\n")
    return item
