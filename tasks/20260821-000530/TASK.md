# Migrate the Today widget to dashboardd 0.2.0

- STATUS: IN PROGRESS
- TAGS: dashboardd, widget, release, nix

## Goal

Keep Today as an independent external widget package while making it compatible with dashboardd 0.2.0 and widget manifest schema 3. Release the compatibility update as Today 0.3.1 before the Home Manager deployment.

## Accepted contract

- Keep all six Today variants and their backend behavior unchanged. They declare no required inputs and continue to open directly from the generated desktop tray.
- Replace source widget manifest schema 2 with schema 3. Add no launch frontend because no Today variant requires launch input.
- Pin the dashboardd flake input and frontend SDK artifact to released version 0.2.0. Keep the backend protocol payload schema version 1 unchanged because it is an independent widget-owned protocol.
- Run Today tests, frontend type checking, static bundle checks, dashboardd composition checks, and the Nix flake checks.
- Release Today 0.3.1 as a compatibility patch. Follow the repository release process: compatibility changes first, then a version-and-changelog-only release commit, annotated tag, and push.

## Completion gate

GitHub exposes Today v0.3.1, and its Nix widget package builds with dashboardd v0.2.0 as a schema version 3 external bundle.

## Implementation notes

- Updated the source manifest to schema version 3, the frontend SDK tarball to dashboardd 0.2.0, and the flake input to the immutable dashboardd 0.2.0 release revision.
- Dashboardd 0.2.0 renamed the packer package output from `dashboardd-widget` to `dashboardd-widget-bundle`; updated the external package build while retaining the installed `dashboardd-widget` command.
- Regenerated the npm and Nix locks. No Today variant gained an input or launch frontend.

## Verification

- `nix flake check -L` passes. It covers Ruff, mypy, pytest, frontend compilation, static schema version 3 bundle checks, all six variants, and composed dashboardd catalog startup.
