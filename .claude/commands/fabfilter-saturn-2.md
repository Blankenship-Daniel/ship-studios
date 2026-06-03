---
description: Drive FabFilter Saturn 2 (measured) — multiband distortion/saturation, 28 styles, headless, no-iLok.
argument-hint: <audio.wav> [goal: warm|parallel|bass|air|density|lofi|master]
---

Invoke the **fabfilter-saturn-2** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the goal (warm glue / parallel smash / bass-translation multiband / air /
transparent density / lo-fi destruction / mastering color). The skill applies **FabFilter Saturn 2**
(`/Library/Audio/Plug-Ins/VST3/FabFilter Saturn 2.vst3`) — a **multiband distortion & saturation** plug-in: up to
**6 bands**, each with its own **distortion style** (28: tube/tape/amp/transformer/saturation + Foldback/Rectify/
Destroy/Smudge/Breakdown FX), **Drive**, bipolar **Dynamics**, resonant **Feedback**, a 4-band **Tone** EQ, per-band
**Mix/Level/Pan**, plus Mid/Side, Linear-phase crossovers, HQ oversampling, and a 50-slot modulation matrix. It
**measures THD/centroid/crest before & after** and A/Bs loudness-matched.

**Governing facts (measured):** **renders headless AND no-iLok** (a clean render candidate like Pro-Q 4) — use the
**VST3** path. **A bare load is NOT neutral — it restores FabFilter's last-saved GUI state** ('Warm Tape', 1 band,
drive 20), so **set every param explicitly** or restore a `dump_state`. The **only bit-exact passthrough** is
`mix=0` or `bypass='Bypassed'` — **`drive=0` is NOT clean** (Warm Tube @drive0 = +1.7 dB / 2.2% THD). **All 956
params are enums**: numeric drive/mix/dynamics/tone/crossover accept floats (snap to grid), but **`band_N_style`
(the sound itself), `_crossover_slope`, `channel_mode`, `processing_mode`, `high_quality_mode` are string enums →
`apply-vst-chain`'s float dict can't drive it.** Use the **[[vst-preset]]** harness (`apply_vst_preset.py`).
Pick the style by harmonic (measured): **Tube** = even+odd (Warm = warmth), **Tape/Saturation** = odd-only, **Amp**
= heavy odd, **Foldback** = wavefold, **Rectify** = octave-up, **Destroy** = crush. **Drive crushes crest** →
protect transients with the **parallel `mix`** or **negative `dynamics`**. Needs `uv sync --extra vst`.

Ready examples: `presets/vst/saturn2-drum-bus-warm.json` (Warm Tube glue, punch kept) ·
`saturn2-parallel-smash.json` (amp grit at 30% parallel mix) · `saturn2-bass-multiband.json` (sub clean, mids
saturated to translate). Full param surface + harmonic table + numbers:
[`docs/vst/fabfilter-saturn-2.md`](../../docs/vst/fabfilter-saturn-2.md).
Pure-DSP alternatives (no plugin): [[vst-saturate]] (`saturate-loop`) · [[excite]] · [[multiband-compress]] · [[sub-design]].
Defer to the skill; report the bands/style/drive/mix/phase, before→after THD/centroid/crest deltas, and the
preset/`.state` path.
