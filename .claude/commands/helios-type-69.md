---
description: Drive the UADx Helios Type 69 Preamp & EQ (measured) — warm British console colour + passive-style 3-band EQ, headless.
argument-hint: <audio.wav> [goal: warm-glue|clean-eq|air|de-box|tighten|colour]
---

Invoke the **helios-type-69** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the goal (warm drive/glue · clean EQ · air · de-box mid · tighten lows ·
subtle colour). The skill drives the **UADx Helios Type 69 Preamp and EQ** (`/Library/Audio/Plug-Ins/VST3/
uaudio_helios_type_69.vst3`) — UA's model of the late-'60s **Helios console** (Olympic Studios; Zeppelin/Hendrix/
Stones): a **passive-style 3-band EQ + valve/transformer preamp, no compressor** — warm, characterful, rock-leaning
British. It **measures spectrum/tilt/centroid/crest before & after** and A/Bs loudness-matched.

**Governing facts (measured, Pedalboard 0.9.23):** **renders headless via the `uaudio_` build** (UADx native, no
iLok) — NOT the `UAD …`/`Legacy .component` passthrough twins. **`gain` is the drive/colour, not just level**:
Line g20 = 0.002 % THD (clean) → Mic g40 = 53 % → Mic g70 = 61 %, even-harmonic warmth; Mic saturates ~10–20 dB
sooner than Line. **The −20 dB pad makes the drive musical** on line-level signals (Mic g40 + pad ≈ 1.9 % THD,
crest 14.6→13.1 — moderate glue; no pad = nuclear). **The bass BOOST is inert headless** (60/120/250/400 → 0.00 dB;
`bass_gain` locked to `'Off'`) — only the **cut** (−3…−15 low shelf) renders, so get low-end weight from the Mic
drive or `[L] apply-eq`. **Peak/Trough is nonlinear** — Peak is 1:1, **Trough needs `mid_gain` ~12–15** for a real
cut (set `mid_type` first, read back). All **14 params are enums**: the string switches (`input_select`/`mid_type`/
`pad`/`eq_in`/`polarity`) can't be set via `apply-vst-chain`'s float dict → use the **[[vst-preset]]** harness
(`apply_vst_preset.py`). **Meters own it** (Gemini hears mono). Needs `uv sync --extra vst`.

Ready examples: `presets/vst/helios-type-69-warm-drum-glue.json` (Mic g40 + pad + 4 dB air → crest 14.6→13.1,
warm/glued, measured) and `helios-type-69-clean-air-tighten.json` (Line, +4 air, −3 bass, mid Trough 700/12 →
crest 14.6→16.0, clean EQ). Full param surface + numbers + history: [`docs/vst/helios-type-69.md`](../../docs/vst/helios-type-69.md).
Pure-DSP alternatives (no plugin): saturation [[vst-saturate]]/`saturate-loop` · air [[excite]] · EQ `[L] apply-eq`.
Warm siblings: [[kit-bb-n105]] (Neve) · [[ssl-4k-e]] (clean British). Defer to the skill; report the path
(Line/Mic+gain+pad), the EQ moves, before→after crest/centroid/tilt deltas, and the preset/`.state` path.
