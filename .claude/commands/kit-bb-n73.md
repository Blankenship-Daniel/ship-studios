---
description: Dial the KIT Plugins BB N73 (Blackbird Neve 1073) for warm/weighty classic-1073 tone — measured.
argument-hint: <audio.wav> [goal: warm-bus/weight/de-box/air/glue]
---

Invoke the **kit-bb-n73** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (warm drum bus / low weight / de-box / Neve air / bus glue). The
skill applies the KIT **BB N73** (`KIT BB N73.vst3`) — a Blackbird **Neve 1073** channel strip, the classic
3-band 1073 sibling of the 4-band [[kit-bb-n105]] (31105) and the warm counterpart to the punchy API
[[kit-bb-a5]] / [[api-vision-channel-strip]]. Warmth + low-end weight come from the **Mic-mode transformer
drive** (`pre_amp_mode="Mic"` + **`pre_amp_saturation=true` (mandatory)**, sensitivity −45…−50 moderate,
toward −80 for more) — **not** from an EQ air boost; the 1073 EQ only tightens + weights (HPF ~50 Hz, low
shelf +3 @60 weight, mid −2 @700 de-box). Applies via the [[vst-preset]] harness and **measures
crest/centroid/tilt + low & low-mid ratios before & after** (warm-weighty = low weight up, de-boxed, centroid
stays dark, crest preserved).

**Governing facts (measured):** it's a **1073 → 3 EQ bands only** (FIXED 12 kHz HF shelf, sweepable mid bell
360–7.2k, low shelf 35–220, HPF 50–300; **no low-mid, no LPF, no Hi-Q**; all bands **±18 dB**). The Neve color
is **MIC-MODE ONLY** — in Line mode `pre_amp_sensitivity`/`pre_amp_saturation` are **inert**; in Mic,
**saturation ON = controlled soft drive, OFF + driven = raw clip** (23–46 % THD). **No host Auto-Gain**
(GUI-only) → compensate Mic drive with `output_gain`. **`master_bus_toggle` IS host-exposed** (MST On = subtle
glue), unlike the N105. **Every param is an enum**: gains/trims accept a float (reach via `apply-vst-chain`),
but **freq/mode/eq/phase/hum/master-buss are string/bool enums → preset harness**. analog hum negligible
offline. **N73 ≠ N105.** iLok/PACE — **verified-headless on this rig** (`probe_plugin.py "N73"` → `RENDERS ✓`);
re-verify elsewhere. Needs `uv sync --extra vst`.

Ready preset: `presets/vst/bb-n73-warm-drum-bus.json`. Full param surface + isolation numbers:
[`docs/vst/kit-bb-n73.md`](../../docs/vst/kit-bb-n73.md). Pure-DSP alternative (no plugin): [[warm-drum-bus]]
+ `[L] saturate-loop` + `[L] apply-eq`. Defer to the skill; report Mic/Line + saturation + drive, EQ moves,
before→after crest/centroid/tilt, and the preset/`.state` path.
