---
description: Drive the SSL Native Bus Compressor 2 (measured) — VCA bus glue / drum-bus / parallel, headless.
argument-hint: <wav-or-bus> [goal: glue|mix-glue|parallel|pump]
---

Invoke the **ssl-bus-compressor-2** skill on `$ARGUMENTS`.

`$1` = a stereo bus / drum submix; optional `$2` = the goal. SSL Native Bus Compressor 2 is the SSL G-series
**VCA "glue"** comp. Classic glue = **2:1 or 4:1, slow attack (10–30 ms), AUTO release, only 2–4 dB GR**,
makeup to match. **Slow attack preserves transients here** (measured: 30 ms passed +2.4 dB more peak than
0.1 ms); **AUTO release = smooth glue, fixed fast releases pump**; **threshold is relative to input level —
dial it to the GR, not a dBFS number**. The tooling gotcha: `ratio`/`release_s`/`sidechain_hpf_hz`/
`oversampling` are string enums and the switches are bools, so `apply-vst-chain`'s float-only dict can't set
them → drive it through the [[vst-preset]] harness (`presets/vst/apply_vst_preset.py`, presets
`ssl-bc2-drum-glue` / `ssl-bc2-mix-glue` / `ssl-bc2-parallel-smash`). The built-in **MIX** knob is parallel
(100% = wet); **S/C HPF** stops the kick pumping the bus. Renders headless via Pedalboard (SSL Cloud license —
verify on new machines). It's a glue stage, NOT a master — hand off to [[master-track]]. Needs
`uv sync --extra vst`. Measure crest/LRA/true-peak + GR before→after to prove glue (not just louder); defer to
the skill + `docs/vst/ssl-bus-compressor-2.md`. Report settings, before→after crest/LRA, measured GR, and the path.
