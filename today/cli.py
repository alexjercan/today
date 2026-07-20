"""The `today` command: one entry point for the-den journal.

Bare `today` opens today's entry in ``$EDITOR`` (creating it from the template
first); the subcommands are non-interactive and machine-readable (``--json``), so
an agent/tool only ever calls subcommands, never the editor.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from today import edit
from today.model import Habit, Task, TomorrowTask, parse_day

DEFAULT_DEN = Path.home() / "personal" / "the-den"
DEFAULT_EDITOR = "nvim"
_PLANNED = "not implemented yet - tracked in this repo's tasks/ (parity port)."


def resolve_den(arg: str | None) -> Path:
    """Den directory: --den, then $DEN_PATH, then the default."""
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("DEN_PATH")
    return Path(env).expanduser() if env else DEFAULT_DEN


def day_for(offset: int) -> date:
    return date.today() + timedelta(days=offset)


def stem_for(offset: int) -> str:
    return day_for(offset).strftime("%Y-%m-%d-%A")


def title_for(offset: int) -> str:
    d = day_for(offset)
    # "%-d" is a non-zero-padded day of month (GNU/BSD); matches the-den's titles.
    return d.strftime("%A, %B %-d, %Y")


def entry_path(den: Path, offset: int) -> Path:
    return den / "Daily" / f"{stem_for(offset)}.md"


def _template(den: Path) -> str:
    tpl = den / "Templates" / "daily.md"
    if tpl.is_file():
        return tpl.read_text(encoding="utf-8")
    # Minimal fallback template if the den has none.
    return "# {{title}}\n\n### 🌱 Habits\n\n### 🍽️ Macros\n\nwhat,protein,carbs,fat\n\n### 📝 Notes\n\n"


def _carry_forward(den: Path, offset: int) -> list[str]:
    """Yesterday's Tomorrow list becomes today's Today list, as `- [ ]` items."""
    prev = entry_path(den, offset - 1)
    if not prev.is_file():
        return []
    day = parse_day(prev)
    return [f"- [ ] {t.text}" for t in day.tomorrow]


def ensure_entry(den: Path, offset: int) -> Path:
    """Create the entry from the template (title + carry-forward) if missing."""
    path = entry_path(den, offset)
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _template(den).replace("{{title}}", title_for(offset))
    carried = _carry_forward(den, offset)
    if carried:
        body = body.rstrip("\n") + "\n\nToday\n" + "\n".join(carried) + "\n"
    path.write_text(body, encoding="utf-8")
    return path


def _cmd_path(args: argparse.Namespace) -> int:
    den = resolve_den(args.den)
    print(entry_path(den, args.offset))
    return 0


def _cmd_create(args: argparse.Namespace) -> int:
    den = resolve_den(args.den)
    print(ensure_entry(den, args.offset))
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    den = resolve_den(args.den)
    path = ensure_entry(den, args.offset)
    day = parse_day(path)
    if args.json:
        print(json.dumps(day.to_dict(), ensure_ascii=False))
    else:
        print(day.title)
        print(
            f"habits: {len(day.habits)}  tasks: {len(day.tasks)}  "
            f"tomorrow: {len(day.tomorrow)}  weight: {day.weight}"
        )
    return 0


def _cmd_edit(args: argparse.Namespace) -> int:
    den = resolve_den(args.den)
    path = ensure_entry(den, args.offset)
    if args.no_edit:
        print(path)
        return 0
    editor = os.environ.get("EDITOR", DEFAULT_EDITOR)
    try:
        return subprocess.call([editor, str(path)])
    except OSError as exc:
        print(f"could not open {editor!r}: {exc}", file=sys.stderr)
        return 1


def _print_tasks(items: list[Task] | list[TomorrowTask]) -> None:
    """Human-readable listing of a Today/Tomorrow slice after a mutation."""
    if not items:
        print("(empty)")
        return
    for item in items:
        if isinstance(item, Task):
            box = "[x]" if item.done else "[ ]"
            print(f"{item.index}. {box} {item.text}")
        else:
            print(f"{item.index}. {item.text}")


def _cmd_task(args: argparse.Namespace) -> int:
    """add/done/rm a task in today's (or --tomorrow's) list, then report it."""
    den = resolve_den(args.den)
    path = ensure_entry(den, args.offset)
    text = path.read_text(encoding="utf-8")
    tomorrow = getattr(args, "tomorrow", False)
    marker = edit.TOMORROW if tomorrow else edit.TODAY

    try:
        if args.action == "add":
            updated = edit.add_item(text, args.text, marker)
        elif args.action == "rm":
            updated = edit.remove_item(text, args.index, marker)
        else:  # done - today-only, toggles the checkbox
            updated = edit.toggle_item(text, args.index)
    except IndexError as exc:
        print(f"today task: {exc}", file=sys.stderr)
        return 1

    if updated != text:
        edit.atomic_write(path, updated)

    day = parse_day(path)
    slice_: list[Task] | list[TomorrowTask] = day.tomorrow if tomorrow else day.tasks
    if args.json:
        print(json.dumps([t.to_dict() for t in slice_], ensure_ascii=False))
    else:
        _print_tasks(slice_)
    return 0


def _print_habits(habits: list[Habit]) -> None:
    """Human-readable listing of habits and their done state."""
    if not habits:
        print("(no habits)")
        return
    for h in habits:
        box = "[x]" if h.done else "[ ]"
        print(f"{box} {h.name}")


def _cmd_habit(args: argparse.Namespace) -> int:
    """toggle a habit's checkbox (by name) or list habits, then report them."""
    den = resolve_den(args.den)
    path = ensure_entry(den, args.offset)

    if args.haction == "toggle":
        text = path.read_text(encoding="utf-8")
        try:
            updated = edit.toggle_habit(text, args.name)
        except KeyError:
            print(f"habit: no habit matching {args.name!r}", file=sys.stderr)
            return 1
        if updated != text:
            edit.atomic_write(path, updated)

    day = parse_day(path)
    if args.json:
        print(json.dumps([h.to_dict() for h in day.habits], ensure_ascii=False))
    else:
        _print_habits(day.habits)
    return 0


def _cmd_planned(args: argparse.Namespace) -> int:
    print(f"`today {args._cmd}` {_PLANNED}", file=sys.stderr)
    return 2


def _add_task_parser(sub: argparse._SubParsersAction) -> None:
    """`today task {add,done,rm}` - mutate the Today (or --tomorrow) list."""
    task = sub.add_parser(
        "task", help="add/complete/remove tasks (today or --tomorrow)"
    )
    actions = task.add_subparsers(dest="action", required=True)

    add = actions.add_parser("add", help="add a task to Today (or --tomorrow)")
    add.add_argument("text", help="the task text")
    add.add_argument(
        "--tomorrow", action="store_true", help="add to the Tomorrow list instead"
    )
    add.add_argument(
        "--json", action="store_true", help="print the updated list as JSON"
    )
    add.set_defaults(func=_cmd_task)

    done = actions.add_parser("done", help="toggle a Today task's checkbox by index")
    done.add_argument("index", type=int, help="1-based task index (from `show --json`)")
    done.add_argument(
        "--json", action="store_true", help="print the updated list as JSON"
    )
    done.set_defaults(func=_cmd_task)

    rm = actions.add_parser("rm", help="remove a task from Today (or --tomorrow)")
    rm.add_argument("index", type=int, help="1-based task index (from `show --json`)")
    rm.add_argument(
        "--tomorrow", action="store_true", help="remove from the Tomorrow list instead"
    )
    rm.add_argument(
        "--json", action="store_true", help="print the updated list as JSON"
    )
    rm.set_defaults(func=_cmd_task)


def _add_habit_parser(sub: argparse._SubParsersAction) -> None:
    """`today habit {toggle,list}` - flip a habit's checkbox or list habits."""
    habit = sub.add_parser("habit", help="toggle/list habits")
    actions = habit.add_subparsers(dest="haction", required=True)

    toggle = actions.add_parser("toggle", help="check/uncheck a habit by name")
    toggle.add_argument("name", help="habit name (a leading emoji is optional)")
    toggle.add_argument(
        "--json", action="store_true", help="print the updated habits as JSON"
    )
    toggle.set_defaults(func=_cmd_habit)

    lst = actions.add_parser("list", help="list habits and their done state")
    lst.add_argument("--json", action="store_true", help="print habits as JSON")
    lst.set_defaults(func=_cmd_habit)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="today",
        description="Open and update the-den journal. Bare `today` opens today's "
        "entry in $EDITOR; subcommands are non-interactive.",
    )
    parser.add_argument(
        "--den", help="den directory (default: $DEN_PATH or ~/personal/the-den)"
    )
    parser.add_argument("-N", "--offset", type=int, default=0, help="days from today")
    parser.add_argument("--no-edit", action="store_true", help="do not open the editor")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("path", help="print today's entry path (do not create)")
    p.set_defaults(func=_cmd_path)

    p = sub.add_parser(
        "create", help="create the entry from the template, print its path"
    )
    p.set_defaults(func=_cmd_create)

    p = sub.add_parser(
        "show", help="read the day (habits/tasks/tomorrow/macros/weight)"
    )
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=_cmd_show)

    _add_task_parser(sub)
    _add_habit_parser(sub)

    # Mutation surface (scaffolded; the parity port is tracked in tasks/).
    for name, help_ in [
        ("weight", "log or show weight"),
        ("macros", "add a macros entry (what,protein,carbs,fat)"),
        ("note", "add/list notes (with tags)"),
    ]:
        p = sub.add_parser(name, help=help_)
        p.set_defaults(func=_cmd_planned, _cmd=name)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd is None:
        return _cmd_edit(args)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
