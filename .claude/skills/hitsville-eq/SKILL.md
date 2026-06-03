---
name: hitsville-eq
description: "Use when running the UADx Hitsville EQ — the single-channel Studio EQ (UA's model of the custom Motown / Hitsville U.S.A. 7-band graphic EQ built by Mike McLean) — for fast, forgiving 'Motown' tone on drums, drum bus, bass, vocals, guitars or a mix bus — 'Hitsville EQ', 'Motown EQ', 'that Motown sound / butter EQ', 'Motown drum / bass / vocal tone', 'use the Hitsville EQ', '7-band Motown graphic EQ', or when you want a clean, hard-to-make-harsh fixed-frequency character EQ. The measured, plugin-specific deep-dive of [[vst-eq]] — a 7-fixed-band (50/130/320/800/2k/5k/12.5k), ±8 dB stepped, inductor-based proportional-Q graphic EQ + a master GAIN + a 3-way In/Out/Off switch; grounded in the real 11-param surface + isolation/THD/proportional-Q render numbers in docs/vst/hitsville-eq.md. The single-channel CHANNEL counterpart to the Mid/Side mastering twin [[hitsville-eq-mastering]]; pair with [[fabfilter-pro-q-4]] for surgery. Stemmy MCP, the `vst` extra. UADx native (iLok account, no dongle; verified-headless on this rig)."
argument-hint: <audio.wav> [goal: motown-drums/warm-bus/mix-glue/air/soften/bass]
---

# hitsville-eq — drive the UADx Hitsville EQ (the Motown Studio EQ, measured)

The plugin-specific, measured version of [[vst-eq]] for the **Hitsville EQ** — the single-channel **Studio
EQ** (`/Library/Audio/Plug-Ins/VST3/uaudio_hitsville_eq.vst3`), UA's model of the custom **7-band graphic
equalizer** built in-house at Motown's **Hitsville U.S.A.** studio (Detroit) by chief engineer **Mike
McLean**. It's a **clean, fast, forgiving "vibe" EQ** — fixed Motown frequencies, interactive
proportional-Q bells, a tiny ±8 dB range that keeps you out of trouble, and a makeup GAIN. The **channel**
counterpart to the Mid/Side mastering twin [[hitsville-eq-mastering]]; reach for [[fabfilter-pro-q-4]] when
you need surgery. Full field guide — param surface, per-band isolation, proportional-Q + THD numbers,
recipes, history — lives in [`docs/vst/hitsville-eq.md`](../../../docs/vst/hitsville-eq.md). This skill is
the workflow.

## The governing facts (read first — measured)

1. **The band knobs ARE dB — and float-dict drivable.** Seven fixed bands (`1_50` … `7_12500`) + a master
   `gain`, each **−8 … +8 dB in 1 dB steps** (real dB: +8 dial ≈ +8 dB measured). Because they're **numeric**,
   `apply-vst-chain`'s float dict sets every one of them — **unlike the SSL/Neve/API strips (and the Mastering
   twin, whose 0–8 knob is NOT dB and needs the harness)**, this EQ runs straight from `apply-vst-chain`. Only
   `bypass` (string `Off/Out/In`), `power` & `master_bypass` (bool) need the [[vst-preset]] harness — and their
   defaults (`In`/on) are already correct.
2. **It's a CLEAN EQ — no saturation at mix level.** Measured **0.000 % THD** (1 kHz, −20/−6/−1 dBFS, flat or
   with a band boosted). The *only* distortion is the **`gain` makeup clipping past 0 dBFS** (gain +8 on a
   −1 dBFS sine → 4.1 %). **Use `gain` to CUT (compensate boosts), never to push level.** For the reviewers'
   "driven Motown harmonic colour," gain-stage INTO it (harness `input_gain_db`) — `apply-vst-chain` can't.
3. **Proportional-Q + interactive bands.** Bigger boost = narrower bell (measured peak:octave **1.1→1.8→3.5**
   at +2/+5/+8). Bands **overlap** — a boost bleeds **~+1.5–2 dB into each neighbour**. Small moves = a broad
   musical tilt; this is a character EQ, not a surgical one. Centers are **fixed** (no sweep). `1_50` is a low
   bell; `7_12500` is a broad HF "air" bell/shelf.
4. **`bypass` is the 3-way IN/OUT/OFF hardware switch.** `In` = EQ active (default); `Out` = EQ bypassed but
   the modelled transformer/amp path stays in-circuit (measured +1.9 dB headroom signature, ≤0.2 dB tilt —
   near-flat colour); `Off` = true hard bypass (0.00).
5. **It's an EQ, not dynamics.** Adding lows lowers crest slightly (denser), but it adds no punch/glue — use
   [[drum-punch]] / a comp for that. It's a per-track/bus **tone** stage; **master/limit AFTER in
   [[master-track]]**, not here.
6. **Meters own this** (Gemini hears mono): `[L] measure-spectrum` (tilt / band ratios / centroid),
   `[L] measure-loudness` (crest), `[L] measure-microdynamics`, `check-clipping`. A **0.00 change = passthrough**
   (wrong build) — re-measure detail, not `changed:true`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **`uaudio_hitsville_eq.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"hitsville"}`. Load the
  **UADx `uaudio_*.vst3`** build (renders headless — verified here); **NOT** the `UAD Hitsville EQ.component`
  twin (passthrough offline), **NOT** `uaudio_hitsville_eq_mastering.vst3` (the M/S mastering version →
  [[hitsville-eq-mastering]]) or `uaudio_hitsville_chambers.vst3` (the reverb). iLok **account** (no dongle);
  **re-verify load+render on a new machine** with a real boost (`probe_plugin.py "hitsville_eq"`).
- **Two ways to drive it:** the seven band gains + `gain` are numeric → set them via `apply-vst-chain`'s
  `parameters` float dict directly. Use the **[[vst-preset]]** harness when you want the gain-stage/peak-trim,
  to DRIVE it for colour (`input_gain_db`), or to set the `bypass`/`power` enums.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (tilt / band ratios / centroid) + `[L] measure-loudness` (crest) +
   `[L] measure-microdynamics`. The "before" column. Balance the source first ([[mix-balance]]) — a balance
   problem is not an EQ problem.
2. **Pick the move by fixed band** — weight = `1_50` (+2…+3); body = `2_130`; de-box/mud = `3_320` (−2);
   honk = `4_800`; attack/presence = `5_2000` (+1); snare/stick snap = `6_5000` (+1…+2, watch 5–7 kHz
   brittleness on hat/cymbals — the house hi-hat note); air = `7_12500` (+1…+2). Keep moves small — at ±1–2
   the proportional-Q is broad/musical.
3. **Compensate level** — set `gain` to a **cut** (−1…−2) to offset the boosts and stay peak-safe. Never
   gain-BOOST hot material (it clips past 0 dBFS).
4. **(Optional) drive for colour** — only if you want the Motown harmonic "yum": via the harness, raise
   `input_gain_db` (e.g. +6…+12) and pull `gain`/output down to compensate. At unity it's a clean EQ (0 % THD).
5. **Apply** — fastest: `[L] apply-vst-chain` with `parameters:{"1_50":3,"3_320":-2,...,"gain":-2}`. For a
   reproducible/gain-staged render use [[vst-preset]] (`apply_vst_preset.py <preset.json> <in> <out>`); set
   `dump_state=true` for byte-exact re-renders. Output → `projects/<track>/mix/`.
6. **Verify** — re-measure. A good tone move = band ratios / centroid / tilt shifted as intended with **crest
   essentially preserved** (it's EQ, not compression); `check-clipping` (the `gain`/boosts can raise true-peak).
   A/B loudness-matched with `[L] render-ab`.

## Recipes (measured starting points)

| Goal | Move (band : dB) | gain |
|---|---|---|
| **Motown drum bus (forward)** ★ | 50 +3 · 130 +1 · 320 −2 · 2000 +1 · 5000 +2 · 12500 +2 | −2 |
| **Warm + tight drum bus (house)** ★ | 50 +3 · 130 +1 · 320 −2 · (top restrained: 5000 0 · 12500 +1) | −1 |
| **Gentle mix/bus polish** | 50 +2 · 320 −1 · 5000 +1 · 12500 +1 | −1 |
| Motown "air" (strings/pads/overheads) | 12500 +2…+3 · 130 +1…+2 | −1 |
| Soften DI guitar / lead | 5000 −2…−3 · 2000 +2 | +1…+2 |
| Bass body | 130 +2 · 320 −2 (de-mud) · 800 +1 | −1 |

★ validated dry→processed on the watercolors drum bus: **motown** low 0.542→0.661, low-mid 0.378→0.248,
centroid 3128→3531 (+403 air), crest 23.6→22.9 (transients kept). **warm** low→0.696, low-mid→0.249, centroid
**3129 (≈dry — warm, not brighter)**, tilt −2.26→−2.43. Presets: `presets/vst/hitsville-eq-motown-drum-bus.json`
· `hitsville-eq-warm-drum-glue.json` · `hitsville-eq-mix-glue.json`.

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset (and `.state` if dumped).
- Report: the band moves (by Hz) + `gain`, before→after **band ratios / centroid / tilt / crest**, that it ran
  headless (real Δ, not 0.00), and that mastering/limiting is deferred to [[master-track]]. A/B loudness-matched.

## Pitfalls

- **`gain` clips past 0 dBFS** — the only distortion at mix level. Use it to CUT; gain-stage for drive via the
  harness `input_gain_db`.
- **No saturation without drive** — at unity it's a clean EQ (0 % THD). Don't expect tape/console warmth; add a
  tape/console stage ([[studer-a800]] / [[ampex-atr-102]] / [[kit-bb-n105]] / [[helios-type-69]]) for that.
- **Fixed centers, ±8 dB cap, 1 dB steps** — a character EQ, not corrective. No notching, no in-between
  frequencies → use [[fabfilter-pro-q-4]] for surgery.
- **Bands interact** (~1.5-octave overlap) — adjacent moves sum; dial broad, don't max one band.
- **`bypass`/`power` are enums** — only the harness can set them (defaults `In`/on are already right). The seven
  band gains + `gain` DO set via `apply-vst-chain` (numeric).
- **Load the right build** — UADx `uaudio_hitsville_eq.vst3` (not the `.component`, not the Mastering twin, not
  the Chambers reverb). iLok account, no dongle — re-verify load+render elsewhere with a real boost.
- **Watch 5–7 kHz on cymbals/hat** — `6_5000` boosts can read brittle; the warm preset leaves it flat.
- **Loudness-match before any A/B** — boosts raise level; "better" is often just "louder."

## Related

- [`docs/vst/hitsville-eq.md`](../../../docs/vst/hitsville-eq.md) — the full measured field guide
- [[hitsville-eq-mastering]] — the Mid/Side **mastering** twin (`uaudio_hitsville_eq_mastering.vst3`; Dip/Peak,
  half-speed, Motown Filters, M/S — use it on the 2-bus; this Studio EQ is the per-track/channel counterpart)
- [[vst-eq]] — the generic EQ skill this specializes · [[vst-preset]] — apply gain-staged / enum chains
- [[fabfilter-pro-q-4]] — the SURGICAL/clean EQ to pair with this BROAD one (notch with Pro-Q, shape with Hitsville)
- [[studer-a800]] / [[ampex-atr-102]] / [[kit-bb-n105]] / [[helios-type-69]] — add the harmonic warmth this clean EQ doesn't
- [[warm-drum-bus]] — the pure-DSP warm bus (tape/tilt, no plugin) · [[drum-punch]] — pure-DSP transient design
- [[master-track]] — do loudness/limiting/compliance AFTER this tonal stage · [[mix-balance]] — balance before EQ
- [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge band variants · [[vst-chain]] — the backbone recipe
- [[gemini-audio-understanding]] — why meters (not Gemini) own centroid/tilt/crest/peak
