---
description: Dial the UADx Hitsville EQ (Motown 7-band Studio graphic EQ) for fast, forgiving tone — measured.
argument-hint: <audio.wav> [goal: motown-drums/warm-bus/mix-glue/air/soften/bass]
---

Invoke the **hitsville-eq** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (Motown drum bus / warm-tight bus / gentle mix polish / air /
soften DI / bass body). The **Hitsville EQ** is the single-channel **Studio EQ** — UA's model of the custom
**Motown / Hitsville U.S.A. 7-band graphic equalizer** (built by Mike McLean): fixed bands at
**50/130/320/800/2k/5k/12.5k**, inductor-based **proportional-Q**, a master **GAIN**, and a 3-way
**In/Out/Off** switch. A **clean, fast, forgiving "vibe" EQ** (the "butter" Motown character), not surgical
(pair with [[fabfilter-pro-q-4]] for surgery). The per-track/channel counterpart to the Mid/Side mastering
twin [[hitsville-eq-mastering]]; a tonal stage — master/limit AFTER in [[master-track]].

Key facts (measured): the **seven band knobs ARE dB** (−8…+8 in 1 dB steps; +8 dial ≈ +8 dB) and are
**numeric → `apply-vst-chain`'s float dict sets all of them** (unlike the console strips / the Mastering twin
whose 0–8 knob is NOT dB). It's a **CLEAN EQ — 0.000 % THD** at mix level; the *only* distortion is the `gain`
makeup **clipping past 0 dBFS** (gain +8 on a −1 dBFS sine → 4.1 %) → use `gain` to CUT, not to push level;
gain-stage INTO it (harness `input_gain_db`) for the "driven Motown colour." **Proportional-Q**: bigger boost
= narrower bell (peak:octave 1.1→1.8→3.5 at +2/+5/+8); bands **overlap/interact** (~+1.5–2 dB into neighbours)
→ dial broad. `bypass` = the **In/Out/Off** switch (In=EQ active, Out=EQ off but transformer/amp colour kept,
Off=true bypass).

**Headless:** load the UADx **`uaudio_hitsville_eq.vst3`** (renders headless here — NOT the `UAD Hitsville
EQ.component` twin = passthrough, NOT `_eq_mastering` (the M/S twin → [[hitsville-eq-mastering]]) or `_chambers`
(the reverb)). The 7 band gains + `gain` set via `apply-vst-chain` directly; `bypass`/`power` (enums, defaults
already correct) and the gain-stage need the [[vst-preset]] harness. Ready presets:
`presets/vst/hitsville-eq-motown-drum-bus.json` · `hitsville-eq-warm-drum-glue.json` · `hitsville-eq-mix-glue.json`.
Needs `uv sync --extra vst`; iLok account, no dongle (verified-headless here — re-verify elsewhere with a real boost).

**Measure before & after** with `[L] measure-spectrum` (band ratios / centroid / tilt) + `[L] measure-loudness`
(crest) — a good tone move keeps crest (it's EQ, not compression); a 0.00 change = wrong build. A/B
loudness-matched with `[L] render-ab`. Full param surface + per-band isolation / THD / proportional-Q tables:
[`docs/vst/hitsville-eq.md`](../../docs/vst/hitsville-eq.md). Defer to the skill; report the band moves (by Hz)
+ `gain`, before→after band-ratios/centroid/tilt/crest, the preset/`.state` path, and that mastering/limiting
is deferred to [[master-track]].
