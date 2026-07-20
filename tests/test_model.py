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
