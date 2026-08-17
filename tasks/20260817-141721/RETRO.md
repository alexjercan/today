# Retro: Use macros CLI for dashboard food entry

- TASK: 20260817-141721
- BRANCH: master
- REVIEW ROUNDS: 1

## What went well

- The split stayed clean: macros owns food identity, search, units, and
  calculation; Today alone performs revision-guarded Markdown writes.
- Exact JSON validation on both sides prevented the integration from depending
  on human-readable CLI output.
- Package testing with an empty PATH proved the macros executable is in the
  backend's Nix closure.
- Browser automation covered the complete piece and gram workflows, keyboard
  selection, totals, phone width, and visual evidence.

## What went wrong

- `makeWrapper` produced a two-file wrapper, but the widget packer correctly
  copied only the declared backend artifact. The packed script referenced a
  missing hidden companion. A self-contained shell script with direct Nix store
  references fixed the closure.
- The first autocomplete popup was taller than the 3x1 tile. Clipping hid the
  highest-ranked result even though keyboard selection still found it.
- Refocusing the quantity input called `setSelectionRange`, which number inputs
  reject. Browser page-error capture found it.

## What to improve next time

- Execute the final packed backend with an empty PATH whenever adding a runtime
  dependency.
- Test visible candidate order, not only DOM order.
- Keep focus restoration specific to each input type.
- Complete owner-repository records before refreshing downstream local locks.

## Action items

- Release macros.nvim before Today, then replace nix.dotfiles' local path inputs
  with tags.
