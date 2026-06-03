---
description: Drive the UADx Vibe Analog Machines (measured) — pick a machine, set drive + warble/tone, headless analog "vibe"/saturation/lo-fi.
argument-hint: <audio.wav> [vibe: sweeten|warm|glow|edge|thicken|vintagize|distort|overdrive|fire|sputter] [+warble]
---

Invoke the **vibe-analog-machines** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the vibe (machine + whether to add warble). The skill drives the **UADx Vibe
Analog Machines** — UA's analog **saturation/coloration** box (formerly **Verve Analog Machines**; renamed 2026-04-14,
so reviews/manual say "Verve" but mean this — and it ships as `/Library/Audio/Plug-Ins/VST3/uaudio_verve.vst3`). Pick a
`machine` (1 of 10), turn up `drive` (`param_1`), shape with the second knob, trim `output_trim`. It's **colour, NOT an
EQ and NOT a compressor**. It **measures centroid/tilt/crest before & after** and A/Bs loudness-matched.

**Governing facts (measured, Pedalboard):** **renders headless** via the `uaudio_verve.vst3` UADx-native build (**iLok
account, no dongle**; bypass == dry to the sample) — NOT the `UAD …`/`.component`/AU passthrough twins. **6 params, the
`machine` is a STRING enum** → use the **[[vst-preset]]** harness (`apply_vst_preset.py`); `apply-vst-chain`'s float
dict sets `param_1`/`param_2`/`output_trim` but **silently misses the machine name**. **`param_1`=DRIVE (amount,
default 40); `param_2` = WARBLE on the 6 TAPE machines / TONE on the 4 PREAMP machines** (same slot, two meanings);
**`output_trim`=clean ±12 dB output slider**. **DRIVE 0 ≠ bypass** (still colours; true null = `master_bypass`/`power`).
**WARBLE is PITCH modulation → INVISIBLE to spectrum/crest meters** (audition it); **TONE** (preamps) *does* move the
centroid (1200↔6000+ Hz). **DRIVE is only ~gain-compensated** → harness peak-normalizes; A/B loudness-matched. **Meters
own the tone** (Gemini hears mono). Needs `uv sync --extra vst`.

**The 10 machines (measured; 6 tape = Drive+Warble · 4 preamp = Drive+Tone):** `SWEETEN` tape — clean brighten/air,
crest held · `EDGE` preamp — clean console tone-shaper · `GLOW` preamp — valve warmth + tone tilt · `WARM` tape —
gentle warm-glue, keeps air · `THICKEN` tape — mid body + crest UP (tighter) · `VINTAGIZE` tape — dark/band-limited
lo-fi · `DISTORT` preamp — driven valve · `OVERDRIVE`/`FIRE` tape — heavy clip · `SPUTTER` preamp — filthiest. The
**Essentials** build (`uaudio_verve_essentials.vst3`) = 4 tape machines, drive only.

Ready examples: `presets/vst/vibe-sweeten-drum-glue.json` (SWEETEN d50 → centroid↑, +air, crest held),
`vibe-warm-drum-bus.json` (WARM d65 → crest 14.6→12.1, warmer, top gently rolled — ≡ SoS's "Warm @ drive ~65 on
drums"), `vibe-lofi-warble.json` (VINTAGIZE d50 + warble 35 → dark + tape wobble). Full surface + per-machine numbers +
history: [`docs/vst/vibe-analog-machines.md`](../../docs/vst/vibe-analog-machines.md). Pure-DSP alternatives (no
plugin): saturation [[vst-saturate]]/`saturate-loop` · air [[excite]] · proper tape [[studer-a800]]/[[ampex-atr-102]]/[[softube-tape]].
Defer to the skill; report the machine+drive(+warble/tone), before→after crest/centroid/tilt deltas, and the preset/`.state` path.
