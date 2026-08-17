"""Subprocess contract tests for the dashboardd backend."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def _den(tmp_path: Path) -> Path:
    den = tmp_path / "den"
    (den / "Templates").mkdir(parents=True)
    (den / "Templates" / "daily.md").write_text(
        "# {{title}}\n\n### 🌱 Habits\n\n- [ ] 💪 Gym\n\n"
        "### 🍽️ Macros\n\nwhat,protein,carbs,fat\n\n### 📝 Notes\n\n",
        encoding="utf-8",
    )
    return den


def _macros(tmp_path: Path) -> Path:
    executable = tmp_path / "macros-fixture"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "args = sys.argv[1:]\n"
        "if args[:1] == ['search']:\n"
        "    print(json.dumps({'results': ["
        "{'id': 'egg:pc', 'name': 'egg', 'unit': 'pc'}, "
        "{'id': 'egg whites:g', 'name': 'egg whites', 'unit': 'g'}]}))\n"
        "elif args[:1] == ['calculate'] and args[args.index('--food') + 1] == 'egg:pc':\n"
        "    amount = float(args[args.index('--amount') + 1])\n"
        "    print(json.dumps({'food': 'egg', 'amount': amount, 'unit': 'pc', "
        "'protein': 6 * amount, 'carbs': 0, 'fat': 5 * amount}))\n"
        "else:\n"
        "    print('Error: Unknown food ID', file=sys.stderr)\n"
        "    raise SystemExit(1)\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def _start(tmp_path: Path) -> subprocess.Popen[str]:
    env = dict(os.environ)
    env["DEN_PATH"] = str(_den(tmp_path))
    env["MACROS_EXECUTABLE"] = str(_macros(tmp_path))
    return subprocess.Popen(
        [sys.executable, "-m", "today.dashboard_backend"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def _send(process: subprocess.Popen[str], kind: str, data: object) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps({"version": 1, "kind": kind, "data": data}) + "\n")
    process.stdin.flush()


def _read(process: subprocess.Popen[str], timeout: float = 3) -> dict[str, Any]:
    assert process.stdout is not None
    ready, _write, _errors = select.select([process.stdout], [], [], timeout)
    assert ready, "backend did not publish a message"
    line = process.stdout.readline()
    assert line
    value = json.loads(line)
    assert isinstance(value, dict)
    return value


def _initialize(process: subprocess.Popen[str]) -> dict[str, Any]:
    ready = _read(process)
    assert ready == {
        "version": 1,
        "kind": "ready",
        "data": {"widget_id": "today"},
    }
    _send(
        process,
        "initialize",
        {
            "instance_id": "today-1",
            "widget_id": "today",
            "variant_id": "tasks",
            "options": {},
        },
    )
    update = _read(process)
    assert update["kind"] == "update"
    return update["data"]["payload"]


def _shutdown(process: subprocess.Popen[str]) -> None:
    _send(process, "shutdown", {})
    assert process.wait(timeout=3) == 0
    assert process.stderr is not None
    assert process.stderr.read() == ""


def test_backend_lifecycle_ping_and_write(tmp_path: Path) -> None:
    process = _start(tmp_path)
    payload = _initialize(process)
    assert payload["schema_version"] == 1
    today = payload["today"]
    _send(process, "ping", {"nonce": 42})
    assert _read(process)["data"] == {"nonce": 42}
    _send(
        process,
        "message",
        {
            "instance_id": "today-1",
            "payload": {
                "command_id": "refresh-1",
                "action": "refresh",
                "data": {},
            },
        },
    )
    refresh = _read(process)["data"]["payload"]
    assert refresh["command_result"]["status"] == "succeeded"
    _send(
        process,
        "message",
        {
            "instance_id": "today-1",
            "payload": {
                "command_id": "add-1",
                "action": "task.add",
                "data": {
                    "date": today["date"],
                    "revision": today["revision"],
                    "text": "from dashboard",
                },
            },
        },
    )
    update = _read(process)["data"]["payload"]
    assert update["command_result"] == {
        "command_id": "add-1",
        "status": "succeeded",
    }
    assert update["today"]["tasks"][0]["text"] == "from dashboard"
    _shutdown(process)


def test_backend_searches_and_calculates_food(tmp_path: Path) -> None:
    process = _start(tmp_path)
    payload = _initialize(process)
    today = payload["today"]
    _send(
        process,
        "message",
        {
            "instance_id": "today-1",
            "payload": {
                "command_id": "search-1",
                "action": "food.search",
                "data": {"query": "eg"},
            },
        },
    )
    result = _read(process)["data"]["payload"]["command_result"]
    assert result == {
        "command_id": "search-1",
        "status": "succeeded",
        "result": {
            "kind": "food.search",
            "query": "eg",
            "candidates": [
                {"id": "egg:pc", "name": "egg", "unit": "pc"},
                {"id": "egg whites:g", "name": "egg whites", "unit": "g"},
            ],
        },
    }
    _send(
        process,
        "message",
        {
            "instance_id": "today-1",
            "payload": {
                "command_id": "food-1",
                "action": "food.add",
                "data": {
                    "date": today["date"],
                    "revision": today["revision"],
                    "food_id": "egg:pc",
                    "amount": 2,
                },
            },
        },
    )
    added = _read(process)["data"]["payload"]
    assert added["command_result"]["status"] == "succeeded"
    assert added["today"]["foods"] == [
        {"index": 1, "name": "egg 2pc", "protein": 12.0, "carbs": 0.0, "fat": 10.0}
    ]
    _shutdown(process)


def test_backend_reports_revision_conflict_in_update(tmp_path: Path) -> None:
    process = _start(tmp_path)
    payload = _initialize(process)
    today = payload["today"]
    command: dict[str, Any] = {
        "instance_id": "today-1",
        "payload": {
            "command_id": "first",
            "action": "task.add",
            "data": {
                "date": today["date"],
                "revision": today["revision"],
                "text": "first",
            },
        },
    }
    _send(process, "message", command)
    _read(process)
    command["payload"]["command_id"] = "stale"
    command["payload"]["data"]["text"] = "stale"
    _send(process, "message", command)
    result = _read(process)["data"]["payload"]["command_result"]
    assert result["status"] == "failed"
    assert result["error"]["code"] == "conflict"
    _shutdown(process)


def test_backend_adds_a_dated_upcoming_task(tmp_path: Path) -> None:
    process = _start(tmp_path)
    _initialize(process)
    future = (date.today() + timedelta(days=3)).isoformat()
    _send(
        process,
        "message",
        {
            "instance_id": "today-1",
            "payload": {
                "command_id": "future-1",
                "action": "upcoming.add",
                "data": {
                    "date": future,
                    "revision": None,
                    "text": "future task",
                },
            },
        },
    )
    payload = _read(process)["data"]["payload"]
    assert payload["command_result"]["status"] == "succeeded"
    assert payload["upcoming"]["next"][0]["date"] == future
    assert payload["upcoming"]["next"][0]["text"] == "future task"
    _shutdown(process)


def test_backend_rejects_bad_json_and_still_shuts_down(tmp_path: Path) -> None:
    process = _start(tmp_path)
    assert _read(process)["kind"] == "ready"
    assert process.stdin is not None
    process.stdin.write("not json\n")
    process.stdin.flush()
    error = _read(process)
    assert error["kind"] == "error"
    assert error["data"]["error"]["code"] == "invalid_json"
    _send(process, "shutdown", {})
    assert process.wait(timeout=3) == 0
    assert process.stderr is not None
    assert "Expecting value" in process.stderr.read()
