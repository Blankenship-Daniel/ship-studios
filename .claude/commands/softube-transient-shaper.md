---
description: Drive the Softube Transient Shaper (measured) — tighten/punch drums, 2-band, headless.
argument-hint: <wav-or-bus> [goal: tighten|kick-click|snare|overheads|bus]
---

Invoke the **softube-transient-shaper** skill on `$ARGUMENTS`.

`$1` = a WAV/stem/drum-bus; optional `$2` = the goal. The Softube Transient Shaper is a 2-band, level-independent
attack(PUNCH)/decay(SUSTAIN) shaper. **Tighten = negative SUSTAIN (LOW band so cymbals keep decay), not PUNCH**
(PUNCH pushed = clicky). Floats (`punch_db`/`sustain_db`/`crossover_freq_hz`/`output_level_db`) go via
`[L] apply-vst-chain`; enums (`*_band`/`punch_type`/`clip`) need the [[vst-preset]] harness
(`presets/vst/apply_vst_preset.py`, e.g. `softube-ts-tighten-low.json`). Renders headless via Pedalboard (iLok —
verify on new machines). Measure crest/PLR before→after to prove it tightened; `[G] detect-mix-issues` to catch
over-shaping (cross-check its mono "dark" claims vs stereo meters). Needs `uv sync --extra vst`. Defer to the
skill + `docs/vst/softube-transient-shaper.md`; report before→after crest/PLR + the path.
