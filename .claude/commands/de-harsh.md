---
description: Tame harshness/ringing with the Soothe-style dynamic resonance suppressor (ducks peaks only when they ring; broadband tone survives).
argument-hint: <mix-or-stem.wav>
---

Invoke the **de-harsh** skill on `$ARGUMENTS`.

`$1` is one stereo WAV (mix, bus, or stem). The skill baselines `measure-spectrum`/`measure-loudness` (optionally `[G] find-resonances`), runs `[L] suppress-resonances` (dynamic, ring-targeted, with a 2–10 kHz harshness tilt), and re-measures. Defer to the skill; lead the report with the mean/max attenuation applied and the harsh-region delta. Note this tool is unit-tested only — ear-check the A/B.
