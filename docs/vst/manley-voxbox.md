# UADx Manley VOXBOX Channel Strip — field guide: all-tube vocal channel (pre + opto comp + passive Pultec EQ + de-ess/limiter), headless

How to drive the **UADx Manley VOXBOX Channel Strip** (`/Library/Audio/Plug-Ins/VST3/uaudio_manley_voxbox.vst3`)
— UA's component-level model of the **Manley Laboratories VOXBOX** (1998), a mono **all-tube** "reference channel
strip" and the most celebrated **vocal channel** ever built (NAMM TECnology Hall of Fame 2016). **Four functional
blocks** in one box: a **tube mic/line preamp**, a **passive electro-optical compressor**, a **passive Pultec-style
(MEQ-5-derived) 3-band EQ**, and a **de-esser / opto limiter** — plus an output transformer (so the *signal-flow*
counts six elements incl. input + transformer: `INPUT → COMPRESSOR → PREAMP → EQ → DE-ESS/LIMITER → OUTPUT`; see §2 TL;DR). It's the **smooth, open, "hi-fi" tube**
member of [[vst-channel-strip]] (and the only one of our deep-dives with a built-in compressor *and* EQ *and*
de-esser): warmer/cleaner/more-flexible than an Avalon 737, the tube opposite of the clean [[ssl-native-channel-strip-2]]
and the punchy [[api-vision-channel-strip]] / [[kit-bb-a5]]. **Part A** is *measured on this rig* (the real Pedalboard
param surface + our own render/THD/meter results); **Part B** is a *web-research synthesis, adversarially verified,
cited* (Manley + UA manuals, Sound on Sound, MusicRadar, reviews). The skill [[manley-voxbox]] is the measured workflow.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the tilt/centroid/crest that
> prove a tonal or dynamics move. Verify every move with `[L] measure-spectrum` / `measure-loudness`. A render that
> "sounds" coloured but shows a 0.00 spectrum/crest delta is a **passthrough** (you loaded the wrong build).

---

## TL;DR (the headline, measured)

1. **It renders headless — load the `uaudio_` build.** `uaudio_manley_voxbox.vst3` loads + processes through
   Pedalboard 0.9.23 (param-response confirmed). The `UAD Manley VOXBOX.component` twin is the **passthrough**
   offline build — never load it ([[vst-verify]]). UADx native = no DSP/iLok dongle for the render here.
2. **The audio path is NOT the GUI layout.** Internal flow is **INPUT → COMPRESSOR → tube PREAMP → EQ → DE-ESS/LIMITER → OUTPUT**
   — the **compressor is FIRST, before the preamp** (it clamps transients before the first tube), and it's **fixed/
   non-reorderable**. Don't reason about order from the panel's left-to-right blocks.
3. **`input` + `gain` + Mic = the tube drive/colour.** Measured 1 kHz THD: **Line in3 g40 = 0.002 %** (clean) →
   **Mic in6 g50 = 5 %** → **Mic in10 g60 = 67 %**, **even-harmonic dominant** (H2 −4.9 dB hard-driven). **Mic
   saturates ~10–20 dB sooner than Line.** On drums the drive lowers crest *and* **BRIGHTENS** as it distorts
   (centroid rises) — the opposite of the Helios/Studer darkening. `input` is an attenuator that sits *before* the
   comp+tube, so opening it drives **both** (compression *and* colour) harder.
4. **The opto compressor RAISES crest on transient material.** It's a smooth, **program-dependent passive-opto**
   leveller (nominal "3:1" — *not* a fixed ratio), placed first; it pulls the *body* down and leaves transients, so
   on the drum loop crest went **14.6 → 19.5**. It's a leveller, not a grabber. **`comp_thresh` is RELATIVE TO
   `input`, and HIGHER number = MORE GR** (inverted vs a dBFS threshold): at input 3 you need thr 8–10 to engage; at
   input 6 even thr 6 = −9 dB GR. **Slow attack = transients pass (crest ↑), Fast attack = control.**
5. **The Pultec EQ dials are nonlinear 0–10, not dB.** Measured: `lo_peak` 2/5/10 → +0.5/+3.4/+10.5 dB @100;
   `hi_peak` 2/5/10 → +0.04/+2.7/+8.6 dB @10k (a **bell**, not a shelf); `mid_dip` 2/5/10 → −0.2/−1.8/−11.7 dB @1k.
   **The bottom half of the dial barely acts — the action is 5–10.** Topology is **PEAK-DIP-PEAK**: LOW boost-only,
   MID cut-only, HIGH boost-only — **no cuts on low/high, no mid boost, no Q control** (proportional-Q narrows with gain).
6. **The de-esser ducks the selected band; the 5th position "Limit" is a smooth opto 10:1 limiter.** `de_ess_sel`
   3K/6K/9K/12K notches the detector (higher `de_ess_thr` = more duck, and it only acts where there's energy:
   6K → −1.8 dB @thr 10 on drums); **`Limit`** is a wideband LA-2A-style opto limiter (≈2 ms/0.5 s) that pulls peaks
   (crest 14.6 → 12.8, +4 dB denser) — *not* a fast brickwall.
7. **All 25 params are enums → drive it with the [[vst-preset]] harness, not `apply-vst-chain`'s float dict.** The
   string switches (`source_select`=Mic, `low_cut`, `comp_byp`/`eq_byp`/`de_ess_byp` In, `comp_attack`/`comp_rel`,
   `de_ess_sel`, `sc_link`, `transformer_byp`, `meter`) are exactly the character controls and can't be set float-only.

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin(".../uaudio_manley_voxbox.vst3")` →
`name="UADx Manley VOXBOX Channel Strip"`, `is_instrument=False`, renders (probe Δparam confirmed). Tested with
**Pedalboard 0.9.23**, input `artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav` (mono, 48 kHz,
crest 14.63, centroid 1593 Hz). The default load comes up effectively flat (comp & EQ are *In* but at 0 amount /
comp_thresh 5, which doesn't engage at low input; de-ess Byp) — but **set every param explicitly** in a preset.

`list-vst-plugins {name_contains:"VOXBOX"}` returns several entries — **use the VST3 `uaudio_` build**:

| Name | Path | Use |
|---|---|---|
| **UADx Manley VOXBOX Channel Strip** | `/Library/Audio/Plug-Ins/VST3/uaudio_manley_voxbox.vst3` | ✅ this one (renders) |
| UAD Manley VOXBOX | `…/Components/UAD Manley VOXBOX.component` | ❌ passthrough twin (offline) |
| UADx Manley VOXBOX (AU) | `…/Components/uaudio_manley_voxbox.component` | AU twin (macOS-only) |

### The real parameter surface (25 enums — authoritative)

**ALL 25 parameters are Pedalboard enums.** Numeric enums (`input`, `gain`, `comp_thresh`, `lo_peak`, `mid_dip`,
`hi_peak`, the three `*_freq`, `de_ess_thr`, `output`, `phase`) accept an on-grid float via `setattr`; string/bool
enums take the exact value. The string switches are the character controls → harness only.

| Param | Type | Values (grid) | Control / measured behaviour |
|---|---|---|---|
| `source_select` | enum | `Line` · `Mic` | input path; **Mic** = the colour path (Line ≈ −4 dB, cleaner; Mic saturates ~10–20 dB sooner) |
| `low_cut` | enum | `Off` · `80 Hz` · `120 Hz` | input high-pass (6 dB/oct, min-phase) |
| `phase` | enum-num | `0.0` · `180.0` | polarity |
| `input` | enum-num | 0.0 … 10.0 (0.1) | **level into the comp+tube** (attenuator; higher = hotter = more compression *and* drive). Default 3.0 |
| `gain` | enum-num | 40·45·50·55·60 dB | preamp **negative-feedback / colour** (subtle 2nd-harmonic; +level). Default 50 |
| `sc_link` | enum | `Sep` · `Link` | **STEREO L/R link** (links the two channels' thresholds) — *not* a comp↔de-ess link; mono locks Link |
| `comp_byp` | enum | `Byp` · `In` | compressor engage |
| `comp_thresh` | enum-num | 0.0 … 10.0 (0.1) | comp depth — **higher = MORE GR** (relative to `input`). Default 5.0 |
| `comp_attack` | enum | `Fast`·`Med Fast`·`Medium`·`Med Slow`·`Slow` | ≈4–70 ms; **Slow lets transients pass, Fast catches them** |
| `comp_rel` | enum | `Slow`·`Med Slow`·`Medium`·`Med Fast`·`Fast` | ≈0.3–5 s (note: enum order is Slow→Fast); voicings map to ELOP/LA-2A (see Part B) |
| `eq_byp` | enum | `Byp` · `In` | EQ engage |
| `lo_peak` | enum-num | 0.0 … 10.0 | LOW boost amount (**bell, boost-only**; nonlinear: 10 ≈ +10.5 dB) |
| `lo_peak_freq` | enum-num | 20·35·50·70·100·150·200·300·500·700·1000 Hz | LOW band centre |
| `mid_dip` | enum-num | 0.0 … −10.0 | MID **cut** amount (**bell, cut-only**; nonlinear: −10 ≈ −11.7 dB) |
| `mid_dip_freq` | enum-num | 200·300·500·700·1000·1500·2000·3000·4000·5000·7000 Hz | MID band centre (the MEQ-5 range) |
| `hi_peak` | enum-num | 0.0 … 10.0 | HIGH boost amount (**bell, boost-only**; nonlinear: 10 ≈ +8.6 dB) |
| `hi_peak_freq` | enum-num | 1500·2000·3000·4000·5000·6400·8000·10000·12000·16000·20000 Hz | HIGH band centre (**11 freqs — includes 2 kHz**, GUI label hides it) |
| `de_ess_byp` | enum | `Byp` · `In` | de-ess/limit engage |
| `de_ess_sel` | enum | `3K`·`6K`·`9K`·`12K`·`Limit` | detector notch band, or **`Limit`** = wideband 10:1 opto limiter |
| `de_ess_thr` | enum-num | 0.0 … 10.0 | de-ess/limit depth — **higher = more**. Default 4.1 |
| `meter` | enum | `GR`·`In`·`Pre Out`·`Out`·`DS` | VU source: 3 levels (In/Pre Out/Out) + 2 GR readouts (`GR` comp, `DS` de-ess) |
| `transformer_byp` | enum | `Byp` · `In` | **output** transformer (wired last; In = colour/weight, Byp = cleaner). Measured near-transparent here |
| `output` | enum-num | −60 … +12 dB | plugin output trim (no make-up gain on the comp → use this to recover level) |
| `power` / `master_bypass` | bool | `True`/`False` · `False`/`True` | unit power / plugin bypass |

### Footguns (proven on this rig)

1. **The audio path ≠ the GUI.** Internal flow is **Input → Compressor → Preamp → EQ → De-ess/Limiter → Output**;
   the comp is *first* (before the preamp) and the chain is fixed. `input` feeds the comp *and* the tube.
2. **The dynamics thresholds are "backwards."** Higher `comp_thresh` / `de_ess_thr` = **more** processing, and
   `comp_thresh` is **relative to `input`** (drive level). At a quiet input, low threshold numbers do nothing — they
   look broken. Push `input` and/or the threshold number up to engage. (Confirmed monotonic via the `Limit` sweep.)
3. **The EQ 0–10 dials are nonlinear and not dB.** Under ~3 they barely move; the action is 5–10 (10 ≈ +10/+8.6/−11.7 dB).
   PEAK-DIP-PEAK only — no cuts on LOW/HIGH, no mid boost, no Q.
4. **`apply-vst-chain`'s float dict can't set the character switches** (`source_select`, `low_cut`, the `*_byp`
   engages, `comp_attack`/`comp_rel`, `de_ess_sel`, `sc_link`, `transformer_byp`, `meter`). Drive it with the **[[vst-preset]]** harness.
5. **`sc_link` is a STEREO link, not a comp↔de-ess link** — Sep ≡ Link measured on mono material; it only matters in stereo.
6. **Wrong build = silent passthrough.** Load `uaudio_manley_voxbox.vst3`; the `UAD Manley VOXBOX.component` twin
   passes audio unprocessed offline — a 0.00 delta is the tell ([[vst-verify]]).

### Measured: `input` + `gain` + Mic = the saturation/colour engine

THD of a 1 kHz sine @ −12 dBFS (comp/EQ/de-ess bypassed; **even-harmonic dominant** = tube/transformer warmth):

| setting | THD | note |
|---|---|---|
| **Line in3 g40** | **0.002 %** | clean reference |
| Line in6 g60 | 27.0 % | Line saturates if both pushed |
| Line in10 g60 | 66.9 % | extreme |
| Mic in3 g40 | 0.004 % | clean at low input |
| Mic in6 g50 | 5.0 % | musical colour / glue zone |
| Mic in6 g60 | 42.3 % | heavy |
| **Mic in10 g60** | **67.6 %** (H2 −4.9 dB) | nuclear |

On the drum loop (peak-normalized): Mic in6 g50 → crest 14.6 → 11.4 (glue, +3–4 dB broadband); Mic in10 g60 →
crest 8.4, **centroid 2962 → 4556** (distortion fizz brightens it). The **output transformer** (`transformer_byp`)
moved THD <0.3 % and centroid ~+25 Hz — **near-transparent on this material** (don't expect Ampex-style transformer colour).

### Measured: the EQ bands (passive Pultec, `eq_byp` In, clean preamp)

- **`lo_peak`** 2/5/10 @100 Hz → **+0.47 / +3.41 / +10.52 dB**; a broad **bell** (10@100: 50 Hz +5.7, 100 +10.5, 200 +6.4, 400 +2.3).
- **`hi_peak`** 2/5/10 @10 kHz → **+0.04 / +2.66 / +8.58 dB**; a **bell** (10@10k: 8k +6.7, 10k +8.6, 16k +1.3) — *not* a shelf.
- **`mid_dip`** −2/−5/−10 @1 kHz → **−0.19 / −1.79 / −11.75 dB** (cut bell). All three confirm the nonlinear 0–10 mapping.

### Measured: the opto compressor + de-esser/limiter

- **Comp threshold (Medium/Medium):** input 3 → thr 6 = 0, thr 8 = −1.8, thr 10 = −4.6 dB GR; input 6 → thr 6 = −9.2,
  thr 10 = −17.4 dB GR. **Higher number = more GR; the `input` knob sets how hard you hit it.** On drums it **raises
  crest** (levels the body): input6/thr10 → crest 14.7 → 20.3.
- **Attack/Release (input 6, thr 10):** attack **Fast → crest 18.5** (peak −6.9), Medium 20.3, **Slow → 23.2** (peak −1.7)
  = slow lets transients through. Release Fast → crest 22.2 (rms −23.7, least sustained GR), Slow → 21.8 (rms −26.6, densest).
- **De-ess band duck (Δ third-oct @ sel, vs byp):** 6K thr 8/10 → −1.26 / −1.83 dB; 3K thr 10 → −1.56; 9K/12K barely
  (no drum energy there). Higher thr = more; needs energy at the freq.
- **`Limit` (wideband):** thr 2/5/8 → peak −0.25 / −1.0 / −3.6 dB, crest 14.7 / 14.1 / 12.9 — a smooth opto limiter
  (peaks down), monotone with threshold.
- **`sc_link`:** Sep ≡ Link (identical) on the dual-mono drum loop — confirms it's a stereo link, inert in mono.

### Measured: the three shipped presets (via the real `apply_vst_preset.py` harness + `[L]` meters)

| metric (`[L]` meters) | dry | `voxbox-drum-glue` | `voxbox-vocal-channel` | `voxbox-bus-tube-glue` |
|---|---|---|---|---|
| crest factor (dB) | 14.63 | **19.53** (↑ optical leveling) | **19.23** (↑) | **12.76** (↓ Limit) |
| PLR (dB) | 17.06 | 19.19 | 18.33 | 12.35 |
| integrated LUFS | −20.13 | −20.19 | −19.32 | **−13.26** (denser) |
| RMS (dBFS) | −17.72 | −20.53 | −20.23 | −13.76 |
| true-peak (dBTP) | −3.07 | −0.99 | −0.99 | −0.91 |
| spectral centroid (Hz) | 1593 | **1482** (darker/rounder) | **1963** (brighter) | 1549 |
| spectral tilt (dB/oct) | −2.71 | −3.04 | −2.48 | −2.82 |
| band_ratio low / low-mid | 0.798 / 0.176 | 0.855 / 0.132 | 0.706 / 0.263 (HPF) | 0.834 / 0.146 |

- **`voxbox-drum-glue`** — Mic in4 g50 + comp(thr8) + Pultec (lo 5@70 / hi 5@10k / mid −3@500): warm, rounded,
  **opened transients** (crest ↑), darker. Tube drum-bus character.
- **`voxbox-vocal-channel`** — Mic in3 g50, HPF 80, comp(thr9, Med/Med-Slow), Pultec (lo 3@100 / mid −3@700 / hi 5@12k),
  de-ess 6K@8: the canonical vocal chain (numbers are a drum-loop sanity render; tune comp/de-ess to the voice).
- **`voxbox-bus-tube-glue`** — Line in4 g40 + light comp + Pultec smile (lo 3@50 / hi 4@16k) + **Limit@5**: gentle tube
  tone + peak control (**crest ↓, +4 dB denser**). The control counterpart to drum-glue's opening.

**The crest direction is the proof:** the compressor *raises* crest (opens transients); the `Limit` mode *lowers* it
(peak control). A 0.00 delta means the `.component` twin loaded.

### How to drive it headless

Use **[[vst-preset]]**'s `apply_vst_preset.py` (`setattr`s every param, strings included), setting **all 25** params
explicitly. `presets/vst/voxbox-*.json` are ready. Apply:
`../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
projects/<track>/mix/<stem>_voxbox.wav` (it peak-normalizes the output, absorbing the drive's level + the no-make-up-gain
comp). Dump the live surface any time with `presets/vst/dump_params.py uaudio_manley_voxbox`; set `dump_state=true`
(via `apply-vst-chain`) for a byte-stable re-render.

---

# Part B — how the Manley VOXBOX works (web-research synthesis, adversarially verified, cited)

> Claims graded by adversarial verdict; corrected where a check refined them; "(reported, unverified)" where no
> authoritative confirmation. **Where the installed plugin's measured surface (Part A) differs, Part A wins for what renders.**

## 1. What it is

- **Maker / origin.** A **mono, single-channel, all-tube (Class-A) "reference channel strip"** designed and hand-built
  by **Manley Laboratories, Inc.** (Chino, CA), **introduced 1998**, **NAMM TECnology Hall of Fame 2016**. Manley's own
  name is the **"VOXBOX Reference Channel Strip / Deluxe All-Tube Recording Channel."** "The ultimate all-tube vocal
  processor" is **UA's tagline** for the plugin (Manley does call it "the unrivalled ultimate vocal channel" in EveAnna
  Manley quotes). **EveAnna Manley** (Manley Labs President) is credited with the **front-panel layout**, **not** the
  circuit — attribute the design to **Manley Laboratories** (don't say "designed by EveAnna Manley"). [SUPPORTED, corrected]
- **All-tube *audio path*, solid-state control.** The signal path is entirely vacuum-tube/Class-A; **sidechain/detector
  circuitry is solid-state**, and the passive EQ + opto cells contain no tubes themselves (tube gain stages make up the
  passive loss). **4 tubes:** 2× `12AX7` (mic-pre + EQ gain) + 2× `12BH7A` line drivers. [SUPPORTED]
- **Four blocks:** (1) tube mic/line preamp, (2) **passive electro-optical compressor**, (3) **passive Pultec-style EQ
  (MEQ-5-derived)**, (4) **de-esser / opto limiter** — plus a **Manley IRON output transformer**.
- **Signature topology — the audio path is `INPUT → COMPRESSOR → MIC PREAMP → EQ → DE-ESS/LIMITER → LINE AMP`** (per
  Manley's block diagram, manual p.12). The **compressor sits first, before the preamp**, to clamp transients before the
  first tube (lowering distortion). The de-ess/limiter is **post-EQ**, last before the output. **Fixed / non-reorderable**
  (only an EQ-INPUT 3-way LINE/PRE/INSERT + per-section bypass). The GUI's left-to-right blocks are **not** the audio path. [CONFIRMED]
- **Primary use:** premium **vocal tracking**; strong on bass DI, acoustic/electric guitar, drums/percussion, VO,
  piano/strings/horns, and as a tube-tone bus processor.

## 2. Preamp / input

- **SOURCE Mic/Line** — Mic is the colour path; **Line ≈ −4 dB** (plugin). On Apollo **Unison**, SOURCE switches the
  hardware preamp input. **GAIN 40/45/50/55/60 dB** sets the preamp's **negative feedback** → it's a **tone/colour
  control** (higher = more drive + mostly 2nd-harmonic), **explicitly "not a pad."** **INPUT** is a **passive
  attenuator before the comp+pre** ("knock down a loud signal, not boost a weak one"); default fully open. [CONFIRMED]
- **LOW filter 120/80/FLAT** — a gentle **6 dB/oct min-phase HPF** (mic/line/instrument). **PHASE 0/180** (mic-only on
  hardware; the middle "LINE" position there disconnects the mic transformer). **48 V phantom** = mic-only, locking,
  FET-condensers only — switch OFF before changing mics. **Mic Z = 2400 Ω; the 100 kΩ is the instrument DI** (don't conflate).
- **METER (5-pos, two kinds):** **levels** LINE IN / PRE OUT / EQ OUT, and **gain-reduction** **G-R** (comp) / **D-S**
  (de-ess). The hardware VU is averaging — track to ~**−6 dBFS** peaks, not 0. **OUTPUT (−60…+12 dB)** is a **plugin-only**
  trim (no hardware master knob; the comp has **no make-up gain** by design — recover level with INPUT/GAIN/THRESHOLD/OUTPUT).
- **XFMR IN/BYPASS** — the **output** transformer, wired **last**; IN = slight colour/weight, BYPASS = cleaner/open
  (a **software-exclusive** bypass in the plugin). *(Part A: near-transparent on our drum material.)*

## 3. The compressor

- **Passive electro-optical** (Vactrol/LDR "dLUX" module, ~0.1 dB insertion loss, no measurable distortion of its own —
  colour comes from the tubes). Manley frames it as a **hybrid** borrowing from **Variable-Mu and ELOP** designs — **not
  simply "an ELOP."** [CONFIRMED, corrected]
- **Ratio: NOT a fixed/selectable 3:1.** The "COMPRESS 3:1" toggle marking is **nominal**; the real ratio is **"program
  dependent and non-linear, generally similar to 3:1."** No ratio control. (The "10:1" elsewhere is the *de-ess/limiter*.) [CONFIRMED]
- **THRESHOLD** continuous, **CW = more comp**, sits after INPUT (set depth via INPUT-drive + THRESHOLD). **ATTACK** 5-step
  **≈4–70 ms** (Slow lets transients pass). **RELEASE** 5-step **≈0.3/0.5/1/2/5 s** with documented voicings:
  **FAST** = ELOP limiter (best 3–8 dB GR); **MED FAST** = LA-2A-like, **tuned for drums & bass**; **MED/MED SLOW** =
  the usual **vocal** choices; **SLOW** = most inaudible (**Slow attack + Slow release ≈ a fader-rider**). (LA-2A ≈ Fast
  atk + Med Fast rel; LA-3A ≈ Slow atk + Med Slow rel.) **25 atk/rel combos.** [SUPPORTED; per-step ms reported, unverified]
- **LINK/SEPARATE** = a **STEREO L/R link** (both channels reduce the same dB to hold the centre) — **not** a comp↔de-ess
  link; mono-in locks to LINK. [CONFIRMED, corrected]
- **Character:** smooth, transparent, "liquid" opto leveling — a **leveler, not a grabber**; "push it hard without sounding smashed."

## 4. The EQ

- **100 % passive LC (inductor/cap) Pultec-style**, based on the **MEQ-5 (midrange Pultec) — NOT the EQP-1A**, extended
  by Manley to full range. **PEAK-DIP-PEAK**: **LOW boost-only / MID cut-only / HIGH boost-only** — no low/high cut, no
  mid boost, **no Q/bandwidth control** (Pultec **proportional-Q**: bandwidth narrows as gain rises; adjacent bands
  interact). **The EQP-1A "boost + cut the same band" trick is impossible here** (separate single-function bands). [CONFIRMED]
- **11 freqs per band (33 total).** LOW: 20/35/50/70/100/150/200/300/500/700/1000 Hz (0…+10 dB). MID: 200/300/500/700/
  1k/1.5k/2k/3k/4k/5k/7k Hz (0…−10 dB). HIGH: **1.5k/2k/3k/4k/5k/6.4k/8k/10k/12k/16k/20k Hz** (0…+10 dB) — **the 2 kHz
  position is real; the GUI label hides it** (don't transcribe only 10). [CONFIRMED, corrected]

## 5. De-esser / limiter

- A **second opto stage** (ELOP-limiter-derived) with a **passive LC notch in the detector**. **3K/6K/9K/12K** tune the
  de-ess detection band (the whole signal ducks when that band exceeds threshold — frequency-conscious, not a band-only
  cut). **THRESHOLD** CW = more. The **5th position `Limit`** bypasses the notch → a **wideband 10:1 LA-2A-style opto
  limiter** (≈2 ms attack / ~0.5 s release) — **smooth/program-dependent, NOT a fast brickwall.** It's **independent of
  the compressor**, so you can compress (pre-EQ) *and* limit (post-EQ) at once. Max GR (spec): Comp 16 dB / Limit 32 dB
  absolute; 8/5 dB at +4 dBu. [CONFIRMED, corrected]

## 6. The UAD / UADx plugin

- **Component-level emulation** built with Manley. **UAD-2/Apollo** release **2016-08-02** ($299); **UADx native**
  (VST3/AU/AAX, CPU) **2023-08-08** — the native build is the headless-renderable one. Reproduces all four sections + the
  fixed serial flow + the software-only **XFMR bypass** and **OUTPUT** trim. **Unison** preamp integration on Apollo.
  **Mono** processor (dual-mono on stereo; Link/Separate covers stereo). Ships factory presets; UA documents **Chuck
  Zwicky's "Warm Male Vox"** (GAIN 60, INPUT way down, 80 Hz roll-off, OUTPUT −6, fastest comp atk/rel, de-ess at 3K).
  Oversampling/internal-rate behaviour is **undocumented** (don't assert). [SUPPORTED]

## 7. How engineers use it

| Source | Moves (starting points) |
|---|---|
| **Lead vocal** ★ | GAIN as colour (40–45 clean → 55–60 grit); INPUT to tame hot input, OUTPUT to recover. Comp ~**3 dB GR**, **Medium/Med-Slow** atk+rel, don't exceed ~−3 dB on tracking. EQ: **MID DIP @1–1.5 k** de-honk, **HI PEAK @12–15 k** air, **LOW PEAK @70–200** chest. De-ess to the offending band; **Limit** as a smooth safety limiter. |
| **Bass DI** | **LOW PEAK @150–200**, **MED FAST** comp (tuned for bass), LINE for clean / MIC for colour. |
| **Acoustic / guitar** | small **MID DIP @3–4 k**, gentle **HI PEAK** sparkle, **MED/MED-SLOW** comp for a few dB. |
| **Drums / perc** | **MED FAST** release ("LA-2A-like, tuned for drums"); PHASE 180 on snare-bottom; the optical comp **opens transients** (Part A). |
| **Bus / mix** | tube tone + body + the `Limit` as gentle glue/peak control (the box adds colour, not transparency). |

## 8. Comparisons & reputation

Smooth, **open, "hi-fi"** tube character — clean by default, **drives to grit** when pushed; "the most authentic analog
emulation" (Chuck Zwicky). Endorsed by Joe Chiccarelli, Zwicky. **vs Avalon VT-737:** the VOXBOX is **mellower / warmer /
cleaner / more flexible** with the better preamp + (comp-first) compressor + more elaborate de-ess/limiter; the Avalon is
**more saturated / "in your face"** with an arguably more complex EQ. A common move: VOXBOX first to control tone, then push
the Avalon for "ethereal pop." [medium confidence]

## 9. Pitfalls / gotchas

1. **Audio path is comp-FIRST and FIXED** — don't infer order from the GUI; Input → Comp → Preamp → EQ → De-ess/Limiter → Output.
2. **Comp ratio is program-dependent, not a fixed 3:1**; no ratio control. It's a **Variable-Mu/ELOP hybrid opto**, not "an ELOP."
3. **Thresholds read "backwards"** (higher number = more), and **`comp_thresh` is relative to `input`** (drive). [Part A]
4. **No comp make-up gain** — recover level via INPUT/GAIN/THRESHOLD/OUTPUT.
5. **INPUT = attenuator (default open); GAIN = colour/negative-feedback (not a pad)** — don't confuse them.
6. **LINK = stereo L/R link**, not comp↔de-ess; inert in mono.
7. **`Limit` is a smooth opto limiter, not a brickwall** — no true-peak/ceiling; hand off to render-mastered / [[fabfilter-pro-l-2]] for the real limiter.
8. **EQ is PEAK-DIP-PEAK only** (no low/high cut, no mid boost, no Q); **based on MEQ-5, not EQP-1A**; the EQP-1A boost+cut trick is impossible.
9. **HI PEAK has 11 freqs incl. 2 kHz** — don't drop it.
10. **EQ 0–10 dials are nonlinear** (action 5–10). **The output transformer is subtle** here (don't expect big colour).
11. **Headless control trap:** all 25 params are enums; the string switches need the **[[vst-preset]]** harness + opaque
    `dump_state`, not `apply-vst-chain`'s float dict; load the **`uaudio_*.vst3`** build (the `UAD …` twin passes through offline).

> **Pure-DSP equivalents (no plugin, deterministic):** tube/opto colour → `[L] saturate-loop`; gentle leveling →
> `[L] compress-loop`; air/presence → [[excite]]; surgical/tilt EQ + low-end weight → `[L] apply-eq`; de-ess →
> [[de-ess]]; peak limiting → `[L] render-mastered` / [[fabfilter-pro-l-2]]. Reach for the VOXBOX when you want *its*
> smooth all-tube vocal-channel voice — opto leveling + passive Pultec EQ + tube colour — in one pass.

---

## Sources

Manley — VOXBOX Owner's Manual (rev. Apr 2023; OVERVIEW & BLOCK DIAGRAM p.12, control descriptions, TUBE & TRIM
LOCATIONS p.19) · Manley official VOXBOX product page · Manley ELOP+ / Stereo Pultec EQ pages · Tape Op — EveAnna Manley
interview (designer attribution). UA — Manley VOXBOX product page + UAD v8.7 press release (2016-08-02, $299) + Support
manual + "Producer Presets Unpacked: VOXBOX" (Chuck Zwicky) + native-release notes (2023-08-08). Reviews — Recording
Magazine (Oct 1998 HW / 2017 plugin), MusicRadar, SonicScoop, KMR Audio (EQ topology), Audio Plugin Guy (LINK = stereo
link), iDesignSound, FrontEndAudio, Full in Bloom, Perfect Circuit (ratio), ProSoundWeb (TEC HoF 2016), TubesRule (tube
complement). Forums — Gearspace VOXBOX settings / vocal-recording / vs-Avalon-737 threads. Plus **our own param-surface
dump + render/THD/meter results (Part A)** on `/Library/Audio/Plug-Ins/VST3/uaudio_manley_voxbox.vst3` via Pedalboard 0.9.23.
