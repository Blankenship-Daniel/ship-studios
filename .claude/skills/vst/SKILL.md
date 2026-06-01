---
name: vst
description: "Use when the user wants to use their own VST3/AU plugins in the pipeline or asks which VST skill applies — 'use my plugins', 'run a VST chain', 'add a real compressor/EQ/reverb plugin', 'what VST skills are there', 'can I use Pultec/SSL/FabFilter here'. The index + doctrine for the VST suite; routes to the per-task vst-* skills. Reference, not a pipeline — it points at the skills and the headless-safe inventory. Stemmy MCP, the `vst` extra."
---

# vst — the VST-plugin skill suite (index + doctrine)

ship-studios can run your installed **third-party VST3 / Audio Unit effect** plugins inside the
mix/master pipeline via `[L] apply-vst-chain` (Pedalboard, the `vst` extra) — **offline & headless**,
no DAW/GUI/audio-device. This skill is the map; reach for a specific `vst-*` skill below, or
`[[vst-chain]]` for a freeform chain.

## The doctrine (every vst-* skill obeys this)

1. **Headless-safe only.** Only suggest plugins in the inventory — see
   [`docs/vst/README.md`](../../../docs/vst/README.md) (779 safe titles, strong candidates by task).
   Confirm the path with `[L] list-vst-plugins {name_contains}` before applying.
2. **Measure before & after.** `[L] measure-loudness` + `[L] measure-spectrum` (+ `measure-stereo`
   for space) bracket every move — prove it landed, the repo's core rule.
3. **`dump_state:true`.** Persist the opaque patch next to the output for a reproducible re-render;
   never rely on `.fxp`/`.vstpreset`.
4. **Opt-in & non-deterministic.** Loads an external binary (unlike the pure-DSP tools). A clean load
   ≠ a valid render — an unlicensed plugin can load in demo/silent mode, so re-measure and flag
   `changed:false`. VST3 is cross-platform; AU is macOS-only.

## The suite

| Skill | Use it to |
|---|---|
| `[[vst-chain]]` | apply an arbitrary ordered effect chain to any WAV (the backbone) |
| `[[vst-browse]]` | discover/search what's installed & loadable, by task category |
| `[[vst-channel-strip]]` | console channel strip on a stem/bus (SSL/Neve/API) |
| `[[vst-eq]]` | corrective / vintage EQ insert (Pultec, Maag, Pro-Q) |
| `[[vst-compress]]` | dynamics insert (1176/LA-2A/bus comp, Pro-C) |
| `[[vst-saturate]]` | tape / harmonic color (Tape Machine, Saturn) |
| `[[vst-reverb]]` | reverb (Valhalla, Pro-R, FlexVerb) — parallel/send |
| `[[vst-delay]]` | delay / echo (EP-34, Brigade, Timeless) |
| `[[vst-de-ess]]` | de-esser, paired with `[G] find-sibilance` |
| `[[vst-master]]` | plugin mastering chain (EQ→comp→limiter) — the VST sibling of `[[master-track]]` |
| `[[vst-amp]]` | guitar/bass amp + pedal tone (TONEX, NAM, Amp Rooms) |

## Prerequisites

- `[L] apply-vst-chain` / `[L] list-vst-plugins` need `uv sync --extra vst` in `../stemmy-loops-mcp`
  (installs Pedalboard). The `[G]` pairing steps (find-sibilance/find-resonances) need `GEMINI_API_KEY`.
- Plugins must be installed **and authorized** on this machine (machine-license, not iLok/UAD-DSP).

## Related

- `[[finalize-mix]]` / `[[master-track]]` / `[[mix-check]]` / `[[stem-master]]` — the pure-DSP pipeline these VST skills slot into as optional, opt-in inserts.
