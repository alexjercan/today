from __future__ import annotations

import json
from pathlib import Path

import pytest

from today.model import parse_day

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.md")))
def test_parse_day_matches_canonical_golden(path: Path) -> None:
    expected = json.loads(path.with_suffix(".json").read_text())
    parsed = parse_day(path).to_dict()
    parsed["file"] = expected["file"]
    assert parsed == expected


def test_missing_sections_use_defaults(tmp_path: Path) -> None:
    path = tmp_path / "2030-01-01-Tuesday.md"
    path.write_text("# Day\n\nUnstructured content\n")
    day = parse_day(path)
    assert day.tasks == []
    assert day.habits == []
    assert day.foods == []
    assert day.notes == []
    assert day.weight is None
    assert day.macros.to_dict() == {
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "calories": 0,
    }


def test_parser_rejects_legacy_layout_by_ignoring_it(tmp_path: Path) -> None:
    path = tmp_path / "day.md"
    path.write_text("# D\n\n### 📝 Notes\n\nToday\n- [ ] old task\n\nweight :: 70 Kg\n")
    day = parse_day(path)
    assert day.tasks == []
    assert day.notes == []
    assert day.weight is None


def test_notes_are_h4_delimited_markdown_blocks(tmp_path: Path) -> None:
    path = tmp_path / "day.md"
    path.write_text(
        "# D\n\n### Notes\n\nignored\n\n#### 09:00 - first\n\n"
        "paragraph\ncontinued\n\n- item\n\n#### second\n\nbody\n"
    )
    notes = parse_day(path).notes
    assert [note.to_dict() for note in notes] == [
        {
            "index": 1,
            "heading": "09:00 - first",
            "body": "paragraph\ncontinued\n\n- item",
        },
        {"index": 2, "heading": "second", "body": "body"},
    ]


def test_weight_requires_one_canonical_line(tmp_path: Path) -> None:
    path = tmp_path / "day.md"
    path.write_text("# D\n\n### Weight\n\n71.4 kg\n")
    assert parse_day(path).weight == 71.4
    path.write_text("# D\n\n### Weight\n\n71.4 kg\nextra\n")
    assert parse_day(path).weight is None


def test_macros_skip_invalid_and_non_finite_rows(tmp_path: Path) -> None:
    path = tmp_path / "day.md"
    path.write_text(
        "# D\n\n### Macros\n\nwhat,protein,carbs,fat\n"
        "eggs,12,1,10\nbad,inf,1,1\nrice,3,40,1\n"
    )
    day = parse_day(path)
    assert [food.name for food in day.foods] == ["eggs", "rice"]
    assert day.macros.protein == 15
    assert day.macros.calories == 323
