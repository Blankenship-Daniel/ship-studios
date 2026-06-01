---
description: Add air/presence with band-limited parallel harmonic excitement (generated from the material, with a 5–7 kHz harshness guard).
argument-hint: <mix-or-stem.wav>
---

Invoke the **excite** skill on `$ARGUMENTS`.

`$1` is one stereo WAV (mix, bus, or stem). The skill baselines `measure-spectrum`, runs `[L] excite-loop` (air or presence band, parallel blend ≈0.3), and re-measures. Defer to the skill; lead the report with the harmonic energy added and the 5–7 kHz guard delta. Excitement creates new harmonics — a static shelf (apply-eq) just boosts existing content + hiss; if it's harsh, use [[de-harsh]] instead.
