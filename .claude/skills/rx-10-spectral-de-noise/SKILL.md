---
name: rx-10-spectral-de-noise
description: "Use when running the RX 10 Spectral De-noise for surgical FFT noise subtraction — 'remove this specific hiss/buzz/whine', 'spectral de-noise', 'subtract the noise floor', 'kill the tonal whine'. The measured, plugin-specific deep-dive of [[vst-chain]] (RX repair). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: hiss|buzz|tonal-whine|gentle]
---

# rx-10-spectral-de-noise — drive the RX 10 Spectral De-noise (measured)

The plugin-specific, measured workflow for **RX 10 Spectral De-noise** (`RX 10 Spectral De-noise.vst3`) —
iZotope's **FFT spectral-subtraction** de-noiser (separate noise vs tonal paths, the surgical sibling of the
broadband [[rx-10-voice-de-noise]]). It estimates a spectral noise profile and subtracts it bin-by-bin — superb
on **hiss, buzz, a tonal whine, an AC bed** on problem material. The pure-DSP twin is `[L] clean-loop`. Full field
guide — render verdicts, the param surface, the niche siblings — [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md).
This skill is the workflow.

## The governing facts (read first)

1. **Renders headless here.** `RX 10 Spectral De-noise.vst3` loads + processes offline through `[L]
   apply-vst-chain` (authorized on this rig; re-verify elsewhere with [[vst-verify]]). It **processes at its
   default** (`noise_reduction_db=12`, `quality='Simple'` already engage) — a bare load is *not* a passthrough.
2. **⚠ HEADLINE GOTCHA — at high settings on music it NUKES the highs.** On an 8 s 48 kHz stereo **drum-bus** clip
   (crest 15.6, centroid 3101), `noise_reduction_db=24` + `quality='Advanced'` measured **2–6 kHz −16 dB, >6 kHz
   −17.5 dB, centroid 3101→849 (−2252 Hz)** — it treated **cymbals as "noise"** and gutted them. On music use
   **4–10 dB GENTLY**; this is a surgical hiss/buzz tool for problem material, **not a tone shaper**. Reserve the
   aggressive settings for a near-silent/noisy capture, never a full mix.
3. **Params are enums (numeric + string).** `[L] apply-vst-chain`'s float dict sets the **numeric** ones
   (`noise_reduction_db` / `tonal_reduction_db` / `linked_reduction_db` 0–40, `noise_threshold_db` /
   `tonal_threshold_db` −6…+6, `artifact_control`, `release_ms`, `smoothing`, `whitening`, gains); the **string**
   enum `quality` (`'Simple'`/`'Advanced'`/`'Extreme'`/`'Adv.+Extr.'`), `fft_size`, and the bools
   (`output_noise_only`, `adaptive_learning`, `link_*`) need the **[[vst-preset]]** harness or a dumped `.state`.
4. **⚠ `adaptive_learning` needs the GUI** to capture a noise profile from a silent region — headless it falls
   back to a default profile. Drive the reduction/threshold manually instead, or learn it in the RX standalone and
   bounce.
5. **Meters own it** (Gemini hears ~16 kbps mono): verify with `[L] measure-spectrum` (watch centroid — a big
   drop means you ate the highs) and `[L] measure-loudness`. Hear the residual via `output_noise_only`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). All pure DSP, no key.
- **`RX 10 Spectral De-noise.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"Spectral De-noise"}`,
  take the **VST3** path. Screen a new install: `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py
  "RX 10 Spectral De-noise"` (expect `RENDERS ✓`). **Loads ≠ renders** — measure detail after.
- **Enum gotcha:** the float dict can set `noise_reduction_db`/thresholds/`artifact_control`, but `quality`,
  `fft_size`, and the bools need the **[[vst-preset]]** harness.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (centroid + HF bands) + `[L] measure-loudness`. Record the centroid; it's
   your over-reduction alarm.
2. **Start gentle** — `noise_reduction_db=4…10`, `quality='Advanced'`, `artifact_control≈7` (default). Keep
   `link_reduction`/`link_threshold` so noise+tonal track together unless you're chasing a specific tonal whine.
3. **Tune the threshold** — `noise_threshold_db` shifts what counts as noise vs signal (+ leaves more source, −
   removes more). Move it before you crank reduction.
4. **Hear the residual** — `output_noise_only=True` ([[vst-preset]]) and confirm only noise plays, **not cymbals/
   air**. If music bleeds into the "noise", lower `noise_reduction_db`.
5. **Bounce + prove** — render via `apply-vst-chain` (or [[vst-preset]] for `quality`/bools). Re-`measure-spectrum`:
   centroid should barely move on a gentle pass; a big drop means you over-reduced. A/B loudness-matched (`[L]
   render-ab` / [[level-match]]). `dump_state=true` once dialed.
6. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch a dull/thin result; cross-check any "dark" flag
   against the centroid ([[gemini-audio-understanding]]). Corrective insert, not a master — hand to [[master-track]].

## Move table

| Goal | Spectral De-noise move |
|---|---|
| **Gentle hiss on music** ★ | `noise_reduction_db 4–10`, `quality='Advanced'`, `artifact_control≈7`, watch centroid. |
| **Surgical buzz / tonal whine** | `tonal_reduction_db` up (unlink first), `noise_reduction_db` low — subtract the tone, spare broadband. |
| **Heavy noise on a near-silent capture** | `noise_reduction_db 18–30`, `quality='Extreme'`/`'Adv.+Extr.'` — ONLY on noisy material, never a full mix. |
| **⚠ Over-reduction proof** ★ | `noise_reduction_db=24`/`quality='Advanced'` on the drum bus measured **2–6 kHz −16 dB, >6 kHz −17.5 dB, centroid −2252 Hz** — it ate the cymbals. Don't do this to music. |
| **Hear what's removed** | `output_noise_only=True` ([[vst-preset]]) — if cymbals play, back off. |

★ on clean/music material keep it gentle (4–10 dB); the aggressive row is the cautionary measurement, not a recipe.

## Outputs

- De-noised file → `projects/<track>/mix/<stem>_rxsdn.wav` (+ `presets/vst/rx-spectral-denoise-*.json` / `.state`).

## Reporting to the user

State the moves (`noise_reduction_db`, `quality`, threshold), the before→after **centroid + HF-band deltas** (the
over-reduction tell), that it ran headless, and the preset/`.state` path. A/B loudness-matched. If you went above
~10 dB on music, flag the centroid drop explicitly.

## Pitfalls

- **#1: it nukes musical highs at high reduction** — `≥~18 dB` on music guts cymbals/air (measured centroid
  −2252 Hz). Keep it 4–10 dB on music; reserve aggressive settings for problem material.
- **`adaptive_learning` is GUI-only** — no profile capture headless; drive reduction/threshold by hand or learn in
  the RX standalone and bounce.
- **`quality='Extreme'`/`'Adv.+Extr.'` is heavier, not cleaner on music** — more subtraction = more artifacts on a
  busy source.
- **Don't drive `quality`/`fft_size`/bools via the float dict** — use [[vst-preset]] or a `.state` blob.
- **It's a noise tool, not a de-harsher** — broadband harshness is [[de-harsh]], sibilance is [[rx-10-de-ess]] /
  [[de-ess]]; spectral subtraction on a "harsh" mix just dulls it.
- **Centroid is the alarm** — always measure it before/after; a big drop = you over-reduced.

## Related

- [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md) — the full RX 10 field guide (per-module render verdicts)
- `[L] clean-loop` — the pure-DSP twin (DC/HPF/denoise/gate, deterministic, no plugin)
- [[rx-10-voice-de-noise]] — the gentler broadband cousin · [[rx-10-de-click]] · [[rx-10-de-ess]] ·
  [[rx-10-de-reverb]] · [[rx-10-de-hum]] (DAW-only sibling)
- [[vst-chain]] — the generic headless VST workflow this specializes · [[vst-preset]] — set `quality`/bools /
  flatten · [[vst-verify]] — prove the build renders · [[vst]] — index/doctrine
- [[mix-check]] (find the problem first) · [[master-track]] (loudness stage) ·
  [[gemini-audio-understanding]] — why meters (not Gemini) own the spectrum read
