---
description: Dial the KIT Plugins BB N105 V2 (Blackbird Neve 8078/31105) for warm/thick Neve tone — measured.
argument-hint: <audio.wav> [goal: warm-bus/weight/de-box/air]
---

Invoke the **kit-bb-n105** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (warm drum bus / low weight / de-box / Neve air). The skill applies
the KIT **BB N105 V2** (`KIT BB N105 V2.vst3`) — a Blackbird **Neve 8078 / 31105** channel strip, the WARM
counterpart to the punchy API siblings [[kit-bb-a5]] / [[api-vision-channel-strip]]. Warmth comes from the
**Mic-mode transformer drive** (`pre_amp_mode="Mic"` + `pre_amp_saturation`, sensitivity −40…−45 subtle,
toward −70 for more) — **not** from an EQ air boost; the 31105 EQ only tightens (HPF ~47 Hz, LF shelf +2 @56
weight, de-box −2 @470). Applies via the [[vst-preset]] harness and **measures crest/centroid/tilt + low &
low-mid ratios before & after** (warm-tight = low weight up, de-boxed, sub tightened, crest preserved/up).

**Governing facts (measured):** the Neve color is **MIC-MODE ONLY** — in Line mode `pre_amp_sensitivity` /
`pre_amp_saturation` are **inert**. **No host Auto-Gain** (GUI-only) → compensate Mic drive with `output_gain`.
**Every param is an enum**: gains accept a float (reach via `apply-vst-chain`), but **freq/mode/Hi-Q/phase/eq/
saturation are string/bool enums → preset harness**. **HF tops at 15 kHz**, **HPF top = 270 Hz**, **Hi-Q is
mids-only**; analog hum negligible offline. **N105 ≠ N73** (1073); the "Master Buss" is API (GUI-only here).
iLok/PACE — **verified-headless on this rig** (`probe_plugin.py "N105"` → `RENDERS ✓`); re-verify elsewhere.
Needs `uv sync --extra vst`.

Ready preset: `presets/vst/bb-n105-warm-drum-bus.json`. Full param surface + isolation numbers:
[`docs/vst/kit-bb-n105.md`](../../docs/vst/kit-bb-n105.md). Pure-DSP alternative (no plugin): [[warm-drum-bus]]
+ `[L] saturate-loop` + `[L] apply-eq`. Defer to the skill; report Mic/Line + drive, EQ moves, before→after
crest/centroid/tilt, and the preset/`.state` path.
