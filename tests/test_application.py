"""Application-layer tests against temporary den directories."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pytest

from today import application

TARGET = date(2030, 5, 7)


def _den(tmp_path: Path) -> Path:
    den = tmp_path / "den"
    (den / "Templates").mkdir(parents=True)
    (den / "Templates" / "daily.md").write_text(
        "# {{title}}\n\n### Tasks\n\n### Habits\n\n- [ ] 💪 Gym\n\n"
        "### Macros\n\nwhat,protein,carbs,fat\n\n### Weight\n\n### Notes\n\n",
        encoding="utf-8",
    )
    return den


def test_ensure_day_is_complete_under_concurrent_creation(tmp_path: Path) -> None:
    den = _den(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as executor:
        paths = list(
            executor.map(lambda _index: application.ensure_day(den, TARGET), range(8))
        )
    assert len(set(paths)) == 1
    text = paths[0].read_text(encoding="utf-8")
    assert text.startswith("# Tuesday, May 07, 2030")
    assert "{{title}}" not in text
    assert not list(paths[0].parent.glob("*.create"))


def test_ensure_day_does_not_carry_legacy_tomorrow(tmp_path: Path) -> None:
    den = _den(tmp_path)
    previous = application.entry_path(den, date(2030, 5, 6))
    previous.parent.mkdir(parents=True)
    previous.write_text(
        "# Monday\n\n### Notes\n\nTomorrow\n- old behavior\n",
        encoding="utf-8",
    )
    target = application.ensure_day(den, TARGET)
    assert "old behavior" not in target.read_text(encoding="utf-8")


def test_revision_conflict_refuses_indexed_write(tmp_path: Path) -> None:
    den = _den(tmp_path)
    day, first = application.read_day(den, TARGET)
    day, second = application.add_task(den, TARGET, "one", first)
    assert day.tasks[0].text == "one"
    with pytest.raises(application.RevisionConflict):
        application.toggle_task(den, TARGET, 1, first)
    assert application.read_day(den, TARGET)[0].tasks[0].done is False
    assert first != second


def test_add_task_with_missing_revision_requires_missing_file(tmp_path: Path) -> None:
    den = _den(tmp_path)
    day, _current = application.add_task(den, TARGET, "scheduled", None)
    assert day.tasks[0].text == "scheduled"
    with pytest.raises(application.RevisionConflict):
        application.add_task(den, TARGET, "stale", None)


def test_upcoming_sorts_dates_and_skips_done_tasks(tmp_path: Path) -> None:
    den = _den(tmp_path)
    later = date(2030, 5, 10)
    earlier = date(2030, 5, 8)
    application.add_task(den, later, "later", None)
    _day, revision = application.add_task(den, earlier, "done", None)
    day, revision = application.add_task(den, earlier, "earlier", revision)
    application.toggle_task(den, earlier, 1, revision)
    upcoming = application.list_upcoming(den, TARGET)
    assert [(item.date, item.text) for item in upcoming] == [
        ("2030-05-08", "earlier"),
        ("2030-05-10", "later"),
    ]


def test_food_rows_can_be_removed_by_displayed_index(tmp_path: Path) -> None:
    den = _den(tmp_path)
    day, current = application.read_day(den, TARGET)
    day, current = application.add_food(den, TARGET, "eggs,12,1,10", current)
    day, current = application.add_food(den, TARGET, "rice,3,40,1", current)
    assert [food.name for food in day.foods] == ["eggs", "rice"]
    day, _current = application.remove_food(den, TARGET, 1, current)
    assert [food.name for food in day.foods] == ["rice"]
    assert day.macros.protein == 3.0


def test_resolve_date_rejects_invalid_and_conflicting_values() -> None:
    with pytest.raises(ValueError, match="invalid date"):
        application.resolve_date("2030-02-30")
    with pytest.raises(ValueError, match="mutually exclusive"):
        application.resolve_date("2030-05-07", 1)
