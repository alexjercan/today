"""Golden parity tests: `parse_day` must reproduce the old `daily --json` output.

Each fixture is a real `Daily/*.md` entry paired with the JSON the old bash `daily`
emitted for it (captured live). We compare every field except `file` (an absolute
path that differs between the fixture copy and the original).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from today.model import parse_day

FIXTURES = Path(__file__).parent / "fixtures"


def _cases() -> list[str]:
    return sorted(p.stem for p in FIXTURES.glob("*.md"))


@pytest.mark.parametrize("stem", _cases())
def test_parse_day_matches_golden(stem: str) -> None:
    golden = json.loads((FIXTURES / f"{stem}.json").read_text())
    parsed = parse_day(FIXTURES / f"{stem}.md").to_dict()

    for key in ("date", "title", "habits", "tasks", "tomorrow", "macros", "weight"):
        assert parsed[key] == golden[key], f"{stem}: field {key!r} differs"


def test_parse_day_reads_the_filename_stem_as_date() -> None:
    stem = _cases()[0]
    day = parse_day(FIXTURES / f"{stem}.md")
    assert day.date == stem
    assert day.file.endswith(f"{stem}.md")


def test_only_standard_checkboxes_are_tasks(tmp_path: Path) -> None:
    """Only `- [ ]` and `- [x]` are tasks. A non-standard marker like `- [~]`
    (the retired "won't do") is skipped, not counted as a task. This is a
    deliberate divergence from the old daily, whose today_tasks() awk stops the
    whole list at the first non-`[ ]`/`[x]` line (dropping every task after it);
    the new parser surfaces the real `[x]`/`[ ]` tasks instead of losing them."""
    path = tmp_path / "2026-07-20-Monday.md"
    path.write_text(
        "# D\n\n### 📝 Notes\n\n"
        "Today\n- [~] wont do this\n- [x] did this\n- [ ] still todo\n",
        encoding="utf-8",
    )
    tasks = parse_day(path).tasks
    # The [~] line is not a task; the [x] and [ ] lines are.
    assert [(t.text, t.done) for t in tasks] == [
        ("did this", True),
        ("still todo", False),
    ]


def test_parse_macros_survives_non_finite_row(tmp_path: Path) -> None:
    """A hand-edited file with an inf/nan macro must not crash the reader (the
    calorie round() would otherwise throw); the bad row is skipped."""
    path = tmp_path / "2026-07-20-Monday.md"
    path.write_text(
        "# D\n\n### 🍽️ Macros\n\nwhat,protein,carbs,fat\n"
        "eggs,10,0,0\nbad,inf,1,1\n\n### 📝 Notes\n\n",
        encoding="utf-8",
    )
    macros = parse_day(path).macros  # must not raise
    assert macros.protein == 10.0  # the inf row is skipped, eggs still counted
    assert macros.calories == 40


def test_parse_macros_survives_finite_sum_overflow(tmp_path: Path) -> None:
    """Finite cells can still sum past DBL_MAX to inf; round() would throw, so
    the calorie total is guarded and the reader degrades to 0 calories."""
    path = tmp_path / "2026-07-20-Monday.md"
    path.write_text(
        "# D\n\n### 🍽️ Macros\n\nwhat,protein,carbs,fat\n"
        "a,1e308,0,0\nb,1e308,0,0\n\n### 📝 Notes\n\n",
        encoding="utf-8",
    )
    macros = parse_day(path).macros  # must not raise despite an inf sum
    assert macros.calories == 0
