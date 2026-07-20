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

from today.model import parse_day

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


def _cmd_planned(args: argparse.Namespace) -> int:
    print(f"`today {args._cmd}` {_PLANNED}", file=sys.stderr)
    return 2


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

    # Mutation surface (scaffolded; the parity port is tracked in tasks/).
    for name, help_ in [
        ("task", "add/complete/remove tasks (today or --tomorrow)"),
        ("habit", "toggle/list habits"),
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
