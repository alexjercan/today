"""Application API for reading and changing the-den daily entries."""

from __future__ import annotations

import fcntl
import math
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterator

from today import edit
from today.model import Day, Task, parse_day

DEFAULT_DEN = Path.home() / "personal" / "the-den"
_DATE_STEM = re.compile(r"^(\d{4}-\d{2}-\d{2})-[A-Za-z]+$")


class RevisionConflict(RuntimeError):
    """The entry changed after the caller read it."""


@dataclass(frozen=True)
class UpcomingTask:
    date: str
    revision: str
    index: int
    text: str
    done: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "revision": self.revision,
            "index": self.index,
            "text": self.text,
            "done": self.done,
        }


def resolve_den(arg: str | None) -> Path:
    """Resolve the den from an argument, environment, or user default."""
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("DEN_PATH")
    return Path(env).expanduser() if env else DEFAULT_DEN


def resolve_date(value: str | None = None, offset: int | None = None) -> date:
    """Resolve one explicit ISO date or an offset from the current date."""
    if value is not None:
        if offset is not None:
            raise ValueError("--date and --offset are mutually exclusive")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(f"invalid date: {value!r}")
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"invalid date: {value!r}") from None
    return date.today() + timedelta(days=offset or 0)


def stem_for(target: date) -> str:
    return target.strftime("%Y-%m-%d-%A")


def title_for(target: date) -> str:
    return target.strftime("%A, %B %d, %Y")


def entry_path(den: Path, target: date) -> Path:
    return den / "Daily" / f"{stem_for(target)}.md"


def date_from_entry(path: Path) -> date | None:
    match = _DATE_STEM.fullmatch(path.stem)
    if match is None:
        return None
    try:
        target = date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return target if path.stem == stem_for(target) else None


def _template(den: Path) -> str:
    template = den / "Templates" / "daily.md"
    if template.is_file():
        return template.read_text(encoding="utf-8")
    return (
        "# {{title}}\n\n### 🌱 Habits\n\n### 🍽️ Macros\n\n"
        "what,protein,carbs,fat\n\n### 📝 Notes\n\n"
    )


@contextmanager
def _write_lock(den: Path) -> Iterator[None]:
    daily = den / "Daily"
    daily.mkdir(parents=True, exist_ok=True)
    lock = daily / ".today.lock"
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _create_complete(path: Path, text: str) -> bool:
    """Link a completed temporary file into place without replacing a winner."""
    fd, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".create"
    )
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return False
        edit._fsync_dir(path.parent)
        return True
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _ensure_day_locked(den: Path, target: date) -> tuple[Path, bool]:
    path = entry_path(den, target)
    if path.is_file():
        return path, False
    body = _template(den).replace("{{title}}", title_for(target))
    return path, _create_complete(path, body)


def ensure_day(den: Path, target: date) -> Path:
    """Create a complete daily entry once, without Tomorrow carry-forward."""
    with _write_lock(den):
        path, _created = _ensure_day_locked(den, target)
        return path


def revision(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_ino}:{stat.st_mtime_ns}:{stat.st_size}"


def read_day(den: Path, target: date, *, create: bool = True) -> tuple[Day, str]:
    path = ensure_day(den, target) if create else entry_path(den, target)
    for _attempt in range(3):
        before = revision(path)
        day = parse_day(path)
        after = revision(path)
        if before == after:
            return day, after
    raise RuntimeError(f"entry changed repeatedly while reading: {path}")


def _mutate_existing(
    den: Path,
    target: date,
    expected_revision: str,
    transform: Callable[[str], str],
) -> tuple[Day, str]:
    with _write_lock(den):
        path, _created = _ensure_day_locked(den, target)
        current = revision(path)
        if current != expected_revision:
            raise RevisionConflict(f"entry changed: {target.isoformat()}")
        text = path.read_text(encoding="utf-8")
        updated = transform(text)
        if updated != text:
            edit.atomic_write(path, updated)
        return parse_day(path), revision(path)


def add_task(
    den: Path,
    target: date,
    text: str,
    expected_revision: str | None,
) -> tuple[Day, str]:
    """Add a task, creating a missing target only when the caller saw it missing."""
    item = text.strip()
    if not item:
        raise ValueError("task text must not be empty")
    with _write_lock(den):
        path = entry_path(den, target)
        if expected_revision is None:
            path, created = _ensure_day_locked(den, target)
            if not created:
                raise RevisionConflict(f"entry appeared: {target.isoformat()}")
        else:
            path, _created = _ensure_day_locked(den, target)
            if revision(path) != expected_revision:
                raise RevisionConflict(f"entry changed: {target.isoformat()}")
        current = revision(path)
        source = path.read_text(encoding="utf-8")
        if revision(path) != current:
            raise RevisionConflict(f"entry changed: {target.isoformat()}")
        edit.atomic_write(path, edit.add_item(source, item, edit.TODAY))
        return parse_day(path), revision(path)


def toggle_task(
    den: Path, target: date, index: int, expected_revision: str
) -> tuple[Day, str]:
    return _mutate_existing(
        den, target, expected_revision, lambda text: edit.toggle_item(text, index)
    )


def remove_task(
    den: Path, target: date, index: int, expected_revision: str
) -> tuple[Day, str]:
    return _mutate_existing(
        den,
        target,
        expected_revision,
        lambda text: edit.remove_item(text, index, edit.TODAY),
    )


def toggle_habit(
    den: Path, target: date, name: str, expected_revision: str
) -> tuple[Day, str]:
    return _mutate_existing(
        den, target, expected_revision, lambda text: edit.toggle_habit(text, name)
    )


def normalize_weight(value: str) -> str:
    cleaned = re.sub(r"(?i)\s*kg\s*$", "", value.strip()).strip()
    normalized = cleaned if "." in cleaned else f"{cleaned}.0"
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", normalized):
        raise ValueError(value)
    return normalized


def set_weight(
    den: Path, target: date, value: str, expected_revision: str
) -> tuple[Day, str]:
    normalized = normalize_weight(value)
    return _mutate_existing(
        den,
        target,
        expected_revision,
        lambda text: edit.set_weight(text, normalized),
    )


def normalize_macros_row(row: str) -> str:
    cells = [cell.strip() for cell in row.split(",")]
    if len(cells) < 4:
        raise ValueError("expected what,protein,carbs,fat")
    for label, cell in zip(("protein", "carbs", "fat"), cells[1:4], strict=True):
        try:
            value = float(cell)
        except ValueError:
            raise ValueError(f"{label} is not a number: {cell!r}") from None
        if not math.isfinite(value):
            raise ValueError(f"{label} is not a finite number: {cell!r}")
    if cells[0] == "what":
        raise ValueError("food name 'what' collides with the table header")
    return ",".join(cells[:4])


def add_food(
    den: Path, target: date, row: str, expected_revision: str
) -> tuple[Day, str]:
    normalized = normalize_macros_row(row)
    return _mutate_existing(
        den,
        target,
        expected_revision,
        lambda text: edit.add_macros_row(text, normalized),
    )


def remove_food(
    den: Path, target: date, index: int, expected_revision: str
) -> tuple[Day, str]:
    return _mutate_existing(
        den,
        target,
        expected_revision,
        lambda text: edit.remove_macros_row(text, index),
    )


def add_note(
    den: Path,
    target: date,
    text: str,
    tag: str | None,
    expected_revision: str,
) -> tuple[list[tuple[str, str | None]], str]:
    _day, current = _mutate_existing(
        den,
        target,
        expected_revision,
        lambda source: edit.add_note(source, text, tag),
    )
    path = entry_path(den, target)
    return edit.iter_notes(path.read_text(encoding="utf-8")), current


def list_notes(den: Path, target: date) -> list[tuple[str, str | None]]:
    path = ensure_day(den, target)
    return edit.iter_notes(path.read_text(encoding="utf-8"))


def list_upcoming(den: Path, after: date) -> list[UpcomingTask]:
    daily = den / "Daily"
    if not daily.is_dir():
        return []
    entries: list[tuple[date, Path]] = []
    for path in daily.glob("*.md"):
        target = date_from_entry(path)
        if target is not None and target > after:
            entries.append((target, path))
    upcoming: list[UpcomingTask] = []
    for target, _path in sorted(entries):
        day, current = read_day(den, target, create=False)
        upcoming.extend(
            UpcomingTask(
                date=target.isoformat(),
                revision=current,
                index=task.index,
                text=task.text,
                done=task.done,
            )
            for task in day.tasks
            if not task.done
        )
    return upcoming


def upcoming_dates(den: Path, after: date) -> list[tuple[date, Day, str]]:
    daily = den / "Daily"
    if not daily.is_dir():
        return []
    result: list[tuple[date, Day, str]] = []
    for path in daily.glob("*.md"):
        target = date_from_entry(path)
        if target is None or target <= after:
            continue
        day, current = read_day(den, target, create=False)
        result.append((target, day, current))
    return sorted(result, key=lambda item: item[0])


def weight_history(den: Path, end: date, days: int) -> list[tuple[str, float]]:
    if days < 1:
        raise ValueError("days must be at least 1")
    result: list[tuple[str, float]] = []
    for delta in range(days - 1, -1, -1):
        target = end - timedelta(days=delta)
        path = entry_path(den, target)
        if not path.is_file():
            continue
        day, _current = read_day(den, target, create=False)
        if day.weight is not None:
            result.append((target.isoformat(), day.weight))
    return result


def task_dicts(tasks: list[Task]) -> list[dict[str, object]]:
    return [task.to_dict() for task in tasks]
