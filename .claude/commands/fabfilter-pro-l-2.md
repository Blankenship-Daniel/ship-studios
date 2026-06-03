---
description: Drive FabFilter Pro-L 2 (measured) — true-peak brickwall limiter, 8 styles, headless, no-iLok.
argument-hint: <audio.wav> [target: -14lufs|-9lufs|loud|clean] [style]
---

Invoke the **fabfilter-pro-l-2** skill on `$ARGUMENTS`.

`$1` is the WAV (a near-final master / loud bus — Pro-L 2 is the **last** insert); the rest hints the loudness
target / style. The skill applies **FabFilter Pro-L 2** (`/Library/Audio/Plug-Ins/VST3/FabFilter Pro-L 2.vst3`) —
a **true-peak brickwall limiter** with 8 styles (Transparent/Punchy/Dynamic/Allround/Aggressive/Modern/Bus/Safe),
LUFS+dBTP metering, oversampling and dither. It **drives `gain` to a LUFS target against a dBTP ceiling** and
verifies integrated LUFS + true-peak after.

**Governing facts (measured):** **renders headless & no-iLok** (clean render candidate) — use the **VST3** path.
**A LIMITER OWNS THE CEILING → render faithfully with `[L] apply-vst-chain`, NOT the renormalizing
`apply_vst_preset.py`** (which re-scales the output and pushes true-peak back over the ceiling). Carry the enums
(style/oversampling/dither/true-peak) in a **`.state`** blob; override the per-track **`gain`** via the float
`parameters`. **True Peak Limiting ON for any dBTP target** — measured TP-on −1.018 dBTP (compliant) vs TP-off
−0.984 dBTP (over) at the same −1.0 ceiling. **Ceilings:** −1.0 dBTP (Spotify/Apple/YouTube/EBU), −2.0 (broadcast).
**Style density (crest @+9):** Aggressive densest (9.49) … Modern most dynamic (10.56); Bus = drum/track glue.
**Dither LAST at the final bit depth** (keep Pro-L 2 dither Off if a later stage dithers). `gain` is per-track —
measure → set → re-measure. Needs `uv sync --extra vst`.

Ready config: `presets/vst/fabfilter-prol2-streaming-master.{state,json}` (Transparent / −1.0 dBTP / TP on / 4× OS).
Full param surface + numbers: [`docs/vst/fabfilter-pro-l-2.md`](../../docs/vst/fabfilter-pro-l-2.md). Pure-DSP
alternative (no plugin, auto-targets LUFS+ceiling): `[L] render-mastered` / [[master-track]]. Defer to the skill;
report style/ceiling/gain, before→after integrated LUFS + true-peak dBTP + crest, and per-platform compliance.
