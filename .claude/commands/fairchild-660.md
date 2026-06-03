---
description: Drive the UADx Fairchild 660 (measured) — vari-mu tube COLOR + glue/leveling, headless.
argument-hint: <wav-or-bus> [goal: color|bus-glue|parallel|tight]
---

Invoke the **fairchild-660** skill on `$ARGUMENTS`.

`$1` = a bus / stem / loop; optional `$2` = the goal. The UADx Fairchild 660 is a **variable-mu TUBE
compressor** that **COLORS more than it crushes** — measured on the Watercolors warm drum bus, **crest stays
~17–19 dB** across input/threshold while it **thickens the low-mids and keeps the punch** (validated
`fc660-drum-color`: crest 17.17→16.90, LRA 2.44→1.84, low-mid ratio 0.179→0.188, low-band punch held, TP
−0.99, +0.27 LU). There is **no ratio/attack/release** — sculpt with **INPUT** (drive = GR *and* harmonic
color), **THRESH** (higher = more GR on this build), and **TIME_CONST** (1=tightest, **4=most open/punchy**,
5/6=program-dependent auto). **SC FILTER** (~60–120 Hz) takes lows out of the detector so the bus stops
pumping; **HR** trims how hard it runs; **MIX** is built-in parallel (crush + blend dry for a NY smash). The
tooling gotcha: **all 12 params are enums**, so `apply-vst-chain`'s float dict can't set them → drive it
through the [[vst-preset]] harness (`presets/vst/apply_vst_preset.py`, presets `fc660-drum-color` /
`fc660-bus-glue` / `fc660-parallel-smash`). Load the **`uaudio_fairchild_660.vst3`** UADx native build (the
`/Components/UAD Fairchild 660.component` twin passes through offline); renders headless here — re-verify on
new machines. **660 = mono** (dual-mono on a stereo bus); for a true stereo mix / M-S use the **670**. It adds
level + harmonics → **A/B loudness-matched**. It's a color/glue stage, NOT a master — hand off to
[[master-track]]. Needs `uv sync --extra vst`. Measure crest/LRA/true-peak + low-mid ratio + low-band punch
before→after to prove color-not-crush; defer to the skill + `docs/vst/fairchild-660.md`. Report settings,
before→after crest/LRA/low-mid shift, and the path.
