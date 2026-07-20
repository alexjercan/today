# Review: finalize nix packaging (20260720-142205, in-repo half)

- VERDICT: APPROVE
- ROUNDS: 1 (out-of-context reviewer)

## Summary

Export `flake.overlays.default` (the tatr pattern), trim the dev dependency group
to the tools actually used, making uv.lock consistent. The cross-repo dotfiles
swap is deliberately deferred to the user (outward-facing; needs a push) and was
correctly scoped out of this review.

## Verified by the reviewer

- Overlay is correct/idiomatic: `flake.overlays.default` is the right flake-parts
  location; `self.packages.${final.stdenv.hostPlatform.system}.today` resolves the
  per-system app (eval type "lambda", mainProgram "today"). No recursion (body
  reads only `.system`, not the `today` attr it defines). `.today` is right here
  (this flake names its package `today`, not `default`). `_prev` is fine.
- Dev-dep trim is safe: grep of tests/ and today/ for respx/asyncio/pytest_asyncio/
  psutil/requests/httpx/async/asyncio_mode returns zero real hits; no
  `[tool.pytest.ini_options] asyncio_mode`. mypy + pytest still pass.
- uv.lock consistent: `uv lock --check` rc 0 ("Resolved 14 packages"), lock
  unchanged, git-tracked (satisfies `nix-flake-untracked-eval`).

## Findings

All nits (confirmations, no changes requested).

## Proof

`uv lock --check`: rc 0. `nix develop -c "ruff check . && mypy . && pytest"`: 87
passed, green. `nix flake check`: all checks passed. `nix run . -- --help` and the
full e2e smoke test through the packaged binary verified in-session.
