# Studer A800 (UAD/UADx) — field guide: warmth & glue without harshness

How to drive the UAD/UADx **Studer A800** tape-machine plugin (`uaudio_studer_a800.vst3`) for warmth,
weight, and glue while staying off the upper-mid edge that driven tape introduces. Two halves: **Part A**
is *measured on this rig* (the real param surface + isolation numbers from our own renders); **Part B** is
a *web-research synthesis* (cited) of how the machine actually works. The skill [[studer-a800]] is the
measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — it can't judge the ±2 dB head bump, deep sub, true-peak
> from tape transients, or HF air. **Meters own this.** Verify every tape move with `[L] measure-spectrum`
> (tilt / centroid / third-octave), `[L] measure-loudness`, `[L] check-clipping`, `[L] measure-distortion`.
> Driving Input raises level *and* pushes true-peak — re-measure after every change.

---

## TL;DR (the headline, measured)

1. **Lightly-driven tape DARKENS — *usually* a harshness cure, not the cause.** Isolated on our drum bus, the
   Studer pulled spectral centroid **−341 Hz** (warmer); every lever we swept only ever darkened it further.
   So when a "tape" chain sounds harsh, **suspect upstream first** — measure each plugin alone (on our 70s drum
   bus the culprit was the **Neve 1073's +2 dB @ 3.2 kHz mid**, centroid **+808**, not the tape). **But tape can
   itself be the harsh one:** over-driving the Input or **under-biasing** generates the tape's *own* odd
   (3rd/5th/7th) saturation + IMD straight into the **2–6 kHz** presence band (§5), and high-headroom GP9/900
   stay brighter. Rule: isolate & measure *every* stage — and fix a **tape-stage** harshness with **less Input /
   over-bias / higher-headroom tape**, not by blaming the EQ. *(Verified 2026-06-03: an adversarial web fact-check
   confirmed the measured darkening; it refuted only the over-absolute "almost always upstream" wording — hence
   this scope.)*
2. **Centroid is a *balance* metric — mind the 30-IPS trap.** We measured **30 IPS as *darker* than 15 IPS**
   (−517 vs −341) even though textbooks call 30 IPS "brighter." Both are true: 30 IPS extends the absolute
   top *and* moves its head bump up to ~100–120 Hz, and on bass-heavy drums that upper-bass weight pulls the
   centroid down. Read the full spectrum, know what the number means.
3. **For taming top-end specifically**, the direct levers (measured) are **`repro_hf_eq` down** (−1364 at 0),
   **bias up / over-bias** (theory), and **less Input drive** — not IPS alone.
4. **Default starting point:** `path_select=Repro`, `tape_type=456`, `ips=15 IPS`, `emphasis_eq=NAB`,
   `cal_level=6.0`, `auto_cal=True`, `noise=False` — then drive `input_level` to taste and trim `output_level`.

---

# Part A — measured on this rig

Probe: `uaudio_studer_a800.vst3` loaded via Pedalboard (stemmy-loops `vst` extra), processing
`projects/drums-kit/mix/bus_70s_balanced.wav` (60 s drum bus) at +10 dB input gain, outputs peak-normalized
before measuring so only **spectral shape** is compared. Centroid (Hz) and 5-band tilt (dB/oct) are the
harshness proxies; the smoothed `band_ratio_*` fields were too coarse to resolve the move.

### The real parameter surface (Pedalboard-exposed)

| Param | Values | Role |
|---|---|---|
| `path_select` | `Thru` · `Input` · `Sync` · `Repro` *(default Repro)* | signal path; **Repro** = full record→tape→reproduce sound |
| `ips` | `Off` · `7.5 IPS` · `15 IPS` · `30 IPS` *(15)* | tape speed — head-bump freq, HF roll-off, headroom, noise |
| `tape_type` | `250` · `456` · `900` · `GP9` *(456)* | formula — saturation onset & tone |
| `cal_level` | `3.0` · `6.0` · `7.5` · `9.0` *(6.0)* | operating level in dB over 185 nWb/m (+6 = 355 nWb/m); headroom, not volume |
| `emphasis_eq` | `NAB` · `CCIR` *(NAB)* | emphasis curve (IEC2/IEC1); NAB has a 50 Hz bass shelf, CCIR doesn't. **AES-locked at 30 IPS** |
| `input_level` | −12 … +24 dB *(0)* | **drive into the tape** — the primary saturation control (also raises level) |
| `output_level` | −24 … +12 dB *(0)* | post-tape make-up; pull down as you raise Input to gain-match |
| `bias` | `0.00 V` … `15.50 V` *(10.18)* | record-head AC bias — **over-bias (higher) = warmer/smoother/less distortion; under-bias = brighter/spittier/more 3rd harmonic** |
| `hf_record_eq` | 0 … 10 *(1.8)* | HF record pre-emphasis (Red card) — a **brightness** control, not a de-harsher |
| `repro_hf_eq` / `repro_lf_eq` | 0 … 10 *(3.5 / 8.8)* | playback HF/LF trim for the **Repro** path (active default) |
| `sync_hf_eq` / `sync_lf_eq` | 0 … 10 *(3.5 / 8.8)* | playback trim for the **Sync** path |
| `auto_cal` | `False` / `True` *(True)* | auto-align bias + record/playback EQ for the chosen Tape/Speed/Cal. **Keep ON** unless deliberately mis-aligning |
| `noise` / `hum_noise` / `hiss_noise` | bool / ±25 / ±25 *(off / 0 / 0)* | modeled hum + hiss; off by default, stacks across instances |
| `power` / `master_bypass` | bool | — |

> Note: there is **no Wow/Flutter control** — wrong plugin for pitch wobble.

### Isolation — which plugin lifts the hi-mid? (centroid = harshness proxy)

| chain element (alone) | centroid | Δ vs dry | tilt | verdict |
|---|---|---|---|---|
| dry balanced bus | 4266 | — | −2.69 | reference |
| **Neve 1073** (mid +2 @ 3.2k, hf +1) | 5074 | **+808** | −1.43 | **the brightener** |
| dbx 160 (−24, 4:1) | 4330 | +64 | −2.05 | ~neutral, opens top slightly |
| **Studer A800** (15 IPS/456/+6) | 3926 | **−341** | −2.56 | **darkens (warms)** |
| full chain | 4948 | +682 | −1.16 | brightness ≈ the Neve |

**Lesson:** the instinct "the tape is harsh" was wrong — the tape was the only thing pulling the top *down*.

### Studer lever sweep (alone, Δcentroid vs dry)

| setting | Δcentroid | reading |
|---|---|---|
| 15 IPS / 456 / +6 (`auto_cal` OFF) | −341 | baseline warm |
| same, `auto_cal=True` | −341 | **no measured change** (but ON is the correct/aligned default) |
| `input_level` 6 → 0 (less drive) | −352 | slightly darker (less HF from saturation) |
| **30 IPS** | **−517** | *darker*, not brighter — head bump up at ~100 Hz adds low-mid weight |
| 30 IPS + `auto_cal` ON + in 0 | −525 | — |
| `emphasis_eq` NAB → **CCIR** | −344 | **≈ no change on this material** (theory: CCIR is leaner/brighter) |
| **`repro_hf_eq` 3.5 → 0** | **−1364** | the most direct top-end kill (playback HF trim) |
| `tape_type` 456 → **GP9** | −254 | least dark — higher headroom stays cleaner/brighter |
| warm combo: 30 IPS / `repro_hf_eq` 2.0 / `hf_record_eq` 0.5 / in 0 | −996 | strong, controlled darkening |

**What this means for de-harshing (in order of directness):** `repro_hf_eq` down ≫ `input_level` down ≈
30 IPS ≈ over-`bias` (untested here, theory-backed) > tape choice. `emphasis_eq` and `auto_cal` moved the
spectrum negligibly *on this drum bus* (they matter more elsewhere / at other speeds).

### The presets that came out of this (in `presets/vst/`)

- `tight-70s-dry.json` — Neve 1073 → dbx 160 → Studer A800 (15 IPS/456/in 6). Punchy, but read **bright/harsh**
  (the Neve mid).
- `tight-70s-warm.json` — Neve **mid 0 / air 0**, tape warms. Centroid 5138 → **4982**.
- `tight-70s-warmer.json` — also **30 IPS + `repro_hf_eq` 2.5** and a softened punch upstream. Centroid → **4386**,
  ≈ the raw balance (4266) with tape glue + punch kept (crest 25.6).

> Our early presets set `auto_cal=False`; it made **no measured difference** here, but per UA the correct
> default is **ON** (it aligns bias + record/playback EQ). Prefer `auto_cal=True` going forward.

---

# Part B — how the machine works (web-research synthesis, cited)

## 1. What it is / what tape does

The **Studer A800** is a professional 2-inch, 24-track analog multitrack recorder; the UAD/UADx plugin models
its full record→tape→reproduce path (electronics, four tape formulas, three speeds, bias, EQ curves). Vs its
sibling the **Ampex ATR-102** (smoother, glossier 2-bus/mastering machine — its own deep-dive is [[ampex-atr-102]]),
the A800 is the **cleaner, punchier multitrack** engineers reach for on a drum bus or for "punch and cohesion"
(pluginoise.com). Canonical split: **Studer on tracks/buses, Ampex on the master.** Its
character leans on **harmonic + compression behavior** more than a huge LF bump (Endino bench data).

The real audio effects of tape, all modeled:

- **Head bump** — a LF response rise of **~+1.5 to +2 dB in-spec** (up to ~3 dB; reads as ±2 dB undulation,
  often with a shallow complementary dip just above), ~1–1.5 octaves wide, from recorded wavelength approaching
  the playback-head pole length; **bigger when under-biased/misaligned**. Center freq is **speed-dependent and
  doubles each time speed doubles** — the octave-per-doubling is the reliable invariant; the *absolute* Hz is
  machine/head-geometry specific (Endino measured ~35–40 Hz @15 IPS on an Ampex MM1200 vs the ~60 Hz
  Studer/Otari alignment figure). This is what "fattens" drums/bass — and it is **not** harmonic distortion.
- **HF softening** — loud HF transients don't survive magnetic recording (self-erasure + gap loss), so the
  top gets "less brash"; slower speed = more HF loss (SoS, CCRMA).
- **Saturation / harmonics** — predominantly **odd-order, chiefly 3rd-harmonic** from the symmetric
  (tanh / S-shaped) magnetization curve. MOL is defined at **3% 3rd-harmonic THD @ 1 kHz**
  (MOL = *Maximum **Output** Level*; 1 kHz is the **open-reel** convention — cassette / some datasheets use
  315/400 Hz. Don't conflate the 3% MOL with the ~1% THD *normal operating level* you align near for headroom).
  This is the lever that turns harsh when overdriven (§5).
- **Tape compression** — gentle, program-dependent, un-pumped transient rounding. Lowers crest, "glues";
  drums benefit most (huge transient spikes).
- **Wow & flutter** — worst at 7.5 IPS (0.06%), spec-equal 15/30 IPS (0.04%). **No W/F knob in the A800 UI.**
- **Noise** — hiss + hum, modeled but **off by default**; floor tracks speed (30 IPS quietest) and Cal.

## 2. The controls (UA naming)

**Primary:** **Path Select** (INPUT = electronics only / SYNC / **REPRO** = fullest tape sound / THRU =
bypass) · **Tape Speed** (7.5/15/30) · **Tape Type** (250/456/900/GP9) · **Cal** (+3/+6/+7.5/+9 dB over
185 nWb/m — headroom, *not* unity gain) · **Equaliser** (NAB/CCIR, AES-locked at 30 IPS; also sets hum
**NAB→60 Hz, CCIR→50 Hz**) · **Input** (−12…+24 dB, the **primary drive/saturation** control) · **Output**
(−24…+12 dB make-up) · **VU** reads post-tape, and the plugin's operating level is **−12 dBFS = 0 VU**.

**Secondary (calibration cards):** **HF Driver / Bias (Red)** — bias + HF record pre-emphasis;
**over-bias = warm/smooth/duller/lower-distortion, under-bias = brighter/edgier/more distortion** — the
deepest warm↔harsh control after Input; its HF Record EQ "injects extra sparkle before tape" = a brightness
control, **not** a de-harsher. **Sync EQ (Yellow)** / **Repro EQ (White)** — playback HF/LF trims for those
paths. **Noise (Blue)** — Hum + Hiss ±25 dB, needs Noise Enable. **Auto Cal** — aligns bias + EQ for the
chosen Tape/Speed/Cal. **Gang/Group** — link channels.

**Uncertainty:** exact head-bump Hz/dB and exact bias dB range are **not published by UA** (general-tape
estimates); plugin Cal nWb/m is not lab-verified — trust the **dB-over-185** relationship.

## 3. The 5 sonic levers

**Lever 1 — IPS (speed).** Sets head-bump center (doubles with speed: 27→54, 60→120, 100→200 Hz), HF
roll-off, distortion/compression onset, noise floor.

| Speed | Head bump | HF / noise | Character |
|---|---|---|---|
| 7.5 | biggest, lowest | most roll-off (~15 kHz), most hiss, W/F 0.06% | most colored / lo-fi |
| 15 | **~50–70 Hz** (≈+2 dB) | smooth roll-off, S/N 66 dB | **warm**, fuller lows, more compression |
| 30 | **~100–120 Hz** | extended top, S/N **70 dB**, flat to ~40 Hz | **clean/punchy**, tighter lows |

WARM → **15 IPS** (or 7.5 dark). BRIGHT/CLEAN → **30 IPS** (SoS heard the 30 IPS lift as a punchy **60–100 Hz**
boost — treat the bump as a *band*). *(See Part A: by spectral centroid, 30 IPS measured **darker** on our
drum bus — the upper-bass bump dominates the balance metric.)*

**Lever 2 — Tape formulation.** Saturation onset/headroom & tone, independent of drive.

| Formula | headroom | Character |
|---|---|---|
| **3M 250** | +3 (lowest) | warmest/vintage, rolled top, soft saturation |
| **Ampex 456** | +6 (~355 nWb/m) | balanced warm/round, best low thump — **default warm tape** |
| **BASF 900** | +9 (~510) | high output, minimal distortion, holds bass; **smoother/rounder than GP9**, can be "doughy" |
| **Quantegy GP9** | +9 (~510) | **ties 900** for highest headroom — the **tighter/punchier/brighter** of the two, tight lows; top can read "metallic" |

WARM → **456** (or 250, earliest soft 3rd-harmonic). CLEAN/HARSH-PRONE → **GP9/900** (stay clean; GP9 vs 900 =
tighter/brighter vs smoother/rounder; GP9 top can edge metallic). **Drive level dominates tape choice.**
*(The metallic / doughy / tightest-lows labels are subjective real-tape descriptors, not UA-published per-model
specs — the hard fact is the headroom order 250 < 456 < 900 ≈ GP9.)*

**Lever 3 — Calibration + Input (record level).** Cal sets where 0 VU sits in flux; Input drives above/below.
Ladder off **185 nWb/m = 0 dB**, +6 per doubling. **456 @ +6 = 355 nWb/m**, ~10 dB below the 3% THD MOL. At
−12 dBFS = 0 VU: 0 VU subtle → +3 thickening → +6 obvious compression+3rd-harmonic → +9 heavy (~3% THD).
WARM/lower-noise → higher Cal / hotter tape / push Input. CLEAN/transient-safe → under-cal (456 @ +3) or 250.
**Gotcha:** the A800 is a **−12 dBFS** plugin — a −18-referenced feed under-drives ~6 dB; a near-0 dBFS mix
slams it.

**Lever 4 — EQ curve (NAB/IEC2 vs CCIR/IEC1).** Headline is the LF: **NAB has a 50 Hz/3180 µs bass shelf;
CCIR has none** → ±~8 dB at the very bottom when mismatched; in-plugin (matched) it's the **presence/absence
of that bass shelf** + an HF time-constant difference.

| | NAB @15 | CCIR @15 | AES @30 |
|---|---|---|---|
| LF shelf | 50 Hz (bassier) | none (leaner) | — |
| HF corner | ~3.15 kHz (50 µs) | ~4.5 kHz (35 µs, **brighter**) | ~9.1 kHz (17.5 µs) |
| Hum | 60 Hz | 50 Hz | — |

WARM/darker-top + more lows → **NAB**. BRIGHTER/leaner → **CCIR**. **No choice at 30 IPS (AES only).**

**Lever 5 — Bias (HF Driver, Red).** AC bias linearizes the cubic (H³) term that makes 3rd harmonic. Standard
**overbias ~1.5–3 dB** above 10 kHz peak (250 ~1–1.5; 456 ~2–3). Under→over bias: 1 kHz output **+2–3 dB**,
10 kHz output **−4–6 dB**. WARM → **over-bias** (smoother, lower distortion, rounds harsh transients; costs
air). HARSH/BRIGHT → **under-bias** (spittier top, rising odd-harmonic crossover-type distortion — FX only).

## 4. Recipes

**(a) Warmth + glue on a DRUM BUS without dulling transients:** REPRO · 456 · 15 IPS · NAB · Cal +6 (or +3
for heat). Raise Input until VU shows only **~1–2 dB peak reduction** on the loudest snare/kick; trim Output
to match. Keep snap: if attack dulls, back Input off 1–3 dB, raise Cal to +9, or go **30 IPS / GP9**; for
heavy saturation use a **parallel/dry-wet** blend. Verify crest+PLR (`measure-microdynamics`) and that the
LF lifted, **not** 2–5 kHz.

**(b) Gentle MIX-BUS tape (peak-safe):** REPRO · 456 or GP9 · 30 IPS (AES) · Cal +6. Input → only ~1–2 dB
transient reduction; trim Output to unity. 15 IPS variant for a warmer/fuller bottom on a bright mix.
First insert (tape sets tone, use less EQ/comp after) **or** last & gentle (glue only). Noise OFF; mind the
**latency** (upsampling) with linear-phase tools.

**(c) Taming digital / upper-mid harshness with tape:** REPRO · **15 IPS** (bigger bump + more HF roll-off,
*not* 30) · **NAB** · **456 or 250**. Input only enough for **~1–3 dB compression**; **stop the moment the top
spits** (that spit is new 3rd harmonic). **Over-bias** for smooth warmth. Place tape **before** the compressor
so it absorbs spikes. If too dull: **don't** reach for HF Driver/HF Record EQ (re-adds brightness) — lighten
drive or move toward 30 IPS/CCIR. **Tilt test:** A/B loudness-matched; if a simple LF-up/HF-down EQ tilt
reproduces the "warmth," it was tilt, not saturation — and tape can't fix a true sibilance hotspot (use
`[L] de-ess` / `[L] apply-dynamic-eq` for surgery, tape for glue).

**(d) Placement & pro starting points (sourced).** Authentic UA usage = A800 on the **first insert** of each
channel (emulates tracking the whole multitrack to tape). For **dynamics/glue**, place tape **pre-compressor**
on a bus (Jacquire King: let the tape "control some of the initial dynamics" so the comp doesn't overwork). For
**color / non-standard** results, put it *after* other processors or in a **send/return** (parallel). There is
**no built-in dry/wet** — to keep dry transients, run it parallel via a send/return or a duplicate track (100 %
wet softens transients). Most-cited starting point: **456 · 15 IPS · Cal +9 · bias slightly hot**. Vance Powell's
published drum preset: **15 IPS · 3M 250 · CCIR**, most channels +3 over 250 nWb/m, with **kick/snare on a lower
ref so they saturate earlier**.

## 5. Why driven tape gets harsh

Tape's saturation curve is **symmetric (tanh)** → it generates **odd** harmonics (3rd, 5th, 7th), **not** the
even (2nd) harmonics tubes/transformers add. The "tape = warm even-order harmonics" belief is **backwards**:
tape's harmonics are predominantly **3rd-order — the harsh kind**; the real warmth is the **LF head bump +
gentle compression** (SoS, Sage Audio). **Predominantly odd ≠ exclusively odd:** the magnetic *process* is
odd/3rd (correct AC bias actively *minimises* the 2nd harmonic — so even-order in tape is a **mis-bias defect**,
not its warmth), but the analog *system* around it (bias/erase/head asymmetry, transformer/tube electronics in
the path) adds *some* 2nd. The symmetric-tanh model is a first-order idealisation; the odd/3rd conclusion and the
anti-myth stance still stand. Odd harmonics aren't octaves (3rd = octave+fifth, 5th = 2 oct+major
third, 7th = dissonant ♭7) so on dense signal they land as non-octave tones in the **2–5 kHz** presence band =
edge. Worse, multi-note saturation makes **intermodulation distortion** (non-harmonic sum/difference tones) —
grit that **no EQ notch fixes**; the cure is **less drive** (any nonlinearity that makes harmonic distortion
*also* makes IMD on multi-tone input — Rod Elliott/ESP — so the single-tone 3% THD MOL **understates** the real
grit on dense program). As Input rises: compression steepens (~3:1 past
MOL) and the stack climbs 3rd → 5th/7th → IMD; a **2–5 kHz (and 6–8 kHz) rise on a driven take is the
harshness signature, not warmth.**

**Levers to avoid harshness:** (1) **back off Input** (#1); (2) **high-headroom tape** (900/GP9) to stay
cleaner at the same drive; (3) **lower Cal** / run tape below rating; (4) **30 IPS** (highest headroom — but
no NAB softness there); (5) **CCIR → NAB** to pull HF emphasis; (6) **over-bias** to trade air for lower
distortion; (7) saturate **dark/low** sources not bright ones, drive the **bus lightly**, use **parallel**
blend.

## 6. Pitfalls & gotchas

- **−12 dBFS, not −18** — gain-stage so peaks land near 0 VU. **Cal ≠ volume** (raising it makes the same Input
  distort more). **Input both saturates AND raises level** — pull Output down and **A/B loudness-matched**.
- **30 IPS removes the NAB/CCIR choice** (AES) and rolls real sub below ~70–85 Hz — don't expect more sub or
  NAB softness there.
- **Head bump is level-independent** — boomy 15-IPS low end is the bump (switch to 30 IPS or HPF post-tape, not
  Cal/drive); the bump also brings a **~140 Hz trough** that can hollow lower mids, and can stack with kick/bass
  into 50–120 Hz mud (measure).
- **No Wow/Flutter knob.** **Noise is OFF by default** and **stacks across instances**. **Extra latency** from
  upsampling. **Run Auto Cal** after every Tape/Speed/Cal change. **HF Driver/HF Record EQ is a brightness
  control, not a de-harsher.**
- **Gang Controls is destructive.** When linked, a parameter edit overwrites **every open A800 instance** at once
  (built for 24-track work) and the old values "cannot be recovered" (red flashing-LED warning). Leave it off
  unless you mean to drive a multi-instance kit in lockstep.
- **Input/Output ranges:** Input **−12…+24 dB**, Output **−24…+12 dB** — confirmed by the UA manual, our measured
  param surface, *and* the screenshot. A manual-mirror page listing *both* as −24…+12 is an OCR error; don't trust it.
- **Disputed/approximate:** exact head-bump Hz/dB & bias dB range unpublished by UA; Cal nWb/m not lab-verified
  (trust dB-over-185); BASF 900 behavior is bias-dependent. Beginner blogs claiming "even-order warmth" are
  **wrong** — trust the symmetric-tanh physics (odd/3rd).
- **Don't EQ-fix a balance problem with tape, or vice-versa.** Meter — don't trust Gemini — for level/peak/stereo.

## 7. Decision table

| Goal | IPS | Tape | Cal | EQ | Drive / Bias |
|---|---|---|---|---|---|
| Warm rock drum bus (heft + bite, no harsh) | 15 | 456 | +6 (or +3) | NAB | Input → ~1–2 dB GR; bias normal |
| Fat/dark drums (kit sits back) | 7.5 | 456 | +6 | NAB | moderate Input; over-bias |
| Modern tight punch drums | 30 | GP9/900 | +9 | AES | push Input (high headroom) |
| Gentle mix-bus glue (peak-safe) | 30 | 456/GP9 | +6 | AES | Input → ~1–2 dB GR; trim Output |
| Warmer/fuller 2-bus | 15 | 456 | +6 | NAB | light Input; over-bias if edgy |
| Tame digital harshness | 15 | 456/250 | +3–+6 | NAB | Input → ~1–3 dB, stop on spit; **over-bias** |
| Transparent mastering glue | 30 | GP9/900 | +6–+9 | AES | modest Input (THD ≪ 1%); bias normal |
| Fat low end / sub weight | 15 | 456 | +6 | NAB | moderate Input (bump ~50–70 Hz) |
| Clean controlled sub | 30 | GP9 | +9 | AES | modest Input (bump ~100 Hz, clears 40–60) |
| Vintage lo-fi / FX | 7.5 | 250/456 | +6 | NAB | high Input; under-bias for grit |

*Default:* REPRO · 456 · 15 IPS · NAB · Cal +6 · Auto Cal ON · Noise OFF — then drive Input and gain-match Output.

---

## 8. The plugin UI & build (UADx vs UAD-2) + panel control-map

This maps the **exact panel in the UADx screenshot** to the Pedalboard params so an agent can read the knobs and
know what each does. **Bold value** = the screenshot's position.

### Front panel (primary — always visible)

| Panel control | Param | Values | What it does |
|---|---|---|---|
| **THRU / INPUT / SYNC / REPRO** buttons *(REPRO lit)* | `path_select` | Thru · Input · Sync · **Repro** | Signal path. THRU = true bypass; INPUT = machine electronics only (no tape sonics, cleanest); SYNC = sync-head record+play; **REPRO = full record→tape→reproduce = the fullest tape sound — the normal mode you want.** |
| **TAPE** knob *(→456; right reel reads 456)* | `tape_type` | 250 · **456** · 900 · GP9 | Tape formulation = saturation onset + tone (**not** a level/volume control). 250 warmest/lowest-headroom → GP9/900 cleanest/highest-headroom (§3). Drive dominates the choice. |
| **CAL** knob *(→+7.5)* | `cal_level` | 3.0 · **6.0** · 7.5 · 9.0 dB | Reference fluxivity in dB over 185 nWb/m (+6 = 355). Sets where 0 VU sits in flux = **headroom, not volume**; higher = more headroom before saturation + higher noise floor. UA per-tape: 250→+3, 456→+6, 900/GP9→+9 (push past for extra color). |
| **INPUT** knob *(→0)* | `input_level` | −12 … **0** … +24 dB | **Primary drive / saturation** (gain into the tape, like a console fader). Hotter = more harmonics + more tape compression + more level *and* true-peak. The main "amount" knob — stop when the top starts to spit (rising 3rd harmonic). |
| **OUTPUT** knob *(→0)* | `output_level` | −24 … **0** … +12 dB | Post-tape make-up gain. Pull it **down** as you push Input so you A/B **loudness-matched**. No tone change. |
| **IPS** knob *(→15)* | `ips` | Off · 7.5 · **15** · 30 IPS | Tape speed = head-bump centre (doubles per speed doubling), HF roll-off, headroom/noise, compression onset. 15 = warm default (LF bump, more compression); 30 = flattest/most-extended top, lowest noise, tighter lows, **AES-EQ-locked** (no NAB/CCIR); OFF stops the transport. |
| **VU meter** *(−20…+3)* | *(read-only)* | **0 VU = −12 dBFS** | Post-tape level / how hard you're driving the tape. Near 0 VU = heavy compression/saturation. **Not a peak meter** — meter true-peak separately. |

### Top bar (UAD Toolbar — shell, **not** A800 params, **not** reachable from a headless float dict)

| Panel control | What it is |
|---|---|
| **IN** *(lit)* | Engage / bypass the whole plugin (shell in/bypass). Lit = processing. |
| **A / B** | Compare two full-settings snapshots; both save with the project. |
| **COPY / PASTE** | Copy/paste the entire setting between instances. For a reproducible **headless** render use a dumped opaque **`dump_state`** blob — **not** Copy/Paste or the preset browser (UA's preset format is not a generic `.vstpreset`). |
| **preset name / palette / "…"** | Preset browser · GUI colour · options menu (Copy A→B, Auto Cal, etc.). |

### Secondary (behind the reel deck — click the **Studer badge / "Open"**; *not* on the screenshot)

| Hidden control | Param | Notes |
|---|---|---|
| **HF Driver / Bias** (Red card) | `bias` (0–15.5 V, def 10.18) · `hf_record_eq` (0–10, def 1.8) | **Over-bias = warmer/smoother/lower-distortion/duller top; under-bias = brighter/spittier/more 3rd-harmonic** — the deepest warm↔harsh control after Input. `hf_record_eq` injects pre-tape sparkle = a **brightness** control, *not* a de-harsher. |
| **Emphasis EQ** | `emphasis_eq` | **NAB** = ~50 Hz bass shelf (bassier); **CCIR** leaner/brighter. **AES-locked at 30 IPS** (LEDs dim). Also sets hum (NAB 60 Hz / CCIR 50 Hz). |
| **Repro EQ / Sync EQ** (White / Yellow) | `repro_hf_eq`·`repro_lf_eq`·`sync_hf_eq`·`sync_lf_eq` (0–10) | Playback-path trims (Repro active on the default path). **`repro_hf_eq` DOWN is the most direct top-end kill** (measured −1364 centroid at 0). |
| **Noise / Auto Cal / Gang** | `noise`·`hum_noise`·`hiss_noise`·`auto_cal`·`gang` | Noise (Blue) OFF default + stacks across instances; **Auto Cal ON** (aligns bias+EQ on any Tape/Speed/Emphasis change); **Gang = destructive global link** of all instances (see Pitfalls). |

### Build & headless notes

- **UADx vs UAD-2.** "UADx" is UA's **native (CPU) build** — VST3/AU/AAX, **no Apollo/Satellite/PCIe DSP needed**.
  One purchase grants both the DSP and native licenses, and UA states the native A800 is sonically identical to the
  DSP version (a marketing claim, not an independent null-test — UA does publish a DSP-vs-native FAQ for the ATR-102).
- **Licensing.** iLok-**account** based, but a **perpetual** UADx license uses **local/computer authorization — no
  USB dongle required** (dongle/cloud only for portability or the UAD **Spark** subscription). On a render farm an
  iLok account + machine auth + **PACE** must still be present even though no UAD DSP hardware is — the iLok/PACE
  landmine the repo flags. See [[vst-verify]].
- **The right binary.** Load **`uaudio_studer_a800.vst3`** (this UADx native build — renders headless). The
  `UAD ….component`/twin passes audio through offline — never use it.

---

## Sources

UA Studer A800 manual (help.uaudio.com) · uaudio.com product page · Sound on Sound A800 review · Tape Op
review · pluginoise.com (UAD Ampex vs Studer) · masteryourtrack.com (tape IPS) · gearspace.com (IPS, NAB vs
CCIR threads) · vintagedigital.com.au (A800 hardware spec) · endino.com/graphs (measured recorder curves) ·
Sage Audio / Sweetwater / CCRMA (tape physics & harmonics) · MRL / pSpatial (NAB vs IEC) · UA UADx-native +
iLok offline-auth FAQ (help.uaudio.com) · SonicScoop / Jacquire King "3 tape techniques" · Production Expert
(how pros use tape) · Mix Online "Analog Tape 101 Pt 3: Bias Magic" · till.com (symmetric curve → odd harmonics)
· Rod Elliott/ESP (THD↔IMD) · IEEE / MRL (even-order = improper-bias indicator). Plus **our own isolation/sweep
measurements** (Part A) on `uaudio_studer_a800.vst3` via Pedalboard, and a **2026-06-03 web + adversarial
fact-check** (27 agents) that confirmed every load-bearing claim and scoped the caveats above.
