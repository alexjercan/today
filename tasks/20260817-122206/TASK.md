# Build writable dashboardd Today widgets

- STATUS: CLOSED
- PRIORITY: 100
- TAGS: dashboardd, widget, nix, python, frontend

## Goal

Turn Today into a writable external dashboardd package for a dedicated mobile-friendly Today dashboard. Today remains the only parser and writer for the-den Markdown. No widget source is added to dashboardd.

The first release contains dedicated Tasks, Habits, Macros, Weight, and Upcoming variants. Every primary daily action must work from normal dashboard mode. Focus adds space, history, destructive actions, and dated planning.

## Platform dependencies

- Frontend SDK: released `@dashboardd/widget-sdk@0.1.0` tarball.
- Packer and discovery: dashboardd commits through `e68a4ac` provide `dashboardd-widget`, `DASHBOARDD_WIDGET_PATH`, and composable Nix widget roots.
- Push the dashboardd platform commits before locking Today's dashboardd flake input. Pin the exact dashboardd commit. A later dashboardd tag can replace the commit pin without changing the package contract.
- Until the commit is remote, local checks use `--override-input dashboardd path:../dashboardd`.

## Widget package

Widget ID: `today`.

| Variant | Size | Focus | Normal purpose |
| --- | --- | --- | --- |
| `tasks` | 3x3 | yes | All of today's tasks, direct toggles, and task entry |
| `habits` | 3x2 | no | All habits as directly writable checkboxes |
| `macros` | 3x1 | yes | Macro totals and compact food entry |
| `weight` | 1x1 | yes | Current weight or direct missing-weight entry |
| `upcoming` | 3x2 | yes | Next five incomplete dated tasks and dated task entry |

All variants show enough date context to make the target day clear. Important content uses dashboardd's normal typography floor. Lists scroll instead of truncating data silently.

## Tasks variant

Normal mode:

- Show every Today task in a scrollable checkbox list.
- Toggle a task immediately from its checkbox.
- Include a compact add-task field.
- Show pending state while a command is in flight.
- Refresh from the backend result. Do not use permanent optimistic state.

Focus mode:

- Use the larger surface for the full list and larger controls.
- Add, toggle, and remove tasks.
- Require confirmation before removal.
- Keep indexed operations revision-guarded so another widget process cannot make an index target the wrong task.

## Habits variant

- Size 3x2 with no required Focus workflow.
- Show every habit as a checkbox, not only a completion count.
- Toggle directly in normal mode.
- Scroll when the configured habit list does not fit.
- Preserve the existing emoji-insensitive and case-insensitive habit matching rules through the shared application API.

## Macros variant

Normal mode:

- Show protein, carbs, fat, and calories.
- Include a compact `what, protein, carbs, fat` food-entry workflow.
- Validate finite numeric values before sending and again in Python before writing.

Focus mode:

- Keep the aggregate visible.
- Show every valid food row with its per-food macro values.
- Add food rows.
- Remove an incorrect row with confirmation.

Extend the Today model to retain valid food rows while calculating the existing aggregate. Preserve the existing `today show --json` contract unless a separate explicit CLI change is approved. The widget application payload can expose food rows without adding them to `Day.to_dict()`.

## Weight variant

Normal 1x1 mode:

- If weight is not logged, show the input directly.
- If weight is logged, show the value prominently.
- Tapping the value enters edit mode.
- Submit with Enter or a compact confirmation control.

Focus mode:

- Show the input and current value.
- Show recent weight history and net change.
- Reuse the existing weight grammar and normalization. Never write a value that the parser cannot read.

## Dated task model

New scheduled tasks are written directly into the target date's daily file under its `Today` list. Do not write new `Tomorrow` sections.

Example:

```text
Daily/2026-08-20-Thursday.md

Today
- [ ] Prepare dashboardd release
```

Behavior:

- Creating a scheduled task ensures the target date's entry exists.
- When the target date arrives, the task naturally appears in the Tasks variant.
- Remove Tomorrow carry-forward. No task is copied between files.
- Keep historical Tomorrow sections parseable as existing journal data, but stop writing and carrying them.
- Remove `--tomorrow` from new task add/remove CLI behavior. This is a documented breaking change.
- Add global `--date YYYY-MM-DD`, mutually exclusive with `-N/--offset`.
- The date selector applies consistently to path, create, show, task, habit, weight, macros, and note commands.
- Add `today upcoming [--json]` for incomplete tasks in future daily files.

Examples:

```bash
today --date 2026-08-20 task add "Prepare dashboardd release"
today --date 2026-08-20 task done 1
today --date 2026-08-20 task rm 1
today upcoming --json
```

## Upcoming variant

Normal mode:

- Scan future `Daily/*.md` entries.
- Exclude today and past dates.
- Flatten incomplete tasks and sort by date, then file order.
- Show the next five tasks with an explicit date on every row.
- Allow direct checkbox toggles against the future file.
- Include a compact date plus task entry.

Focus mode:

- Show a month calendar beginning on the current month.
- Disable dates before today.
- Mark dates containing tasks and show incomplete counts.
- Allow month navigation.
- Selecting a date shows all tasks in that date's Today list.
- Add, toggle, and remove tasks for the selected date.
- Creating a task for a missing date creates the daily entry first.
- Calendar navigation is frontend-local. File creation and mutation remain Python responsibilities.

Future file discovery is unbounded by an arbitrary horizon. Only existing future daily files are parsed. A selected blank date has no file until the first explicit add.

## Shared application layer

Add `today/application.py` and move reusable behavior out of `today.cli`.

Public responsibilities:

- Resolve the den path.
- Resolve ISO dates and offsets.
- Map a date to the weekday-suffixed daily filename.
- Ensure a day exists with race-safe creation.
- Read and summarize a day.
- List future dated tasks.
- Read weight history.
- Add, toggle, and remove dated tasks.
- Toggle habits.
- Add and remove food rows.
- Set weight.
- Verify revisions before indexed mutations.

The CLI and dashboard backend must call this application layer. They must not duplicate Markdown parsing or transforms.

## Race-safe creation and writes

Several variants can start separate backend processes at once.

- Build new entries from the den template.
- Create with exclusive filesystem semantics.
- If another process wins creation, read its completed file.
- Do not carry Tomorrow items into the new entry.
- Mutations remain parse -> transform -> atomic write.
- Preserve fsync behavior.
- A backend write refreshes its own state immediately.
- Other variant processes observe the atomic replacement through polling.

Today's entry is ensured when a backend initializes and on day rollover. Future entries are created only after an explicit dated add.

## Model changes

Add a retained food-row model containing index, name, protein, carbs, and fat. Parse only rows accepted by the existing finite-number rules. Aggregate calculations use the retained valid rows.

Add an edit operation that removes a food row by its displayed valid-row index without disturbing headers, invalid hand-edited rows, prose, line endings, or unrelated sections.

Keep legacy Tomorrow parsing for existing files. New application and CLI writes target dated Today lists.

## Backend

Add:

```text
today/dashboard_backend.py
today-dashboardd-widget
```

Use Python standard-library JSON Lines over stdin/stdout.

Lifecycle:

1. Emit `ready` for widget ID `today`.
2. Validate `initialize`, instance ID, widget ID, variant ID, and options.
3. Ensure today's entry and publish state.
4. Respond to `ping` with the same `pong` nonce.
5. Validate widget commands and command IDs.
6. Poll at a bounded one-second interval for atomic file changes and day rollover.
7. Publish only when state changes.
8. Exit zero on `shutdown`.

Stdout contains protocol messages only. Diagnostics use stderr. Flush every message.

Each placed variant has a separate backend process. All processes read and write the same files through the application layer.

## Backend state payload

The payload is private widget state, not user-visible JSON.

```json
{
  "schema_version": 1,
  "today": {
    "date": "2026-08-17",
    "revision": "inode:mtime:size",
    "tasks": [{"index": 1, "text": "Go to gym", "done": false}],
    "habits": [{"name": "Gym", "done": false}],
    "foods": [
      {
        "index": 1,
        "name": "eggs",
        "protein": 12,
        "carbs": 1,
        "fat": 10
      }
    ],
    "macros": {"protein": 12, "carbs": 1, "fat": 10, "calories": 142},
    "weight": 72.5
  },
  "upcoming": {
    "next": [
      {
        "date": "2026-08-20",
        "revision": "inode:mtime:size",
        "index": 1,
        "text": "Prepare dashboardd release",
        "done": false
      }
    ],
    "dates": [
      {
        "date": "2026-08-20",
        "revision": "inode:mtime:size",
        "tasks": [
          {"index": 1, "text": "Prepare dashboardd release", "done": false}
        ]
      }
    ]
  },
  "weight_history": [{"date": "2026-08-17", "value": 72.5}],
  "command_result": null
}
```

ISO dates are protocol values. Weekday filename suffixes remain an application detail.

A revision identifies the file state used to produce indexed values. Use stable file metadata that changes across atomic replacement. A command targeting an indexed item includes the target date and displayed revision. On conflict, publish the latest state with a failed command result instead of mutating.

## Backend commands

Every command contains a non-empty `command_id`, action, data object, and relevant revision/date.

Supported actions:

- `task.add`
- `task.toggle`
- `task.remove`
- `habit.toggle`
- `food.add`
- `food.remove`
- `weight.set`
- `upcoming.add`
- `upcoming.toggle`
- `upcoming.remove`
- `refresh`

The backend validates all fields and values. It reports pending state in the frontend, then publishes a success, conflict, or failure through `command_result`. Protocol framing errors also use structured backend `error` messages where applicable.

## Frontend

Add a private npm package under `widget/frontend`.

Use only:

- Released `@dashboardd/widget-sdk@0.1.0` tarball.
- TypeScript as a build-only dependency.

Use type-only SDK imports so `tsc` emits one self-contained ES module per variant without webpack or esbuild. Keep component styles inside each module or a shared TypeScript style string. Emit:

```text
widget/frontend/dist/tasks.js
widget/frontend/dist/habits.js
widget/frontend/dist/macros.js
widget/frontend/dist/weight.js
widget/frontend/dist/upcoming.js
```

Frontends validate backend payloads at runtime. Every mount releases listeners and pending state in `destroy()`. Focus-capable variants update without remounting through `setPresentation()`.

Use command IDs and visible pending/error state. Disable duplicate submissions while a command is pending. Confirm destructive removals. Checkboxes and form submission are explicit writes and are allowed in normal mode.

## Source manifest

Add `widget/widget.toml` with source schema version 2 and the five variants. It references the built Python launcher and emitted frontend modules only. No build commands belong in the manifest.

## Nix packaging

Add a dashboardd flake input and keep it pinned. Extend outputs with:

- Existing `packages.today` and default package.
- New `packages.dashboardd-widget`.

Build flow:

1. Build the existing Today Python application and backend entry point.
2. Build frontend modules from the locked npm dependencies and released SDK artifact.
3. Stage the Python launcher and frontend files.
4. Run dashboardd's `dashboardd-widget pack`.
5. Run static `dashboardd-widget check`.
6. Install under `$out/share/dashboardd/widgets/today/`.

The packaged backend launcher must retain the Today Python runtime closure. The widget package must not copy dashboardd source or depend on dashboardd workspace membership.

## Tests

Application and domain:

- Existing CLI and golden parser tests remain green except intentional Tomorrow behavior replacements.
- Race-safe creation with two contenders.
- Date and offset mutual exclusion.
- Direct future-file scheduling.
- No Tomorrow carry-forward.
- Upcoming ordering across multiple future dates.
- Date rollover moves a stored future task into today's normal read naturally.
- Revision conflicts refuse indexed writes.
- Food row retention, aggregation, addition, and precise removal.
- Weight history and writes.

Backend subprocess:

- Ready, initialize, initial update, ping/pong, refresh, command success, conflict, invalid command, polling refresh, rollover, shutdown, stdout discipline, and stderr behavior.
- Use a temporary den. Never access the real den in tests.

Frontend:

- Locked external SDK installation.
- TypeScript compilation for every variant.
- Runtime payload guards.
- Command construction and pending/result handling where practical without a browser dependency.

Bundle and Nix:

- Exact standard package layout.
- Executable packaged backend.
- Static `dashboardd-widget check`.
- Run the backend from the Nix output against a fixture den.
- Compose dashboardd built-in and Today roots with `lib.makeSearchPath`.
- Start packaged dashboardd and verify the Today variants in the widget catalog.
- Run `nix flake check` from a clean tracked source.

Manual product proof:

- Compose local dashboardd and Today packages.
- Use a fixture den first, then the real den.
- Build a dedicated Today dashboard.
- Verify normal-mode writes for tasks, habits, macros, weight, and upcoming.
- Verify Tasks, Macros, Weight, and Upcoming Focus workflows.
- Verify phone-sized interaction and capture review screenshots before nix.dotfiles integration.

## Documentation and release

- Add a short Unreleased changelog line for the writable dashboard widget and dated-task CLI change.
- Document `--date`, removal of new Tomorrow writes/carry-forward, and `upcoming` in README.
- Document `DEN_PATH`, widget package output, dashboardd composition, and normal/Focus writes.
- Keep `pyproject.toml` and `today.__version__` unchanged until an explicit release task.
- Record implementation decisions, evidence, tradeoffs, and retrospective in this task folder.

## Delivery order

1. Push dashboardd commits through `e68a4ac`.
2. Pin the dashboardd commit in Today.
3. Add the shared application layer and replace CLI-local path/date/create behavior.
4. Implement race-safe no-carry entry creation and dated CLI task behavior.
5. Retain food rows and add precise food removal.
6. Implement and test the Python backend and write commands.
7. Implement Tasks, Habits, Macros, Weight, and Upcoming frontends.
8. Add manifest and Nix package.
9. Pass focused tests and `nix flake check`.
10. Compose with dashboardd and a fixture den.
11. Stop for visual and mobile interaction review.
12. Integrate through nix.dotfiles after approval.

## Definition of Done

- Today remains the only Markdown parser and writer.
- No Today widget source or generated bundle exists in dashboardd.
- All five variants are installed from `packages.dashboardd-widget` through the standard widget search path.
- Tasks and habits are complete writable checkbox lists in normal mode.
- Macros accepts food in normal mode and shows/removes foods in Focus.
- Missing weight is writable directly in 1x1 normal mode; Focus shows history.
- Upcoming shows the next five dated tasks and Focus provides a writable month calendar.
- Scheduled tasks live directly in target-date Today lists and appear in Tasks on that date.
- New Tomorrow writes and carry-forward are removed and documented as breaking.
- Every indexed write is revision-guarded and every destructive write is confirmed in the frontend.
- Backend polling synchronizes separate variant processes and handles day rollover.
- The frontend installs the released SDK artifact rather than a dashboardd source path.
- The Nix package retains the Python runtime closure and passes static pack/check validation.
- Dashboardd discovers built-in and Today roots together without source copying.
- All Today checks, dashboardd composition checks, and manual mobile review pass.

## Out of scope

- Google Calendar integration.
- Arbitrary event scheduling.
- Rewriting Today in Rust.
- Duplicating the-den parsing in dashboardd or frontend code.
- Non-Nix binary distribution beyond the existing source-build workflow.
- nix.dotfiles installation before product review.

## Implementation notes

Implemented on `master` in four initial slices:

- `9c93498` adds the dated application API, race-safe entry creation, direct
  future-file scheduling, food retention/removal, CLI changes, and tests.
- `ebf90d7` adds the Python dashboardd backend and lifecycle tests.
- `2877e90` adds the TypeScript frontends and source manifest.
- `5a914ed` pins dashboardd and adds the reproducible Nix widget package and
  composition checks.

The dashboardd dependency was already available at remote commit `e68a4ac`, so
Today pins that exact revision. The frontend lock uses the released SDK v0.1.0
tarball. Nix uses `importNpmLock.buildNodeModules`, which avoids a manually
maintained aggregate npm dependency hash.

The source frontend is one self-contained variant dispatcher. The initial
multi-file TypeScript output imported `shared.js`, but the public packer copies
only each declared variant entry artifact. Browser testing caught the missing
runtime module. Consolidating the implementation keeps every packed variant
self-contained without adding a bundler. Each manifest variant references the
same built module; the packer installs independent stable variant filenames.

A frontend mount sends an explicit `refresh` command. The first browser test
showed that an update emitted before a browser event stream connects is not
replayed by dashboardd. Explicit refresh makes direct dashboard and Focus URLs
load current state immediately. Polling still synchronizes file changes among
separate variant backend processes.

The weight history uses the CLI's established seven-day default. The Upcoming
calendar uses ISO Monday-first weeks. Visual testing compressed the 3x1 Macros
header and controls and prevented 1x1 Weight values from wrapping on a
three-column phone dashboard.

## Evidence

`nix flake check -L` passes all 12 checks on x86_64-linux:

- Ruff.
- Mypy across 12 Python source files.
- 102 pytest tests.
- TypeScript frontend build.
- Static bundle pack/check.
- Packaged dashboardd catalog composition with all five variants.

A packaged dashboardd instance was composed from its built-in widget root and
Today's independent Nix widget root against a temporary den. Browser automation
proved normal-mode writes for task and habit toggles, food addition, weight
replacement, and dated task creation. It also opened Tasks, Macros, Upcoming,
and Weight Focus directly, rejected horizontal phone overflow, and reported no
page errors.

Review artifacts:

- `artifacts/today-dashboard-desktop.png`
- `artifacts/today-dashboard-phone.png`
- `artifacts/today-tasks-focus.png`
- `artifacts/today-macros-focus.png`
- `artifacts/today-upcoming-focus.png`
- `artifacts/today-weight-focus.png`

## Approval and integration

User approved the desktop and phone visuals and interactions. nix.dotfiles
commit `398642f` now installs dashboardd and Today's independent widget package,
composes both widget roots, and runs dashboardd as an enabled Home Manager user
service on `127.0.0.1:7331`. Runtime verification discovered Today and all five
variants from the packaged catalog.
