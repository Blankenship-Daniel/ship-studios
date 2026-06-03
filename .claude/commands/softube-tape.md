---
description: Drive the Softube Tape plugin (measured) — warm/tight/glue/parallel/lo-fi tape, headless.
argument-hint: <wav-or-bus> [goal: warm|tight|mix-glue|parallel|lofi]
---

Invoke the **softube-tape** skill on `$ARGUMENTS`.

`$1` = a WAV/stem/drum-bus/mix-bus; optional `$2` = the goal. **Softube Tape** (`Tape.vst3`) is a three-machine
tape emulation (deck + RC-1 Remote Control). **Amount is gain-compensated → it moves crest, not tone** (measured:
a2 −0.2 dB → a8 −0.9 → a10 −4.9 dB crest; glue lives ≤6–7). Pick by character: **Type A = clean, B = fattest/
darkest, C = colored**; **15 IPS = fattest lows, 30 IPS = tightest/brightest**; **High Freq Trim** is the tone
lever (±~560 Hz); **Crosstalk narrows/glues (never widens) and is inert on mono**. The bare default is HOT
(Amount 7.8 / WET / Crosstalk 50) — set values explicitly.

**Harness is mandatory:** 13 of 15 params are STRING ENUMS, so `apply-vst-chain`'s float dict can't set them —
run a `presets/vst/softube-tape-*.json` ({drum-glue-warm, drum-tight, mix-bus-glue, parallel-thick, lofi})
through `apply_vst_preset.py` with the `vst` venv. Renders headless via Pedalboard (Softube/iLok — verify on new
machines). Measure crest + centroid/tilt before→after (warm = down; tight = up; glue = crest only ~1–2 dB down,
not collapsed); render-ab loudness-matched (Input isn't gain-compensated). Needs `uv sync --extra vst`. NOT the
Ampex ([[ampex-atr-102]]) or Studer ([[studer-a800]]). Defer to the skill + `docs/vst/softube-tape.md`; report
the settings, before→after crest/centroid, and the output/preset path.
