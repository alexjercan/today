"""CLI tests against a temp den - no real journal, no editor."""

from __future__ import annotations

import json
from pathlib import Path

from today.cli import (
    build_parser,
    day_for,
    entry_path,
    main,
    resolve_den,
    stem_for,
    title_for,
)


def _den(tmp_path: Path) -> Path:
    den = tmp_path / "den"
    (den / "Daily").mkdir(parents=True)
    (den / "Templates").mkdir(parents=True)
    (den / "Templates" / "daily.md").write_text(
        "# {{title}}\n\n### 🌱 Habits\n\n- [ ] 📕 Learn\n- [ ] 💪 Gym\n\n"
        "### 🍽️ Macros\n\nwhat,protein,carbs,fat\n\n### 📝 Notes\n\n",
        encoding="utf-8",
    )
    return den


def test_resolve_den_prefers_arg_then_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEN_PATH", str(tmp_path / "from-env"))
    assert resolve_den(str(tmp_path / "from-arg")) == tmp_path / "from-arg"
    assert resolve_den(None) == tmp_path / "from-env"


def test_create_fills_the_title_from_the_template(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    rc = main(["--den", str(den), "create"])
    assert rc == 0
    path = Path(capsys.readouterr().out.strip())
    assert path == entry_path(den, 0)
    text = path.read_text()
    assert "{{title}}" not in text  # template placeholder filled
    assert stem_for(0).split("-")[-1] in text  # weekday in the title


def test_show_json_reports_the_parsed_day(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    rc = main(["--den", str(den), "show", "--json"])
    assert rc == 0
    day = json.loads(capsys.readouterr().out)
    assert day["date"] == stem_for(0)
    assert [h["name"] for h in day["habits"]] == ["📕 Learn", "💪 Gym"]
    assert day["tasks"] == []
    assert day["weight"] is None


def test_path_does_not_create_the_entry(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    rc = main(["--den", str(den), "path"])
    assert rc == 0
    assert not entry_path(den, 0).exists()  # path is read-only


def test_title_pads_day_of_month_to_two_digits() -> None:
    """the-den titles are zero-padded ("Friday, January 02, 2026"), matching the
    old today's `date +%d`. Scan a month of offsets so a single-digit day is hit
    regardless of the run date."""
    for off in range(0, 40):
        d = day_for(off)
        expected = f"{d.strftime('%A, %B')} {d.day:02d}, {d.year}"
        assert title_for(off) == expected


def test_carry_forward_turns_tomorrow_into_today(tmp_path: Path) -> None:
    den = _den(tmp_path)
    # Yesterday has a Tomorrow list; creating today should carry it into Today.
    prev = entry_path(den, -1)
    prev.write_text(
        "# yesterday\n\n### 📝 Notes\n\nTomorrow\n- ship the thing\n",
        encoding="utf-8",
    )
    main(["--den", str(den), "create"])
    from today.model import parse_day

    day = parse_day(entry_path(den, 0))
    assert [t.text for t in day.tasks] == ["ship the thing"]


def test_carry_forward_no_previous_entry_is_clean(tmp_path: Path) -> None:
    """No yesterday file: create still succeeds with an empty Today (old today
    warns and skips the carry-over)."""
    from today.model import parse_day

    den = _den(tmp_path)
    assert not entry_path(den, -1).exists()
    rc = main(["--den", str(den), "create"])
    assert rc == 0
    day = parse_day(entry_path(den, 0))
    assert day.tasks == []
    assert "Today" not in entry_path(den, 0).read_text()  # no empty Today marker


def test_carry_forward_empty_tomorrow_carries_nothing(tmp_path: Path) -> None:
    """Yesterday has a Tomorrow header but no bullets: nothing is carried."""
    from today.model import parse_day

    den = _den(tmp_path)
    entry_path(den, -1).write_text(
        "# yesterday\n\n### 📝 Notes\n\nTomorrow\n\nsome prose\n", encoding="utf-8"
    )
    main(["--den", str(den), "create"])
    day = parse_day(entry_path(den, 0))
    assert day.tasks == []


def test_carry_forward_multiple_tomorrow_items(tmp_path: Path) -> None:
    from today.model import parse_day

    den = _den(tmp_path)
    entry_path(den, -1).write_text(
        "# yesterday\n\n### 📝 Notes\n\nTomorrow\n- one\n- two\n- three\n",
        encoding="utf-8",
    )
    main(["--den", str(den), "create"])
    day = parse_day(entry_path(den, 0))
    assert [(t.index, t.text, t.done) for t in day.tasks] == [
        (1, "one", False),
        (2, "two", False),
        (3, "three", False),
    ]


def test_note_add_then_list_roundtrips(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "note", "add", "buy milk"])
    capsys.readouterr()
    rc = main(["--den", str(den), "note", "list", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == [{"text": "buy milk", "tag": None}]


def test_note_add_with_tag_and_filter(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "note", "add", "ship release", "--tag", "work"])
    main(["--den", str(den), "note", "add", "call mom", "--tag", "home"])
    main(["--den", str(den), "note", "add", "untagged thing"])
    capsys.readouterr()
    # Filter by tag.
    rc = main(["--den", str(den), "note", "list", "--tag", "work", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == [
        {"text": "ship release", "tag": "work"}
    ]
    # Listing all yields every note, tag split out.
    main(["--den", str(den), "note", "list", "--json"])
    allnotes = json.loads(capsys.readouterr().out)
    assert allnotes == [
        {"text": "ship release", "tag": "work"},
        {"text": "call mom", "tag": "home"},
        {"text": "untagged thing", "tag": None},
    ]


def test_note_list_does_not_include_tasks_or_weight(tmp_path: Path, capsys) -> None:
    """Notes listing must ignore the Today/Tomorrow lists and the weight line."""
    den = _den(tmp_path)
    main(["--den", str(den), "task", "add", "a today task"])
    main(["--den", str(den), "task", "add", "a tomorrow task", "--tomorrow"])
    main(["--den", str(den), "weight", "75"])
    main(["--den", str(den), "note", "add", "the only note"])
    capsys.readouterr()
    main(["--den", str(den), "note", "list", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out == [{"text": "the only note", "tag": None}]


def test_note_add_rejects_multiword_tag(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    before = entry_path(den, 0).read_text()
    capsys.readouterr()
    rc = main(["--den", str(den), "note", "add", "x", "--tag", "two words"])
    assert rc == 1
    assert "single word" in capsys.readouterr().err
    assert entry_path(den, 0).read_text() == before  # file untouched


def test_note_add_rejects_marker_in_text_with_tag(tmp_path: Path, capsys) -> None:
    """With --tag the appended marker must be unambiguous, so a text already
    carrying a 'note ::' marker is rejected."""
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    capsys.readouterr()
    rc = main(
        ["--den", str(den), "note", "add", "sneaky note :: home", "--tag", "work"]
    )
    assert rc == 1


def test_note_untagged_text_can_carry_inline_marker(tmp_path: Path, capsys) -> None:
    """Without --tag a text carrying its own `note :: tag` is stored verbatim and
    read back with that tag split out (the old daily -n convention)."""
    den = _den(tmp_path)
    main(["--den", str(den), "note", "add", "remember note :: home the address"])
    capsys.readouterr()
    main(["--den", str(den), "note", "list", "--tag", "home", "--json"])
    assert json.loads(capsys.readouterr().out) == [
        {"text": "remember the address", "tag": "home"}
    ]


def test_note_add_rejects_empty_text(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    before = entry_path(den, 0).read_text()
    capsys.readouterr()
    rc = main(["--den", str(den), "note", "add", "   ", "--tag", "work"])
    assert rc == 1
    assert "must not be empty" in capsys.readouterr().err
    assert entry_path(den, 0).read_text() == before  # file untouched


def test_note_list_empty_on_fresh_entry(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    rc = main(["--den", str(den), "note", "list", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == []


def test_macros_add_appends_and_aggregates(tmp_path: Path, capsys) -> None:
    from today.model import parse_day

    den = _den(tmp_path)
    rc = main(["--den", str(den), "macros", "add", "eggs,12,1,10", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    # 12*4 + 1*4 + 10*9 = 142 kcal (Atwater).
    assert out == {"protein": 12.0, "carbs": 1.0, "fat": 10.0, "calories": 142}
    # The row lands under the CSV header, and parse_day aggregates it.
    text = entry_path(den, 0).read_text()
    assert "what,protein,carbs,fat\neggs,12,1,10\n" in text
    assert parse_day(entry_path(den, 0)).macros.protein == 12.0


def test_macros_add_accumulates_multiple_rows(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "macros", "add", "eggs,12,1,10"])
    capsys.readouterr()
    rc = main(["--den", str(den), "macros", "add", "rice,3,40,1", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["protein"] == 15.0
    assert out["carbs"] == 41.0
    assert out["fat"] == 11.0


def test_macros_bare_reports_aggregate(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "macros", "add", "eggs,12,1,10"])
    capsys.readouterr()
    rc = main(["--den", str(den), "macros", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["protein"] == 12.0


def test_macros_rejects_non_numeric_row(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    before = entry_path(den, 0).read_text()
    capsys.readouterr()
    rc = main(["--den", str(den), "macros", "add", "eggs,lots,1,10"])
    assert rc == 1
    assert "macros:" in capsys.readouterr().err
    assert entry_path(den, 0).read_text() == before  # file untouched


def test_macros_rejects_too_few_columns(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    capsys.readouterr()
    rc = main(["--den", str(den), "macros", "add", "eggs,12,1"])
    assert rc == 1


def test_macros_rejects_non_finite_cells(tmp_path: Path, capsys) -> None:
    """inf/nan/1e400 pass float() but make the parser's calorie round() throw -
    logging one would poison the file, so the writer must reject them."""
    from today.cli import _normalize_macros_row
    from today.model import parse_day

    for bad in ("x,inf,1,1", "x,1,nan,1", "x,1,1,-inf", "x,1e400,1,1"):
        try:
            _normalize_macros_row(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} should be rejected")
    # End to end: rejected, file untouched, and the day still parses.
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    before = entry_path(den, 0).read_text()
    capsys.readouterr()
    rc = main(["--den", str(den), "macros", "add", "x,inf,1,1"])
    assert rc == 1
    assert entry_path(den, 0).read_text() == before
    parse_day(entry_path(den, 0))  # does not raise


def test_macros_capital_what_is_data_not_header(tmp_path: Path, capsys) -> None:
    """The parser skips only lowercase `what,`; `What,...` is data, and the
    writer accepts it - so the two agree it is aggregated."""
    den = _den(tmp_path)
    main(["--den", str(den), "macros", "add", "What,5,0,0", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["protein"] == 5.0


def test_macros_rejects_row_that_parser_would_drop_as_header(
    tmp_path: Path, capsys
) -> None:
    """A food literally named 'what' produces a 'what,...' line the parser skips
    as the table header, so it must be rejected rather than silently dropped."""
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    capsys.readouterr()
    rc = main(["--den", str(den), "macros", "add", "what,1,2,3"])
    assert rc == 1
    assert "header" in capsys.readouterr().err


def test_weight_log_writes_the_line_and_json(tmp_path: Path, capsys) -> None:
    from today.model import parse_day

    den = _den(tmp_path)
    rc = main(["--den", str(den), "weight", "75", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"date": stem_for(0), "weight": 75.0}
    text = entry_path(den, 0).read_text()
    assert "weight :: 75.0 Kg" in text
    # Round-trips through the parser.
    assert parse_day(entry_path(den, 0)).weight == 75.0


def test_weight_normalizes_unit_and_decimal(tmp_path: Path) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "weight", "80Kg"])
    assert "weight :: 80.0 Kg" in entry_path(den, 0).read_text()


def test_weight_updates_in_place(tmp_path: Path) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "weight", "75"])
    main(["--den", str(den), "weight", "74.5"])
    text = entry_path(den, 0).read_text()
    assert text.count("weight ::") == 1  # updated, not duplicated
    assert "weight :: 74.5 Kg" in text


def test_weight_rejects_non_numeric(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    before = entry_path(den, 0).read_text()
    capsys.readouterr()
    rc = main(["--den", str(den), "weight", "heavy"])
    assert rc == 1
    assert "not a number" in capsys.readouterr().err
    assert entry_path(den, 0).read_text() == before  # file untouched


def test_weight_rejects_values_the_parser_cannot_read(tmp_path: Path, capsys) -> None:
    """`float()` accepts these but the parser regex does not - logging any of
    them would silently write a line that reads back as weight=None."""
    from today.cli import _normalize_weight

    for bad in ("-3", "1e3", "inf", "nan", ".5", "1.", "+5", "1_000", ""):
        try:
            _normalize_weight(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} should be rejected")
    # And the CLI surfaces it as an error, leaving the file untouched.
    den = _den(tmp_path)
    main(["--den", str(den), "create"])
    before = entry_path(den, 0).read_text()
    capsys.readouterr()
    rc = main(["--den", str(den), "weight", "1e3"])
    assert rc == 1
    assert entry_path(den, 0).read_text() == before


def test_weight_show_reports_recent_trend(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    # Log weight on three consecutive days ending today.
    for offset, value in ((-2, "70"), (-1, "71"), (0, "72")):
        main(["--den", str(den), "-N", str(offset), "weight", value])
    capsys.readouterr()
    rc = main(["--den", str(den), "weight", "--days", "3", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["weight"] == 72.0
    assert out["change"] == 2.0
    assert [r["weight"] for r in out["recent"]] == [70.0, 71.0, 72.0]


def test_weight_show_empty_when_none_logged(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    rc = main(["--den", str(den), "weight", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"weight": None, "change": None, "recent": []}


def test_habit_list_reports_habits_and_state(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    rc = main(["--den", str(den), "habit", "list", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == [
        {"name": "📕 Learn", "done": False},
        {"name": "💪 Gym", "done": False},
    ]


def test_habit_toggle_matches_ignoring_emoji_and_case(tmp_path: Path, capsys) -> None:
    from today.model import parse_day

    den = _den(tmp_path)
    # Match by the bare name, no emoji, any case.
    rc = main(["--den", str(den), "habit", "toggle", "gym", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == [
        {"name": "📕 Learn", "done": False},
        {"name": "💪 Gym", "done": True},
    ]
    # Persisted, and only the Gym checkbox changed.
    day = parse_day(entry_path(den, 0))
    assert [(h.name, h.done) for h in day.habits] == [
        ("📕 Learn", False),
        ("💪 Gym", True),
    ]
    # Toggling again flips it back off.
    main(["--den", str(den), "habit", "toggle", "💪 Gym"])
    day = parse_day(entry_path(den, 0))
    assert day.habits[1].done is False


def test_habit_toggle_unknown_is_an_error(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    before = entry_path(den, 0)
    main(["--den", str(den), "create"])
    original = before.read_text()
    capsys.readouterr()
    rc = main(["--den", str(den), "habit", "toggle", "nope"])
    assert rc == 1
    assert "no habit matching" in capsys.readouterr().err
    # A rejected toggle leaves the file untouched.
    assert before.read_text() == original


def test_habit_toggle_preserves_the_rest_of_the_file(tmp_path: Path) -> None:
    den = _den(tmp_path)
    path = entry_path(den, 0)
    original = (
        "# Monday\n\n### 🌱 Habits\n\n- [ ] 📕 Learn\n- [ ] 💪 Gym\n\n"
        "### 🍽️ Macros\n\nwhat,protein,carbs,fat\n\n### 📝 Notes\n\n"
        "Today\n- [ ] a task with [ ] brackets in it\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(original, encoding="utf-8")
    main(["--den", str(den), "habit", "toggle", "Learn"])
    # Only the Learn habit checkbox flips; the Today task (also a checkbox) and
    # its literal brackets are untouched.
    assert path.read_text() == original.replace("- [ ] 📕 Learn", "- [x] 📕 Learn", 1)


def test_task_add_appends_a_today_checkbox(tmp_path: Path, capsys) -> None:
    from today.model import parse_day

    den = _den(tmp_path)
    rc = main(["--den", str(den), "task", "add", "write the tests", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == [{"index": 1, "text": "write the tests", "done": False}]
    # Round-trips through the parser identically.
    day = parse_day(entry_path(den, 0))
    assert [(t.index, t.text, t.done) for t in day.tasks] == [
        (1, "write the tests", False)
    ]


def test_task_add_tomorrow_uses_a_plain_bullet(tmp_path: Path) -> None:
    from today.model import parse_day

    den = _den(tmp_path)
    main(["--den", str(den), "task", "add", "ship it", "--tomorrow"])
    text = entry_path(den, 0).read_text()
    assert "\nTomorrow\n- ship it\n" in text
    day = parse_day(entry_path(den, 0))
    assert [t.text for t in day.tomorrow] == ["ship it"]


def test_task_done_toggles_the_checkbox(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "task", "add", "a"])
    main(["--den", str(den), "task", "add", "b"])
    capsys.readouterr()
    rc = main(["--den", str(den), "task", "done", "2", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == [
        {"index": 1, "text": "a", "done": False},
        {"index": 2, "text": "b", "done": True},
    ]
    # Toggling again flips it back.
    main(["--den", str(den), "task", "done", "2", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out[1]["done"] is False


def test_task_rm_deletes_by_index(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    for word in ("a", "b", "c"):
        main(["--den", str(den), "task", "add", word])
    capsys.readouterr()
    rc = main(["--den", str(den), "task", "rm", "2", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert [t["text"] for t in out] == ["a", "c"]
    # Indices are renumbered by the parser on the next read.
    assert [t["index"] for t in out] == [1, 2]


def test_task_rm_out_of_range_is_an_error(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    main(["--den", str(den), "task", "add", "only one"])
    before = entry_path(den, 0).read_text()
    capsys.readouterr()
    rc = main(["--den", str(den), "task", "rm", "9"])
    assert rc == 1
    assert "task #9" in capsys.readouterr().err
    # A rejected mutation leaves the file untouched.
    assert entry_path(den, 0).read_text() == before


def test_task_add_preserves_the_rest_of_the_file(tmp_path: Path) -> None:
    den = _den(tmp_path)
    path = entry_path(den, 0)
    original = (
        "# Monday\n\n### 🌱 Habits\n\n- [x] 📕 Learn\n\n### 🍽️ Macros\n\n"
        "what,protein,carbs,fat\n\n### 📝 Notes\n\nToday\n- [ ] existing\n\n"
        "some freeform prose that must survive byte-for-byte\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(original, encoding="utf-8")
    main(["--den", str(den), "task", "add", "new one"])
    updated = path.read_text()
    # Only the inserted line differs; every other line is preserved verbatim.
    assert updated == original.replace(
        "- [ ] existing\n", "- [ ] existing\n- [ ] new one\n"
    )


def test_parser_exposes_the_full_command_surface() -> None:
    parser = build_parser()
    sub = next(a for a in parser._actions if a.dest == "cmd")
    assert {
        "path",
        "create",
        "show",
        "task",
        "habit",
        "weight",
        "macros",
        "note",
    } <= set(sub.choices or ())
