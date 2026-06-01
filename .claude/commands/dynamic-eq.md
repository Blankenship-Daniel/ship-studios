---
description: Carve a level-dependent frequency problem with threshold-gated per-band dynamic EQ (cut above / boost below).
argument-hint: <mix-or-stem.wav>
---

Invoke the **dynamic-eq** skill on `$ARGUMENTS`.

`$1` is one stereo WAV (mix, bus, or stem). The skill baselines `measure-spectrum`/`measure-loudness`, confirms the problem is level-dependent, runs `[L] apply-dynamic-eq` (cut above threshold to de-mud only when a band gets loud, or boost below to fill dips), and re-measures. Defer to the skill; lead the report with the per-band max applied gain change and when it fired. Note this tool is unit-tested only — ear-check the A/B.
