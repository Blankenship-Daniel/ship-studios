---
name: ssl-bus-compressor-2
description: "Use when running the SSL Native Bus Compressor 2 for bus glue / drum-bus compression — 'SSL bus comp', 'SSL Native Bus Compressor 2', 'glue the drum bus with the SSL', 'that SSL G-bus glue/quad-comp sound', 'bus compress the mix with the SSL', 'parallel/NY comp on the drums', or any VCA stereo-bus glue with that plugin. The measured, plugin-specific deep-dive of [[vst-compress]] — the SSL G-series quad bus VCA 'glue' comp, grounded in the real Pedalboard param surface + threshold/attack/release/ratio/parallel/SC-HPF render numbers in docs/vst/ssl-bus-compressor-2.md. Stemmy MCP, the `vst` extra."
argument-hint: <wav-or-bus> [goal: glue|mix-glue|parallel|pump]
---

# ssl-bus-compressor-2 — drive the SSL Native Bus Compressor 2 (measured)

The plugin-specific, measured version of [[vst-compress]] for **SSL Native Bus Compressor 2**
(`/Library/Audio/Plug-Ins/VST3/SSL Native Bus Compressor 2.vst3`) — the **VCA stereo-bus "glue"** comp
(the SSL 4000 G-series quad bus compressor in software). It's the *cohesion/density* counterpart to the
console-tone strips ([[api-vision-channel-strip]] / [[kit-bb-a5]] / [[kit-bb-n105]] / [[studer-a800]]) and
the transient-design [[softube-transient-shaper]]. Full field guide — param surface, the threshold→GR map,
the attack/release/ratio behavior, parallel MIX, SC-HPF, recipes, pitfalls, sources — lives in
[`docs/vst/ssl-bus-compressor-2.md`](../../../docs/vst/ssl-bus-compressor-2.md). This skill is the workflow.

## The governing facts (read first)

1. **It's a GLUE comp, not a tone box.** The classic recipe is the whole point: **ratio 2:1 or 4:1,
   slow attack (10–30 ms), AUTO release, only 2–4 dB GR, makeup to match.** Measured on the Watercolors
   warm drum bus that lands a *gentle* glue — crest 17.2→16.5, LRA 2.44→2.07 (tighter), +0.7 LU, true-peak
   still −0.98. Reach for more GR only deliberately.
2. **Slow attack DOES preserve transients here — measured (the textbook holds, unlike the API strip).**
   At fixed GR, **30 ms attack let the kick/snare peak through 2.4 dB louder than 0.1 ms** (peak −9.0 vs
   −11.4; crest 19.3 vs 18.2). Use **10–30 ms for punch**, fast (0.1–3 ms) to clamp peaks. Cross-check
   against [[api-vision-channel-strip]] where "slow = punch" was *false* — it's plugin-specific, so measure.
3. **AUTO release = smooth program-dependent glue; fixed fast releases PUMP.** Measured: AUTO gave crest
   ~18; fixed **0.1–0.6 s gave crest ~21** (more pump/breath, more apparent GR). AUTO is the safe glue
   default; pick a fixed fast release on purpose for an aggressive/pumping effect.
4. **Threshold is RELATIVE to input level, not dBFS — dial it to the GR, never to a number.** On a
   −17 LUFS / −1 dBFS bus: thresh **+5 ≈ 3–4 dB GR**, **0 ≈ 6.7 dB**, **−8 ≈ 11 dB**. On other material
   the same number gives different GR — gain-stage consistently (harness `input_gain_db`) and re-dial.
5. **The tooling gotcha (the big one):** `ratio`, `release_s`, `sidechain_hpf_hz`, `oversampling` are
   **string enums** and `comp_bypass`/`external_s_c`/`mix_lock` are **bools** — `apply-vst-chain`'s
   **float-only** `parameters` dict can set only `threshold_db` / `makeup_gain_db` / `attack_ms` /
   `dry_wet_mix`. Since **ratio and release are fundamental**, you must drive this through the
   **[[vst-preset]] harness** (`presets/vst/apply_vst_preset.py`, which `setattr`s every param). Enum
   strings are exact: `ratio="4:1"`, `release_s="AUTO"`, `sidechain_hpf_hz="59.9"` (non-round!).
6. **Meters own it** (Gemini hears ~16 kbps mono): **GR = measured peak/RMS drop; glue = crest/PLR down a
   little + LRA tighter.** `[L] measure-loudness` / `[L] measure-microdynamics`. A "glued" feel with no
   crest/LRA change is a level illusion. Cross-check Gemini's mono "dull/squashed" claims vs the meters
   ([[gemini-audio-understanding]]).

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- The plugin **renders headless via Pedalboard** (`changed:true` on this rig). SSL Native is **iLok/PACE**
  machine-activated (authorized here) — so it carries the **iLok render-farm landmine** caveat: **re-verify
  load+render on any new machine**, and an unactivated/demo seat may load yet render demo-noise/silence
  ([[vst]]).
- It's a **STEREO BUS** insert (a drum/mix submix), not a master limiter and not a single mono close mic.
  Balance the bus first ([[mix-balance]]); hand the glued result to [[master-track]] for loudness/limiting.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest / PLR / LRA / true-peak) + `[L] measure-microdynamics`
   on the bus. The "before" column.
2. **Pick the move** from the table below. Start gentle (glue), escalate only on purpose.
3. **Gain-stage consistently** — the harness `input_gain_db`; threshold is relative to it.
4. **Apply via the preset harness** (ratio/release are string enums → `apply-vst-chain` can't set them):
   `…/stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py presets/vst/ssl-bc2-*.json <in>
   <out>`. Ready-made: **`ssl-bc2-drum-glue`** (validated), **`ssl-bc2-parallel-smash`**, **`ssl-bc2-mix-glue`**.
   For a float-only nudge (threshold/makeup/attack/mix on an already-good ratio/release) `apply-vst-chain`
   works; set `dump_state=true` for a reproducible re-render.
5. **Dial threshold to GR** — re-measure; target **2–4 dB GR** for glue (peak/RMS drop). Lower threshold =
   more GR; reset makeup so output ≈ input loudness for an honest A/B.
6. **Prove it** — re-`measure-loudness`/`measure-microdynamics`: expect crest down *a little* (not
   collapsed), **LRA tighter**, true-peak safe; punch retained if you used a slow attack. A/B
   loudness-matched (`[L] render-ab` or [[level-match]]).
7. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch pumping (fast release / too much GR) or a
   choked/dull bus; reconcile any mono "dull" flag against the stereo meters before reacting.

## Recipes (measured starting points — re-dial threshold to your level)

| Goal | Ratio | Attack | Release | GR target | MIX | S/C HPF | Preset |
|---|---|---|---|---|---|---|---|
| **Drum-bus glue** ★ | 4:1 | 30 ms | AUTO | 2–4 dB | 100% | OFF | `ssl-bc2-drum-glue` |
| Gentle **mix-bus glue** | 2:1 | 10 ms | AUTO | 1–3 dB | 100% | ~60 Hz | `ssl-bc2-mix-glue` |
| **Parallel / NY** smash | 10:1 (or X) | 1–3 ms | 0.3 s | 8–12 dB | 30–50% | OFF | `ssl-bc2-parallel-smash` |
| **Pump / EDM** glue | 4:1 | 10 ms | 0.1 s | 4–6 dB | 100% | ~60–90 Hz | (from drum-glue, release 0.1) |
| Tame **peaks** (control) | 4:1 | 0.1–1 ms | AUTO | 3–6 dB | 100% | OFF | (from drum-glue, fast attack) |

★ the validated gentle glue (`presets/vst/ssl-bc2-drum-glue.json` → `projects/watercolors/mix/ssl_bc2_glue_demo.wav`).
**S/C HPF** takes the kick out of the detector so it stops pumping the whole bus — measured: 60 Hz dropped
GR 8.9→7.8 dB and let the kick punch ~1 dB more through. **MIX** is the built-in parallel knob (100% = fully
wet). **Oversampling** 2x/4x is free offline (default 4x); leave it on. External S/C, 360 Console, GroupSense,
Mix Lock — leave default for standalone offline use.

## Reporting to the user

State the settings (ratio / attack / release / GR / MIX / SC-HPF), before→after **crest / LRA / true-peak**
and the measured **GR**, that it ran headless, and that glue came from modest GR + slow attack + AUTO (not
squash). A/B loudness-matched so "glued" isn't just "louder."

## Pitfalls

- **Don't drive it through `apply-vst-chain` alone** — it can't set ratio/release/SC-HPF/oversampling
  (string enums) or the bool switches → silently leaves them at default. Use the [[vst-preset]] harness.
- **Threshold ≠ dBFS** — a preset's threshold number won't reproduce the same GR on a different-level bus;
  re-dial to the GR.
- **Louder ≠ better** — makeup hides over-compression; judge by crest/LRA, not level.
- **Too-fast attack kills drum punch** — verify peak/crest; slow attack (10–30 ms) preserves transients here.
- **Fixed fast release pumps** — that's a feature for EDM, a bug for transparent glue (use AUTO).
- **It's not a master** — don't limit here; this is a finalize-mix / stem-master / drum-bus glue stage.
- **SC-HPF values are non-round strings** (`'59.9'`, `'79.9'`, `'120.0'`) — pull from the plugin's valid
  list; `'60.0'` is rejected.

## Related

- [`docs/vst/ssl-bus-compressor-2.md`](../../../docs/vst/ssl-bus-compressor-2.md) — the full measured field guide
- [[vst-compress]] — the generic compressor skill this specializes · [[finalize-mix]] — the pre-master bus-glue stage this fits · [[stem-master]] — per-stem/bus corrective stage
- [[vst-preset]] — apply enum/gain-staged chains (required here) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants
- [[drum-punch]] — pure-DSP transient design (no plugin) · [[multiband-compress]] — per-band dynamics (no plugin) · [[mix-balance]] — balance the bus before glue
- [[api-vision-channel-strip]] / [[kit-bb-a5]] / [[kit-bb-n105]] / [[studer-a800]] — console/tape *tone* siblings · [[gemini-audio-understanding]] — why meters (not Gemini mono) own GR/crest
