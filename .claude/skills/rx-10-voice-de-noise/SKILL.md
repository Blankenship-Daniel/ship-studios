---
name: rx-10-voice-de-noise
description: "Use when running the RX 10 Voice De-noise for broadband noise removal — 'de-noise this', 'remove the hiss/rumble/room tone', 'clean up the background noise'. The measured, plugin-specific deep-dive of [[vst-chain]] (RX repair). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: hiss|rumble|broadband-noise|gentle]
---

# rx-10-voice-de-noise — drive the RX 10 Voice De-noise (measured)

The plugin-specific, measured workflow for **RX 10 Voice De-noise** (`RX 10 Voice De-noise.vst3`) — iZotope's
**broadband adaptive de-noiser**, repurposed from the offline RX repair suite as a real-time insert. Its job is
to peel continuous **rumble / hiss / room tone** off a signal without an explicit noise profile. The pure-DSP
twin is `[L] clean-loop` (DC/HPF/denoise/gate). Full field guide — the per-module render verdicts, the param
surface, and the niche siblings — [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md). This skill is the
workflow.

## The governing facts (read first)

1. **Renders headless here.** `RX 10 Voice De-noise.vst3` loads + processes offline through `[L]
   apply-vst-chain` (authorized on this rig; re-verify elsewhere with [[vst-verify]]). RX is iZotope's
   **offline-repair** suite repurposed as a real-time insert — it **processes at its default** (`reduction=12`,
   `adaptive_mode=True` already engage), so a bare load is *not* a passthrough.
2. **The numbers are modest on clean material.** On an 8 s 48 kHz stereo **drum-bus** clip (crest 15.6, centroid
   3101), `optimize_for='Music'` + `reduction=18` + `master_threshold=3` measured **low band −1.3 dB**, rms −1.2,
   crest +0.7, centroid +171 — it removed broadband rumble/hiss with a tiny touch-up. **This tool shines on
   NOISY/roomy/hissy problem material** (preamp hiss, AC hum bed, room tone), not as a tone shaper on a clean
   bus; the small deltas above are the proof-of-engagement, not the use case.
3. **Params are enums (numeric + string).** `[L] apply-vst-chain`'s float dict sets the **numeric** ones
   (`threshold_1..6`, `master_threshold`, `reduction`, `input_gain_db`, `output_gain_db`); the **string** enums
   (`optimize_for` `'Dialogue'`/`'Music'`, `filter_type` `'Surgical'`/`'Gentle'`) and the `adaptive_mode` bool
   need the **[[vst-preset]]** harness (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
4. **Adaptive mode works headless — but "Learn" does not.** `adaptive_mode=True` (the default) tracks the noise
   floor continuously and renders fine. RX's **GUI noise-profile "Learn"** (capturing a specific noise print from
   a silent region) is **GUI-only** — headless it falls back to the default adaptive profile.
5. **Meters own it** (Gemini hears ~16 kbps mono): verify with `[L] measure-spectrum` (did the low/HF noise band
   drop without dulling the source?) and `[L] measure-loudness`. Hear the residual via `output_*_only` to dial it.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). All pure DSP, no
  API key.
- **`RX 10 Voice De-noise.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"Voice De-noise"}` and take
  the **VST3** path. Screen a new install with `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py
  "RX 10 Voice De-noise"` (expect `RENDERS ✓`). **Loads ≠ renders** — always measure detail after.
- **Enum gotcha:** `apply-vst-chain`'s `parameters` is float-only — fine for `reduction` / `master_threshold` /
  `threshold_*` / gains, but to set `optimize_for`/`filter_type`/`adaptive_mode` use the **[[vst-preset]]** harness.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness`. The
   "before" column. Note the noise band (LF rumble, HF hiss).
2. **Set the character** — for music/instruments use `optimize_for='Music'` (preserves musical content;
   `'Dialogue'` is voice-tuned and can scoop instruments). `filter_type='Gentle'` for fewer artifacts on
   musical sources, `'Surgical'` only when the noise is dense.
3. **Dial the amount** — start `reduction=12` (default) and raise toward `~18` on noisy material; `master_threshold`
   sets how far above the floor counts as signal (+3 leaves a touch more noise but fewer artifacts; lower = more
   aggressive). The six `threshold_1..6` are per-band offsets if one band needs more — leave at −70 otherwise.
4. **Hear the residual** — set `output_noise_only` analog (RX exposes a monitor on each module) to confirm you're
   removing noise, not source. Then bounce the real pass via `apply-vst-chain` (or the [[vst-preset]] harness for
   the string enums). Set `dump_state=true` once dialed for a byte-stable re-render.
5. **Prove it** — re-`measure-spectrum`/`measure-loudness`. The noise band should drop while the source band-ratios
   hold (a 0.00 spectrum delta = passthrough). A/B loudness-matched (`[L] render-ab` / [[level-match]]).
6. **QC** — over-reduction thins/swirls the source (warble artifacts); back off `reduction` or raise
   `master_threshold`. It's a corrective insert, not a master — hand off to [[master-track]] for loudness.

## Move table

| Goal | Voice De-noise move |
|---|---|
| **Broadband noise on a bus/instrument** ★ | `optimize_for='Music'`, `filter_type='Gentle'`, `reduction≈18`, `master_threshold≈+3`. ★ measured (drum bus): **low band −1.3 dB**, rms −1.2, crest +0.7, centroid +171 — modest on a clean bus, strong on noisy captures. |
| **Voice / dialogue hiss** | `optimize_for='Dialogue'`, `reduction 8–14`, `filter_type='Surgical'` if dense. |
| **Gentle clean-up (preserve air)** | `reduction 4–8`, `master_threshold +3…+6` — light touch so cymbals/air survive. |
| **One band too noisy (e.g. LF rumble)** | raise that band's `threshold_N` toward the floor; or pair an HPF (`[L] apply-eq`). |
| **Hear what's removed** | `output_noise_only=True` ([[vst-preset]]) — dial reduction until only noise plays. |

★ on the clean test bus the deltas are small *by design* — the win is on roomy/hissy material. Cite the measured
proof-of-engagement, then say plainly this is a noise tool, not a tone shaper.

## Outputs

- De-noised file → `projects/<track>/mix/<stem>_rxvdn.wav` (+ the reusable `presets/vst/rx-voice-denoise-*.json`
  and `.state` if dumped).

## Reporting to the user

State the moves (`optimize_for`, `filter_type`, `reduction`, `master_threshold`), the before→after **noise-band /
centroid / loudness deltas**, that it ran headless, and the preset/`.state` path. A/B loudness-matched. Say
plainly that on clean source the change is small — this earns its keep on noisy captures.

## Pitfalls

- **It's a noise tool, not an EQ** — don't reach for it to make a clean bus "warmer"; the deltas are tiny there.
  Use [[mix-check]] → an EQ move for tone.
- **"Learn" / noise-profile capture is GUI-only** — headless it uses the default adaptive profile; for a specific
  hum/noise print, dial it in the RX standalone/DAW and bounce.
- **Over-reduction swirls** — too much `reduction` adds warble/musical-noise artifacts; back off or raise
  `master_threshold`.
- **`optimize_for='Dialogue'` on instruments scoops mids** — use `'Music'` for non-voice material.
- **Don't drive the string enums via the float dict** — `optimize_for`/`filter_type`/`adaptive_mode` need
  [[vst-preset]] or a `.state` blob.
- **Spectral De-noise is the FFT-subtraction cousin** for surgical hum/buzz ([[rx-10-spectral-de-noise]]) — but it
  **nukes musical highs at high settings**; for a broadband floor, this Voice De-noise is the gentler tool.

## Related

- [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md) — the full RX 10 field guide (per-module render verdicts)
- `[L] clean-loop` — the pure-DSP twin (DC/HPF/denoise/gate, deterministic, no plugin)
- [[rx-10-spectral-de-noise]] — surgical FFT spectral subtraction · [[rx-10-de-click]] · [[rx-10-de-ess]] ·
  [[rx-10-de-reverb]] · [[rx-10-de-hum]] (DAW-only sibling)
- [[vst-chain]] — the generic headless VST workflow this specializes · [[vst-preset]] — set the string enums /
  flatten · [[vst-verify]] — prove the build renders · [[vst]] — index/doctrine
- [[mix-check]] (find the problem first) · [[master-track]] (loudness stage) ·
  [[gemini-audio-understanding]] — why meters (not Gemini) own the spectrum read
