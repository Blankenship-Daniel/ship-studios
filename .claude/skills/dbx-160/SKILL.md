---
name: dbx-160
description: "Use when running the UADx dbx 160 Compressor for punchy/aggressive VCA compression on drums (kick/snare/room), bass, or a drum bus — 'dbx 160', 'dbx compressor', 'put the dbx on the snare/kick/drums/bass', 'that dbx snare thwack/knock', 'punchy VCA compression', 'add punch to the drums', 'parallel-smash the drum bus', 'New York compression', '4:1 on everything'. The measured, plugin-specific deep-dive of [[vst-compress]] — a feed-forward, true-RMS, hard-knee Blackmer-VCA compressor that on drums ADDS punch (RAISES crest) rather than leveling it, and is exceptionally CLEAN (its character is dynamic, not harmonic), grounded in the real 8-enum-param Pedalboard surface + ratio/threshold/sidechain/parallel/THD render numbers in docs/vst/dbx-160.md. Stemmy MCP, the `vst` extra."
---

# dbx-160 — drive the UADx dbx 160 Compressor (measured)

The plugin-specific, measured version of [[vst-compress]] for the **UADx dbx 160 Compressor**
(`/Library/Audio/Plug-Ins/VST3/uaudio_dbx_160.vst3`) — Universal Audio's model of **dbx Inc.'s 1976 dbx 160
"VU"** (David Blackmer's VCA compressor/limiter). It is the **feed-forward, true-RMS, hard-knee VCA** that
**ADDS punch on drums** — the crest-RAISING counterpart to the crest-*dropping* opto [[la-3a]], the
crest-*holding* tube [[fairchild-660]], and the clean VCA *glue* of [[ssl-bus-compressor-2]]. Full field guide
— param surface, the ratio / threshold / sidechain / parallel maps, the (near-zero) harmonic signature,
recipes, the variant/folklore corrections, sources — lives in
[`docs/vst/dbx-160.md`](../../../docs/vst/dbx-160.md). This skill is the workflow.

## The governing facts (read first — all measured on this rig)

1. **The ratio (`compress`) is a CREST control, and on drums it runs UP.** A feed-forward true-RMS VCA pulls
   down the *sustained body* (RMS) while the *sharp transients* ride over the top — so crest **rises**. On the
   Watercolors warm drum bus (thr −30, no makeup): **1.5–2:1 slightly LOWERS crest (16.7); 4:1 → 19.6;
   10:1 → 21.4; Inf:1 → 22.4** (source 17.9). The crossover from "levels" to "adds punch" is **between 2:1 and
   4:1**. This is the dbx, and it's why it's legendary on snare/drums.
2. **No attack/release knobs.** The true-RMS feed-forward detector sets **program-dependent** timing (dbx spec:
   attack ~15 ms for 10 dB over → ~3 ms for 30 dB over — *too slow to catch a drum's leading edge*, which is
   why transients ride through). You sculpt with **COMPRESS** (ratio), **THRESHOLD** and the **PULL/SC** sidechain.
3. **Lower threshold = more GR = MORE crest enhancement** on drums. At 4:1, thr −15 → −40 walks crest 16.6 →
   ~20.5. There's no input-drive knob — **the threshold IS the drive control** (set it relative to the source).
4. **`sc_filter` (the hardware PULL/SC) is a detector high-pass — and it INVERTS the character.** Turning it ON
   pulls the lows out of the detector so the *bright transients* drive the GR → they get clamped → **crest
   collapses (20.7 → 14.7) and the tone goes bassier**. It's a **de-harsh / transient-tame / de-pump** mode, not
   a punch mode. **OFF for punch; ON to smooth a bright bus or stop a kick over-pumping the comp.**
5. **It is an exceptionally CLEAN VCA — character is DYNAMIC, not harmonic.** 1 kHz THD: **0.00001 % at 1:1,
   0.043 % at 4:1, 0.055 % at Inf:1** — cleaner than the opto [[la-3a]] (0.37 % working) and far cleaner than the
   tube boxes. The dbx colors the *envelope*, not the spectrum.
6. **`gain` is perfectly clean makeup** (exact dB, crest invariant) — but it's *post* and can clip; at **1:1 the
   plugin is transparent.** The harness peak-trims to −1 dBFS so `gain` is mostly normalized away in a preset.
7. **`mix` (UA-added) is built-in parallel.** Because the fully-wet dbx is *already high-crest* (the RMS
   signature), parallel restores **body / level / density**, not transients — a weight move.
8. **Tooling:** 8 params, **all enums**. `thresh` / `gain` / `mix` are numeric (the `apply-vst-chain` float dict
   can set those), but **the ratio `compress` is a STRING enum (`' 4.0:1'`, leading space; `'10.0:1'`; `'Inf:1'`)
   and `meter` / `sc_filter` are string/bool** → since the ratio is the whole point, drive it through the
   **[[vst-preset]] harness** (`presets/vst/apply_vst_preset.py`, which `setattr`s every param + snaps a numeric
   ratio to the nearest valid string).
9. **It adds level + changes crest → always A/B at matched loudness** ([[level-match]] / `render-ab`). **dbx 160
   = MONO unit** (linked dual-mono on a stereo bus). It's a punch/leveling stage, **not** a master — hand off to
   [[master-track]].

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **Load the `uaudio_dbx_160.vst3` UADx native build** — it **renders headless & processes offline**
  (`RENDERS ✓` here). The `/Library/Audio/Plug-Ins/Components/UAD dbx 160.component` and
  `/VST3/Universal Audio/.../UAD dbx 160.vst3` twins are legacy UAD builds and **pass audio through unprocessed**
  offline — never use them ([[vst-verify]] / [[vst-hosting-outside-daw]]). UADx native is the no-iLok-dongle
  perpetual lineage, but re-verify `RENDERS ✓` on a new machine.
- Balance the bus first ([[mix-balance]]); hand the punched/glued result to [[master-track]] — this is a
  punch/leveling stage, **not** a master/limiter.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest / LRA / PLR / true-peak) + `[L] measure-microdynamics`
   (per-band block-crest + punch) + `[L] measure-spectrum` (centroid + low/low-mid ratio). The "before."
2. **Pick the move** from the table below. Decide the **ratio** (2:1 to gently level, 4:1 for the signature
   punch, ∞:1 for hard limiting / parallel), the **threshold** (lower = more GR = more punch), and whether to
   engage **PULL/SC** (only to tame a bright bus / de-pump a bass-heavy one).
3. **Apply via the preset harness** (so `compress`/`sc_filter`/`meter` land):
   `…/stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py presets/vst/dbx160-*.json <in> <out>`.
   Ready-made: **`dbx160-drum-punch`** (validated ★), **`dbx160-bus-glue`**, **`dbx160-parallel-punch`**.
4. **Dial it to the result:** raise the **ratio** or lower the **THRESHOLD** for more punch (watch crest *climb*);
   **PULL/SC ON** if it pumps on a bass-heavy bus or the top is spitty (crest will *fall*); **GAIN** for makeup;
   **MIX** down for parallel weight. Re-measure after each change.
5. **Prove it** — re-`measure-loudness` / `measure-microdynamics` / `measure-spectrum`: for the punch presets
   expect **broadband crest UP**, the **kick (low-band) crest down** (body tightened), **low-mid fuller**, LRA
   tighter; for bus-glue expect **crest slightly down** (leveling). **A/B loudness-matched** (`[L] render-ab` /
   [[level-match]]) so "punchier" isn't just "louder."
6. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch pumping (lower the ratio / engage PULL/SC) or a
   thin/over-compressed bus; reconcile any mono "dull/dynamics" flag against the stereo meters
   ([[gemini-mastering-feedback-cross-check]]).

## Recipes (measured starting points — re-dial to your level)

| Goal | compress (ratio) | thresh dBFS | sc_filter | mix | Preset |
|---|---|---|---|---|---|
| **Drum-bus punch** (the signature) ★ | **4.0:1** | **−24** | off | 100 | `dbx160-drum-punch` |
| **Gentle bus glue / leveling** | 2.0:1 | −22 | off | 100 | `dbx160-bus-glue` |
| **Parallel weight / density** | **Inf:1** | −30 | off | **50** | `dbx160-parallel-punch` |
| **Snare / kick (close mic)** | 4–6:1 | to ~6–10 dB GR | off | 100 | (recipe) |
| **Bass DI** | 3–5:1 | to ~3–6 dB GR | off/on | 100 | (recipe) |
| **Room / ambience smash** | ∞:1 | low | off | 100 | (recipe) |
| **Tame a bright / pumping bus** | 4–6:1 | engaging | **on** | 100 | (recipe) |

★ validated gentle-to-punch set (`presets/vst/dbx160-*.json` → `projects/watercolors/mix/dbx160_*_demo.wav`).
**COMPRESS** is the crest control (≤2:1 levels, 4:1+ punches, ∞:1 hard-limits). **THRESHOLD** lower = more GR =
more punch (it's the drive). **PULL/SC** off = punch, on = de-harsh/de-pump (crest drops + bassier). **GAIN**
clean makeup (peak-trimmed away in a preset). **MIX** = parallel (weight, not transient-restore). Leave `power`
on, `master_bypass` off; the harness peak-trims to −1 dBFS so loudness-match before judging.

## Reporting to the user

State the settings (ratio · threshold · sidechain on/off · mix), before→after **crest / LRA / true-peak** + the
per-band move (broadband crest up but kick low-band crest down = "tighter kick, more punch") and any tonal shift,
that it ran headless via the `uaudio_dbx_160.vst3` build, and that the character is **clean feed-forward true-RMS
VCA punch — it ADDS crest on drums (dynamic, not harmonic, ~0.04 % THD)**, the opposite of an opto leveler. A/B
loudness-matched so "punchier" isn't "louder."

## Pitfalls

- **Wrong build = passthrough** — the `/Components/UAD dbx 160.component` and `Universal Audio/.../UAD dbx 160.vst3`
  twins pass audio through offline. Load `uaudio_dbx_160.vst3`; verify `RENDERS ✓` + measure *detail* ([[vst-verify]]).
- **`compress` / `sc_filter` / `meter` are string/bool enums** — `apply-vst-chain`'s float dict can't set them
  (you'd be stuck at the default 4:1, sc off). Use the [[vst-preset]] harness for any ratio/sidechain recipe.
- **No attack/release knobs** — timing is automatic/program-dependent; don't go looking. Control transient
  bleed-through with the *ratio + GR amount* and use GAIN/MIX for contrast.
- **Don't expect a leveler** — at 4:1+ the dbx RAISES crest (punch), it doesn't smooth dynamics. For smoothing
  use the [[la-3a]] (opto, drops crest) or [[ssl-bus-compressor-2]] (clean VCA glue).
- **Bass-heavy bus pumping?** Engage **PULL/SC** (detector HPF) so the kick stops over-triggering — but note it
  also tames the bright transients (crest down, bassier), so it's a tradeoff, not free punch.
- **Modest ratios aren't gentle** — even 2:1 reads more aggressive than the number suggests on this colored VCA;
  trust the meters.
- **GAIN is post and can clip** — make up modestly; it's also peak-trimmed away in a preset, so set the *ratio +
  threshold* for character, not the gain.
- **The threshold dial reads mV/V, not dB** (the host param is full-scale −55…0 dB; the artwork stays mV).
- **It's not a peak limiter / not a master** — its RMS attack lets transients through; hand off to
  [[master-track]] for true-peak control / loudness.
- **Don't conflate variants** — the plugin is the hard-knee **1976 160 VU**: no OverEasy, no negative/INFINITY+
  ratio (those are 160X/160A). (See `docs/vst/dbx-160.md` Part B.)

## Related

- [`docs/vst/dbx-160.md`](../../../docs/vst/dbx-160.md) — the full measured field guide (Part A measured + Part B cited)
- [[vst-compress]] — the generic compressor skill this specializes · [[la-3a]] — opto LEVELER (drops crest, odd-harmonic) vs the dbx's punch (raises crest, clean) · [[fairchild-660]] — tube COLOR (holds crest, even-harmonic) · [[ssl-bus-compressor-2]] — clean VCA stereo glue
- [[vst-preset]] — apply enum chains (required for the ratio) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants
- [[finalize-mix]] / [[stem-master]] — stages this fits · [[drum-punch]] — pure-DSP transient design (no plugin) · [[multiband-compress]] — band-split dynamics
- [[gemini-mastering-feedback-cross-check]] — why meters (not Gemini mono) own crest/GR
