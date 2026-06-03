---
description: Drive the SSL Native Channel Strip 2 (measured) — clean console EQ/comp/gate, headless.
argument-hint: <wav-or-bus> [role: drum-bus|kick|snare|overheads|vocal|bass|mix-bus]
---

Invoke the **ssl-native-channel-strip-2** skill on `$ARGUMENTS`.

`$1` = a WAV/stem/bus; optional `$2` = the role. The SSL Native Channel Strip 2 (XL 9000K model) is the **CLEAN**
console strip — precise EQ + glue, no added color, so **don't gain-stage into it**. **`apply-vst-chain` can't drive
it** (every meaningful control is a string enum — `eq_type` G/E, `*_type` Shelf/Bell, `compressor_peak` RMS/Peak,
`compressor_fast_attack`, `gate_expander`, all routing — or a log-stepped freq): use the [[vst-preset]] harness
(`presets/vst/apply_vst_preset.py`, e.g. `ssl-native-cs2-drum-bus.json`). Measured facts: passthrough at unity;
the comp's **normal attack barely grabs drums (~1 dB GR) → engage `compressor_fast_attack="In"`** (it *raised* crest
here, didn't squash); **E vs G EQ is subtle** (G brighter, E warmer); **LF gain is ±16.5 measured, not ±20**;
`high_pass_filter_hz` is log-stepped (`35.0` works, `40.0` errors → silently OUT). Renders headless via Pedalboard
(iLok — re-verify on new machines). Needs `uv sync --extra vst`. Measure crest/centroid before→after to prove the
move; A/B loudness-matched with OUT TRIM; `[G] detect-mix-issues` to catch over-comp/harshness (cross-check mono
"dark" claims vs stereo meters). Defer to the skill + `docs/vst/ssl-native-channel-strip-2.md`; report before→after
crest/centroid + the path. It's a bus/stem insert, not a master — hand off to [[master-track]].
