---
description: Drive the UAD/UADx Ampex ATR-102 Master Tape for 2-bus / mastering / mixdown tape glue — measured.
argument-hint: <audio.wav> [goal: master-glue/warm-2bus/drum-glue/tame-harsh]
---

Invoke the **ampex-atr-102** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (transparent master glue / warm 2-bus / drum glue / tame harshness).
The skill applies the **UAD/UADx Ampex ATR-102 Master Tape** (`uaudio_ampex_atr-102_tape.vst3`) — the **2-track
¼/½/1″ mastering & mixdown** machine, the smooth/glossy counterpart to the punchier multitrack [[studer-a800]].
Applies via the [[vst-preset]] harness and **measures centroid/tilt + crest/PLR before & after**.

**Governing facts (measured on this rig):** the ATR's **gloss is the output TRANSFORMER = even/2nd harmonics**
(toggle OFF → centroid −751, much darker; a 1 kHz sine probe shows +15 dB H2 ON-vs-OFF), while the **tape itself
is odd/3rd** — driven hard the odd stack (3rd→5th→7th) turns harsh, cure = **less Record level**. **−12 dBFS =
0 VU**: **Record level = the drive** (raises level + saturates), **Reproduce = makeup**, **Auto Gain**
compensates. **WIDTH × SPEED is the signature combo**: **15 IPS = warm/full** (wider→darker), **30 IPS =
bright/tight** (wider→leaner low, 0.63→0.53); **1″/30 IPS = hi-fi master**, **1/2″/15 IPS = warm mixdown**.
**NAB/CCIR is inert at 30 IPS** (AES-locked). **Re-assert `auto_cal:true` with the full speed/tape/cal/width set**
or repro-EQ stays mis-calibrated (~−800 Hz at 30 IPS). Enums/bools/per-channel levels → **preset harness**, not
`apply-vst-chain`. UADx native — **renders headless, no iLok**; the `UAD *.component` twin passes through (don't
use it). Needs `uv sync --extra vst`.

Ready presets: `presets/vst/ampex-atr-{master-glue,warm-2bus,drum-glue}.json`. Full param surface + isolation /
harmonic numbers: [`docs/vst/ampex-atr-102.md`](../../docs/vst/ampex-atr-102.md). Pure-DSP alternative (no
plugin): [[finalize-mix]] + `[L] saturate-loop` (tape mode) + `[L] apply-eq`. It's a **color insert, not a
limiter** — hand loudness/ceiling to [[master-track]]. Defer to the skill; report path/IPS/tape/cal/width/
transformer + Record drive, before→after centroid/tilt/crest, and the preset/`.state` path.
