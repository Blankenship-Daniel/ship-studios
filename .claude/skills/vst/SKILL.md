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

1. **Verify it RENDERS, not just loads.** A plugin can load headless yet pass audio through unchanged
   or ignore its params. Trust only plugins that *process* — pre-screen with `[[vst-verify]]`. The
   inventory ([`docs/vst/README.md`](../../../docs/vst/README.md), 779 titles) is a *load* probe → it
   overcounts. Confirm the path with `[L] list-vst-plugins {name_contains}` first.
2. **Use the build that renders.** For UADx: `/Library/Audio/Plug-Ins/VST3/uaudio_*.vst3` renders; the
   `UAD ….component` / `…/Universal Audio/UAD ….vst3` twins **pass through** offline — always pick `uaudio_*`.
3. **Measure before & after — detail, not just loudness.** `[L] measure-loudness` + `[L] measure-spectrum`
   (+ `measure-stereo`/`measure-microdynamics`) bracket every move. A **0.00 change in spectrum/crest/tilt
   = passthrough**, even if `changed:true`.
4. **Gain-stage analog units.** Tube comps / tape / consoles need a healthy level (~+18 dB) to engage;
   `[L] apply-vst-chain` has no gain-stage, so a quiet bus barely processes — use `[[vst-preset]]` for chains
   that need drive.
5. **Enum/bool params → `[[vst-preset]]`.** `apply-vst-chain`'s `parameters` is float-only; many controls
   are enum strings / bools (`output='-6.0 dB'`, `gain='Low'`, `auto_cal=False`) — set those via the preset
   harness, not the float dict.
6. **Reproducible & opt-in.** `dump_state:true` (or a saved preset) persists the patch — never `.fxp`/`.vstpreset`.
   It's an external, non-deterministic binary (unlike the pure-DSP tools). VST3 cross-platform; AU macOS-only.

## The suite

| Skill | Use it to |
|---|---|
| `[[vst-chain]]` | apply an arbitrary ordered effect chain to any WAV (the backbone) |
| `[[vst-browse]]` | discover/search what's installed & loadable, by task category |
| `[[vst-verify]]` | **prove a plugin renders** (responds to params) vs loads/passthrough — the backstop |
| `[[vst-preset]]` | save & apply reusable chains (gain-stage + enum params + state blobs) |
| `[[vst-shootout]]` | render N chain/preset variants & adversarially judge to a winner |
| `[[vst-channel-strip]]` | console channel strip on a stem/bus (SSL/Neve/API) |
| `[[vst-eq]]` | corrective / vintage EQ insert (Pultec, Maag, Pro-Q) |
| `[[vst-compress]]` | dynamics insert (1176/LA-2A/bus comp, Pro-C) |
| `[[vst-saturate]]` | tape / harmonic color (Tape Machine, Saturn) |
| `[[vst-reverb]]` | reverb (Valhalla, Pro-R, FlexVerb) — parallel/send |
| `[[vst-delay]]` | delay / echo (EP-34, Brigade, Timeless) |
| `[[vst-de-ess]]` | de-esser, paired with `[G] find-sibilance` |
| `[[vst-master]]` | plugin mastering chain (EQ→comp→limiter) — the VST sibling of `[[master-track]]` |
| `[[vst-amp]]` | guitar/bass amp + pedal tone (TONEX, NAM, Amp Rooms) |

### Per-plugin deep-dives (measured)

| Skill | Use it to |
|---|---|
| `[[studer-a800]]` | drive the **UAD Studer A800** tape machine — warmth/glue/de-harsh, grounded in the real param surface + isolation numbers ([`docs/vst/studer-a800.md`](../../../docs/vst/studer-a800.md)) |
| `[[api-vision-channel-strip]]` | drive the **UAD API Vision Channel Strip** — tight/punchy/forward drums (212/215/235/225/550/560), measured crest map + shootout ([`docs/vst/api-vision-channel-strip.md`](../../../docs/vst/api-vision-channel-strip.md)) |

## Prerequisites

- `[L] apply-vst-chain` / `[L] list-vst-plugins` need `uv sync --extra vst` in `../stemmy-loops-mcp`
  (installs Pedalboard). The `[G]` pairing steps (find-sibilance/find-resonances) need `GEMINI_API_KEY`.
- Plugins must be installed **and authorized** on this machine (machine-license, not iLok/UAD-DSP).

## Related

- `[[finalize-mix]]` / `[[master-track]]` / `[[mix-check]]` / `[[stem-master]]` — the pure-DSP pipeline these VST skills slot into as optional, opt-in inserts.
