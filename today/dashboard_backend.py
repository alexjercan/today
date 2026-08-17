"""dashboardd JSON Lines backend for the writable Today widgets."""

from __future__ import annotations

import json
import selectors
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, TextIO

from today import application

WIDGET_ID = "today"
VARIANTS = {"tasks", "habits", "macros", "weight", "upcoming"}


class CommandError(ValueError):
    pass


class Backend:
    def __init__(
        self,
        stdin: TextIO = sys.stdin,
        stdout: TextIO = sys.stdout,
        stderr: TextIO = sys.stderr,
        *,
        den: Path | None = None,
        today_fn: Callable[[], date] = date.today,
        poll_seconds: float = 1.0,
    ) -> None:
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.den = den if den is not None else application.resolve_den(None)
        self.today_fn = today_fn
        self.poll_seconds = poll_seconds
        self.instance_id: str | None = None
        self.variant_id: str | None = None
        self.last_state: str | None = None

    def send(self, kind: str, data: dict[str, object]) -> None:
        print(
            json.dumps(
                {"version": 1, "kind": kind, "data": data},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            file=self.stdout,
            flush=True,
        )

    def error(self, code: str, message: str) -> None:
        self.send(
            "error",
            {
                "instance_id": self.instance_id,
                "error": {"code": code, "message": message},
            },
        )

    def state(
        self, command_result: dict[str, object] | None = None
    ) -> dict[str, object]:
        target = self.today_fn()
        day, current = application.read_day(self.den, target)
        upcoming_dates = application.upcoming_dates(self.den, target)
        next_tasks: list[dict[str, object]] = []
        dates: list[dict[str, object]] = []
        for scheduled_date, scheduled_day, scheduled_revision in upcoming_dates:
            tasks = [task.to_dict() for task in scheduled_day.tasks]
            dates.append(
                {
                    "date": scheduled_date.isoformat(),
                    "revision": scheduled_revision,
                    "tasks": tasks,
                }
            )
            for task in scheduled_day.tasks:
                if task.done:
                    continue
                next_tasks.append(
                    {
                        "date": scheduled_date.isoformat(),
                        "revision": scheduled_revision,
                        **task.to_dict(),
                    }
                )
        history = application.weight_history(self.den, target, 7)
        return {
            "schema_version": 1,
            "today": {
                "date": target.isoformat(),
                "title": day.title,
                "revision": current,
                "tasks": [task.to_dict() for task in day.tasks],
                "habits": [habit.to_dict() for habit in day.habits],
                "foods": [food.to_dict() for food in day.foods],
                "macros": day.macros.to_dict(),
                "weight": day.weight,
            },
            "upcoming": {"next": next_tasks[:5], "dates": dates},
            "weight_history": [
                {"date": day_value, "value": weight} for day_value, weight in history
            ],
            "command_result": command_result,
        }

    def publish(
        self,
        command_result: dict[str, object] | None = None,
        *,
        force: bool = False,
    ) -> None:
        if self.instance_id is None:
            return
        payload = self.state(command_result)
        stable_payload = dict(payload)
        stable_payload["command_result"] = None
        fingerprint = json.dumps(stable_payload, sort_keys=True, separators=(",", ":"))
        if not force and command_result is None and fingerprint == self.last_state:
            return
        self.last_state = fingerprint
        self.send(
            "update",
            {"instance_id": self.instance_id, "payload": payload},
        )

    def initialize(self, data: dict[str, object]) -> None:
        if self.instance_id is not None:
            raise CommandError("Backend is already initialized")
        instance_id = data.get("instance_id")
        widget_id = data.get("widget_id")
        variant_id = data.get("variant_id")
        options = data.get("options")
        if not isinstance(instance_id, str) or not instance_id:
            raise CommandError("Instance ID is required")
        if widget_id != WIDGET_ID:
            raise CommandError("Widget ID does not match")
        if not isinstance(variant_id, str) or variant_id not in VARIANTS:
            raise CommandError("Variant ID is not supported")
        if not isinstance(options, dict) or options:
            raise CommandError("Today variants do not accept options")
        self.instance_id = instance_id
        self.variant_id = variant_id
        self.publish(force=True)

    def process_command(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise CommandError("Command payload must be an object")
        command_id = payload.get("command_id")
        action = payload.get("action")
        data = payload.get("data")
        if not isinstance(command_id, str) or not command_id:
            raise CommandError("Command ID is required")
        if not isinstance(action, str) or not action:
            self.publish(
                self.failed(command_id, "invalid_command", "Action is required"),
                force=True,
            )
            return
        if not isinstance(data, dict):
            self.publish(
                self.failed(
                    command_id, "invalid_command", "Command data must be an object"
                ),
                force=True,
            )
            return
        try:
            self.execute(action, data)
        except application.RevisionConflict as exc:
            result = self.failed(command_id, "conflict", str(exc))
        except (CommandError, IndexError, KeyError, LookupError, ValueError) as exc:
            result = self.failed(command_id, "invalid_command", str(exc))
        except OSError as exc:
            print(str(exc), file=self.stderr, flush=True)
            result = self.failed(command_id, "write_failed", str(exc))
        else:
            result = {"command_id": command_id, "status": "succeeded"}
        self.publish(result, force=True)

    @staticmethod
    def failed(command_id: str, code: str, message: str) -> dict[str, object]:
        return {
            "command_id": command_id,
            "status": "failed",
            "error": {"code": code, "message": message},
        }

    def execute(self, action: str, data: dict[str, object]) -> None:
        if action == "refresh":
            return
        target = self.command_date(data)
        today = self.today_fn()
        if action.startswith("upcoming."):
            if target <= today:
                raise CommandError("Upcoming commands require a future date")
            task_action = action.removeprefix("upcoming.")
            self.execute_task(task_action, target, data, allow_missing=True)
            return
        if action.startswith("task."):
            if target != today:
                raise CommandError("Task commands require today's date")
            self.execute_task(action.removeprefix("task."), target, data)
            return
        if target != today:
            raise CommandError("This command requires today's date")
        revision = self.required_revision(data)
        if action == "habit.toggle":
            application.toggle_habit(
                self.den, target, self.required_string(data, "name"), revision
            )
        elif action == "food.add":
            application.add_food(
                self.den, target, self.required_string(data, "row"), revision
            )
        elif action == "food.remove":
            application.remove_food(
                self.den, target, self.required_index(data), revision
            )
        elif action == "weight.set":
            application.set_weight(
                self.den, target, self.required_string(data, "value"), revision
            )
        else:
            raise CommandError(f"Unsupported action: {action}")

    def execute_task(
        self,
        action: str,
        target: date,
        data: dict[str, object],
        *,
        allow_missing: bool = False,
    ) -> None:
        if action == "add":
            expected = data.get("revision")
            if expected is not None and not isinstance(expected, str):
                raise CommandError("Revision must be a string or null")
            if expected is None and not allow_missing:
                raise CommandError("Revision is required")
            application.add_task(
                self.den,
                target,
                self.required_string(data, "text"),
                expected,
            )
            return
        revision = self.required_revision(data)
        index = self.required_index(data)
        if action == "toggle":
            application.toggle_task(self.den, target, index, revision)
        elif action == "remove":
            application.remove_task(self.den, target, index, revision)
        else:
            raise CommandError(f"Unsupported task action: {action}")

    @staticmethod
    def command_date(data: dict[str, object]) -> date:
        value = data.get("date")
        if not isinstance(value, str):
            raise CommandError("Date is required")
        try:
            return application.resolve_date(value)
        except ValueError as exc:
            raise CommandError(str(exc)) from None

    @staticmethod
    def required_revision(data: dict[str, object]) -> str:
        value = data.get("revision")
        if not isinstance(value, str) or not value:
            raise CommandError("Revision is required")
        return value

    @staticmethod
    def required_string(data: dict[str, object], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CommandError(f"{key.capitalize()} is required")
        return value

    @staticmethod
    def required_index(data: dict[str, object]) -> int:
        value = data.get("index")
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise CommandError("Index must be a positive integer")
        return value

    def handle(self, envelope: object) -> bool:
        if not isinstance(envelope, dict):
            self.error("invalid_message", "Message must be an object")
            return True
        if envelope.get("version") != 1:
            self.error("unsupported_version", "Backend protocol version must be 1")
            return True
        kind = envelope.get("kind")
        data = envelope.get("data")
        if not isinstance(data, dict):
            self.error("invalid_message", "Message data must be an object")
            return True
        try:
            if kind == "initialize":
                self.initialize(data)
            elif kind == "message":
                if self.instance_id is None:
                    raise CommandError("Backend is not initialized")
                if data.get("instance_id") != self.instance_id:
                    raise CommandError("Instance ID does not match")
                self.process_command(data.get("payload"))
            elif kind == "ping":
                nonce = data.get("nonce")
                if not isinstance(nonce, int) or isinstance(nonce, bool) or nonce < 0:
                    raise CommandError("Ping nonce must be a non-negative integer")
                self.send("pong", {"nonce": nonce})
            elif kind == "error":
                pass
            elif kind == "shutdown":
                return False
            else:
                raise CommandError("Unsupported message kind")
        except CommandError as exc:
            self.error("invalid_message", str(exc))
        except OSError as exc:
            print(str(exc), file=self.stderr, flush=True)
            self.error("backend_failed", str(exc))
        return True

    def run(self) -> int:
        self.send("ready", {"widget_id": WIDGET_ID})
        selector = selectors.DefaultSelector()
        selector.register(self.stdin, selectors.EVENT_READ)
        running = True
        while running:
            events = selector.select(self.poll_seconds)
            if not events:
                if self.instance_id is not None:
                    try:
                        self.publish()
                    except OSError as exc:
                        print(str(exc), file=self.stderr, flush=True)
                        self.error("read_failed", str(exc))
                continue
            line = self.stdin.readline()
            if line == "":
                break
            try:
                envelope: Any = json.loads(line)
            except json.JSONDecodeError as exc:
                print(str(exc), file=self.stderr, flush=True)
                self.error("invalid_json", "Message is not valid JSON")
                continue
            running = self.handle(envelope)
        selector.close()
        return 0


def main() -> int:
    return Backend().run()


if __name__ == "__main__":
    raise SystemExit(main())
