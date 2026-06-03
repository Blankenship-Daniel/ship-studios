---
description: Drive the UADx Manley Massive Passive (measured) — broad/musical 4-band parallel passive EQ (standard + MST), headless.
argument-hint: <audio.wav> [goal: drum-bus|low-end|air-deharsh|master-polish|de-mud|tilt]
---

Invoke the **manley-massive-passive** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus/master; the rest hints the goal (broad drum/mix-bus tone · big-but-tight low end · air without
harshness · gentle master polish · de-mud/de-box · broad tilt). The skill drives the **UADx Manley Massive Passive** —
UA's model of the **Manley Massive Passive**, a 2-channel **all-passive (LC inductor) EQ with a solid-state input buffer +
all-tube make-up amp** and 4 overlapping bands per channel. Two builds: the **standard**
(`uaudio_manley_massive_passive.vst3`, continuous, ±20 dB — the screenshot's "Massive Passive Stereo Equalizer") and the
**MST / mastering** version (`uaudio_manley_massive_passive_m.vst3`, stepped for recall + a ±2.5 dB L/R trim). It
**measures spectrum/tilt/centroid/band-ratios/crest before & after** and A/Bs loudness-matched.

**Governing facts (measured, Pedalboard 0.9.23):** **renders headless via the `uaudio_` build** (UADx native, no dongle
here) — NOT the `UAD Manley Massive Passive*.component` passthrough twins, and **`probe_plugin.py` FALSE-flags it as
passthrough** because **every band defaults to `OUT`** (set `enable=BOOST`/`CUT` or nothing happens). It's a **PARALLEL**
passive EQ so the **bands INTERACT** (two boosts measure ~1.4–2.0 dB LESS than their sum). **The GAIN dial is steeply
nonlinear AND bandwidth-coupled — dB = gain × bandwidth, not the dial** (action 6–16; at default bw a bell dial 10 ≈ +6,
dial 20 ≈ +12; the ±20 dB ceiling needs a NARROW bandwidth — himid dial 20 went +4.6 at bw 1.0 → +20.9 at bw 3.0).
**BANDWIDTH 1.0 = widest, 3.0 = narrowest/most gain** (reversed Q). **SHELF ≫ BELL for level**, and **a SHELF + NARROW
bandwidth grows a resonant corner** (low shelf @47 bw3.0 dial20 = +15 @20 / +0.4 @47 / +3.3 @150 — "the shelves aren't
shelves"); keep `bw` WIDE for a clean shelf. Signature moves: **LOW-END TRICK** (low SHELF boost + low-mid BELL CUT →
big-but-tight; one band can't boost+cut), **AIR TRICK** (hi SHELF @16k + hi-mid CUT @3.3k → air while presence drops),
**27 kHz** = supersonic "3D" air shelf (render at 96 k). It's a **clean EQ** (0.03 % THD flat @−18 dBFS → 0.24 % @0 dBFS;
subtle even-harmonic make-up colour) — **crest HELD** (EQ, not dynamics); "flat" is NOT a null (only `master_bypass`).
**All 51 params are enums**: `enable`/`shape`/`lopass`/`hipass`/`ctrllink`/`power` are STRING/bool enums the
`apply-vst-chain` float dict can't set → use the **[[vst-preset]]** harness (`apply_vst_preset.py`), **set BOTH ch1* and
ch2*** (LINKED mirrors ch1→ch2; no M/S — L/R + Link only). **Meters own it** (Gemini hears mono). Needs `uv sync --extra vst`.

Ready examples: `presets/vst/massive-passive-drum-bus.json` (std — weight + tight low-mids + air: low 0.80→0.86, low-mid
0.18→0.13), `massive-passive-low-end-trick.json` (std — low SHELF @47 + low-mid CUT @180 → big-but-tight), 
`massive-passive-air-deharsh.json` (std — 16k air + 3.3k presence CUT → high 0.0043→0.0061 while the harsh presence drops),
and `massive-passive-master-polish.json` (MST — gentle 2-bus low weight + 390 de-mud + 16k air, crest 14.6→14.1). Full
param surface + transfer-function/THD numbers + history: [`docs/vst/manley-massive-passive.md`](../../docs/vst/manley-massive-passive.md).
Pure-DSP alternatives (no plugin): broad shelves/tilt + weight `[L] apply-eq` · air [[excite]] · level-dependent de-harsh
[[de-harsh]]. EQ siblings: [[pultec-eqp-1a]] / [[pultec-meq-5]] / [[hitsville-eq-mastering]] (broad/vintage) · [[fabfilter-pro-q-4]]
(surgical). Defer to the skill; report the build (standard/MST), engaged bands (band · Boost/Cut · Shelf/Bell · gain ·
bandwidth · freq), before→after band-ratio/centroid/tilt deltas (crest held), and the preset/`.state` path.
