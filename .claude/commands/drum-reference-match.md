---
description: Reference-match a phase-aligned drum kit's tone, per stem (local DSP).
argument-hint: <stems dir> <reference.wav>
---

Invoke the **drum-reference-match** skill on `$ARGUMENTS`.

`$1` is the folder (with a `phase-aligned/` set from `/drum-phase-align`), `$2` the reference. The skill drives the local `drum-prep` CLI (`analyze` then `reference-match`): it measures the coherent kit sum, builds one corrective curve toward the reference, and distributes it per stem (cuts to all, boosts to band owners) with zero-phase EQ, writing `<dir>/ref-matched/`. Requires `uv sync --extra drum-prep`. Use `--strength` to dial the match. Report the per-stem EQ and the 6-band residual before→after.
