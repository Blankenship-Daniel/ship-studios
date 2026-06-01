---
description: Compress frequency bands independently (LR4 multiband), proven via per-band gain reduction + crest.
argument-hint: <mix-or-stem.wav>
---

Invoke the **multiband-compress** skill on `$ARGUMENTS`.

`$1` is one stereo WAV (mix, bus, or stem). The skill baselines `measure-loudness`/`measure-spectrum`, runs `[L] multiband-compress` (LR4 crossovers, an independent compressor per band — compress only the misbehaving band), and re-measures. Defer to the skill; lead the report with per-band gain reduction and the crest before → after. This is per-band level control — punch (transient) is [[drum-punch]].
