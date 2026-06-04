---
name: rx-10-de-ess
description: "Use when running the RX 10 De-ess for sibilance / harsh-HF control on a vocal or bright bus — 'de-ess this vocal', 'tame the esses', 'spectral de-ess', 'the cymbals/hi-hat spit'. The measured deep-dive of [[vst-de-ess]]. Stemmy MCP, the `vst` extra."
argument-hint: <vocal-or-bus.wav> [goal: classic|spectral|cymbal-spit]
---

# rx-10-de-ess — drive the RX 10 De-ess (measured)

The plugin-specific, measured workflow for **RX 10 De-ess** (`RX 10 De-ess.vst3`) — iZotope's **split-band /
spectral de-esser**, repurposed from the offline RX repair suite as a real-time insert. Two algorithms:
**Classic** (band-split GR) and **Spectral** (frequency-selective, shapes only the sibilant partials). The
pure-DSP twin is [[de-ess]] (native split-band, deterministic, no plugin). Full field guide — render verdicts,
the param surface, the niche siblings — [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md). This skill
is the workflow.

## The governing facts (read first)

1. **Renders headless here.** `RX 10 De-ess.vst3` loads + processes offline through `[L] apply-vst-chain`
   (authorized on this rig; re-verify elsewhere with [[vst-verify]]). It **processes at its default**
   (`algorithm='Classic De-ess'`, `threshold=-12`, `cutoff_freq=2500` already engage) — a bare load is *not* a
   passthrough.
2. **Modest on non-sibilant material — that's correct.** On a non-sibilant **full mix**, `algorithm='Spectral
   De-ess'` + `threshold=-28` + `cutoff_freq=6000` measured **>6 kHz −0.7 dB** — it ducks sibilant/cymbal HF only
   when it trips. The win is on a spitty vocal or a bright bus with real sibilance; on a clean mix the small delta
   is the proof-of-engagement, not the use case.
3. **Pair with `[G] find-sibilance` to set the band/threshold from the measurement.** `[G] find-sibilance` is on
   the gemini server but is **PURE DSP — no `GEMINI_API_KEY`, no network**. It returns the measured sibilant
   center Hz + threshold → feed `cutoff_freq` / `threshold` directly (same discipline as the pure-DSP [[de-ess]]).
4. **Params are enums (numeric + string).** `[L] apply-vst-chain`'s float dict sets the **numeric** ones
   (`threshold` −60…0, `cutoff_freq` 800–8000, `spectral_shaping` 0–100, `spectral_tilt` −100…+100); the **string**
   enum `algorithm` (`'Classic De-ess'`/`'Spectral De-ess'`), `speed` (`'Fast'`/`'Slow'`), and the bools
   (`output_ess_only`, `absolute_mode`) need the **[[vst-preset]]** harness or a dumped `.state`.
5. **Meters own it** (Gemini hears ~16 kbps mono): verify with `[L] measure-spectrum` (the >6 kHz / sibilant-band
   delta) — read the band, don't trust a mono "harsh" vibe. Hear the residual via `output_ess_only`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G] find-sibilance`
  (optional) is **pure DSP — no key**. All pure DSP, no API key.
- **`RX 10 De-ess.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"De-ess"}`, take the **VST3** path.
  Screen a new install: `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "RX 10 De-ess"` (expect
  `RENDERS ✓`). **Loads ≠ renders** — measure detail after.
- **Enum gotcha:** the float dict sets `threshold`/`cutoff_freq`/`spectral_*`; `algorithm`/`speed`/bools need the
  **[[vst-preset]]** harness.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum {path}`. Note the 4–9 kHz / sibilant region — the "before" column the
   de-ess delta is judged against.
2. **Locate the band** — `[G] find-sibilance {path}` (pure DSP, no key) → measured `center_hz` + `threshold`.
   Feed `cutoff_freq ≈ center_hz` (split below it) and set `threshold` so only the esses trip.
3. **Pick the algorithm** — `'Spectral De-ess'` shapes only the sibilant partials (more transparent, best on
   cymbal spit / harsh "sh"); `'Classic De-ess'` band-splits and ducks (simpler, fast vocals). `speed='Fast'`
   for quick esses, `'Slow'` for a smoother grab.
4. **Dial it** — start `threshold` from the measurement, `spectral_shaping ≈ 50` (Spectral). Hear the residual
   with `output_ess_only=True` ([[vst-preset]]) — only esses/spit should play, not whole words/cymbals.
5. **Bounce + prove** — render via `apply-vst-chain` (or [[vst-preset]] for `algorithm`/`speed`/bool).
   Re-`measure-spectrum`: the sibilant band drops, overall tilt barely moves. A/B loudness-matched (`[L]
   render-ab` / [[level-match]]). `dump_state=true` once dialed.
6. **QC** — over-ducking lisps the vocal / dulls cymbals; raise `threshold` or lower the GR. Corrective insert,
   not a master — hand to [[master-track]].

## Move table

| Goal | De-ess move |
|---|---|
| **Spitty vocal "ess"** | `algorithm='Spectral De-ess'`, `cutoff_freq` from `find-sibilance` (~6–8 kHz), `threshold` so only esses trip, `speed='Fast'`. |
| **Harsh "sh"/cymbal spit on a bright bus** ★ | `algorithm='Spectral De-ess'`, `threshold≈-28`, `cutoff_freq≈6000` — measured (full mix): **>6 kHz −0.7 dB** (ducks sibilant/cymbal HF; modest on a non-sibilant mix). |
| **Simple fast de-ess** | `algorithm='Classic De-ess'`, `cutoff_freq≈2500`, `threshold` to taste. |
| **Tilt the de-ess HF** | `spectral_tilt` biases the reduction higher/lower in the band (Spectral). |
| **Hear what's removed** | `output_ess_only=True` ([[vst-preset]]) — only esses/spit should play. |

★ on a non-sibilant mix the delta is small *by design* — the win is on a spitty source. Cite the measured
proof-of-engagement, then say plainly this is a sibilance tool, not a tone shaper.

## Outputs

- De-essed file → `projects/<track>/mix/<stem>_rxdes.wav` (+ `presets/vst/rx-de-ess-*.json` / `.state`).

## Reporting to the user

Lead with the **sibilant-band / >6 kHz delta** (the proof you ducked esses, not the whole top), state the
`algorithm` + `cutoff_freq` + `threshold`, that it ran headless, and the preset/`.state` path. A/B loudness-matched.

## Pitfalls

- **Over-ducking lisps the vocal / dulls cymbals** — raise `threshold` so only the esses trip; the pure-DSP
  [[de-ess]] has the same discipline.
- **A whole-top harshness isn't sibilance** — that's [[de-harsh]] (resonance suppression) or an EQ tilt, not
  de-essing.
- **Hi-hat "spit" may be a balance problem** — a too-loud overhead reads as sibilant; check levels with
  [[mix-balance]] first.
- **Don't drive `algorithm`/`speed`/bool via the float dict** — use [[vst-preset]] or a `.state` blob.
- **`find-sibilance` needs no key** — it's pure DSP; never imply a `GEMINI_API_KEY`.

## Related

- [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md) — the full RX 10 field guide (per-module render verdicts)
- [[de-ess]] — the pure-DSP twin (native split-band, deterministic, no plugin) · [[vst-de-ess]] — the generic
  headless de-esser workflow this specializes
- [[rx-10-voice-de-noise]] · [[rx-10-spectral-de-noise]] · [[rx-10-de-click]] · [[rx-10-de-reverb]] ·
  [[rx-10-de-hum]] (DAW-only sibling)
- [[vst-preset]] — set `algorithm`/`speed`/bool / flatten · [[vst-verify]] — prove the build renders ·
  [[vst]] — index/doctrine
- [[mix-check]] · [[master-track]] (loudness stage) · `[G] find-sibilance` (pure DSP, no key) — set the band ·
  [[gemini-audio-understanding]] — why meters (not Gemini) own the spectrum read
