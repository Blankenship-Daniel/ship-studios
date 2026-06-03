---
description: Drive the UADx Manley VOXBOX Channel Strip (measured) — all-tube vocal channel (pre + opto comp + passive Pultec EQ + de-ess/limiter), headless.
argument-hint: <audio.wav> [goal: vocal|drum-glue|bus-glue|colour|level|air|de-box|de-ess|limit]
---

Invoke the **manley-voxbox** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the goal (vocal channel · tube drum glue · bus tone + peak control · tube
colour · level/compress · air · de-box mid · de-ess · limit). The skill drives the **UADx Manley VOXBOX Channel Strip**
(`/Library/Audio/Plug-Ins/VST3/uaudio_manley_voxbox.vst3`) — UA's model of the **Manley VOXBOX** (1998), a mono
**all-tube** vocal channel: **tube pre + passive electro-optical compressor + passive Pultec-style (MEQ-5) 3-band EQ +
de-esser/opto-limiter** + output transformer. It **measures spectrum/tilt/centroid/crest before & after** and A/Bs
loudness-matched.

**Governing facts (measured, Pedalboard 0.9.23):** **renders headless via the `uaudio_` build** (UADx native, no dongle
here) — NOT the `UAD Manley VOXBOX.component` passthrough twin. **The audio path is NOT the GUI layout** — internal flow
is `INPUT → COMPRESSOR → tube PREAMP → EQ → DE-ESS/LIMITER → OUTPUT` (comp is FIRST, fixed). **`input` + `gain` + Mic =
the tube drive/colour**: Line in3 g40 = 0.002 % THD (clean) → Mic in6 g50 = 5 % → Mic in10 g60 = 67 %, even-harmonic;
Mic saturates ~10–20 dB sooner than Line, and on drums the drive BRIGHTENS as it distorts. **The opto comp RAISES crest**
(levels the body, opens transients: drum loop 14.6→19.5); it's a program-dependent opto (nominal "3:1", not fixed), and
**`comp_thresh` is RELATIVE TO `input` — higher number = MORE GR** (Slow attack passes transients, Fast catches them).
**The Pultec EQ 0–10 dials are nonlinear** (action 5–10): lo 10≈+10.5 / hi 10≈+8.6 dB (bells) / mid 10≈−11.7 dB; it's
**PEAK-DIP-PEAK** (LOW boost / MID cut / HIGH boost, no cuts/Q), and **HI has 11 freqs incl. 2 kHz**. **De-ess** ducks
the selected band (3K/6K/9K/12K, higher thr = more); the 5th position **`Limit` is a smooth opto 10:1 limiter** (peak
control, crest ↓ — not a brickwall). All **25 params are enums**: the string switches (`source_select`/`low_cut`/the
`*_byp` engages/`comp_attack`/`comp_rel`/`de_ess_sel`/`sc_link`/`transformer_byp`/`meter`) can't be set via
`apply-vst-chain`'s float dict → use the **[[vst-preset]]** harness (`apply_vst_preset.py`). `sc_link` is a stereo link
(inert mono); the output transformer is subtle here. **Meters own it** (Gemini hears mono). Needs `uv sync --extra vst`.

Ready examples: `presets/vst/voxbox-vocal-channel.json` (Mic + 80 Hz HPF + opto comp + Pultec body/air/de-honk + de-ess
6K — the canonical vocal chain), `voxbox-drum-glue.json` (Mic drive + comp opening transients + Pultec weight/air →
crest 14.6→19.5, warm/rounded), and `voxbox-bus-tube-glue.json` (Line tube tone + Pultec smile + `Limit` peak control →
crest 14.6→12.8, +4 dB denser). Full param surface + numbers + history: [`docs/vst/manley-voxbox.md`](../../docs/vst/manley-voxbox.md).
Pure-DSP alternatives (no plugin): opto/tube colour [[vst-saturate]]/`saturate-loop` · leveling `compress-loop` · de-ess
[[de-ess]] · air [[excite]] · EQ `[L] apply-eq`. Channel-strip siblings: [[ssl-native-channel-strip-2]] / [[api-vision-channel-strip]]
/ [[kit-bb-n105]] / [[helios-type-69]]. Defer to the skill; report the path (Line/Mic + input/gain), engaged blocks
(comp thr/atk/rel + GR, EQ moves, de-ess/Limit), before→after crest/centroid/tilt deltas, and the preset/`.state` path.
