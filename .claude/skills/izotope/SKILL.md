---
name: izotope
description: "Use when the user wants to use their iZotope plugins in the pipeline or asks which iZotope skill applies — 'iZotope', 'Ozone', 'Neutron', 'RX', 'Nectar', 'Neoverb', 'use my iZotope plugins', 'which iZotope renders here'. The index + render-verdict map for the installed iZotope suite; routes to the per-module deep-dives and the [[vst]] categories. Reference, not a pipeline — it points at the skills + the headless-render reality. Stemmy MCP, the `vst` extra."
argument-hint: [what you want to do — e.g. Neutron EQ, RX de-noise, Ozone master]
---

# izotope — the iZotope plugin map (index + render verdicts)

You have the full **iZotope** line installed (Ozone 11 + 10, Neutron 4, RX 10 + 8, Nectar 3, Neoverb,
Relay, Tonal Balance Control 2). This skill is the map: which modules actually **render in the headless
pipeline** (`[L] apply-vst-chain`, Pedalboard, offline) versus which are **DAW-only**, and where to route.
Each verdict below was **probe + measure verified on this Mac** — not assumed. Sub-map under [[vst]].

## The governing reality (read first)

1. **iZotope is NI/iLok-licensed → most of it is gated headless.** Verdicts here are this rig's truth; **re-verify
   elsewhere** with [[vst-verify]]. The two failure modes that matter: a module that **hangs on authorization**
   (Ozone 11) and a module that **loads + responds to *output gain* but its actual DSP is inert** (Neutron
   Compressor/Gate, Ozone Equalizer) — a naive load/param probe **false-reports "RENDERS"** for both. Trust the
   *measured detail* (spectrum/crest moved), not `changed:true`.
2. **Every iZotope param is an enum** (numeric + string). `[L] apply-vst-chain`'s float dict sets the **numeric**
   enums (gains, thresholds, drive); **string/bool** enums (shapes, modes, targets, module bypass) need the
   **[[vst-preset]]** harness (`apply_vst_preset.py` setattr) or a dumped `.state`.
3. **The AI "Assistants" are GUI-only** — Ozone Master Assistant, Neutron Track/Mix Assistant, Nectar Vocal
   Assistant, Neoverb Reverb Assistant, RX Repair Assistant won't run headless. You drive the **manual DSP**.
4. **Meters own tone/loudness/peak/stereo** (Gemini hears 16 kbps mono): bracket every move with
   `[L] measure-spectrum` / `measure-loudness` / `measure-stereo`.

## Neutron 4 — the mixing suite (the strongest iZotope set here)

The whole tone/transient/exciter side **renders + engages headless**; the dynamics side does not.

| Module | Verdict | Skill / route |
|---|---|---|
| Equalizer | ✅ renders & engages (12-band static/dynamic, M/S width) | [[neutron-4-equalizer]] |
| Transient Shaper | ✅ renders & engages (3-band attack/sustain) | [[neutron-4-transient-shaper]] |
| Sculptor | ✅ renders & engages (target-based spectral leveler) | [[neutron-4-sculptor]] |
| Exciter | ✅ renders & engages (3-band harmonic) | [[neutron-4-exciter]] |
| Compressor / Gate | ⚠ render but **dynamics inert headless** (0 dB GR at threshold −45/ratio 10) | [[vst-compress]] / [[multiband-compress]] / [[fabfilter-pro-mb]] |
| Unmask | ⚠ needs a **companion Neutron instance**'s sidechain → no-op single-instance | [[unmask-stems]] (pure DSP) |
| Visual Mixer | 📊 metering only, no audio | the repo's meters / [[mix-balance]] |

Full surface: [`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md).

## RX 10 — the repair suite (most of it renders, directly useful for hum/hiss/bleed/clicks)

| Module | Verdict | Skill / route |
|---|---|---|
| Voice De-noise | ✅ broadband adaptive de-noise | [[rx-10-voice-de-noise]] |
| Spectral De-noise | ✅ FFT subtraction (⚠ nukes HF on music — use gently) | [[rx-10-spectral-de-noise]] |
| De-click | ✅ declicker (⚠ transient-safe only at low sensitivity) | [[rx-10-de-click]] |
| De-ess | ✅ split/spectral de-esser | [[rx-10-de-ess]] |
| De-reverb | ✅ ambience/tail reduction | [[rx-10-de-reverb]] |
| De-crackle · De-clip · De-plosive · Mouth De-click · Breath Control · Guitar De-noise | ✅ render (niche) — drive like their siblings, no dedicated skill | [[vst-chain]] |
| **De-hum** | ⚠ **renders PASSTHROUGH** (Δ=0 across 6 params — self-bypasses) → DAW-only | [[rx-10-de-hum]] |
| Repair Assistant · Monitor · Connect | 🚫 AI-learn / metering / bridge — no headless audio | DAW / the repo's meters |

Full surface: [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md).

## Ozone 11 — the mastering suite (⚠ ALL DAW-only here)

Every Ozone 11 module is unusable in the headless pipeline on this rig: Maximizer / Dynamics / Imager / Match EQ /
Vintage* / Stabilizer / Low End Focus / Spectral Shaper / Impact / Master Rebalance / Clarity **hang on iLok**;
the **Equalizer loads but its EQ does not engage** (only the locked output gain responds → false "RENDERS").
Reach for the DAW-only deep-dive (dial → bounce → measure) and use the headless substitute in the pipeline:

| Module | Substitute (renders headless) | Skill |
|---|---|---|
| Maximizer (IRC limiter) | [[fabfilter-pro-l-2]] / pure-DSP [[master-track]] | [[ozone-11-maximizer]] |
| Equalizer | [[fabfilter-pro-q-4]] / `[L] apply-eq` / [[de-harsh]] | [[ozone-11-equalizer]] |
| Imager | `[L] adjust-stereo` (bass mono + M/S width) | [[ozone-11-imager]] |
| Match EQ | [[reference-match]] / [[house-curve]] | [[ozone-11-match-eq]] |
| Dynamics / Vintage Comp | [[vst-compress]] · Vintage Tape → [[studer-a800]] · Dynamic EQ → [[dynamic-eq]] | (DAW-only — see doc) |

Full surface + per-module substitutes: [`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md). (Ozone 10 is the same story — older twin.)

## Nectar 3 · Neoverb (both render & engage)

- **Nectar 3** — all-in-one **vocal** channel strip (gate/comp/de-ess/EQ/saturation/reverb…); drive it on an
  isolated vocal → [[nectar-3]] ([[vst-channel-strip]]). [`docs/vst/izotope-nectar.md`](../../../docs/vst/izotope-nectar.md).
- **Neoverb** — AI-assisted 3-engine **reverb** (manual engines render; ⚠ wide → check mono-sum) → [[neoverb]]
  ([[vst-reverb]]). [`docs/vst/izotope-neoverb.md`](../../../docs/vst/izotope-neoverb.md).

## Metering / utility — no audio change (use the repo's own meters instead)

**Tonal Balance Control 2**, **Neutron 4 Visual Mixer**, **RX 10 Monitor**, **Relay** are analyzers/utilities —
they produce no processed audio, so they don't belong in `apply-vst-chain`. Headless, the pipeline's pure-DSP
meters replace them: `[L] measure-spectrum` (tonal balance), `measure-loudness`, `measure-stereo`, plus
[[understand-audio]] / [[mix-check]] for the read.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). Plugins must be
  installed **and authorized**; the AI assistants need the GUI. Always [[vst-verify]] before trusting a render.

## Related

- [[vst]] — the VST suite index/doctrine · [[vst-chain]] — the headless render backbone · [[vst-preset]] — enum/state harness · [[vst-verify]] — prove render-vs-inert
- [[vst-eq]] / [[vst-compress]] / [[vst-saturate]] / [[vst-reverb]] / [[vst-de-ess]] / [[vst-channel-strip]] / [[vst-master]] — the task categories the iZotope deep-dives slot into
- [[mix-check]] / [[master-track]] / [[stem-process]] — the pure-DSP pipeline these inserts plug into · [[gemini-audio-understanding]] — why meters (not Gemini) own the tonal read
