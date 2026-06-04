---
name: vst
description: "Use when the user wants to use their own VST3/AU plugins in the pipeline or asks which VST skill applies — 'use my plugins', 'run a VST chain', 'add a real compressor/EQ/reverb plugin', 'what VST skills are there', 'can I use Pultec/SSL/FabFilter here'. The index + doctrine for the VST suite; routes to the per-task vst-* skills. Reference, not a pipeline — it points at the skills and the headless-safe inventory. Stemmy MCP, the `vst` extra."
argument-hint: [what you want to do]
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
| `[[izotope]]` | the iZotope family map (Ozone/Neutron/RX/Nectar/Neoverb) + headless render verdicts |

### Per-plugin deep-dives (measured)

> **Naming convention:** each plugin skill is named by its most recognizable identifier — the model number when iconic (`[[la-3a]]`, `[[dbx-160]]`), else vendor-product (`[[fabfilter-pro-q-4]]`) — so a new deep-dive's name is a deliberate call, not a guess.

| Skill | Use it to |
|---|---|
| `[[studer-a800]]` | drive the **UAD Studer A800** tape machine — warmth/glue/de-harsh, grounded in the real param surface + isolation numbers ([`docs/vst/studer-a800.md`](../../../docs/vst/studer-a800.md)) |
| `[[softube-tape]]` | drive **Softube Tape** — 3-machine (A/B/C) tape color/glue/lo-fi; **Amount is gain-compensated** (moves crest not tone), Crosstalk glues/narrows (not width), 13/15 params are string enums → preset harness only ([`docs/vst/softube-tape.md`](../../../docs/vst/softube-tape.md)) |
| `[[api-vision-channel-strip]]` | drive the **UAD API Vision Channel Strip** — tight/punchy/forward drums (212/215/235/225/550/560), measured crest map + shootout ([`docs/vst/api-vision-channel-strip.md`](../../../docs/vst/api-vision-channel-strip.md)) |
| `[[ssl-4k-e]]` | drive the **SSL 4K E** (SL 4000 E channel) — clean/weighty British console; the **Brown/Black/Orange** EQ cards + grabby VCA comp (FAST out = punch, opposite of API), string enums via the harness ([`docs/vst/ssl-4k-e.md`](../../../docs/vst/ssl-4k-e.md)) |
| `[[fabfilter-pro-q-4]]` | drive **FabFilter Pro-Q 4** — surgical + per-band dynamic + **Spectral Dynamics** + Character EQ; renders headless & **no-iLok**, but the 581-param surface needs the flatten-first preset harness, not the float dict ([`docs/vst/fabfilter-pro-q-4.md`](../../../docs/vst/fabfilter-pro-q-4.md)) |
| `[[fabfilter-pro-l-2]]` | drive **FabFilter Pro-L 2** — true-peak brickwall **limiter** (8 styles, LUFS/dBTP metering); renders headless & **no-iLok**, but a limiter **owns the ceiling** → render faithfully via `apply-vst-chain` + a `.state` blob (NOT the renormalizing harness) ([`docs/vst/fabfilter-pro-l-2.md`](../../../docs/vst/fabfilter-pro-l-2.md)) |
| `[[la-3a]]` | drive the **UADx Teletronix LA-3A** — solid-state opto **LEVELER** (it *reduces* crest, unlike the crest-holding tube `[[fairchild-660]]`) + odd/3rd-harmonic grit; **HF Emphasis = a built-in sidechain HPF** (raise it to keep the kick punching on drums), Peak Reduction has a dead zone ~0–2, `comp_limit`/`meter` are string enums → preset harness for Limit mode; renders headless via `uaudio_la3a.vst3` ([`docs/vst/la-3a.md`](../../../docs/vst/la-3a.md)) |
| **Pultec Passive EQ Collection** (`[[pultec-eqp-1a]]` · `[[pultec-meq-5]]` · `[[pultec-hlf-3c]]`) | the three UADx passive-tube Pultec boxes — **[[pultec-eqp-1a]]** lows+air program EQ (the low-end trick + air-without-fizz; knobs 0–10 not-dB & nonlinear) · **[[pultec-meq-5]]** the MID-range EQ (LOW PEAK / DIP / HIGH PEAK, 200 Hz–7 kHz; here the **0–10 dial is ~dB** — LOW PEAK +10.7/HIGH PEAK +8.8/DIP saturates −11 — and boost+DIP at the same Hz FOCUSES not cancels) · **[[pultec-hlf-3c]]** the passive HP/LP FILTER (0.000 % THD, only subtracts). Each renders headless via `uaudio_pultec_*.vst3` (iLok account); freq selectors are string enums → preset harness ([`docs/vst/pultec-meq-5.md`](../../../docs/vst/pultec-meq-5.md)) |

### All per-plugin deep-dives (measured)

The table above highlights a few; the **complete set** — each a measured field guide grounded in
`docs/vst/<plugin>.md`. Reach for the specific skill when you know the box:

- **Channel strips / consoles:** [[api-vision-channel-strip]] · [[ssl-4k-e]] · [[ssl-native-channel-strip-2]] · [[la-6176]] · [[helios-type-69]] · [[kit-bb-a5]] · [[kit-bb-n105]] · [[kit-bb-n73]] · [[manley-voxbox]]
- **Compressors:** [[fairchild-660]] · [[manley-variable-mu]] · [[la-3a]] · [[dbx-160]] · [[distressor]] · [[ssl-bus-compressor-2]]
- **EQs:** [[pultec-eqp-1a]] · [[pultec-meq-5]] · [[pultec-hlf-3c]] · [[manley-massive-passive]] · [[hitsville-eq]] · [[hitsville-eq-mastering]] · [[neutron-4-equalizer]] · [[neutron-4-sculptor]]
- **Tape / saturation / transient:** [[studer-a800]] · [[ampex-atr-102]] · [[oxide-tape]] · [[softube-tape]] · [[vibe-analog-machines]] · [[softube-transient-shaper]] · [[neutron-4-exciter]] · [[neutron-4-transient-shaper]] · [[tape-j-37]] (⚠ loads but renders passthrough headless — DAW-only)
- **FabFilter:** [[fabfilter-pro-q-4]] · [[fabfilter-pro-mb]] · [[fabfilter-saturn-2]] · [[fabfilter-pro-l-2]]
- **iZotope — repair (RX) / vocal / reverb / mastering:** [[rx-10-voice-de-noise]] · [[rx-10-spectral-de-noise]] · [[rx-10-de-click]] · [[rx-10-de-ess]] · [[rx-10-de-reverb]] · [[nectar-3]] · [[neoverb]] · [[rx-10-de-hum]] (⚠ DAW-only) · [[ozone-11-maximizer]] / [[ozone-11-equalizer]] / [[ozone-11-imager]] / [[ozone-11-match-eq]] (⚠ Ozone = DAW-only, iLok) — full map + verdicts: [[izotope]]

## Prerequisites

- `[L] apply-vst-chain` / `[L] list-vst-plugins` need `uv sync --extra vst` in `../stemmy-loops-mcp`
  (installs Pedalboard). The `[G]` find-sibilance / find-resonances pairing steps are **pure DSP — no
  `GEMINI_API_KEY`** (they sit on the stemmy-gemini server but make no model call; only the §4 "Gemini
  listens" critique tools need the key).
- Plugins must be installed **and authorized** on this machine. Most headless-safe boxes are machine-
  licensed; the UADx `uaudio_*.vst3` deep-dives authorize via an **iLok *account*** (no dongle/UAD-DSP) —
  see each deep-dive. iLok/PACE-dongle-protected titles are render-farm landmines.

## Related

- `[[finalize-mix]]` / `[[master-track]]` / `[[mix-check]]` / `[[stem-master]]` — the pure-DSP pipeline these VST skills slot into as optional, opt-in inserts.
