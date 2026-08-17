from __future__ import annotations

from pathlib import Path

import pytest

from today import edit
from today.model import parse_day

BASE = (
    "# D\n\n### Tasks\n\n- [ ] one\n- [x] two\n\n"
    "### Habits\n\n- [ ] Learn\n\n"
    "### Macros\n\nwhat,protein,carbs,fat\n\n"
    "### Weight\n\n### Notes\n\n"
)


def test_task_mutations_are_scoped_to_tasks() -> None:
    added = edit.add_task(BASE, "three")
    assert "- [ ] three" in added
    assert "### Habits\n\n- [ ] Learn" in added
    toggled = edit.toggle_task(added, 1)
    assert "### Tasks\n\n- [x] one" in toggled
    removed = edit.remove_task(toggled, 2)
    assert "- [x] two" not in removed


def test_task_index_errors() -> None:
    with pytest.raises(IndexError):
        edit.toggle_task(BASE, 9)
    with pytest.raises(IndexError):
        edit.remove_task(BASE, 0)


def test_missing_task_section_is_not_created() -> None:
    with pytest.raises(LookupError):
        edit.add_task("# D\n", "x")


def test_habit_toggle_is_section_scoped() -> None:
    source = BASE.replace("- [ ] one", "- [ ] Learn")
    changed = edit.toggle_habit(source, "learn")
    assert "### Tasks\n\n- [ ] Learn" in changed
    assert "### Habits\n\n- [x] Learn" in changed


def test_weight_is_one_canonical_line() -> None:
    first = edit.set_weight(BASE, "71.0")
    assert "### Weight\n\n71.0 kg" in first
    second = edit.set_weight(first, "72.5")
    assert second.count(" kg") == 1
    assert "72.5 kg" in second


def test_food_rows_use_valid_row_indexes() -> None:
    source = edit.add_macros_row(BASE, "eggs,12,0,10")
    source = source.replace("eggs,12,0,10\n", "eggs,12,0,10\nprose\n")
    source = edit.add_macros_row(source, "rice,3,40,1")
    changed = edit.remove_macros_row(source, 2)
    assert "rice,3,40,1" not in changed
    assert "prose" in changed


def test_structured_note_add_edit_remove() -> None:
    added = edit.add_note(BASE, "10:30 - work", "First line\n\n- item")
    assert "#### 10:30 - work\n\nFirst line\n\n- item" in added
    changed = edit.edit_note(added, 1, "10:31 - work", "Changed")
    assert "#### 10:31 - work\n\nChanged" in changed
    assert "First line" not in changed
    removed = edit.remove_note(changed, 1)
    assert "####" not in removed
    assert "### Notes" in removed


def test_note_indexes_only_h4_blocks() -> None:
    source = BASE + "loose content\n\n#### valid\n\nbody\n"
    changed = edit.edit_note(source, 1, "valid", "new")
    assert "loose content" in changed
    assert "new" in changed


def test_note_index_errors() -> None:
    with pytest.raises(IndexError):
        edit.edit_note(BASE, 1, "x", "body")
    with pytest.raises(IndexError):
        edit.remove_note(BASE, 1)


def test_crlf_is_preserved_for_existing_lines() -> None:
    source = BASE.replace("\n", "\r\n")
    changed = edit.toggle_task(source, 1)
    assert "\r\n" in changed
    assert "\n" not in changed.replace("\r\n", "")


def test_atomic_write_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "day.md"
    path.write_text(BASE)
    edit.atomic_write(path, edit.add_task(path.read_text(), "new"))
    assert parse_day(path).tasks[-1].text == "new"
