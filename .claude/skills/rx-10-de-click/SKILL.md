---
name: rx-10-de-click
description: "Use when running the RX 10 De-click for click/pop/crackle removal — 'remove the clicks', 'de-click this vinyl/edit', 'fix the pops and crackle', 'clean up the mouth clicks'. The measured, plugin-specific deep-dive of [[vst-chain]] (RX repair). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: vinyl|edits|crackle|drums]
---

# rx-10-de-click — drive the RX 10 De-click (measured)

The plugin-specific, measured workflow for **RX 10 De-click** (`RX 10 De-click.vst3`) — iZotope's **declicker**,
which detects and interpolates transient clicks/pops/crackle (vinyl ticks, digital edits, mouth clicks, comb
zipper-noise). The pure-DSP twin is `[L] clean-loop` — but use `declick=false` on drums there, for the same reason
this skill's sensitivity must stay low on percussion. Full field guide — render verdicts, the param surface, the
niche siblings — [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md). This skill is the workflow.

## The governing facts (read first)

1. **Renders headless here.** `RX 10 De-click.vst3` loads + processes offline through `[L] apply-vst-chain`
   (authorized on this rig; re-verify elsewhere with [[vst-verify]]). It **processes at its default**
   (`sensitivity=3`, `algorithm='Single-band'` already engage) — a bare load is *not* a passthrough.
2. **It's subtle on click-free material — that's correct.** On an 8 s 48 kHz stereo **drum-bus** clip (crest
   15.6, centroid 3101) with no clicks, `sensitivity=7` measured **centroid −25, mid −0.4, crest +0.0** — it
   found nothing to fix and, importantly, **did NOT eat the transients** at sens 7. This tool earns its keep on
   **clicky problem material** (vinyl rip, glitchy edit, crackle); on clean audio the right result is "almost no
   change".
3. **Params are enums (numeric + string).** `[L] apply-vst-chain`'s float dict sets the **numeric** ones
   (`sensitivity` 0.5–10, `frequency_skew` −10…+10, `click_widening` 0–5); the **string** enum `algorithm`
   (`'Single-band'`/`'Multi-band (periodic clicks)'`/`'Multi-band (random clicks)'`/`'Low-latency'`) and the
   `output_clicks_only` bool need the **[[vst-preset]]** harness or a dumped `.state`.
4. **⚠ On percussion, raise sensitivity carefully — a declicker can mistake a sharp transient for a click.** That
   is exactly why the repo's pure-DSP `[L] clean-loop` runs `declick=false` on drum material. Sens 7 held our drum
   transients (crest +0.0), but push it higher and it will start interpolating snare/kick attacks. Use
   `output_clicks_only` to confirm you're removing clicks, not hits.
5. **Meters own it** (Gemini hears ~16 kbps mono): verify with `[L] measure-loudness` (**crest must not collapse**
   — that's the "ate my transients" alarm) and `[L] measure-spectrum`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). All pure DSP, no key.
- **`RX 10 De-click.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"De-click"}`, take the **VST3**
  path. Screen a new install: `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "RX 10 De-click"`
  (expect `RENDERS ✓`). **Loads ≠ renders** — measure detail after.
- **Enum gotcha:** the float dict sets `sensitivity`/`frequency_skew`/`click_widening`; `algorithm` and
  `output_clicks_only` need the **[[vst-preset]]** harness.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (note crest — the transient-safety reference) + `[L] measure-spectrum`.
2. **Pick the algorithm** — `'Single-band'` (default) for general clicks; `'Multi-band (random clicks)'` for vinyl
   crackle / dense random ticks; `'Multi-band (periodic clicks)'` for a regular zipper/buzz; `'Low-latency'` only
   when latency matters (lower quality).
3. **Dial sensitivity LOW first** — start `sensitivity=3` (default) and raise only until the clicks are gone.
   `frequency_skew` biases detection toward HF clicks (+) or LF thumps (−); `click_widening` extends each repair
   for fat clicks. **On drums, do NOT chase a high sensitivity** — it interpolates attacks.
4. **Confirm you're catching clicks, not source** — `output_clicks_only=True` ([[vst-preset]]); you should hear
   only ticks, not drum hits or words. If hits appear, lower `sensitivity`.
5. **Bounce + prove** — render via `apply-vst-chain` (or [[vst-preset]] for `algorithm`/bool). Re-`measure-loudness`:
   **crest should hold** (transients intact); the click energy is gone. A/B loudness-matched (`[L] render-ab` /
   [[level-match]]). `dump_state=true` once dialed.
6. **QC** — listen for dulled attacks / lisping. Corrective insert, not a master — hand to [[master-track]].

## Move table

| Goal | De-click move |
|---|---|
| **General clicks / digital edits** | `algorithm='Single-band'`, `sensitivity 3–5`. |
| **Vinyl crackle / dense ticks** | `algorithm='Multi-band (random clicks)'`, `sensitivity 4–6`. |
| **Periodic zipper / buzz** | `algorithm='Multi-band (periodic clicks)'`, `sensitivity` to taste. |
| **Drums / percussion (transient-safe)** ★ | keep `sensitivity ≤ ~7` — measured: at sens 7 on the drum bus **crest +0.0** (transients held). Higher will eat attacks (why `[L] clean-loop` uses `declick=false` on drums). |
| **Fat clicks** | raise `click_widening` 1–3; bias HF with `frequency_skew` +. |
| **Hear what's removed** | `output_clicks_only=True` ([[vst-preset]]) — only ticks should play. |

★ subtle on click-free material is the correct result; the proof is crest holding, not a big spectral delta.

## Outputs

- De-clicked file → `projects/<track>/mix/<stem>_rxdck.wav` (+ `presets/vst/rx-declick-*.json` / `.state`).

## Reporting to the user

State the `algorithm` + `sensitivity`, the before→after **crest** (the transient-safety proof) and any click-energy
reduction, that it ran headless, and the preset/`.state` path. A/B loudness-matched. On clean material, say plainly
the small change is expected — this is a problem-material tool.

## Pitfalls

- **#1: high sensitivity eats transients** — a declicker can mistake a snare/kick attack for a click. Keep
  `sensitivity` low on percussion (the repo's `[L] clean-loop` uses `declick=false` on drums for this reason); watch
  crest.
- **Wrong algorithm wastes effort** — vinyl crackle wants `'Multi-band (random clicks)'`, not `'Single-band'`.
- **Don't drive `algorithm`/bool via the float dict** — use [[vst-preset]] or a `.state` blob.
- **It's a click tool, not a de-noiser** — continuous hiss/rumble is [[rx-10-voice-de-noise]] /
  [[rx-10-spectral-de-noise]]; declicking won't touch a noise floor.
- **De-crackle / Mouth De-click are separate RX modules** for those specific jobs (render headless but no
  dedicated skill — drive like this one; see the doc).

## Related

- [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md) — the full RX 10 field guide (per-module render verdicts)
- `[L] clean-loop` — the pure-DSP twin (DC/HPF/declick/denoise/gate; `declick=false` on drums) ·
- [[rx-10-voice-de-noise]] · [[rx-10-spectral-de-noise]] · [[rx-10-de-ess]] · [[rx-10-de-reverb]] ·
  [[rx-10-de-hum]] (DAW-only sibling)
- [[vst-chain]] — the generic headless VST workflow this specializes · [[vst-preset]] — set `algorithm`/bool /
  flatten · [[vst-verify]] — prove the build renders · [[vst]] — index/doctrine
- [[mix-check]] · [[master-track]] (loudness stage) · [[gemini-audio-understanding]] — why meters own the read
