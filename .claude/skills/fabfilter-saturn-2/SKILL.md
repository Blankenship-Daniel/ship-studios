---
name: fabfilter-saturn-2
description: "Use when running FabFilter Saturn 2 for multiband distortion / saturation / harmonic color on a stem, bus, or loop — 'Saturn 2', 'FabFilter Saturn', 'saturate this', 'multiband saturation', 'tube/tape/amp/transformer warmth', 'add harmonics/grit/drive', 'tape glue on the drum bus', 'parallel smash the drums', 'make the bass cut on small speakers', 'lo-fi/destroy/bitcrush', 'add air with saturation'. The measured, plugin-specific deep-dive of [[vst-saturate]] — a 6-band distortion engine with 28 styles (tube/tape/amp/transformer/saturation + Foldback/Rectify/Destroy FX), per-band Drive/Dynamics/Feedback/Tone/Mix, Mid-Side, Linear-phase + HQ oversampling, grounded in the real 956-param Pedalboard surface + our render/harmonic results in docs/vst/fabfilter-saturn-2.md. Renders headless, no-iLok. Stemmy MCP, the `vst` extra."
---

# fabfilter-saturn-2 — drive FabFilter Saturn 2 (measured)

The plugin-specific, measured workflow for **FabFilter Saturn 2** (`/Library/Audio/Plug-Ins/VST3/FabFilter
Saturn 2.vst3`) — a **multiband distortion & saturation** plug-in: up to **6 bands**, each with its own
**distortion style** (28 of them), **Drive**, bipolar **Dynamics**, resonant **Feedback**, a 4-control **Tone** EQ,
per-band **Mix/Level/Pan**, plus Mid/Side, Linear-phase crossovers, HQ oversampling, and a deep modulation matrix.
The **color/saturation** member of [[vst-saturate]] (vs the EQ [[fabfilter-pro-q-4]] and dynamics
[[fabfilter-pro-mb]] FabFilter siblings, or the dedicated tape machines [[ampex-atr-102]] / [[studer-a800]] /
[[softube-tape]]). Full field guide — real param surface, footguns, harmonic table, recipes, our numbers, sources —
[`docs/vst/fabfilter-saturn-2.md`](../../../docs/vst/fabfilter-saturn-2.md). This skill is the workflow.

## The governing facts (read first)

1. **Renders headless AND no-iLok — uniquely safe here.** It loads + processes through Pedalboard 0.9.23 (probe
   Δparam = 8.6e-01), and FabFilter uses a **simple license key, no iLok/PACE/dongle** — a clean render-farm
   candidate like its Pro-Q 4 sibling (unlike the [[vst-hosting-outside-daw]] landmines). Use the **VST3** path
   (the AU `.component` twin is also installed — don't grab it).
2. **A bare load is NOT neutral — it restores FabFilter's last-saved GUI state** (ours: 1 band, style `Warm Tape`,
   drive 20, output −1 dB, HQ Off). So every "fresh" render rides a leftover preset. **Set every param explicitly**
   (`num_active_bands`, per-band `style`/`drive`/`mix`/`dynamics`/tone/`level`, global `mix`/`output_gain`/
   `channel_mode`/`processing_mode`/`high_quality_mode`), or restore a `dump_state` blob. The **only bit-exact
   passthrough** is `mix=0` or `bypass="Bypassed"` — **`drive=0` is NOT clean** (Warm Tube @ drive 0 = +1.7 dB /
   2.2 % THD).
3. **`apply-vst-chain`'s float dict can't pick a style.** All 956 params are `valid_values` lists; the **string
   enums** — `band_N_style` (*the sound itself*), `band_N_crossover_slope`, `band_N_state`, `channel_mode`,
   `processing_mode`, `high_quality_mode` — can't be set via a float-only dict. **Use the [[vst-preset]] harness**
   (`apply_vst_preset.py`, `setattr`) for any real move; the float dict only tweaks numeric drive/mix/dynamics/tone
   on an already-configured instance.
4. **Pick the style by the harmonic you want (measured, 1 kHz @ drive 50).** **Tube** = even **+** odd (Warm Tube
   even-leaning = warmth); **Tape** = **odd-only, no 2nd harmonic**; **Saturation** = odd, transparent→dense
   (Subtle Saturation is the cleanest of all, 0.1 % THD); **Amp** = heavy odd (50–130 % THD); **Transformer** =
   mixed; **Foldback** = wavefolder (5th > fundamental); **Rectify** = octave-up (fundamental removed); **Destroy**
   = bit-crush mush. **Drive crushes crest** (14.6→5.6 @drive80) — protect transients with the **parallel `mix`**
   (mix 30 restored crest to 12.7) or **negative `dynamics`** (−0.8 → crest 10.8 vs +0.8 → 8.0). **Meters own it**
   (Gemini hears mono) — read THD/centroid/crest, A/B level-matched (drive auto-comp ≠ a LUFS match).

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G] mastering-feedback`
  / `detect-mix-issues` (optional, `GEMINI_API_KEY`) to judge if it got harsh.
- **`FabFilter Saturn 2.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"Saturn"}` and take the
  **VST3** path. Screen a new install with `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "Saturn 2"`
  (expect `RENDERS ✓`). No-iLok, but **loads ≠ renders** — always measure detail after.
- **Enum gotcha:** `apply-vst-chain`'s `parameters` is float-only → it can't set `band_N_style` / `_crossover_slope`
  / `channel_mode` / `processing_mode` / `high_quality_mode` (string enums), and a bare load isn't neutral. For any
  real move use the **[[vst-preset]]** harness, which `setattr`s every param.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (centroid + 5-band) + `[L] measure-loudness` (crest/LUFS) +
   `[L] measure-distortion` (THD). The "before" column.
2. **Pick the intent → style + drive**:
   - **Warm glue** → Warm Tube/Tape, drive 15–25, full band (shipped `saturn2-drum-bus-warm.json`).
   - **Aggression / parallel smash** → Amp/Destroy/Rectify driven hard, blended via global `mix` 20–35
     (shipped `saturn2-parallel-smash.json`).
   - **Bass that translates / multiband** → 2–3 bands, sub band `mix=0` (clean), saturate the mids
     (shipped `saturn2-bass-multiband.json`).
   - **Air** → high band, Clean Tube/Warm Tape very low drive + Tone treble/presence (twin: [[excite]]).
   - **Transparent density** → Subtle Saturation, modest drive.
3. **Build a set-everything preset** (`presets/vst/saturn2-*.json`): set `num_active_bands`; per used band
   `band_N_enabled=true`, `band_N_style`, `band_N_drive`, `band_N_mix`, `band_N_dynamics`, the tone bands,
   `band_N_level` (+`band_N_crossover_frequency`/`_slope` for multiband); make unused bands inert with
   `band_N_mix=0`; set global `mix`, `output_gain`, `channel_mode`, `processing_mode`, `high_quality_mode`. Apply:
   `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
   projects/<track>/mix/<stem>_saturn2.wav`. Set `dump_state=true` (via `apply-vst-chain`) once dialed for a
   byte-stable re-render.
4. **Prove it** — re-`measure-distortion`/`measure-spectrum`/`measure-loudness`. Confirm THD rose, the intended
   centroid/tilt moved, and **detail changed** (a 0.00 delta = passthrough; `mix=0`/`drive=0` are the no-op traps).
   Watch **crest** — if drive crushed it, drop the global `mix` (parallel) or pull `dynamics` negative.
5. **A/B level-matched** (`[L] render-ab` / [[level-match]]) — Saturn's drive auto-compensation is not a LUFS match,
   so louder-isn't-better is the trap.
6. **QC** — `[G] detect-mix-issues` / `mastering-feedback` (genre/intent set) to catch over-drive (harsh/fizzy);
   cross-check any mono "harsh" flag against the meters ([[gemini-mastering-feedback-cross-check]]). It's a
   per-track/bus insert — hand the result to [[master-track]] for loudness; don't drive on the 2-bus loudness stage.

## Move table

| Goal | Saturn 2 move |
|---|---|
| **Warm drum/bus glue** | 1 band Warm Tube/Tape, drive 15–25, `dynamics` −0.2…−0.4 (keep punch), tone bass +1–2 / treble −1. |
| **Parallel smash** | Amp (British Rock / Plexi) or Destroy/Rectify, drive 45–70, global `mix` 20–35 — grit under the dry hits. |
| **Bass translation** ★ | 2 bands split ~110 Hz: low band `mix=0` (sub clean), high band Warm Tube/Amp drive 40–60 + presence/treble. |
| **Air / sheen** | top band (split ~5–7 kHz), low band `mix=0`, high band Clean Tube/Warm Tape **very low drive** + treble/presence. (Twin: [[excite]].) |
| **Transparent density** | Subtle Saturation, drive 20–40 — adds level/glue with the least tone change (0.1 % THD baseline). |
| **De-fizz / soften top** | high band Warm/Clean Tape low drive — soft dynamic top control. (Twins: [[de-harsh]] / [[de-ess]].) |
| **Lo-fi / destruction** | Destroy (bitcrush+SR), Foldback (wavefold), Breakdown (down-pitch), Rectify (octave crunch), Smudge (smear). HQ Good/Superb to tame aliasing. |
| **Mastering color** | barely-there Subtle Tube/Tape, `processing_mode="Linear Phase"` + `high_quality_mode="Superb"` (crossover/aliasing clean). |
| **Stereo color** | `channel_mode="Mid/Side"` → warm the Mid, brighten the Side via per-band style/tone. |
| **Movement (headless)** | Envelope Follower → Drive (the one modulation source that renders offline). |

★ shipped example `presets/vst/saturn2-bass-multiband.json`: 2 bands @110 Hz, sub `mix=0`, highs Warm Tube drive 45
+ presence — measured centroid 3007→3479 with the sub left clean.

## Outputs

- `projects/<track>/mix/<stem>_saturn2.wav` + the reusable `presets/vst/saturn2-*.json` (and `.state` if dumped).

## Reporting to the user

State the move (bands: style/drive/mix/tone, which is parallel, M/S or full), HQ + phase mode, the before→after
**THD / centroid / crest** deltas, that it ran headless (no-iLok), and the preset/`.state` path. A/B loudness-matched
so taste isn't a level illusion; flag if drive crushed the crest and how you protected it (parallel mix / dynamics).

## Pitfalls

- **Don't trust a bare load to be flat** (restores the last GUI state) and **don't drive it via the float dict**
  (can't set the *style*) — set everything via [[vst-preset]], or a `dump_state` blob.
- **`drive=0` ≠ clean** — use `mix=0` / `bypass` for a true dry reference; A/B level-matched.
- **Hard styles alias** — raise `high_quality_mode` to Good/Superb for amp/Destroy/Foldback or high-freq drive.
- **Linear phase only touches crossovers + HQ**, not the Tone EQ or each style's modeling.
- **Modulation is mostly a DAW feature offline** — only the Envelope Follower (and audio-triggered EG) reliably render.
- **It's a 2020 plugin, not 2024** — don't conflate its feature set with Pro-Q 4.
- A saturator is a tonal/color insert, not mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/fabfilter-saturn-2.md`](../../../docs/vst/fabfilter-saturn-2.md) — the full measured field guide
- [[vst-saturate]] — the generic saturation skill this specializes · [[vst-preset]] — apply enum/style chains ·
  [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- FabFilter siblings: [[fabfilter-pro-q-4]] (EQ) · [[fabfilter-pro-mb]] (multiband dynamics) · [[fabfilter-pro-l-2]] (limiter)
- Other tape/saturation color: [[ampex-atr-102]] · [[studer-a800]] · [[softube-tape]] · [[helios-type-69]]
- Pure-DSP twins (no plugin, deterministic): [[vst-saturate]]'s `[L] saturate-loop` · [[excite]] (excite-loop) ·
  [[multiband-compress]] · [[sub-design]] · [[de-harsh]] / [[de-ess]]
- [[mix-check]] (find the problem first) · [[gemini-mastering-feedback-cross-check]] — why meters (not Gemini) own the read
