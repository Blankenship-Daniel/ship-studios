---
description: Build one shared tonal target from references and match every mix in an EP/album to it (tonal consistency).
argument-hint: <references...> -- <mixes-or-album-dir>
---

Invoke the **house-curve** skill on `$ARGUMENTS`.

Build a reusable house curve with `[L] build-target-profile` over the reference WAVs, then for each mix `[L] match-to-profile` for the per-band delta and `[L] match-eq`/`apply-eq` to close it, re-checking convergence. Defer to the skill; lead the report with per-track before→after deltas and the cross-track spread. This makes the set tonally consistent — hand off to [[batch-master]] for loudness.
