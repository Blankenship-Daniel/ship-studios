---
name: fairchild-660
description: "Use when running the UADx Fairchild 660 for vintage tube color + glue/leveling on a drum bus, mix bus, vocal, or bass — 'Fairchild 660', 'vari-mu tube glue', 'that thick tube drum sound', 'parallel-smash the drums with the Fairchild', 'add tube weight/density'. The plugin-specific deep-dive of [[vst-compress]] — variable-mu tube color (vs the VCA glue of [[ssl-bus-compressor-2]]). Stemmy MCP, the `vst` extra."
argument-hint: <wav-or-bus> [goal: color|bus-glue|parallel|tight]
---

# fairchild-660 — drive the UADx Fairchild 660 (measured)

The plugin-specific, measured version of [[vst-compress]] for the **UADx Fairchild 660**
(`/Library/Audio/Plug-Ins/VST3/uaudio_fairchild_660.vst3`) — Universal Audio's model of the
**Fairchild Model 660 variable-mu (vari-mu) tube compressor-limiter**. It is the **tube COLOR + glue**
counterpart to the VCA glue of [[ssl-bus-compressor-2]], the console-tone strips
([[api-vision-channel-strip]] / [[kit-bb-a5]] / [[kit-bb-n105]] / [[ssl-4k-e]] / [[studer-a800]]) and the
mastering-tape [[ampex-atr-102]]. Full field guide — param surface, the input/threshold/time-constant maps,
the color signature, recipes, pitfalls, the 660-vs-670 note, sources — lives in
[`docs/vst/fairchild-660.md`](../../../docs/vst/fairchild-660.md). This skill is the workflow.

## The governing facts (read first)

1. **It COLORS more than it crushes.** On this UADx 660 the **crest factor stays ~17–19 dB across the whole
   input/threshold range** — it levels RMS and *thickens the low-mids* without clamping transients. Validated
   gentle move on the Watercolors warm drum bus (`fc660-drum-color`): **crest 17.17→16.90, LRA 2.44→1.84
   (tighter), low-mid energy ratio 0.179→0.188 (thicker), low-band punch HELD (27.15→27.19), +0.27 LU,
   true-peak −0.99**. The vari-mu "weight/glue, keep the punch" reputation is real here — *measured*.
2. **There is NO ratio / attack / release knob.** You sculpt with **INPUT** (drive into the tube),
   **THRESH**, and **TIME_CONST**. **INPUT drives BOTH gain reduction AND harmonic color** — it colors even
   at low GR, so it's a tone box as much as a comp.
3. **TIME CONSTANT is the transient/density control (1–6).** Measured crest by position on the drum bus:
   **tc4 = most open/punchy (crest 18.2)**, **tc1 = tightest/most controlled (15.4)**, tc2–3 in between, and
   **tc5/tc6 = the program-dependent AUTO positions (denser here, crest ~15–16.7)**. Pick tc4 to keep punch,
   tc1 to clamp, tc5/6 for breathing auto-release glue.
4. **THRESHOLD direction (this build): HIGHER `thresh` = MORE gain reduction.** thresh 2 ≈ barely working /
   loud, thresh 8 ≈ heavy (output dropped ~9 dB vs thresh 6). Dial it to the GR you hear, not to a number.
5. **SC FILTER takes lows out of the DETECTOR only** (audio low end untouched). Raising it **60→250 Hz let
   output rise ~+4.7 dB** as the kick/bass stopped triggering GR — set ~60–120 Hz so low end stops pumping
   the bus and the kick punches through.
6. **HR (Headroom 4–28 dB) is the operating-level trim.** Lower HR (8) = hotter / denser; higher HR (24) =
   cleaner / more open (crest up). Default 16 is neutral. Use it to set how hard it runs without re-dialing input.
7. **MIX (0–100) is built-in parallel** (100 = fully wet). Crush a hot/fast wet, blend dry back ~30–50% for a
   NY smash that keeps attack (`fc660-parallel-smash`: +1.81 LU, crest 17.17→15.34, denser low end).
8. **The tooling gotcha (the big one):** **ALL 12 params are enums** (numeric *and* string) —
   `apply-vst-chain`'s **float-only** `parameters` dict can't set them reliably (it silently misses `sc_filt`,
   `time_const`, `meter`, the bools, and snaps numerics oddly). **Drive it through the [[vst-preset]] harness**
   (`presets/vst/apply_vst_preset.py`, which `setattr`s every param + snaps to the nearest valid value).
9. **It ADDS level + harmonics → always A/B at matched loudness** ([[level-match]] / `render-ab`). Louder is
   not better; judge by crest/LRA + the low-mid thickening, not level.
10. **660 = MONO unit** (runs linked dual-mono on a stereo bus here, which works but isn't true stereo
    detection). For a **true stereo bus** prefer the **670** (`uaudio_fairchild_670.vst3` — adds an L-R/L-V
    *lateral-vertical* (Mid/Side) matrix + sidechain/control link). Use the 660 on mono sources (snare, kick,
    bass, mono vocal) or when you want the dual-mono character; the 670 for stereo mixes / M-S.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **Load the `uaudio_fairchild_660.vst3` UADx native build** — it **renders headless & processes offline**
  (`changed:true` here). The `/Library/Audio/Plug-Ins/Components/UAD Fairchild 660.component` twin **passes
  audio through unprocessed** offline — never use it ([[vst-verify]] / [[vst]]). UADx
  native is the no-iLok perpetual lineage (like [[ampex-atr-102]] / Pultec), but re-verify `changed:true`
  on a new machine.
- Balance the bus first ([[mix-balance]]); hand the colored/glued result to [[master-track]] — this is a
  color/glue stage, **not** a master/limiter.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest / LRA / PLR / true-peak) + `[L] measure-microdynamics`
   (low-band punch) + `[L] measure-spectrum` (centroid + low/low-mid ratio, to see the thickening). The "before."
2. **Pick the move** from the table below. Start gentle (color/glue), escalate only on purpose.
3. **Apply via the preset harness** (every param is an enum → `apply-vst-chain` can't):
   `…/stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py presets/vst/fc660-*.json <in> <out>`.
   Ready-made: **`fc660-drum-color`** (validated), **`fc660-bus-glue`**, **`fc660-parallel-smash`**.
4. **Dial it to the result:** more INPUT or higher THRESH = more leveling + color; **TIME_CONST** sets
   punch (tc4) vs control (tc1) vs auto (tc5/6); **SC_FILT** ~60–120 Hz if the low end pumps; **HR** to set
   how hard it runs; **MIX** down for parallel. Re-measure after each change.
5. **Prove it** — re-`measure-loudness` / `measure-microdynamics` / `measure-spectrum`: expect crest roughly
   held (not collapsed), **LRA a touch tighter**, **low-mid ratio up** (the thickening), low-band punch
   retained (tc4) or deliberately denser (parallel), true-peak safe. **A/B loudness-matched** so "bigger"
   isn't just "louder."
6. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch pumping (too-fast TC / too much GR) or a
   choked/dull bus; reconcile any mono "dull" flag against the stereo meters ([[gemini-audio-understanding]]).

## Recipes (measured starting points — re-dial to your level)

| Goal | input | thresh | time_const | sc_filt | mix | HR | Preset |
|---|---|---|---|---|---|---|---|
| **Drum color + glue** (keep punch) ★ | −6 | 6 | **4** | 60 Hz | 100 | 16 | `fc660-drum-color` |
| **Mix / 2-bus glue** (auto release) | −8 | 5 | **5** | 90 Hz | 100 | 16 | `fc660-bus-glue` |
| **Parallel / NY smash** | 0 | 8 | **1** | Off | **40** | 12 | `fc660-parallel-smash` |
| **Tight / dense control** | −4 | 6 | **1** | 60 Hz | 100 | 16 | (drum-color, tc1) |
| **Vocal leveling** (mono src) | −8…−4 | 5–6 | 3–4 | 60–90 Hz | 100 | 16 | (recipe) |
| **Bass weight** (mono src) | −6…−4 | 5–6 | 4 | Off | 100 | 16 | (recipe) |

★ the validated gentle color (`presets/vst/fc660-drum-color.json` → `projects/watercolors/mix/fc660_drum_color_demo.wav`).
**INPUT** −48…0 dB (toward 0 = hotter = more GR + more color). **THRESH** 0–10 (higher = more GR). **TIME_CONST**
1=tightest … 4=most open … 5/6=program-dependent auto. **SC_FILT** Off…500 Hz (detector only). **HR** {4,8,12,16,20,24,28}
dB headroom trim. **MIX** 100=wet. Leave `bal` 0, `dc_thr` ~7.5, `output` 0 (the harness peak-trims), `power` on.

## Reporting to the user

State the settings (input / thresh / time_const / SC-filt / HR / mix), before→after **crest / LRA / true-peak**
+ the **low-mid ratio** shift (the thickening) and **low-band punch** (held or denser), that it ran headless via
the `uaudio_*.vst3` build, and that the character came from tube color + leveling (not squash). A/B
loudness-matched so "bigger" isn't just "louder."

## Pitfalls

- **Don't drive it through `apply-vst-chain` alone** — all 12 params are enums; the float-only dict silently
  misses `sc_filt` / `time_const` / `meter` / the bools and mishandles numerics. Use the [[vst-preset]] harness.
- **Wrong build = passthrough** — the `/Components/UAD Fairchild 660.component` twin passes audio through
  offline. Load `uaudio_fairchild_660.vst3`; verify `changed:true` + measure *detail* ([[vst-verify]]).
- **It colors → louder & thicker** — A/B at matched loudness; don't mistake added level/harmonics for "better."
- **Too-fast TIME_CONST + too much GR pumps** — keep tc4 for punch; reach for tc1/auto on purpose.
- **Bass pumps the whole bus** — raise the SC FILTER (60–120 Hz) to take lows out of the detector.
- **Stereo bus on the 660** — it's a mono unit running dual-mono; for true stereo / M-S use the **670**.
- **It's not a master** — color/glue stage; hand off to [[master-track]] for loudness/limiting.

## Related

- [`docs/vst/fairchild-660.md`](../../../docs/vst/fairchild-660.md) — the full measured field guide (Part A measured + Part B cited)
- [[vst-compress]] — the generic compressor skill this specializes · [[ssl-bus-compressor-2]] — VCA glue sibling (crush vs color) · [[dbx-160]] — feed-forward true-RMS VCA that ADDS punch (raises crest) vs the Fairchild's crest-holding tube color · [[la-3a]] — opto leveler (drops crest) · [[finalize-mix]] / [[stem-master]] — stages this fits
- [[vst-preset]] — apply enum chains (required here) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants
- [[ampex-atr-102]] / [[studer-a800]] — tube/tape color siblings · [[kit-bb-n105]] — warm Neve tone · [[drum-punch]] — pure-DSP transient design (no plugin)
- [[gemini-audio-understanding]] — why meters (not Gemini mono) own crest/GR
