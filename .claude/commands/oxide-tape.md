---
description: Drive the UAD/UADx Oxide Tape Recorder (measured) — fast warm/master glue or lo-fi tape color, headless.
argument-hint: <wav-or-bus> [goal: warm|master|lofi|clean]
---

Invoke the **oxide-tape** skill on `$ARGUMENTS`.

`$1` = a WAV/stem/drum-bus/mix-bus/master; optional `$2` = the goal. The **UAD/UADx Oxide Tape Recorder**
(`uaudio_oxide_tape.vst3`) is UA's stripped-down tape machine — **one Input drive** + four switches (Input/Repro
path, 7.5/15 IPS, NAB/CCIR EQ, NR). **`input_level` is the whole color knob**: it trades crest for harmonics
(measured +0→+24 = crest 14.3→11.1, THD 0.16%→38% odd-3rd) and there's **no Auto-Gain** (trim `output_level` to
match). It's **near-neutral at low drive and BRIGHTENS as you push it** (centroid 2990→3800) — driven Oxide gets
brighter/grittier, not warmer. **CCIR = brighter top (+448 centroid) vs NAB warmer; 15 IPS = warm/full lows,
7.5 = colored/leaner-low** (no 30 IPS). **NR (default on) is a noise-floor switch, not a tone control.** Tape =
odd harmonics (Repro); the Input path = clean 2nd-harmonic sheen, no compression.

Goals → presets in `presets/vst/`: **warm** = `oxide-warm-drum-glue` (Repro/15/NAB, Input +7, ~1 dB glue) ·
**master** = `oxide-master-glue` (15/NAB, gentle +4, before the limiter) · **lofi** = `oxide-lofi-color`
(7.5/NAB, +14, odd-3rd grit) · **clean** = Path=Input electronics sheen.

**Harness for the switches:** `input_level`/`output_level` are numeric (reachable via `apply-vst-chain`), but
`path_select`/`ips`/`emphasis_eq`/`noise_reduct` are string/bool enums the float dict ignores — run a
`presets/vst/oxide-*.json` through `apply_vst_preset.py` with the `vst` venv. Renders headless via Pedalboard
(UADx native, no iLok; load `uaudio_oxide_tape.vst3`, NOT the `.component` twin). Measure crest + centroid/tilt
+ THD before→after; render-ab loudness-matched (Input isn't gain-compensated). Needs `uv sync --extra vst`.
The lighter/faster cousin of [[ampex-atr-102]] / [[studer-a800]]. Defer to the skill + `docs/vst/oxide-tape.md`;
report the settings, before→after crest/centroid, and the output/preset path.
