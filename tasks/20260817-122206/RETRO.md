# Retro: Provide writable Today dashboardd widgets

- TASK: 20260817-122206
- BRANCH: master
- REVIEW ROUNDS: 1

## What went well

- Keeping Markdown ownership in Today allowed the CLI, backend, and widgets to
  share one application API and one revision model.
- Building the external package early proved the dashboardd platform contract
  with a real Python runtime rather than another repository fixture.
- Browser automation exercised actual writes against a fixture den and caught
  integration failures that static package checks could not detect.
- Separate widgets kept normal mode direct and low-clutter while Focus retained
  history, removals, and dated planning.

## What went wrong

- The first frontend build emitted imports of `shared.js`, but the packer copies
  only declared variant entry artifacts. Static checks passed because every
  declared file existed; the browser found the missing transitive module.
- Dashboardd can emit the initial backend update before a browser subscribes.
  Direct dashboard and Focus loads were blank until mount requested a refresh.
- Initial phone layouts gave Macros too little control width and allowed the
  Weight value to wrap.

## What to improve next time

- Test built package artifacts in a browser before considering frontend
  packaging complete.
- Treat each declared frontend artifact as an isolated load unit unless the
  platform contract explicitly supports dependency closure.
- Test late subscribers and direct Focus URLs for every stateful widget.
- Include dense phone composition in the first visual pass.

## Action items

- Release Today before replacing nix.dotfiles' local path input with a GitHub
  tag.
