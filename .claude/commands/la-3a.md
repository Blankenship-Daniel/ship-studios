---
description: Drive the UADx Teletronix LA-3A (measured) — solid-state opto leveling / glue / parallel smash, headless.
argument-hint: <wav-or-bus> [goal: drum-glue|bus-level|parallel|guitar|vocal]
---

Invoke the **la-3a** skill on `$ARGUMENTS`.

`$1` = a bus / stem / loop; optional `$2` = the goal. The UADx Teletronix LA-3A is a **solid-state electro-
optical (T4) LEVELER** — the 1969 successor to the tube LA-2A. Unlike the crest-holding tube [[fairchild-660]]
it **actually levels: it reduces crest** (measured on the Watercolors warm drum bus — crest 17.2→14.2 at
pr 4 ≈ 3 dB GR, →12.8 at pr 6). There is **no ratio/attack/release** (opto, program-dependent) — sculpt with
**PEAK REDUCTION** (amount; dead zone ~0–2, bites from 3–4, more = more GR + lower crest, make up with GAIN),
**COMP/LIM** (Limit clamps harder + darker), **HF EMPHASIS** (the drum control: raise it to take lows out of
the detector so the kick stops pumping → less GR, more punch + brightness; hf 0 = full-range = most GR +
darkest + most pumped), **GAIN** (clean makeup, ~4.9 dB/unit) and **MIX** (parallel; blends AFTER makeup so
raise GAIN when you blend down). It colors with **odd/3rd-harmonic solid-state grit, not tube warmth**
(~0 % THD until compressing, then ~0.37 %; clean at rest). The tooling gotcha: 8 params all enums —
**`comp_limit` and `meter` are STRING enums** the float dict can't set → drive it through the [[vst-preset]]
harness (`presets/vst/apply_vst_preset.py`, presets `la3a-drum-glue` / `la3a-bus-level` / `la3a-parallel-smash`).
Load the **`uaudio_la3a.vst3`** UADx native build (the `/Components/UAD Teletronix LA-3A.component` legacy twin
passes through offline); renders headless here — re-verify on new machines. **LA-3A = mono** (dual-mono on a
stereo bus). It adds level + grit → **A/B loudness-matched**. Leveling/glue stage, NOT a master — hand off to
[[master-track]]. Needs `uv sync --extra vst`. Measure crest/LRA/true-peak + low-mid ratio + per-band punch
before→after to prove leveling-not-just-louder; defer to the skill + `docs/vst/la-3a.md`. Report settings,
before→after crest/LRA/density + any tonal shift, and the path.
