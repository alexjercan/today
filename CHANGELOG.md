# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Entries are short -
one line each. Breaking changes are tagged **(breaking)**.

## [Unreleased]

### Added

- Add writable dashboardd widgets for tasks, habits, macros, weight, and dated upcoming tasks.

### Changed

- **(breaking)** Replace embedded Today, Tomorrow, weight, and loose-note syntax with canonical Tasks, Weight, and `####`-delimited Notes sections.
- **(breaking)** Replace manual dashboard macro entry with fuzzy food selection and quantity calculation through the packaged `macros` CLI.
- **(breaking)** Schedule future tasks in dated daily files through `--date`; remove new Tomorrow writes and carry-forward.

## [0.2.0] - 2026-08-11

### Added

- Export the `today` agent skill as `skills.today` from the Nix flake.

## [0.1.0] - 2026-07-31

The first tagged release. Everything below shipped before the project started
tagging.

### Added

- `today` - open today's the-den entry in `$EDITOR`, creating it from the den's template first.
- `today path` - print the entry path without creating it; `today create` creates it and prints the path.
- `today show [--json]` - read the whole day: habits, tasks, tomorrow, notes, macros and weight.
- Carry-forward: a new entry starts with yesterday's Tomorrow list as its Today tasks.
- `today task add/done/rm`, each with a `--tomorrow` variant, addressing tasks by their 1-based index.
- `today habit toggle <name>` (a leading emoji is optional) and `today habit list [--json]`.
- `today weight <kg>` to log or update the day's weight, plus `today weight [--json]` to show it and its trend.
- `today macros add "what,protein,carbs,fat"` and bare `today macros` for the day's aggregate.
- `today note add <text> [--tag <tag>]` and `today note list [--tag <tag>]`.
- `-N/--offset` to operate on another day, and `--den`/`$DEN_PATH` to point at another den.
- `--json` output on every read, matching the old `daily --json` shape.
- Nix packaging: `nix run .`, a `today` package and a system-agnostic overlay for consumers.
- `today --version`.

[unreleased]: https://github.com/alexjercan/today/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/alexjercan/today/releases/tag/v0.2.0
[0.1.0]: https://github.com/alexjercan/today/releases/tag/v0.1.0
