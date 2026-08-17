from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tasks/20260817-150307/migrate_daily.py"
spec = importlib.util.spec_from_file_location("migrate_daily", SCRIPT)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_preserves_legacy_domains_and_note_content() -> None:
    source = (
        "# Day\n\n### 🌱 Habits\n\n- [x] Read\n\n"
        "### 🍽️ Macros\n\nwhat,protein,carbs,fat\negg,6,0,5\n\n"
        "### 📝 Notes\n\nToday\n- [ ] task\n\n"
        "note :: project\n\nA long\nnote body.\n\n"
        "loose text\n\nweight :: 71.4 Kg\n\nTomorrow\n- later\n"
    )
    result = migration.migrate(source)
    assert "### Tasks\n\n- [ ] task" in result
    assert "### Habits\n\n- [x] Read" in result
    assert "### Weight\n\n71.4 kg" in result
    assert "#### project" in result
    assert "A long\nnote body." in result
    assert "loose text" in result
    assert "#### Historical Tomorrow\n\n- later" in result
    assert "note ::" not in result
    assert "weight ::" not in result


def test_migration_is_idempotent() -> None:
    canonical = (
        "# Day\n\n### Tasks\n\n- [ ] task\n\n### Habits\n\n"
        "### Macros\n\nwhat,protein,carbs,fat\n\n### Weight\n\n"
        "### Notes\n\n#### 10:00\n\nbody\n"
    )
    assert migration.migrate(migration.migrate(canonical)) == migration.migrate(
        canonical
    )
