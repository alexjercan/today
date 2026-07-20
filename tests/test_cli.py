"""CLI tests against a temp den - no real journal, no editor."""

from __future__ import annotations

import json
from pathlib import Path

from today.cli import build_parser, entry_path, main, resolve_den, stem_for


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


def test_mutation_subcommands_are_scaffolded(tmp_path: Path, capsys) -> None:
    den = _den(tmp_path)
    rc = main(["--den", str(den), "habit"])
    assert rc == 2  # planned, exits non-zero with a clear message
    assert "not implemented yet" in capsys.readouterr().err


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
