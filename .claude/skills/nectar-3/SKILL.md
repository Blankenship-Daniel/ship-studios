---
name: nectar-3
description: "Use when running the iZotope Nectar 3 all-in-one vocal channel strip on an isolated vocal (or a bright mono source) — 'Nectar 3', 'iZotope vocal channel', 'Nectar saturation/comp/de-ess on the vocal', 'add tube/tape warmth to the vox', 'full vocal strip in one box'. The measured, plugin-specific deep-dive of [[vst-channel-strip]]. Stemmy MCP, the `vst` extra."
argument-hint: <vocal.wav> [goal: warmth|comp|de-ess|saturate|full-strip]
---

# nectar-3 — drive the iZotope Nectar 3 vocal channel strip (measured)

The plugin-specific, measured workflow for **iZotope Nectar 3** (`/Library/Audio/Plug-Ins/VST3/Nectar 3.vst3`) —
iZotope's all-in-one **vocal channel strip** (696 params): a stack of independent modules (gate, two compressors,
de-esser, two EQs, saturation, delay, reverb, harmony, dimension, limiter, unmask) you engage à la carte. The
**vocal-first / one-box** member of [[vst-channel-strip]] (vs the console-modeled SSL/Neve/API strips). Full field
guide — module-by-module surface, footguns, recipes, our numbers, sources —
[`docs/vst/izotope-nectar.md`](../../../docs/vst/izotope-nectar.md). This skill is the workflow.

## The governing facts (read first — measured on this rig, Pedalboard 0.9.23)

1. **It RENDERS headless** (NI/iLok-account-authorized on this Mac). Use the **VST3** `Nectar 3.vst3` path. **Loads ≠
   renders elsewhere** — re-verify on a new machine with [[vst-verify]] (a 0.00 spectrum/loudness delta = passthrough).
2. **The drivers are OFF at default — you MUST drive them.** `saturation_amount` defaults to **0** (no color until you
   raise it), `comp_1_threshold_db` to **0** and `comp_2_threshold_db` to **0** (no GR until you lower it). A bare
   instance with everything at default is near-passthrough on those modules — set the amount/threshold explicitly.
3. **It's a VOCAL tool — use it on ISOLATED VOCALS** (or a bright mono lead). Our numbers are on a **vocal clip**.
   For drums / bus / master reach for the dedicated console, comp, and tape skills instead.
4. **Params are enums (numeric + string).** `[L] apply-vst-chain`'s float dict can set the **numeric** ones
   (`saturation_amount`, `comp_1_threshold_db`/`_ratio`, `deesser_frequency_hz`/`_threshold_db`, EQ band gains/freqs)
   on an already-active module — but the **string/bool** enums (`*_bypass` to engage a module, `saturation_mode`,
   `comp_1_mode`) need the **[[vst-preset]] harness** (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
5. **The `harmony` module is a pitch/harmony generator** (GUI/MIDI-driven) — minimal headless utility; skip it in
   the pipeline. Per-module pure-DSP twins exist: de-esser → [[de-ess]], EQ → `[L] apply-eq`, comp → `[L] compress-loop`.
6. **The "Vocal Assistant" is GUI-only** — it won't run headless; you drive the manual DSP modules yourself.
7. **Meters own tone** (Gemini hears ~16 kbps mono): read `[L] measure-spectrum` (tilt/centroid/bands),
   `measure-loudness` (crest/PLR), `measure-stereo`. A/B loudness-matched ([[level-match]] / `[L] render-ab`).

## The parameter surface (modules — see the doc for the full table)

Each module has a `*_bypass` (False = engaged; harness only to toggle) + a `*_wet_mix`. The drivable headliners:
**Saturation** — `saturation_mode` (`Analog`/`Retro`/`Tape`/`Tube`/`Warm`/`Decimate`/`Distort`, def **Tape**; string →
harness), `saturation_amount` (0..100, def **0**). **Comp 1 / Comp 2** — `comp_N_threshold_db` (−40..0, def **0**),
`comp_N_ratio` (1..50, def 2.5), `comp_N_attack_ms`/`_release_ms`, `comp_N_mode` (`Digital`/`Vintage`/`Optical`/
`Solid-State`; string → harness). **De-esser** — `deesser_frequency_hz` (800..8000, def 2500), `deesser_threshold_db`
(−20..0, def 0 = no action). **EQ 1 / EQ 2** — 24 bands each (`eq_1_bN_gain_db`/`_frequency_hz`/`_q`/`_shape`; shapes
are string → harness). **Gate · Delay · Reverb · Dimension · Limiter · Unmask** — each its own `*_bypass` + controls.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid) + `[L] measure-loudness` (crest/PLR). The
   "before" column. Decide the goal: warmth, leveling, de-ess, or the full strip.
2. **Engage only the modules you want** (harness — set each `*_bypass`). Leave the rest bypassed; a bare default does
   nothing on the drive modules anyway.
3. **Saturation (warmth/air).** Set `saturation_mode` (Tape default, or Tube/Warm/Analog) + raise `saturation_amount`
   (60 ≈ a real move). It generates harmonics/air — on a vocal this lifts >6 kHz and the centroid.
4. **Compression (leveling).** Engage Comp 1; set `comp_1_threshold_db` negative (−18 ≈ moderate) + `comp_1_ratio`
   (3 ≈ vocal). Lower threshold = more GR = lower crest. Comp 2 for serial/parallel leveling.
5. **De-ess.** Set `deesser_frequency_hz` to the sibilant band (~6–8 k) + raise `deesser_threshold_db` (more negative
   number is NOT more — it's a relative duck; sweep with `deesser_listen` in the GUI, then set the value).
6. **EQ (tone).** EQ 1/EQ 2 bands for HPF + presence/air — but a pure-DSP `[L] apply-eq` is often simpler/cheaper.
7. **Build a preset** (`presets/vst/nectar3-*.json`) setting the engaged modules' params explicitly + their `*_bypass`,
   and apply: `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
   projects/<track>/mix/<stem>_nectar3.wav`. Set `dump_state=true` via `apply-vst-chain` once dialed for a byte-stable
   re-render.
8. **Prove it** — re-`measure-spectrum`/`measure-loudness`. **Saturation → centroid/>6k UP**; **comp → crest DOWN**;
   **de-ess → the 4–9 k band drops**. A 0.00 delta = passthrough (wrong module engaged or amount still 0). A/B
   loudness-matched.
9. **QC** — `[G] detect-mix-issues` (genre/intent set) for over-drive / over-de-ess; cross-check any mono "harsh/dull"
   flag against the meters ([[gemini-audio-understanding]]). It's a per-vocal insert, not a master — hand to [[master-track]].

## Move table (measured on a vocal clip)

| Goal | Nectar 3 move |
|---|---|
| **Warmth + air + leveling** ★ | `saturation_mode=Tape`, `saturation_amount=60` + `comp_1_threshold_db=−18`, `comp_1_ratio=3` → see ★ below. |
| **Warmth / saturation only** | engage Saturation; `Tape`/`Tube`/`Warm`, raise `saturation_amount` (60 ≈ real, 20–40 subtle). Lifts highs/centroid. |
| **Compress / level** | engage Comp 1; `threshold_db` negative (−18 mod, deeper = more GR), `ratio` 2.5–4; Comp 2 for serial. (Twin: `[L] compress-loop`.) |
| **De-ess** | engage De-esser; `deesser_frequency_hz` 6–8 k, raise `deesser_threshold_db` until only esses duck. (Twin: [[de-ess]].) |
| **EQ tone** | EQ 1/EQ 2 bands (HPF + presence/air); shapes are string → harness. (Twin: `[L] apply-eq`.) |
| **Gate** | engage Gate; set `gate_open_db`/`gate_close_db`/`gate_ratio` to clean between phrases. |
| **(skip headless)** Harmony / Delay / Reverb / Dimension | GUI/MIDI-driven generators — minimal headless value; use [[vst-reverb]]/[[vst-delay]] for space, [[neoverb]] for reverb. |

★ the shipped example (`presets/vst/nectar3-vocal-warmth.json`): `saturation_mode=Tape`, `saturation_amount=60` +
`comp_1_threshold_db=−18`, `comp_1_ratio=3` measured on a vocal clip: **>6 kHz +9.9 dB** (saturation harmonics/air),
crest **17.5 → 16.0 (−1.5, comp leveling)**, low / low-mid / mid **−2.7 / −2.8 / −4.9 dB**, centroid **846 → 1132**.
A real, big change — set both `saturation_mode` (string) and the engaged modules' `*_bypass` via the harness.

## Outputs

- `projects/<track>/mix/<stem>_nectar3.wav` + the reusable `presets/vst/nectar3-*.json` (and `.state` if dumped).

## Reporting to the user

State which modules are engaged (saturation mode + amount; comp threshold/ratio + GR; de-ess band/threshold; EQ
moves), the before→after **crest / centroid / tilt / target-band deltas**, that it ran headless, and the preset/`.state`
path. A/B loudness-matched so warmth isn't a level illusion.

## Pitfalls

- **It's a VOCAL tool** — don't reach for it on drums / bus / master; use the console / comp / tape skills there.
- **Default = near-passthrough on the drivers** — `saturation_amount` is **0** and the comp thresholds are **0** at
  default; you must drive them or you'll ship an unprocessed copy with a false `changed:true`.
- **Float dict can't engage a module or set a mode** — `*_bypass`, `saturation_mode`, `comp_N_mode` are string/bool
  enums → the [[vst-preset]] harness (or a `.state`).
- **The harness upmixes mono→stereo and peak-normalizes** (`output_peak_dbfs`, def −1.0) — fine for a single vocal
  insert; for channel-preserving work use `[L] apply-vst-chain`.
- **Harmony is a pitch generator** (GUI/MIDI) — don't expect headless harmonies; the AI **Vocal Assistant is GUI-only** too.
- **De-ess threshold isn't "lower = more"** — it's a relative duck; verify the 4–9 k band actually dropped.
- A vocal channel is a per-track insert, **not** mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/izotope-nectar.md`](../../../docs/vst/izotope-nectar.md) — the full measured field guide ·
  [[izotope]] — the iZotope index
- [[vst-channel-strip]] — the generic skill this specializes · [[vst-saturate]] / [[vst-compress]] / [[vst-de-ess]] —
  its per-module generic cousins · [[vst-preset]] — apply enum/all-explicit chains · [[vst-verify]] — prove the build
  renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- Channel-strip siblings: [[manley-voxbox]] (all-tube vocal) · [[ssl-native-channel-strip-2]] (clean) ·
  [[la-6176]] (tube pre + comp)
- Pure-DSP twins (no plugin): saturation → `[L] saturate-loop` ([[vst-saturate]]); leveling → `[L] compress-loop`;
  de-ess → [[de-ess]]; air → [[excite]]; surgical/tilt EQ → `[L] apply-eq`
- [[mix-check]] (find the problems first) · [[finalize-mix]] · [[gemini-audio-understanding]] — why meters own the spectrum read
