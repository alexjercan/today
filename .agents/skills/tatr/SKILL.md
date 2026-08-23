---
name: tatr
description: Create, list, query, and edit Today's Markdown tasks when tracked work is requested.
---

# Tatr

Tasks live at `tasks/<YYYYMMDD-HHMMSS>/TASK.md`.

```bash
tatr new "Title" -p 100 -t tag
tatr ls --sort priority
tatr ls --filter ':status eq OPEN'
tatr edit <id> --status IN_PROGRESS
```

Valid statuses are `OPEN`, `IN_PROGRESS`, and `CLOSED`. Use `-r ROOT` for
another project. Edit an existing task body directly. Keep task-specific
evidence with the task.
