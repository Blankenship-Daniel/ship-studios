---
name: manley-massive-passive
description: "Use when running the UAD/UADx Manley Massive Passive (the standard EQ or the MST mastering version) for broad/musical tonal EQ on a master, mix bus, drum bus, or stem — 'Massive Passive', 'Manley Massive Passive', 'Massive Passive MST', 'mastering EQ', 'put the Massive Passive on the 2-bus/mix/drums', 'big musical low end', 'air without harshness', 'the everything-sounds-better EQ', 'broad analog mastering tilt'. The measured, plugin-specific deep-dive of [[vst-eq]] / [[vst-master]] — a 4-band-per-channel PARALLEL passive (LC inductor) EQ with a solid-state input buffer + all-tube make-up gain: Boost/Out/Cut + Shelf/Bell + a bandwidth knob per band, where dB = gain x bandwidth (NOT the dial), narrowed shelves grow a resonant corner, and the parallel bands interact (don't sum). Grounded in the real 51-enum-param Pedalboard surface + transfer-function/THD render numbers in docs/vst/manley-massive-passive.md. The BROAD musical counterpart to the surgical [[fabfilter-pro-q-4]] and the fixed-band [[pultec-eqp-1a]]. Renders headless (UADx native, no dongle here). Stemmy MCP, the `vst` extra."
---

# manley-massive-passive — drive the UADx Manley Massive Passive (measured)

The plugin-specific, measured workflow for the **UADx Manley Massive Passive** — UA's model of the **Manley Laboratories
Massive Passive**, a 2-channel EQ whose tone-shaping network is **all-passive (LC inductor/capacitor/resistor)** with a
**solid-state input buffer + all-tube make-up amp**, and **4 overlapping bands per channel**. Two builds are installed:
the **standard** EQ (`uaudio_manley_massive_passive.vst3`, continuous controls, ±20 dB — the unit in the screenshot that
names itself "MASSIVE PASSIVE STEREO EQUALIZER") and the **MST / Mastering version** (`uaudio_manley_massive_passive_m.vst3`,
stepped/detented for recall + a precise ±2.5 dB L/R trim). It's the **BROAD, musical, "everything sounds better"** tonal
shaper — the opposite end of the EQ spectrum from the surgical [[fabfilter-pro-q-4]] and a more flexible full-range cousin
of the fixed-band [[pultec-eqp-1a]]. Full field guide — real param surface, signature quirks, footguns, recipes, our
numbers, sources — [`docs/vst/manley-massive-passive.md`](../../../docs/vst/manley-massive-passive.md). This skill is the workflow.

## The governing facts (read first — all measured on this rig, Pedalboard 0.9.23)

1. **Renders headless — use the `uaudio_` build.** `uaudio_manley_massive_passive.vst3` (standard) /
   `uaudio_manley_massive_passive_m.vst3` (MST) load + process (UADx native). The
   `/Components/UAD Manley Massive Passive*.component` AU twins are the **passthrough** offline build — never load them
   ([[uadx-uaudio-build-renders-headless]]). UADx native = no dongle for the render here.
2. **Every band defaults to `OUT` (out of circuit).** A bare load does NOTHING and the canned `probe_plugin.py`
   **false-flags it as passthrough** (it pushes a gain on an OUT band). You MUST set a band's `enable` to **`BOOST`**
   or **`CUT`** for its gain to do anything — verify with a real boost + `measure-spectrum`, not the probe (set e.g.
   `ch1loenable=BOOST`, `ch1logain=20`, render, confirm the low end moved).
3. **It's a PARALLEL passive EQ — the bands INTERACT, gains DON'T sum.** Measured: lo+himid both-boost lands **1.4–2.0
   dB LESS than the sum** of each alone in the overlap (≈0.6–0.9 dB on the gentler MST). This is the source of its
   "musical" glued feel — you sculpt a *shape*, not independent bands; re-measure, don't reason band-by-band.
4. **The GAIN dial is steeply NONLINEAR and BANDWIDTH-COUPLED — dB = gain × bandwidth, you can't read dB off the dial.**
   (Standard 0–20 / MST 0–11.) Dial **1–4 ≈ nothing; the action is 6–16.** At default bandwidth a BELL reads dial 5 ≈
   +1 dB, dial 10 ≈ +6, dial 20 ≈ +11–12. To reach the **±20 dB ceiling** (±11 on MST), **narrow the bandwidth** —
   himid dial 20 went **bw 1.0 +4.6 → bw 2.0 +11.8 → bw 3.0 +20.9 dB**. CUT is near-symmetric.
5. **BANDWIDTH: 1.0 = WIDEST/gentlest, 3.0 = NARROWEST/tallest + most gain** (reversed vs a normal Q; Manley calls it
   "damping/resonance"). Standard default 2.0, MST default 1.0. Narrowing both *focuses* the band and *lifts* the peak.
6. **SHELF ≫ BELL for level**, and **a SHELF + NARROW bandwidth grows a resonant corner** — the famous "the shelves
   aren't shelves": a low SHELF @47 at bw 3.0, dial 20 boosts **+15 dB @20 Hz** but **DIPS to +0.4 @47 (the corner)
   then bumps +3.3 @150** — the Pultec curve in one band. Keep bandwidth WIDE for a clean shelf; narrow it for the bump.
7. **Signature moves (measured):** the **LOW-END TRICK** = low SHELF boost + a low-mid BELL CUT (one band can't
   boost+cut) → weight + a low-mid scoop = "big but tight"; the **AIR TRICK** = hi SHELF boost @16k + a hi-mid BELL CUT
   @3.3k → air up top **while the harsh presence comes down** (the 16k/27k shelves are voiced with their dip ~8 kHz =
   "air without esses"). The band-4 **27 kHz** position is the supersonic "3D" air shelf — render it at **96 k** (at
   48 k its corner folds near Nyquist into a midrange dip; prefer 16 kHz at 48 k).
8. **It's a CLEAN EQ with a subtle, even-harmonic (H2-dominant), level-dependent colour** from the all-tube make-up amp:
   **0.03 % THD flat @−18 dBFS → 0.24 % @0 dBFS**; a big boost ≈ doubles it (odd harmonics rise). Not a saturation box.
   **Crest is HELD** (it's EQ, not dynamics). The make-up trim (`ch?gain`) is a **clean, linear dB** (std −6…+4, MST ±2.5).
9. **"Engaged flat" is NOT a true null** — it adds the faint H2 colour + a ~+1 dB lift @16–18k (standard; MST is flatter)
   + a near-Nyquist rolloff. Only `master_bypass=true` nulls → **loudness-match every A/B** ([[level-match]] / `render-ab`).
10. **All 51 params are enums → drive it with the [[vst-preset]] harness, not `apply-vst-chain`'s float dict.** Gain/bw/freq
    are numeric enums (on-grid floats OK), but **`enable`/`shape`/`lopass`/`hipass`/`ctrllink`/`power` are STRING/bool
    enums** the float dict can't set — and those switches are the whole instrument. **Set BOTH ch1* and ch2*** (LINKED
    mirrors ch1→ch2, but explicit is safe). No built-in M/S — it's L/R + Link only. **Meters own it** (Gemini hears mono).

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]` perceptual tools
  (optional, `GEMINI_API_KEY`) for an A/B read.
- Confirm the build: `[L] list-vst-plugins {name_contains:"Massive Passive"}` returns only the `.component` twins —
  the headless builds are at `/Library/Audio/Plug-Ins/VST3/uaudio_manley_massive_passive.vst3` (standard) /
  `…_m.vst3` (MST). Dump the live surface:
  `../stemmy-loops-mcp/.venv/bin/python presets/vst/dump_params.py massive_passive`.
- **Do NOT trust `probe_plugin.py` here** — it false-flags passthrough (bands default OUT). Verify with a real boost
  (fact #2). Re-measure curves any time with `… scripts/mix/massive_passive_sweep.py [mst] [96000]`.

## The parameter surface (51 enums — see the doc for the full grid)

Per channel `ch1`/`ch2`, four bands `lo` / `lomid` / `himid` / `hi`, each with **`enable`** (`CUT`/`OUT`/`BOOST`, default
**OUT**) · **`shape`** (`BELL`/`SHELF`; lo+hi default SHELF, mids default BELL — all four can be either) · **`gain`**
(numeric enum, standard 0→20 / MST 0→11 in 16 steps) · **`bw`** (numeric enum 1.0→3.0; 1.0 widest, 3.0 narrowest) ·
**`freq`** (stepped grid). Per channel: **`lopass`** (std `OFF/18/12/9/7.5/6 kHz`, MST `OFF/52/40/27/20/15 kHz`) ·
**`hipass`** (std `OFF/22/39/68/120/220 Hz`, MST `OFF/12/16/23/30/39 Hz`) · **`gain`** (make-up trim, std −6…+4 / MST
±2.5 in 0.5-dB) · **`enable`** (`OUT`/`IN`, default IN). Global: **`ctrllink`** (`LINKED`/`UNLINKED`, default LINKED —
mirrors ch1→ch2) · `power` · `master_bypass`.

**Frequency grids (Hz, both builds):** `lo` 22/33/47/68/100/150/220/330/470/680/1000 · `lomid` 82/120/180/270/390/560/820/1200/1800/2700/3900 ·
`himid` 220/330/470/680/1000/1500/2200/3300/4700/6800/10000 · `hi` 560/820/1200/1800/2700/3900/5600/8200/12000/16000/**27000**.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid) + `[L] measure-loudness` (crest/PLR). The
   "before" column. Decide the job: subtle **master polish**, **drum-bus weight/tighten**, **air without harshness**, or
   a corrective tonal move. Pick the build: **standard** for mix/tracking (wider range, audible-band filters), **MST**
   for recallable mastering (±11 dB stepped, ±2.5 dB L/R trim, subsonic/ultrasonic filters).
2. **Pick the bands.** Set each engaged band's `enable` to `BOOST` or `CUT`, choose `shape` (SHELF for big broad moves,
   BELL for focused), pick `freq` on the grid. Leave unused bands `OUT`.
3. **Dial gain × bandwidth, not "dB".** Start `bw` WIDE (1.0–2.0) for broad/gentle; raise the gain dial into the **6–16**
   action zone. Need more dB or a tighter move? **Narrow the bandwidth** (toward 3.0) — it both focuses and lifts.
   Remember a SHELF moves far more level than a BELL at the same dial, and the bands interact (re-measure the combination).
4. **Reach for the signature moves.** *Big-but-tight low end:* low SHELF boost @33–68 (wide) + a low-mid BELL CUT
   @180–390. *Air without harsh:* hi SHELF boost @12–16k + a hi-mid BELL CUT @2.5–3.3k (or a NARROW hi shelf / the 27k
   position at 96 k for pure top air). *Resonant shelf bump (Pultec-y):* narrow the bandwidth on a shelf.
5. **Filters / trim (optional).** `hipass` (passive, steep ~18 dB/oct) to clean subsonic rumble; `lopass` (std 6–18k
   carves the audible top; MST is supersonic-edge). Use the per-channel `gain` trim for the final recall/level match.
6. **Build a preset** (`presets/vst/massive-passive-*.json`) setting **all engaged params on BOTH channels** + `ctrllink`
   / `power` / `master_bypass`, and apply with the harness:
   `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
   projects/<track>/mix/<stem>_mp.wav` (it `setattr`s the string enums and peak-normalizes). Set `dump_state=true` via
   `apply-vst-chain` once dialed for a byte-stable re-render.
7. **Prove it** — re-`measure-spectrum`/`measure-loudness`. The deltas land in the **band ratios / centroid / tilt**;
   **crest is HELD** (it's EQ, not dynamics) — a crest crash means you over-drove the make-up amp. A 0.00 spectrum delta
   = the `.component` passthrough twin loaded. A/B loudness-matched ([[level-match]] / `[L] render-ab`).
8. **QC** — `[G] mastering-feedback` / `detect-mix-issues` (genre/intent set) for over-bright/over-scooped; cross-check
   any mono "harsh/dull" flag against the meters ([[gemini-mastering-feedback-cross-check]]). It's a tonal insert, **not
   a limiter** — hand the result to [[master-track]] / [[fabfilter-pro-l-2]] for loudness.

## Move table (measured)

| Goal | Massive Passive move |
|---|---|
| **Broad drum/mix-bus tone** ★ | std: lo SHELF @68 + lomid BELL CUT @270 + hi SHELF @12k → weight (low 0.80→0.86) + tight low-mids (0.18→0.13) + less harsh presence + air, crest held (shipped `massive-passive-drum-bus`). |
| **Big-but-tight low end** ★ | std: LOW-END TRICK — lo SHELF @47 boost + lomid BELL CUT @180 → low 0.80→0.85, low-mid 0.18→0.13 (scoop), top untouched (shipped `massive-passive-low-end-trick`). Single-band: low SHELF @47, bw ~3.0. |
| **Air without harshness** ★ | std: hi SHELF @16k + himid BELL CUT @3.3k → high-mid 0.0113→0.0056 (de-harsh), high 0.0043→0.0061 (air), centroid 1593→2038 (shipped `massive-passive-air-deharsh`). |
| **Gentle master polish** ★ | MST: lo SHELF @47 g4.4 + lomid CUT @390 g2.93 + hi SHELF @16k g5.13, bw 1.0 → +weight, a touch of air, −low-mud, crest 14.6→14.1 (shipped `massive-passive-master-polish`). Before the limiter. |
| **More dB / tighter focus** | NARROW the bandwidth (raise `bw` toward 3.0) — it lifts the peak and focuses; the gain dial alone caps low when wide. |
| **Pure top air (no presence)** | hi SHELF @12–16k with a NARROW `bw` (≈3.0) → lifts >10k only; or the 27k position at 96 k (a wide bump tilts the whole top). |
| **Resonant low bump (Pultec-y)** | low SHELF + NARROW `bw` → sub boost + corner dip + low-mid bump above. |
| **Clean broad weight** | low SHELF, WIDE `bw` (1.0) → smooth shelf, no corner resonance. |
| **De-mud / de-box** | low-mid BELL CUT @270–500 (gentle dial; narrow for a focused scoop). |
| **A hint of tube warmth** | drive the input hotter + a boost (more make-up gain = more even-harmonic THD, 0.03→0.24 %) — subtle; it's an EQ, not a saturator. |
| **Subsonic clean-up / top roll** | `hipass` (std 22–68 Hz / MST 12–39 Hz) · `lopass` (std 6–18k carves; MST 15–52k supersonic-edge). |

## Outputs

- `projects/<track>/mix/<stem>_mp.wav` (or `masters/` for a 2-bus polish) + the reusable `presets/vst/massive-passive-*.json`
  (and `.state` if dumped).

## Reporting to the user

State the build (standard vs MST), which bands are engaged (band · Boost/Cut · Shelf/Bell · gain dial · bandwidth · freq),
the before→after **band-ratio / centroid / tilt** deltas (crest should be ~held — it's EQ), that it ran headless via the
`uaudio_` build, and the preset/`.state` path. A/B loudness-matched so "bigger/airier" isn't a level illusion.

## Pitfalls

- **Wrong build = silent passthrough** — load `uaudio_manley_massive_passive.vst3` (or `…_m.vst3`), not the
  `UAD Manley Massive Passive*.component` twins. **And `probe_plugin.py` false-flags passthrough** (bands default OUT) —
  verify with a real boost.
- **Bands default OUT** — nothing happens until you set `enable=BOOST`/`CUT`. The most common "it didn't work."
- **Float dict can't drive it** — `enable`/`shape`/`lopass`/`hipass`/`ctrllink`/`power` are string/bool enums → the
  [[vst-preset]] harness only. **Set BOTH channels.**
- **The GAIN dial is not dB** — nonlinear (action 6–16) and **bandwidth-coupled** (dB = gain × bw). A wide-bandwidth max
  boost is only a couple dB; narrow it for more. Measure, don't trust the dial.
- **Narrowed shelves grow a resonant corner** (sub boost + corner dip + bump above) — wide bandwidth for a clean shelf.
- **The bands interact** (parallel passive) — two boosts are less than their sum; sculpt the shape, re-measure.
- **It's a clean EQ, not a colour box** — the make-up colour is subtle (≤0.25 % THD); don't expect heavy Pultec/console drive.
- **"Flat" is not a null** (tube/transformer colour + top lift) — only `master_bypass` nulls; loudness-match every A/B.
- **It's not a limiter** — no ceiling/true-peak control; hand off to [[master-track]] / [[fabfilter-pro-l-2]] for loudness.

## Related

- [`docs/vst/manley-massive-passive.md`](../../../docs/vst/manley-massive-passive.md) — the full measured field guide (Part A measured + Part B topology/history/usage, cited)
- [[vst-eq]] / [[vst-master]] — the generic skills this specializes · [[vst-preset]] — apply enum/all-explicit chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- EQ siblings: [[pultec-eqp-1a]] (fixed-band passive tube program EQ — lows+air) · [[pultec-meq-5]] (passive mid EQ) · [[hitsville-eq-mastering]] (Motown M/S graphic mastering EQ) · [[fabfilter-pro-q-4]] (surgical/dynamic, the SHARP counterpart) · [[helios-type-69]] (passive inductor console EQ + drive)
- Manley siblings: [[manley-voxbox]] (all-tube vocal channel) · [[manley-variable-mu]] (clean vari-mu bus/master comp) — the dynamics partners to this EQ on a master
- Pure-DSP twins (no plugin): broad shelves/tilt + low-end weight → `[L] apply-eq` · air/presence → [[excite]] · de-harsh (level-dependent) → [[de-harsh]]
- [[mix-check]] (find the problems first) · [[mastering-plan]] (a full master) · [[uadx-uaudio-build-renders-headless]] (why the build matters)
