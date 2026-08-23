"""The non-interactive and editor command surface for the-den."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from today import __version__, application
from today import macros as food_database
from today.model import Day, Habit, Note, Task

DEFAULT_DEN = application.DEFAULT_DEN
DEFAULT_EDITOR = "nvim"

resolve_den = application.resolve_den
_normalize_weight = application.normalize_weight
_normalize_macros_row = application.normalize_macros_row


def day_for(offset: int) -> date:
    return date.today() + timedelta(days=offset)


def stem_for(offset: int) -> str:
    return application.stem_for(day_for(offset))


def title_for(offset: int) -> str:
    return application.title_for(day_for(offset))


def entry_path(den: Path, offset: int) -> Path:
    return application.entry_path(den, day_for(offset))


def ensure_entry(den: Path, offset: int) -> Path:
    return application.ensure_day(den, day_for(offset))


def _target(args: argparse.Namespace) -> date:
    return application.resolve_date(args.date, args.offset)


def _read(args: argparse.Namespace) -> tuple[Path, date, Day, str]:
    den = resolve_den(args.den)
    target = _target(args)
    day, current = application.read_day(den, target)
    return den, target, day, current


def _cmd_path(args: argparse.Namespace) -> int:
    print(application.entry_path(resolve_den(args.den), _target(args)))
    return 0


def _cmd_create(args: argparse.Namespace) -> int:
    print(application.ensure_day(resolve_den(args.den), _target(args)))
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    _den, _target_date, day, _revision = _read(args)
    if args.json:
        print(json.dumps(day.to_dict(), ensure_ascii=False))
    else:
        print(day.title)
        print(
            f"habits: {len(day.habits)}  tasks: {len(day.tasks)}  "
            f"notes: {len(day.notes)}  weight: {day.weight}"
        )
    return 0


def _cmd_edit(args: argparse.Namespace) -> int:
    path = application.ensure_day(resolve_den(args.den), _target(args))
    if args.no_edit:
        print(path)
        return 0
    editor = os.environ.get("EDITOR", DEFAULT_EDITOR)
    try:
        return subprocess.call([editor, str(path)])
    except OSError as exc:
        print(f"could not open {editor!r}: {exc}", file=sys.stderr)
        return 1


def _print_tasks(items: list[Task]) -> None:
    if not items:
        print("(empty)")
        return
    for item in items:
        box = "[x]" if item.done else "[ ]"
        print(f"{item.index}. {box} {item.text}")


def _cmd_task(args: argparse.Namespace) -> int:
    den = resolve_den(args.den)
    target = _target(args)
    _day, current = application.read_day(den, target)
    try:
        if args.action == "add":
            day, _revision = application.add_task(den, target, args.text, current)
        elif args.action == "rm":
            day, _revision = application.remove_task(den, target, args.index, current)
        else:
            day, _revision = application.toggle_task(den, target, args.index, current)
    except (IndexError, ValueError, application.RevisionConflict) as exc:
        print(f"today task: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([task.to_dict() for task in day.tasks], ensure_ascii=False))
    else:
        _print_tasks(day.tasks)
    return 0


def _print_habits(habits: list[Habit]) -> None:
    if not habits:
        print("(no habits)")
        return
    for habit in habits:
        box = "[x]" if habit.done else "[ ]"
        print(f"{box} {habit.name}")


def _cmd_habit(args: argparse.Namespace) -> int:
    den = resolve_den(args.den)
    target = _target(args)
    day, current = application.read_day(den, target)
    if args.haction == "toggle":
        try:
            day, _revision = application.toggle_habit(den, target, args.name, current)
        except LookupError:
            print(f"habit: no habit matching {args.name!r}", file=sys.stderr)
            return 1
        except application.RevisionConflict as exc:
            print(f"habit: {exc}", file=sys.stderr)
            return 1
    if args.json:
        print(json.dumps([habit.to_dict() for habit in day.habits], ensure_ascii=False))
    else:
        _print_habits(day.habits)
    return 0


def _print_weight_trend(recent: list[tuple[str, float]], change: float | None) -> None:
    if not recent:
        print("(no weight logged)")
        return
    for day_value, weight in recent:
        print(f"{day_value}: {weight} Kg")
    if change is not None:
        sign = "+" if change > 0 else ""
        print(f"change: {sign}{round(change, 2)} Kg over {len(recent)} entries")


def _cmd_weight(args: argparse.Namespace) -> int:
    den = resolve_den(args.den)
    target = _target(args)
    if args.value is not None:
        day, current = application.read_day(den, target)
        try:
            day, _revision = application.set_weight(den, target, args.value, current)
        except ValueError:
            print(f"weight: not a number: {args.value!r}", file=sys.stderr)
            return 1
        except application.RevisionConflict as exc:
            print(f"weight: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"date": day.date, "weight": day.weight}))
        else:
            print(f"logged weight: {day.weight} Kg")
        return 0

    recent = application.weight_history(den, target, args.days)
    latest = recent[-1][1] if recent else None
    change = recent[-1][1] - recent[0][1] if len(recent) >= 2 else None
    if args.json:
        print(
            json.dumps(
                {
                    "weight": latest,
                    "change": change,
                    "recent": [
                        {"date": day_value, "weight": weight}
                        for day_value, weight in recent
                    ],
                }
            )
        )
    else:
        _print_weight_trend(recent, change)
    return 0


def _cmd_macros(args: argparse.Namespace) -> int:
    action = getattr(args, "maction", None)
    try:
        if action in {"query", "search"}:
            database = food_database.Database.load(
                food_database.resolve_database(args.database)
            )
            query = " ".join(args.query)
            candidates = database.query(query)
            if getattr(args, "json", False):
                print(
                    json.dumps(
                        {"results": candidates},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                )
            else:
                for candidate in candidates:
                    print(f"{candidate['name']} {candidate['unit']}")
            return 0
        if action == "calculate":
            database = food_database.Database.load(
                food_database.resolve_database(args.database)
            )
            item = database.calculate(args.food, args.amount)
            if getattr(args, "json", False):
                print(
                    json.dumps(
                        item.to_dict(), ensure_ascii=False, separators=(",", ":")
                    )
                )
            else:
                print(item.to_row())
            return 0
        if action == "insert":
            item = food_database.insert(
                food_database.resolve_database(args.database), args.row
            )
            if getattr(args, "json", False):
                print(
                    json.dumps(
                        item.to_dict(), ensure_ascii=False, separators=(",", ":")
                    )
                )
            else:
                print(item.to_row())
            return 0

        den = resolve_den(args.den)
        target = _target(args)
        day, current = application.read_day(den, target)
        if action == "add":
            day, _revision = application.add_food(den, target, args.row, current)
        elif action == "rm":
            day, _revision = application.remove_food(den, target, args.index, current)
    except (
        OSError,
        ValueError,
        LookupError,
        IndexError,
        application.RevisionConflict,
    ) as exc:
        print(f"macros: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json", False):
        print(json.dumps(day.macros.to_dict()))
    else:
        macros = day.macros
        print(
            f"protein: {macros.protein}  carbs: {macros.carbs}  "
            f"fat: {macros.fat}  calories: {macros.calories}"
        )
    return 0


def _print_notes(notes: list[Note]) -> None:
    if not notes:
        print("(no notes)")
        return
    for note in notes:
        print(f"{note.index}. {note.heading}")
        if note.body:
            print(note.body)


def _cmd_note(args: argparse.Namespace) -> int:
    den = resolve_den(args.den)
    target = _target(args)
    day, current = application.read_day(den, target)
    try:
        if args.naction == "add":
            day, _revision = application.add_note(
                den, target, args.body, args.title, current
            )
        elif args.naction == "edit":
            if args.index < 1 or args.index > len(day.notes):
                raise IndexError(f"note {args.index} not found")
            heading = args.heading or day.notes[args.index - 1].heading
            day, _revision = application.edit_structured_note(
                den, target, args.index, heading, args.body, current
            )
        elif args.naction == "rm":
            day, _revision = application.remove_note(den, target, args.index, current)
    except (IndexError, ValueError, LookupError, application.RevisionConflict) as exc:
        print(f"note: {exc}", file=sys.stderr)
        return 1
    notes = day.notes
    if args.json:
        print(json.dumps([note.to_dict() for note in notes], ensure_ascii=False))
    else:
        _print_notes(notes)
    return 0


def _cmd_upcoming(args: argparse.Namespace) -> int:
    items = application.list_upcoming(resolve_den(args.den), _target(args))
    if args.json:
        print(json.dumps([item.to_dict() for item in items], ensure_ascii=False))
    elif not items:
        print("(no upcoming tasks)")
    else:
        for item in items:
            print(f"{item.date}  {item.index}. [ ] {item.text}")
    return 0


def _add_task_parser(sub: argparse._SubParsersAction) -> None:
    task = sub.add_parser("task", help="add/complete/remove dated Today tasks")
    actions = task.add_subparsers(dest="action", required=True)
    add = actions.add_parser("add", help="add a task to the selected date")
    add.add_argument("text", help="the task text")
    add.add_argument("--json", action="store_true")
    add.set_defaults(func=_cmd_task)
    done = actions.add_parser("done", help="toggle a task checkbox by index")
    done.add_argument("index", type=int)
    done.add_argument("--json", action="store_true")
    done.set_defaults(func=_cmd_task)
    remove = actions.add_parser("rm", help="remove a task by index")
    remove.add_argument("index", type=int)
    remove.add_argument("--json", action="store_true")
    remove.set_defaults(func=_cmd_task)


def _add_habit_parser(sub: argparse._SubParsersAction) -> None:
    habit = sub.add_parser("habit", help="toggle/list habits")
    actions = habit.add_subparsers(dest="haction", required=True)
    toggle = actions.add_parser("toggle", help="toggle a habit by name")
    toggle.add_argument("name")
    toggle.add_argument("--json", action="store_true")
    toggle.set_defaults(func=_cmd_habit)
    listing = actions.add_parser("list", help="list habits")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=_cmd_habit)


def _add_weight_parser(sub: argparse._SubParsersAction) -> None:
    weight = sub.add_parser("weight", help="log or show weight")
    weight.add_argument("value", nargs="?")
    weight.add_argument("--days", type=int, default=7)
    weight.add_argument("--json", action="store_true")
    weight.set_defaults(func=_cmd_weight)


def _add_macros_parser(sub: argparse._SubParsersAction) -> None:
    macros = sub.add_parser(
        "macros", help="manage day totals or query the food database"
    )
    macros.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    macros.set_defaults(func=_cmd_macros)
    actions = macros.add_subparsers(dest="maction")
    add = actions.add_parser("add", help="append a what,protein,carbs,fat day row")
    add.add_argument("row")
    add.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    add.set_defaults(func=_cmd_macros)
    remove = actions.add_parser("rm", help="remove a valid day food row by index")
    remove.add_argument("index", type=int)
    remove.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    remove.set_defaults(func=_cmd_macros)

    query = actions.add_parser(
        "query", aliases=["search"], help="fuzzy-query the macros.nvim food database"
    )
    query.add_argument("query", nargs="+")
    query.add_argument("--database")
    query.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    query.set_defaults(func=_cmd_macros)
    calculate = actions.add_parser(
        "calculate", help="scale one database food to a quantity"
    )
    calculate.add_argument("--food", required=True)
    calculate.add_argument("--amount", required=True, type=float)
    calculate.add_argument("--database")
    calculate.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS
    )
    calculate.set_defaults(func=_cmd_macros)
    insert = actions.add_parser(
        "insert", help="atomically insert a row into the food database"
    )
    insert.add_argument("row")
    insert.add_argument("--database")
    insert.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    insert.set_defaults(func=_cmd_macros)


def _add_note_parser(sub: argparse._SubParsersAction) -> None:
    note = sub.add_parser("note", help="add/list/edit/remove structured notes")
    actions = note.add_subparsers(dest="naction", required=True)
    add = actions.add_parser("add", help="append a structured note")
    add.add_argument("body")
    add.add_argument("--title")
    add.add_argument("--json", action="store_true")
    add.set_defaults(func=_cmd_note)
    listing = actions.add_parser("list", help="list structured notes")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=_cmd_note)
    change = actions.add_parser("edit", help="replace a note heading and body")
    change.add_argument("index", type=int)
    change.add_argument("body")
    change.add_argument("--heading")
    change.add_argument("--json", action="store_true")
    change.set_defaults(func=_cmd_note)
    remove = actions.add_parser("rm", help="remove a structured note")
    remove.add_argument("index", type=int)
    remove.add_argument("--json", action="store_true")
    remove.set_defaults(func=_cmd_note)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="today",
        description="Open and update the-den journal. Subcommands are non-interactive.",
    )
    parser.add_argument("--version", action="version", version=f"today {__version__}")
    parser.add_argument(
        "--den", help="den directory (default: $DEN_PATH or ~/personal/the-den)"
    )
    dates = parser.add_mutually_exclusive_group()
    dates.add_argument("--date", help="target date as YYYY-MM-DD")
    dates.add_argument("-N", "--offset", type=int, help="days from today")
    parser.add_argument("--no-edit", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    path = sub.add_parser("path", help="print the selected entry path")
    path.set_defaults(func=_cmd_path)
    create = sub.add_parser("create", help="create the selected entry")
    create.set_defaults(func=_cmd_create)
    show = sub.add_parser("show", help="read the selected day")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=_cmd_show)
    _add_task_parser(sub)
    _add_habit_parser(sub)
    _add_weight_parser(sub)
    _add_macros_parser(sub)
    _add_note_parser(sub)
    upcoming = sub.add_parser("upcoming", help="list incomplete future tasks")
    upcoming.add_argument("--json", action="store_true")
    upcoming.set_defaults(func=_cmd_upcoming)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.cmd is None:
            return _cmd_edit(args)
        return int(args.func(args))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
