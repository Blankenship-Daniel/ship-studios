---
description: Drive the UADx Pultec MEQ-5 mid-range EQ (measured) — passive midrange shaping (LOW PEAK / DIP / HIGH PEAK), headless.
argument-hint: <audio.wav> [goal: de-box|presence|warm-body|scoop|attack]
---

Invoke the **pultec-meq-5** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the goal (de-honk/de-box / presence-attack / warmth-body / mid scoop /
snare attack). The skill drives the **UADx Pultec MEQ-5 EQ** (`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_meq-5.vst3`)
— UA's model of the **Pultec MEQ-5 "Mid-Range Equalizer"**: a **passive LC inductor EQ + tube make-up amp +
transformers**, focused on the **midrange (~200 Hz–7 kHz)** via three overlapping sections — **LOW PEAK** boost
(200/300/500/700/1000 Hz), a **DIP** cut (200 Hz–7 kHz, 11 steps), and a **HIGH PEAK** boost (1.5/2/3/4/5 kHz) —
plus a clean output trim. The **MIDRANGE** member of the Pultec Passive EQ Collection ([[pultec-eqp-1a]] = lows+air,
[[pultec-hlf-3c]] = filters). It **measures spectrum/centroid/mid-ratio/crest before & after** and A/Bs loudness-matched.

**Governing facts (measured, Pedalboard):** **renders headless via the `uaudio_` build** (UADx native, iLok account;
`master_bypass=True` is the only TRUE null) — NOT a `UAD …`/`Legacy .component` twin (passthrough). **The MEQ-5 0–10
dial is ROUGHLY dB here** — *unlike* the [[pultec-eqp-1a]] (nonlinear, not-dB) and [[hitsville-eq-mastering]] ("8 ≈
+5 dB") knobs: **LOW PEAK ≈ +1 dB/unit → +10.7 dB max**, **HIGH PEAK ≈ +0.9/unit → +8.8 dB max**, the **DIP
saturates** (~−4.9 @4, −8.9 @6, −11 dB max, ~flat past 7). Sections are **broad overlapping bells** (boost ~1.5–2 oct,
DIP ~1 oct, HIGH PEAK narrows at higher freq). **Boost + DIP at the same freq does NOT cancel** — it focuses (700 @10 +
700 @10 = ~+2.3 dB, tighter shoulders). **Midrange-only** (nothing < 200 Hz or > 5 kHz — use [[pultec-eqp-1a]] for
lows/air, [[pultec-hlf-3c]] for filters, [[fabfilter-pro-q-4]] for notches). **Colour = curves + a gentle
level-dependent harmonic driven by the INPUT** (THD 0.012 % @−18 → 0.096 % @0 dBFS); the **`output` trim is a CLEAN
post-gain** that does NOT saturate → drive the input for colour. **10 params, all enums:** the **three AMOUNT knobs**
(`lm_peak`/`mid_dip`/`hm_peak`) set via `apply-vst-chain`'s float dict, but the **FREQUENCY selectors**
(`lm_freq`/`mid_freq`/`hm_freq`) + `output` + `enable` are **STRING enums it silently drops** (→ defaults lm 200 /
mid 700 / hm 1.5k = wrong bands) → use the **[[vst-preset]]** harness (`apply_vst_preset.py`). **Meters own it** (Gemini
hears mono). Needs `uv sync --extra vst`.

Ready examples: `presets/vst/pultec-meq5-mid-scoop.json` (DIP 700 @5 + HP 4k @3 + LP 200 @2 → de-honk/de-box),
`pultec-meq5-drum-presence.json` (LP 200 @3 + DIP 500 @4 + HP 3k @5 → forward attack, centroid 2223→2261, high-mid
0.035→0.051), and `pultec-meq5-warm-body.json` (LP 300 @4 + DIP 2k @4 + HP 5k @4 → low-mid warmth, low-mid 0.327→0.433,
centroid 2223→2069, crest held). Full param surface + curve/amount tables + history:
[`docs/vst/pultec-meq-5.md`](../../docs/vst/pultec-meq-5.md). It's BROAD/musical — notches → [[fabfilter-pro-q-4]];
level-dependent → [[dynamic-eq]]; attack via transients (not EQ) → [[drum-punch]]. Pure-DSP alternative (no plugin):
broad mid bells/scoop via `[L] apply-eq` (low Q ≈ 0.7). Defer to the skill; report the path, the section(s) + freq
(CPS/KCS) + amount, before→after centroid/mid-ratios/crest deltas (crest should hold — it's EQ), and the preset/`.state`
path. Loudness-match the A/B. Master/limit AFTER in [[master-track]].
