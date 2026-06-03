---
name: manley-variable-mu
description: "Use when running the UADx Manley Variable Mu for CLEAN/transparent vari-mu tube glue, leveling, M/S mastering, or parallel compression on a mix bus, 2-bus, master, drum bus, vocal, or bass — 'Manley Variable Mu', 'Vari-Mu', 'Variable Mu compressor', 'transparent tube bus glue', 'glue the mix bus with the Manley', 'mastering compressor', 'M/S bus compression', 'vari-mu on the 2-bus', 'parallel-smash the drums with the Manley'. The measured, plugin-specific deep-dive of [[vst-compress]] — an all-tube variable-mu compressor that LEVELS macro-dynamics while KEEPING transients (crest held/up, even-harmonic color only when driven), grounded in the real 23-enum-param Pedalboard surface + threshold/input/attack/recovery/comp-vs-limit/headroom/M-S render numbers in docs/vst/manley-variable-mu.md. The CLEAN counterpart to the thicker [[fairchild-660]]. Stemmy MCP, the `vst` extra."
argument-hint: <wav-or-bus> [goal: drum-glue|bus-glue|parallel|master-ms]
---

# manley-variable-mu — drive the UADx Manley Variable Mu (measured)

The plugin-specific, measured version of [[vst-compress]] for the **UADx Manley Variable Mu**
(`/Library/Audio/Plug-Ins/VST3/uaudio_manley_variable_mu.vst3`) — Universal Audio's model of the **Manley Labs
Stereo Variable Mu® Limiter Compressor**, the all-tube vari-mu bus/mastering compressor. It is the
**CLEAN / transparent** vari-mu glue counterpart to the thicker, more colored [[fairchild-660]], the VCA glue
of [[ssl-bus-compressor-2]], and the tube/tape color of [[ampex-atr-102]] / [[studer-a800]]. Full field guide —
param surface, the threshold/input/attack/recovery/headroom maps, the harmonic signature, the M/S move,
recipes, pitfalls, Manley-vs-Fairchild, sources — lives in
[`docs/vst/manley-variable-mu.md`](../../../docs/vst/manley-variable-mu.md). This skill is the workflow.

## The governing facts (read first)

1. **It's the CLEAN vari-mu — levels macro-dynamics, KEEPS transients.** On the Watercolors warm drum bus the
   signature glue (`manley-vari-mu-drum-glue`) **raised crest 17.17→17.39** while **tightening LRA 2.44→2.07**,
   low-mid barely up (0.179→0.184), **low-band punch held** (27.30), true-peak −0.98. The Fairchild 660 on the
   *same* bus *dropped* crest to 16.90 and thickened more — **Manley = transparent leveler/glue, Fairchild =
   thicker color.**
2. **No ratio knob.** Ratio is program-dependent, set by **COMP vs LIMIT** + drive. **COMP ≈ 1.5:1 soft knee;
   LIMIT ≈ 4:1 → ~20:1 past 12 dB.** Measured at thresh 4: **LIMIT −5.8 dB GR vs COMP −2.2 dB** (much more
   for the same threshold), crest still ~17.3.
3. **THRESHOLD maps DIRECTLY (not inverted like the Fairchild's enum): LOWER `l_thresh` = MORE GR.** Default
   **10 = MAX = least compression**; drop toward 0 for more. Crest rises as it levels.
4. **`dual_input` (0–10, default 6) is a SINGLE SHARED drive/level** — the "amount + color" lever. Drive it up
   to hit the tubes (and `headroom` down) for color; toward 0 it starves/cleans.
5. **ATTACK: 0 = SLOW (punch, crest 17.4) … 10 = FAST (clamp, 16.4)** — flat until ~7 then grabs. **RECOVERY
   (5-pos `Slo/Med Slo/Med/Med Fast/Fast`): `Med` = most open (17.38), `Fast` = densest/pumps (16.40).** Times
   ≈ Slo 8 s · Med Slo 4 s · Med 0.6 s · Med Fast 0.4 s · Fast 0.2 s.
6. **HEADROOM (4–28 dB, default 16) is the INVERTED drive lever:** LOWER value = hotter into the tubes (more
   saturation, *less* GR for a fixed input); HIGHER = cleaner + MORE GR. Measured HR4 ≈ no GR + most color
   (crest 16.90), HR28 = −5.8 dB GR + crest collapse (15.96). Dial to the meter.
7. **Color is EVEN-harmonic (2nd) and LEVEL-dependent** — clean at −18 dBFS (~0.03–0.05 % THD), colors when
   hot (−6 dBFS → 0.21 %, H2 ~10 dB > H3). **Drive the level in for color; lowering threshold alone just levels.**
8. **HP SIDECHAIN `In` (fixed −3 dB @ 100 Hz)** takes lows out of the detector → less bass-triggered GR
   (+0.8 dB out). Engage on kick/bass-heavy material so the bus stops pumping.
9. **Real M/S — the move the mono Fairchild 660 can't do.** `in_matrix`/`out_matrix` = `M-S` with `ctrl_link`
   + `sc_link` **Unlinked** → **`l_*` controls = MID, `r_*` = SIDE.** Compress the MID harder than the SIDE to
   **widen** (measured corr 0.975→0.956, width −18.9→−16.4 dB), the SIDE harder to narrow. **Linked M-S == L-R**
   (no imaging change — unlinking is the point).
10. **MIX (0–100) is built-in parallel** (100 = wet). Crush a hot/fast wet in LIMIT, blend dry back ~40–50 %
    for a NY smash that keeps the slam.
11. **The tooling gotcha:** **ALL 23 params are enums** (numeric values AND string switches) —
    `apply-vst-chain`'s **float-only** dict can't set the string enums (`recovery` / `comp_lim` / `hp_sc_filt`
    / `*_matrix` / `*_link` / `*_bypass`) → **drive it through the [[vst-preset]] harness**
    (`presets/vst/apply_vst_preset.py`, which `setattr`s every param + snaps to the nearest valid value).
12. **It adds level + harmonics → always A/B at matched loudness** ([[level-match]] / `render-ab`). Judge by
    crest / LRA / width, not level. It's a color/glue stage, **not** a master — hand off to [[master-track]].

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **Load the `uaudio_manley_variable_mu.vst3` UADx native build** — it **renders headless & processes offline**
  (`RENDERS ✓` here). The `/Library/Audio/Plug-Ins/Components/UAD Manley Variable Mu.component` twin **passes
  audio through unprocessed** offline (`PASSTHROUGH ✗`) — never use it ([[vst-verify]] /
  [[vst]]). UADx native = no-iLok lineage, but re-verify `RENDERS ✓` on a new machine.
- Balance the bus first ([[mix-balance]]); hand the glued result to [[master-track]] — color/glue stage, not a
  master/limiter.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest / LRA / PLR / true-peak) + `[L] measure-microdynamics`
   (low-band punch) + `[L] measure-spectrum` (centroid + low/low-mid ratio) + `[L] measure-stereo` (if M/S).
   The "before."
2. **Pick the move** from the table below. Start gentle (glue), escalate only on purpose.
3. **Apply via the preset harness** (every param is an enum → `apply-vst-chain` can't):
   `…/stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py presets/vst/manley-vari-mu-*.json <in> <out>`.
   Ready-made: **`manley-vari-mu-drum-glue`** (validated ★), **`manley-vari-mu-bus-glue`**,
   **`manley-vari-mu-parallel-smash`**, **`manley-vari-mu-master-ms-glue`**.
4. **Dial it to the result:** lower THRESH or more DUAL INPUT = more leveling; **ATTACK** sets punch (low) vs
   clamp (high); **RECOVERY** Med = open, Fast = dense; **COMP→LIMIT** for more ratio; **HP-SC In** if the low
   end pumps; **HEADROOM** down for color/drive; **MIX** down for parallel; **M-S + unlink** for width.
   Re-measure after each change.
5. **Prove it** — re-`measure-loudness` / `measure-microdynamics` / `measure-spectrum` (+ `measure-stereo` for
   M/S): expect **crest held/up** (not collapsed), **LRA tighter**, low-mid only slightly up, low-band punch
   retained, true-peak safe; for M/S expect correlation down + width up. **A/B loudness-matched** so "glued"
   isn't just "louder."
6. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch pumping (too-fast attack/recovery or too much
   GR) or a choked bus; reconcile any mono "dull" flag against the stereo meters
   ([[gemini-audio-understanding]]).

## Recipes (measured starting points — re-dial to your level)

| Goal | dual_input | thresh | attack | recovery | comp/lim | hp_sc | mix | matrix | Preset |
|---|---|---|---|---|---|---|---|---|---|
| **Drum glue** (keep punch) ★ | 6 | 5 | 3 | **Med** | Comp | In | 100 | L-R | `manley-vari-mu-drum-glue` |
| **Mix / 2-bus glue** | 6 | 6 | 2 | Med Slo | Comp | In | 100 | L-R | `manley-vari-mu-bus-glue` |
| **Parallel / NY smash** | 8 | 2 | 8 | Fast | **Limit** | Flat | **45** | L-R | `manley-vari-mu-parallel-smash` |
| **M/S master glue (wider)** | 6 | mid 6 / side 9 | 2 | Med Slo | Comp | In | 100 | **M-S unlink** | `manley-vari-mu-master-ms-glue` |
| **Mastering (transparent)** | 5–6 | 7–8 | 0–2 | Slo/Med Slo | Comp | In | 100 | L-R (LINK) | (bus-glue, gentler) |
| **Vocal / bass leveling** | 5–6 | 5–6 | 2–4 | Med | Comp | In | 100 | L-R | (recipe) |
| **Add tube color** | 8–10 | 6–7 | 2 | Med | Comp | In | 100 | L-R | drive in + **headroom 8–12** |

★ validated (`presets/vst/manley-vari-mu-drum-glue.json` → `projects/watercolors/mix/manley_drum_glue_demo.wav`).
**THRESH** 0–10 (lower = more GR; 10 = MAX = least). **DUAL INPUT** 0–10 (higher = hotter/more drive + color).
**ATTACK** 0=slow/punch … 10=fast/clamp. **RECOVERY** Med = open, Fast = dense. **HEADROOM** {4,8,12,14,16,18,20,24,28}
(lower = hotter/more color/less GR). **MIX** 100=wet. Keep `l_*`==`r_*` in L-R; in M-S `l_*`=MID, `r_*`=SIDE.

## Reporting to the user

State the settings (input / thresh / attack / recovery / comp-lim / HP-SC / headroom / mix / matrix),
before→after **crest / LRA / true-peak** (+ **low-mid ratio** and **low-band punch**; for M/S add
**correlation / width**), that it ran headless via the `uaudio_*.vst3` build, and that the character came from
clean vari-mu leveling (+ even-harmonic color only if driven), NOT squash. A/B loudness-matched so "glued"
isn't just "louder." If they wanted *thick/colored* glue instead of *clean*, point them at [[fairchild-660]].

## Pitfalls

- **Don't drive it through `apply-vst-chain` alone** — all 23 params are enums; the float-only dict silently
  misses every string switch (`recovery` / `comp_lim` / `hp_sc_filt` / matrices / links / bypass). Use the
  [[vst-preset]] harness.
- **Wrong build = passthrough** — the `/Components/UAD Manley Variable Mu.component` twin passes audio through
  offline. Load `uaudio_manley_variable_mu.vst3`; verify `RENDERS ✓` + measure *detail* ([[vst-verify]]).
- **Color is level-dependent** — to get the tube sound, drive DUAL INPUT up / HEADROOM down so the signal is
  hot; lowering the threshold alone just levels (stays clean).
- **HEADROOM is inverted** (lower value = hotter/more color/less GR) — the most misread control; dial to meter.
- **Not a punch tool** — its slow attack passes transients (great for *keeping* punch, useless for *adding* it).
  For punch use [[drum-punch]] or a FET/VCA comp.
- **LINK needs matched channels**; **linked M-S == L-R** — unlink `ctrl_link`+`sc_link` for the M/S move.
- **It adds level + harmonics** — A/B at matched loudness; don't mistake louder/thicker for "better."
- **It's not a master** — color/glue stage; hand off to [[master-track]] for loudness/limiting.

## Related

- [`docs/vst/manley-variable-mu.md`](../../../docs/vst/manley-variable-mu.md) — the full measured field guide (Part A measured + Part B cited)
- [[vst-compress]] — the generic compressor skill this specializes · [[fairchild-660]] — the thicker/more-colored vari-mu sibling (clean vs color) · [[ssl-bus-compressor-2]] — VCA glue sibling
- [[vst-preset]] — apply enum chains (required here) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants
- [[finalize-mix]] / [[stem-master]] / [[master-track]] — stages this fits · [[level-match]] — loudness-matched A/B
- [[ampex-atr-102]] / [[studer-a800]] — tube/tape color siblings · [[drum-punch]] — pure-DSP transient design (no plugin)
- [[gemini-audio-understanding]] — why meters (not Gemini mono) own crest/GR/width
