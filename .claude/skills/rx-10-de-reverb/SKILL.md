---
name: rx-10-de-reverb
description: "Use when running the RX 10 De-reverb for ambience / room-tail reduction — 'de-reverb this', 'remove the room/reverb tail', 'dry up this recording', 'tighten the roomy drums/spill'. The measured, plugin-specific deep-dive of [[vst-chain]] (RX repair). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: room-tail|spill|tighten|gentle]
---

# rx-10-de-reverb — drive the RX 10 De-reverb (measured)

The plugin-specific, measured workflow for **RX 10 De-reverb** (`RX 10 De-reverb.vst3`) — iZotope's **de-reverb /
ambience reducer**, repurposed from the offline RX repair suite as a real-time insert. It estimates the
reverberant tail and suppresses it per-band, drying up a roomy capture or a spill-laden close mic. The de-spill
twin is [[bleed-gate]] (gate / least-squares cancel a correlated source). Full field guide — render verdicts, the
param surface, the niche siblings — [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md). This skill is the
workflow.

## The governing facts (read first)

1. **Renders headless here.** `RX 10 De-reverb.vst3` loads + processes offline through `[L] apply-vst-chain`
   (authorized on this rig; re-verify elsewhere with [[vst-verify]]). It **processes at its default**
   (`reduction=10`, the four `band_strength_*=6` already engage) — a bare load is *not* a passthrough.
2. **Modest on a dryish bus — strong on roomy/spill material.** On an 8 s 48 kHz stereo **drum-bus** clip (crest
   15.6, centroid 3101) that's already fairly dry, `reduction=16` measured **low band −0.8 dB**, rms −0.6, crest
   **+0.6** (the tail-removal tightens). The win is on a **roomy room mic, a wet vocal, a spill-laden close mic**;
   on a dry bus the small delta is the proof-of-engagement, not the use case.
3. **Params are enums (numeric + string).** `[L] apply-vst-chain`'s float dict sets the **numeric** ones
   (`tail_length` 0.5–4, `reduction` −10…+20, `band_strength_low` / `_low_mid` / `_high_mid` / `_high` 0–10,
   `artifact_smoothing` 0–10); the **bools** (`enhance_dry_signal`, `output_reverb_only`) need the **[[vst-preset]]**
   harness or a dumped `.state`. (This module has no string algorithm enum.)
4. **⚠ The adaptive tail-profile capture wants the GUI.** Headless it uses the default adaptive estimate; for a
   precise room print, learn it in the RX standalone and bounce. The manual `reduction` / `band_strength_*` /
   `tail_length` controls all render fine headless.
5. **Meters own it** (Gemini hears ~16 kbps mono): verify with `[L] measure-loudness` (crest up + rms down = tail
   removed/tightened) and `[L] measure-spectrum`. Hear the residual via `output_reverb_only`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). All pure DSP, no key.
- **`RX 10 De-reverb.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"De-reverb"}`, take the **VST3**
  path. Screen a new install: `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "RX 10 De-reverb"`
  (expect `RENDERS ✓`). **Loads ≠ renders** — measure detail after.
- **Enum gotcha:** the float dict sets `reduction`/`tail_length`/`band_strength_*`/`artifact_smoothing`; the
  `enhance_dry_signal` / `output_reverb_only` bools need the **[[vst-preset]]** harness.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (note crest + rms — the tail-removal reference) + `[L] measure-spectrum`.
2. **Set the tail** — `tail_length` to the room's decay (short for a tight room, longer for a big hall). Start
   `reduction=10` (default) and raise toward `~16` for a wet source.
3. **Shape per band** — the four `band_strength_*` (low / low-mid / high-mid / high) target the tail where it
   lives — drop `band_strength_high` if you only need to dry the boomy room, raise `_low` to kill a low rumble
   tail. `artifact_smoothing` higher = fewer artifacts, less aggressive.
4. **Hear the residual** — `output_reverb_only=True` ([[vst-preset]]) to confirm you're removing the tail, not the
   dry hits. `enhance_dry_signal` can lift the recovered direct sound.
5. **Bounce + prove** — render via `apply-vst-chain` (or [[vst-preset]] for the bools). Re-`measure-loudness`:
   **crest should rise / rms drop** as the tail comes off. A/B loudness-matched (`[L] render-ab` / [[level-match]]).
   `dump_state=true` once dialed.
6. **QC** — over-reduction makes it sound thin/swirly/underwater; back off `reduction` or raise
   `artifact_smoothing`. Corrective insert, not a master — hand to [[master-track]].

## Move table

| Goal | De-reverb move |
|---|---|
| **Dry up a roomy capture / room mic** ★ | `reduction≈16`, `tail_length` to the decay — measured (drum bus): **low −0.8 dB**, rms −0.6, crest **+0.6** (tightens; modest on a dry bus, strong on roomy material). |
| **Tame a wet vocal tail** | `reduction 10–16`, bias `band_strength_high_mid`/`_high` to the sibilant-tail region. |
| **Tighten spill on a close mic** | moderate `reduction`, short `tail_length` — but for inter-mic spill the twin [[bleed-gate]] is often cleaner (gate/cancel a correlated source). |
| **Gentle ambience trim** | `reduction 4–8`, high `artifact_smoothing` — preserve natural space. |
| **Hear what's removed** | `output_reverb_only=True` ([[vst-preset]]) — only the tail should play. |

★ on a dry bus the change is small *by design* — the win is on roomy/spill-laden material. Cite the measured
proof-of-engagement, then say plainly this is an ambience tool, not a tone shaper.

## Outputs

- De-reverbed file → `projects/<track>/mix/<stem>_rxdrv.wav` (+ `presets/vst/rx-de-reverb-*.json` / `.state`).

## Reporting to the user

State the moves (`reduction`, `tail_length`, which `band_strength_*`), the before→after **crest + rms deltas** (the
tail-removal proof), that it ran headless, and the preset/`.state` path. A/B loudness-matched. On dry material, say
plainly the small change is expected — this earns its keep on roomy captures.

## Pitfalls

- **Over-reduction sounds underwater/swirly** — too much `reduction` strips natural space and adds artifacts; back
  off or raise `artifact_smoothing`.
- **Inter-mic SPILL is often a bleed-gate job, not de-reverb** — to cancel the hi-hat out of the overheads or gate
  a close mic between hits, reach for [[bleed-gate]] first; de-reverb is for the room *tail*.
- **Adaptive tail capture is GUI-leaning** — headless uses the default estimate; for a precise room print, learn
  in the RX standalone and bounce. Manual controls render fine.
- **Don't drive the bools via the float dict** — `enhance_dry_signal`/`output_reverb_only` need [[vst-preset]].
- **De-plosive / Breath Control are separate RX modules** for plosives/breaths (render headless but no dedicated
  skill — drive like this one; see the doc).

## Related

- [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md) — the full RX 10 field guide (per-module render verdicts)
- [[bleed-gate]] — the de-spill twin (gate / least-squares cancel a correlated source; local DSP)
- [[rx-10-voice-de-noise]] · [[rx-10-spectral-de-noise]] · [[rx-10-de-click]] · [[rx-10-de-ess]] ·
  [[rx-10-de-hum]] (DAW-only sibling)
- [[vst-chain]] — the generic headless VST workflow this specializes · [[vst-preset]] — set the bools / flatten ·
  [[vst-verify]] — prove the build renders · [[vst]] — index/doctrine
- [[mix-check]] · [[master-track]] (loudness stage) · [[gemini-audio-understanding]] — why meters own the read
