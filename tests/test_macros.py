"""Food database and machine-facing macros command tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from today import macros
from today.cli import main


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "macros.csv"
    path.write_text(
        "chicken thigh 100grams,25,0,5\n"
        "egg 1piece,6,0,5\n"
        "chicken breast 100g,31,0,3.6\n"
        "broken row\n",
        encoding="utf-8",
    )
    return path


def test_database_parses_units_and_skips_invalid_rows(tmp_path: Path) -> None:
    database = macros.Database.load(_database(tmp_path))
    assert sorted(database.foods) == [
        "chicken breast:g",
        "chicken thigh:g",
        "egg:pc",
    ]
    assert database.foods["chicken thigh:g"].unit == "g"
    assert database.foods["egg:pc"].unit == "pc"


def test_query_is_fuzzy_case_insensitive_and_deterministic(tmp_path: Path) -> None:
    database = macros.Database.load(_database(tmp_path))
    assert database.query("CH") == [
        {"id": "chicken breast:g", "name": "chicken breast", "unit": "g"},
        {"id": "chicken thigh:g", "name": "chicken thigh", "unit": "g"},
    ]
    assert [item["id"] for item in database.query("eg")] == [
        "egg:pc",
        "chicken breast:g",
        "chicken thigh:g",
    ]


def test_calculate_scales_grams_and_pieces(tmp_path: Path) -> None:
    database = macros.Database.load(_database(tmp_path))
    gram = database.calculate("CHICKEN BREAST:G", 150)
    assert gram.to_dict() == {
        "food": "chicken breast",
        "amount": 150,
        "unit": "g",
        "protein": 46.5,
        "carbs": 0,
        "fat": 5.4,
    }
    piece = database.calculate("egg:pc", 2)
    assert (piece.protein, piece.carbs, piece.fat) == (12, 0, 10)


@pytest.mark.parametrize("amount", [0, -1, float("inf"), float("nan")])
def test_calculate_rejects_non_positive_or_non_finite_amounts(
    tmp_path: Path, amount: float
) -> None:
    with pytest.raises(ValueError, match="positive finite"):
        macros.Database.load(_database(tmp_path)).calculate("egg:pc", amount)


def test_insert_canonicalizes_and_atomically_appends(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "macros.csv"
    inserted = macros.insert(path, "apple 2pieces,0.6,50,0.4")
    assert inserted.id == "apple:pc"
    assert path.read_text(encoding="utf-8") == "apple 2pc,0.6,50,0.4\n"
    macros.insert(path, "olive oil 10grams,0,0,10")
    assert path.read_text(encoding="utf-8").endswith("olive oil 10g,0,0,10\n")


@pytest.mark.parametrize(
    "row",
    [
        "apple 0pc,1,2,3",
        "apple 1kg,1,2,3",
        "apple 1pc,nan,2,3",
        "apple 1pc,-1,2,3",
        "missing macros 1pc,1,2",
    ],
)
def test_invalid_database_rows_are_rejected(row: str) -> None:
    with pytest.raises(ValueError):
        macros.parse_row(row)


def test_cli_query_json_uses_environment_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MACROS_DATABASE", str(_database(tmp_path)))
    assert main(["macros", "query", "ch", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "results": [
            {"id": "chicken breast:g", "name": "chicken breast", "unit": "g"},
            {"id": "chicken thigh:g", "name": "chicken thigh", "unit": "g"},
        ]
    }


def test_cli_json_before_query_action_is_preserved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "macros",
                "--json",
                "query",
                "ch",
                "--database",
                str(_database(tmp_path)),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["results"][0]["id"] == (
        "chicken breast:g"
    )


def test_cli_search_alias_and_explicit_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "macros",
                "search",
                "egg",
                "--database",
                str(_database(tmp_path)),
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["results"][0]["id"] == "egg:pc"


def test_cli_calculate_and_insert_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _database(tmp_path)
    assert (
        main(
            [
                "macros",
                "calculate",
                "--food",
                "egg:pc",
                "--amount",
                "2",
                "--database",
                str(path),
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {
        "food": "egg",
        "amount": 2,
        "unit": "pc",
        "protein": 12,
        "carbs": 0,
        "fat": 10,
    }
    assert (
        main(
            [
                "macros",
                "insert",
                "apple 1piece,0.3,25,0.2",
                "--database",
                str(path),
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["unit"] == "pc"
    assert path.read_text(encoding="utf-8").endswith("apple 1pc,0.3,25,0.2\n")


def test_cli_database_io_error_has_no_stdout_or_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "macros",
                "query",
                "egg",
                "--database",
                str(tmp_path),
                "--json",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("macros: ")
    assert "directory" in captured.err.lower()
    assert "Traceback" not in captured.err


def test_cli_invalid_amount_has_no_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "macros",
                "calculate",
                "--food",
                "egg:pc",
                "--amount",
                "0",
                "--database",
                str(_database(tmp_path)),
                "--json",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "positive finite" in captured.err
