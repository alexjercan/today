# Use macros CLI for dashboard food entry

- STATUS: CLOSED
- PRIORITY: 100
- TAGS: dashboardd, macros, food, nix

Replace manual macro entry in the Today dashboard widget with macros.nvim food autocomplete and quantity-based calculation.

## Requirements

- Today remains the only writer for daily Markdown.
- macros.nvim owns food search, units, and macro calculation through JSON CLI commands.
- Normal mode provides debounced keyboard-accessible autocomplete and one quantity field.
- The selected food determines grams or pieces.
- Remove manual protein, carbohydrate, and fat submission.
- Include the macros executable in the packaged widget runtime closure.
- Preserve revision-guarded food writes and Focus removals.

## Definition of Done

- Search returns at most eight deterministic candidates without blocking food writes.
- Stale search responses do not replace newer results.
- Add requires a selected candidate and positive amount.
- Gram and piece foods produce correct Markdown rows.
- Packaged dashboardd can search and add food without relying on interactive PATH.
- Python, TypeScript, Nix, browser, and Home Manager checks pass.

## Implementation

- Added `food.search` command results with an eight-result limit and request
  identity for stale-response rejection.
- Changed `food.add` to accept only a stable food ID and positive quantity.
  The backend calls macros, validates its JSON, creates the calculated CSV row,
  then uses Today's existing revision-guarded atomic write.
- Replaced manual P/C/F inputs with a debounced combobox, keyboard selection,
  and a quantity control whose unit comes from the selected food.
- Gram selections default to 100; piece selections default to 1.
- Added macros as a flake input and included its executable through the packed
  backend's direct Nix runtime closure.
- Added exact backend subprocess tests and desktop/phone browser evidence.

## Verification

- `nix flake check -L`: passed all 12 checks, including 103 pytest tests,
  Ruff, Mypy, TypeScript, package validation, and catalog composition.
- Packaged backend with an empty `PATH`: searched and added a calculated piece
  entry through the bundled macros executable.
- Browser automation: fuzzy search, mouse-visible and keyboard-selectable
  candidates, piece and gram defaults, two calculated writes, updated totals,
  no frontend exceptions, and no phone horizontal overflow.
- Evidence: `food-autocomplete.png` and `food-phone.png`.

## Home Manager deployment

nix.dotfiles commit `5727cb6` makes Today's macros input follow the local
macros.nvim JSON CLI checkout and sets the service's database explicitly to
`~/.local/share/nvim/macros.csv`. Its flake check and Home Manager activation
build passed. The switch restarted the healthy service with all five Today
instances. A read-only packaged backend search against the real database
returned both chicken entries for `chick`.
