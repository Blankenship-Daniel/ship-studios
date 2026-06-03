---
description: Drive the UADx Empirical Labs Distressor (measured) — 8-curve knee comp + Dist 2/3 distortion, headless.
argument-hint: <wav-or-bus> [goal: drum-glue|aggressive|parallel|opto|2bus]
---

Invoke the **distressor** skill on `$ARGUMENTS`.

`$1` = a bus / stem / loop; optional `$2` = the goal. The UADx Empirical Labs **EL8 Distressor** is Dave Derr's
"digitally-controlled analog **knee**" compressor — **8 ratio curves** (1:1 / 2:1 / 3:1 / 4:1 / **6:1 workhorse**
/ **10:1 Opto** / 20:1 / **NUKE** saturated brick-wall) plus a built-in **harmonic distortion** box
(**Dist 2 = 2nd-harmonic warmth**, **Dist 3 = 2nd+3rd grit**). It compresses AND distorts; **INPUT drives both**
(there's **no threshold knob** — you drive *into* the chosen curve). Measured on the Watercolors warm drum bus
(in8): dry crest 17.9 → 6:1 16.0, **20:1 13.6 (hardest)**, NUKE 14.3. **ATTACK is the master punch control and
LOWER = FASTER** (10:1: attack 0 → crest 10.0 clamped, attack 10 → crest 19.1 punching through); **RELEASE**
lower = faster/denser/brighter. **DETECTOR HP** pulls the kick out of the sidechain (kick forward + louder);
**`Emp`** ≈ a 6 kHz de-ess/de-harsh detector. **MIX** is built-in parallel (NUKE mix 30 keeps the dry
transients = NY smash). The tooling gotcha: **`ratio`/`detector`/`audio` are string enums**, so
`apply-vst-chain`'s number-only dict can't set them → drive through the [[vst-preset]] harness
(`presets/vst/apply_vst_preset.py`, presets `distressor-drum-glue` ★ / `distressor-aggressive-drums` /
`distressor-parallel-smash`). **British Mode is GUI-only** (not in the 12-param headless surface) → approximate
with NUKE/20:1 + fast attack + Dist 3. Load the **`uaudio_distressor.vst3`** UADx native build (the
`/Components/UAD Empirical Labs Distressor.component` twin passes through offline); renders headless here —
re-verify on new machines. It adds level + harmonics → **A/B loudness-matched** ([[level-match]] / `render-ab`).
Comp/color/glue stage, NOT a master — hand off to [[finalize-mix]] / [[master-track]]. Needs `uv sync --extra
vst`. Measure crest / LRA / true-peak (+ THD/H2/H3 if Dist used, + low-band shift if HP used) before→after;
defer to the skill + `docs/vst/distressor.md`. Report curve + settings, before→after numbers, and the path.
