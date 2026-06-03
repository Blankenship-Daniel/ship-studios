---
description: Drive the UADx Manley Variable Mu (measured) — clean/transparent vari-mu tube glue, leveling, M/S, headless.
argument-hint: <wav-or-bus> [goal: drum-glue|bus-glue|parallel|master-ms]
---

Invoke the **manley-variable-mu** skill on `$ARGUMENTS`.

`$1` = a bus / mix / master / stem / loop; optional `$2` = the goal. The UADx Manley Variable Mu is an all-tube
**variable-mu** compressor and the **CLEAN / transparent** vari-mu — measured on the Watercolors warm drum bus
it **levels macro-dynamics while KEEPING transients** (validated `manley-vari-mu-drum-glue`: crest 17.17→**17.39**,
LRA 2.44→**2.07**, low-mid 0.179→0.184, low-band punch held, TP −0.98), where the [[fairchild-660]] on the same
bus *dropped* crest and thickened more (clean glue vs thick color). There is **no ratio knob** — sculpt with
**COMP vs LIMIT** (≈1.5:1 vs ≈4:1→20:1; measured LIMIT −5.8 dB vs COMP −2.2 dB GR at thresh 4), **THRESHOLD**
(lower = more GR; 10 = MAX = least — *direct* mapping, unlike the Fairchild's inverted enum), the shared **DUAL
INPUT** drive (0–10), **ATTACK** (0=slow/punch … 10=fast/clamp), **RECOVERY** (Med = open, Fast = dense; Slo 8 s
… Fast 0.2 s), and the **inverted HEADROOM** lever (lower = hotter into the tubes/more color/less GR). **Color is
even-harmonic and level-dependent** — drive DUAL INPUT up / HEADROOM down to hit the tubes (clean at −18 dBFS,
0.21 % THD when driven hot). **HP SIDECHAIN In** (fixed −3 dB @ 100 Hz) stops bass pumping the bus; **MIX** is
built-in parallel; and **real M/S** (`in/out_matrix` M-S + `ctrl_link`/`sc_link` **Unlink** → `l_*`=MID, `r_*`=SIDE)
widens by squeezing the mid (measured corr 0.975→0.956, width −18.9→−16.4 dB) — the move the **mono** 660 can't do.
The tooling gotcha: **all 23 params are enums**, so `apply-vst-chain`'s float dict can't set the string switches →
drive it through the [[vst-preset]] harness (`presets/vst/apply_vst_preset.py`, presets `manley-vari-mu-drum-glue`
/ `manley-vari-mu-bus-glue` / `manley-vari-mu-parallel-smash` / `manley-vari-mu-master-ms-glue`). Load the
**`uaudio_manley_variable_mu.vst3`** UADx native build (the `/Components/UAD Manley Variable Mu.component` twin
passes through offline); renders headless here — re-verify on new machines. It adds level + harmonics → **A/B
loudness-matched**. It's a color/glue stage, NOT a master — hand off to [[master-track]]. Needs `uv sync --extra
vst`. Measure crest/LRA/true-peak (+ low-mid ratio + low-band punch; correlation/width for M/S) before→after to
prove glue-not-crush; defer to the skill + `docs/vst/manley-variable-mu.md`. Report settings, before→after
crest/LRA + the imaging shift (if M/S), and the path.
