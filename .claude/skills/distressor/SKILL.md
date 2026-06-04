---
name: distressor
description: "Use when running the UADx Empirical Labs Distressor (EL8) for aggressive/forward compression, parallel smash, room-mic NUKE, or harmonic grit — 'Distressor', 'Empirical Labs', 'EL8', 'NUKE the room mics', 'Dist 2/Dist 3 warmth'. The deep-dive of [[vst-compress]] / [[vst-saturate]]. Stemmy MCP, the `vst` extra."
argument-hint: <wav-or-bus> [goal: drum-glue|aggressive|parallel|opto|2bus]
---

# distressor — drive the UADx Empirical Labs Distressor (measured)

The plugin-specific, measured version of [[vst-compress]] / [[vst-saturate]] for the **UADx Empirical Labs
EL8 Distressor** (`/Library/Audio/Plug-Ins/VST3/uaudio_distressor.vst3`) — Dave Derr's "digitally-controlled
analog **knee**" compressor with **8 ratio curves** (silky leveling → saturated brick-wall) and a built-in
**harmonic distortion** generator (Dist 2 / Dist 3). It's the **aggressive, forward, do-anything** comp in the
dynamics family — the digitally-controlled-knee + harmonic-distortion counterpart to the tube COLOR of [[fairchild-660]], the solid-state
opto leveling of [[la-3a]], and the VCA glue of [[ssl-bus-compressor-2]]. Full field guide — param surface, the
ratio/input/attack/release/detector/distortion/mix maps, the harmonic signature, recipes, pitfalls, sources —
lives in [`docs/vst/distressor.md`](../../../docs/vst/distressor.md). This skill is the workflow.

## The governing facts (read first)

1. **It compresses AND distorts.** The audio path adds harmonics on top of GR; **INPUT drives both together**.
   Norm is near-clean (THD 0.2 %); **Dist 2 = 2nd-harmonic warmth** (+9 dB H2 at 6:1/in8), **Dist 3 = 2nd+3rd
   grit**; slam INPUT and even Norm clips (odd-harmonic, THD → 24 %+). Always A/B loudness-matched.
2. **RATIO = 8 curves, and it sets the threshold too — there is NO threshold knob.** You drive *into* the
   curve with INPUT. Measured crest on the warm drum bus (in8): dry **17.9** → 2:1 14.5, 4:1 16.3, **6:1 16.0
   (the workhorse start)**, 10:1 14.7, **20:1 13.6 (hardest clamp)**, **NUKE 14.3 (saturated brick-wall, built
   for room mics)**. 10:1 = the **Opto** (LA-2A-style) curve.
3. **ATTACK is the master punch control, and LOWER = FASTER.** At 10:1/in8: **attack 0 → crest 10.0** (clamps
   the transient), **attack 10 → crest 19.1** (transients punch *through*, above dry). For punch, turn attack
   *up* toward 10; to clamp, down toward 0. (Matches the 50 µs–30 ms spec.)
4. **RELEASE: lower = faster = denser/brighter/pumpier; higher = slower/smoother (but holds level down).**
   Fast release is the aggressive Distressor "attitude."
5. **DETECTOR HP takes the kick out of the sidechain → kick punches through + bus gets louder** (RMS +3.9 dB
   at 10:1; low end forward). **`Emp`** boosts ~6 kHz *in the detector* = built-in de-ess/de-harsh. HP is the
   cure for LF pumping at heavy GR. (There's also an **AUDIO `HP`** ~80 Hz that removes the lows you *hear* —
   different filter.)
6. **MIX is built-in parallel** (Dry↔Comp). NUKE/in9: mix 100 → crest 15.2, mix 30 → 17.0 (dry transients
   restored). Crush + blend for a NY smash.
7. **OUTPUT** is calibrated makeup (default 6.5 ≈ "−10 gear", 8 ≈ "+4 tape"); **HR** (headroom 4–28) sets the
   internal operating level (drive without INPUT's color, for A/B matching). No output meter — watch GR.
8. **The tooling gotcha:** `ratio` / `detector` / `audio` are **string enums** — `apply-vst-chain`'s
   number-only `parameters` dict **can't pass them** (`"10:1"`/`"HP"`/`"Dist 2"`). The dials
   (input/attack/release/output/mix) + headroom *are* numeric and reachable, but ratio defines the sound →
   **drive it through the [[vst-preset]] harness** (`presets/vst/apply_vst_preset.py`).
9. **British Mode is NOT exposed headless** (12-param surface, no Brit toggle — GUI-only). Approximate the
   1176-all-buttons aggression with NUKE/20:1 + fast attack + Dist 3.
10. **Renders headless via the `uaudio_distressor.vst3` UADx native build** (`changed:true`). The
    `/Components/UAD Empirical Labs Distressor.component` twin **passes audio through** offline — never use it.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **Load the `uaudio_distressor.vst3` UADx native build** — it **renders headless & processes offline**
  (`RENDERS ✓` here). The `/Components/UAD Empirical Labs Distressor.component` twin passes audio through
  offline — never use it ([[vst-verify]] / [[vst]]). UADx native is the iLok-account
  (no-dongle) lineage, but re-verify `changed:true` on a new machine.
- Balance the bus first ([[mix-balance]]); hand the compressed/colored result to [[finalize-mix]] /
  [[master-track]] — this is a comp/color/glue stage, **not** a master/limiter.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest / LRA / PLR / true-peak) + `[L] measure-microdynamics`
   (per-band punch) + `[L] measure-spectrum` (centroid + low/low-mid). The "before."
2. **Pick the curve + move** from the table below. Default workhorse: **6:1, dials at 5**. Start gentle and
   escalate on purpose (NUKE/20:1 are effects).
3. **Apply via the preset harness** (ratio/detector/audio are string enums → `apply-vst-chain` can't):
   `…/stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py presets/vst/distressor-*.json <in> <out>`.
   Ready-made: **`distressor-drum-glue`** (validated ★), **`distressor-aggressive-drums`**,
   **`distressor-parallel-smash`**.
4. **Dial it to the result:** higher RATIO or more INPUT = more clamp/density + more color; **ATTACK** sets
   punch (toward 10) vs clamp (toward 0); **RELEASE** sets density/aggression (fast) vs smooth (slow);
   **DETECTOR HP** if lows pump / you want the kick forward, **Emp** to tame ~6 kHz harshness; **MIX** down for
   parallel; **Dist 2** for warmth / **Dist 3** for grit. Re-measure after each change.
5. **Prove it** — re-`measure-loudness` / `measure-microdynamics` / `measure-spectrum` (+ `measure-distortion`
   if you pushed Dist/INPUT): expect crest down per the move (held ~2 dB for glue, −6 for aggressive, restored
   by MIX for parallel), LRA tighter, kick/low end forward with HP, true-peak safe. **A/B loudness-matched**
   ([[level-match]] / `render-ab`) so "bigger" isn't just "louder."
6. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch over-pumping (too-fast attack/release + heavy
   GR), harshness from Dist 3, or a choked bus; reconcile any mono "dull/harsh" flag against the meters
   ([[gemini-audio-understanding]]).

## Recipes (measured starting points — re-dial to your GR)

| Goal | ratio | input | attack | release | audio | detector | mix | Preset |
|---|---|---|---|---|---|---|---|---|
| **Musical drum glue** (keep feel) ★ | 2:1 | 5 | 8 | 5 | Dist 2 | HP | 100 | `distressor-drum-glue` |
| **Aggressive / forward drums** | 10:1 | 8 | 4 | 2 | Dist 2 | HP | 100 | `distressor-aggressive-drums` |
| **Parallel / NY smash** | NUKE | 9 | 1 | 1 | Dist 3 | Norm | **30** | `distressor-parallel-smash` |
| **Smooth opto leveling** (vocal/bass) | 10:1 | 5–6 | 9–10 | 0–1 | Dist 2 | HP(+Emp) | 100 | (recipe) |
| **Transparent 2-bus glue** | 2:1 | 4–5 | 9–10 | 4 | Dist 2 (light) | HP | 100 | (drum-glue @ 2:1) |
| **Room-mic explosion** | NUKE | 9–10 | 10 | 1–2 | Dist 3 | — | 100 | (parallel @ mix 100) |
| **Snare smack** (mono src) | 6:1 | 6–8 | 6 | 5 | Dist 2/3 | HP | 100 | (recipe) |

★ validated (`presets/vst/distressor-drum-glue.json` → `projects/watercolors/mix/distressor_drum_glue_demo.wav`:
crest 17.17→15.06, LRA 2.44→1.96, +2.0 LU, TP −0.99, low end forward). **Dials are 0–10½ knob positions**
(attack/release: **0 = fast, 10 = slow**; input = drive, output = makeup). Leave `power` on, `bypass`/`master_bypass` off; the harness peak-trims to −1 dBFS.

## Reporting to the user

State the curve + settings (ratio / input / attack / release / detector / audio / mix), before→after
**crest / LRA / true-peak** (+ low-band shift if you used HP, + THD/H2/H3 if you used Dist), that it ran
headless via the `uaudio_distressor.vst3` build, and whether the character came from compression, harmonic
color, or both. A/B loudness-matched so "bigger" isn't just "louder."

## Pitfalls

- **Don't drive it through `apply-vst-chain` alone** — `ratio`/`detector`/`audio` are string enums the
  number-only dict can't pass (it leaves the `6:1`/`Norm`/`Norm` default). Use the [[vst-preset]] harness.
- **British Mode is GUI-only here** — approximate with NUKE/20:1 + fast attack + Dist 3.
- **Wrong build = passthrough** — the `/Components/UAD ….component` twin passes audio through offline. Load
  `uaudio_distressor.vst3`; verify `changed:true` + measure *detail* ([[vst-verify]]).
- **Attack direction trips people — lower = faster.** For punch, turn attack UP toward 10.
- **It compresses AND distorts → louder + thicker** — A/B at matched loudness; don't mistake +LU/THD for "better."
- **Fast attack + heavy GR pumps the lows** — engage the detector HP, slow the attack, or use 10:1 Opto.
- **NUKE/20:1 are effects, not a 2-bus master** — they lift the noise floor/bleed; keep room mics well under
  the close mics. For transparent glue stay at 2:1/3:1.
- **It's not a master** — comp/color/glue stage; hand to [[finalize-mix]] / [[master-track]]; brick-wall with
  [[fabfilter-pro-l-2]] or `render-mastered`.

## Related

- [`docs/vst/distressor.md`](../../../docs/vst/distressor.md) — the full measured field guide (Part A measured + Part B cited) · `scripts/mix/distressor_sweep.py` — the characterization sweep
- [[vst-compress]] / [[vst-saturate]] — the generic skills this specializes · [[finalize-mix]] / [[stem-master]] — stages this fits
- [[fairchild-660]] — tube COLOR comp (holds crest) · [[la-3a]] — solid-state opto leveler · [[ssl-bus-compressor-2]] — VCA glue · [[fabfilter-pro-mb]] — multiband dynamics — the dynamics family
- [[vst-preset]] — apply enum chains (required here) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge ratio/attack variants · [[drum-punch]] — pure-DSP transient design (no plugin)
- [[gemini-audio-understanding]] — why meters (not Gemini mono) own crest/GR/THD
