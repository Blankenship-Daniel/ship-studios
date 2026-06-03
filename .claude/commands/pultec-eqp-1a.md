---
description: Drive the UADx Pultec EQP-1A program EQ (measured) — passive tube EQ; the low-end trick + air-without-fizz, headless.
argument-hint: <audio.wav> [goal: lowend-trick|air|de-harsh|smile|presence|colour]
---

Invoke the **pultec-eqp-1a** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the goal (low-end trick / air-without-fizz / de-harsh / broad smile /
HF presence / tone-print colour). The skill drives the **UADx Pultec EQP-1A EQ** (`/Library/Audio/Plug-Ins/VST3/
uaudio_pultec_eqp-1a.vst3`) — UA's model of the legendary **Pultec EQP-1A**: a **passive LC inductor EQ + push-pull
tube makeup amp + transformers**. The broad, musical vintage EQ whose two signature tricks are the **low-end trick**
(boost + atten the *same* CPS → big tight bottom) and **air-without-fizz** (independent HF boost vs HF cut freqs). It
**measures spectrum/tilt/centroid/low-ratio/crest before & after** and A/Bs loudness-matched.

**Governing facts (measured, Pedalboard):** **renders headless via the `uaudio_` build** (UADx native, iLok/PACE but
offline-OK once locally authorized) — NOT the `UAD …`/`Legacy .component` passthrough twins. **Boost/Atten/Bandwidth
knobs are 0–10 DIAL POSITIONS, not dB, and nonlinear** (action 4→8; low boost @60 CPS knob 4≈+4, 6≈+11, 8≈+15 dB) —
dial to the meter. **The LOW-END TRICK is real**: `lf_boost`+`lf_atten` at the same `low_freq` don't cancel (boost
peaks below the CPS, atten dips above) → e.g. 60 CPS B7/A5 = +12 dB @60 with a −2.4 dB scoop @1k. **Air-without-fizz**:
`high_freq` (boost) and `hf_atten_freq` (cut) are independent → 16 KCS boost + 10 KCS atten = +2.7 dB @16k while
pulling 3–8k. **It colours via CURVES, not drive** (~0.002 % THD @−18 dBFS, ~0.01 % @−6 — faint odd-harmonic). **It's
never a true bypass**: engaged-flat = +1.1 dB makeup + top-softening (matches UA's ~1.13 dB), `enable=Out` is *brighter*
(amp stays in), only `master_bypass=true` nulls → **loudness-match every A/B**. **5 of 12 params are STRING enums**
(`low_freq`/`high_freq`/`hf_atten_freq`/`enable`/`output`) → use the **[[vst-preset]]** harness (`apply_vst_preset.py`),
not `apply-vst-chain`'s float dict. **Meters own it** (Gemini hears mono). Needs `uv sync --extra vst`.

Ready examples: `presets/vst/pultec-drum-lowend-glue.json` (60 CPS B5/A4 + de-harsh + sheen → warm+tight drums, low
ratio 0.80→0.88, low-mid scoop 0.18→0.12, crest held), `pultec-air-without-fizz.json` (16 KCS boost + 10 KCS atten →
+1.5 dB @16k air, 5–8k tamed, crest held), and `pultec-master-smile.json` (gentle 30 CPS trick + 16 KCS air → broad
smile, crest held; before the limiter). Full param surface + curves + numbers + history:
[`docs/vst/pultec-eqp-1a.md`](../../docs/vst/pultec-eqp-1a.md). It's BROAD/musical — for notches pair with
[[fabfilter-pro-q-4]]; for level-dependent moves [[dynamic-eq]]. Pure-DSP alternatives (no plugin): broad/tilt EQ +
the trick (low-shelf boost + low-mid bell cut) `[L] apply-eq` · air [[excite]] · tube/tape colour `saturate-loop` /
[[ampex-atr-102]]. Vintage siblings: [[helios-type-69]] · [[hitsville-eq-mastering]]. Defer to the skill; report the
path, the moves (CPS+boost/atten, KCS+boost/q, ATTEN-SEL+atten), before→after crest/centroid/tilt/low-ratio deltas
(crest should hold — it's EQ), and the preset/`.state` path.
