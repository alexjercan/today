"""Unit tests for the safe write-back foundation (today/edit.py).

These exercise the transform functions directly and assert byte-level
preservation of everything outside the edited list, using the real fixtures.
"""

from __future__ import annotations

from pathlib import Path

from today import edit
from today.model import parse_day

FIXTURES = Path(__file__).parent / "fixtures"
SATURDAY = FIXTURES / "2026-07-18-Saturday.md"


def test_add_creates_a_today_section_when_missing() -> None:
    text = "# Monday\n\n### 📝 Notes\n\n"
    out = edit.add_item(text, "first task", edit.TODAY)
    assert out == "# Monday\n\n### 📝 Notes\n\nToday\n- [ ] first task\n"


def test_add_appends_after_the_last_existing_item() -> None:
    text = "# D\n\n### 📝 Notes\n\nToday\n- [ ] one\n- [x] two\n\ntrailing prose\n"
    out = edit.add_item(text, "three", edit.TODAY)
    assert out == (
        "# D\n\n### 📝 Notes\n\nToday\n- [ ] one\n- [x] two\n- [ ] three\n\n"
        "trailing prose\n"
    )


def test_add_tomorrow_creates_a_plain_bullet_section() -> None:
    text = "# D\n\n### 📝 Notes\n\nToday\n- [ ] one\n"
    out = edit.add_item(text, "later", edit.TOMORROW)
    assert out == "# D\n\n### 📝 Notes\n\nToday\n- [ ] one\n\nTomorrow\n- later\n"


def test_toggle_flips_only_the_target_checkbox(tmp_path: Path) -> None:
    text = "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n- [ ] b\n"
    out = edit.toggle_item(text, 2)
    assert out == "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n- [x] b\n"
    assert edit.toggle_item(out, 2) == text  # round-trips back


def test_remove_deletes_the_target_line() -> None:
    text = "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n- [ ] b\n- [ ] c\n"
    out = edit.remove_item(text, 2, edit.TODAY)
    assert out == "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n- [ ] c\n"


def test_out_of_range_raises() -> None:
    text = "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n"
    for fn in (
        lambda: edit.remove_item(text, 5, edit.TODAY),
        lambda: edit.toggle_item(text, 5),
        lambda: edit.remove_item(text, 1, edit.TOMORROW),  # no Tomorrow section
    ):
        try:
            fn()
        except IndexError:
            continue
        raise AssertionError("expected IndexError")


def test_fixture_prose_survives_a_toggle() -> None:
    """Saturday has a Today checkbox followed by a long prose block - editing the
    task must not disturb any of that prose."""
    original = SATURDAY.read_text(encoding="utf-8")
    out = edit.toggle_item(original, 1)
    # The single task line flips from [x] to [ ]; nothing else changes.
    assert out == original.replace(
        "- [x] let's implement more", "- [ ] let's implement more", 1
    )
    # And the whole thing still parses.
    assert out.count("\n") == original.count("\n")


def test_atomic_write_replaces_the_file(tmp_path: Path) -> None:
    path = tmp_path / "entry.md"
    path.write_text("old\n", encoding="utf-8")
    edit.atomic_write(path, "new\n")
    assert path.read_text(encoding="utf-8") == "new\n"
    # No stray temp files left behind.
    assert [p.name for p in tmp_path.iterdir()] == ["entry.md"]


def test_add_then_parse_matches_expected(tmp_path: Path) -> None:
    """The core contract: write via edit, read via parse_day, get what we wrote."""
    path = tmp_path / "2026-07-20-Monday.md"
    path.write_text("# Monday\n\n### 📝 Notes\n\n", encoding="utf-8")
    edit.atomic_write(path, edit.add_item(path.read_text(), "task one", edit.TODAY))
    edit.atomic_write(path, edit.add_item(path.read_text(), "task two", edit.TODAY))
    edit.atomic_write(path, edit.toggle_item(path.read_text(), 1))
    day = parse_day(path)
    assert [(t.index, t.text, t.done) for t in day.tasks] == [
        (1, "task one", True),
        (2, "task two", False),
    ]


def test_crlf_file_preserves_line_endings() -> None:
    """A CRLF file must not be silently rewritten to LF by an edit."""
    text = "# D\r\n\r\n### 📝 Notes\r\n\r\nToday\r\n- [ ] a\r\n- [ ] b\r\n"
    out = edit.toggle_item(text, 2)
    # Only the checkbox flips; every CRLF terminator is preserved.
    assert out == "# D\r\n\r\n### 📝 Notes\r\n\r\nToday\r\n- [ ] a\r\n- [x] b\r\n"
    # A new item is inserted with the file's own CRLF, not a bare LF.
    added = edit.add_item(text, "c", edit.TODAY)
    assert added.endswith("- [ ] b\r\n- [ ] c\r\n")
    assert "\n" not in added.replace("\r\n", "")  # no stray lone LFs


def test_no_trailing_newline_is_preserved() -> None:
    """Editing a file that does not end in a newline keeps existing bytes intact."""
    text = "# D\n\n### 📝 Notes\n\nToday\n- [ ] a"  # no final newline
    out = edit.toggle_item(text, 1)
    assert out == "# D\n\n### 📝 Notes\n\nToday\n- [x] a"


def test_add_lands_inside_notes_when_a_section_follows() -> None:
    """A new list must be created inside Notes, not under a later section."""
    text = "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n\n### 🌱 Habits\n\n- [ ] Learn\n"
    out = edit.add_item(text, "later", edit.TOMORROW)
    # Tomorrow appears between the Today list and the Habits header, not after it.
    assert out == (
        "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n\nTomorrow\n- later\n\n"
        "### 🌱 Habits\n\n- [ ] Learn\n"
    )


def test_mixed_list_index_matches_parser(tmp_path: Path) -> None:
    """When a plain bullet is interleaved with Today checkboxes, `task done N`
    must touch exactly the item parse_day exposes as index N."""
    path = tmp_path / "day.md"
    path.write_text(
        "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n- plain\n- [ ] b\n",
        encoding="utf-8",
    )
    day = parse_day(path)
    # The parser numbers by position among ALL bullets: a=1, b=3 (plain has no id).
    assert [(t.index, t.text) for t in day.tasks] == [(1, "a"), (3, "b")]
    # Toggling index 3 flips b, leaving the plain bullet untouched.
    edit.atomic_write(path, edit.toggle_item(path.read_text(), 3))
    assert (
        path.read_text() == "# D\n\n### 📝 Notes\n\nToday\n- [ ] a\n- plain\n- [x] b\n"
    )
    # Index 2 lands on the plain bullet, which is not a task -> rejected.
    try:
        edit.toggle_item(path.read_text(), 2)
    except IndexError:
        pass
    else:
        raise AssertionError("index 2 (a plain bullet) should not be toggleable")
