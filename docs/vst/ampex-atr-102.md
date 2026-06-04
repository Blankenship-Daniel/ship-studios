# Ampex ATR-102 (UAD/UADx) — field guide: the 2-track mastering tape, glue & gloss without harshness

How to drive the UAD/UADx **Ampex ATR-102 Master Tape** plugin (`uaudio_ampex_atr-102_tape.vst3`) — the
**2-track ¼/½/1″ mastering & mixdown** machine, the smooth/glossy counterpart to the punchier multitrack
**[[studer-a800]]**. Two halves: **Part A** is *measured on this rig* (the real 30-param surface + isolation /
width×speed / harmonic numbers from our own renders); **Part B** is a *web-research synthesis* (cited) of how
the machine actually works. The skill [[ampex-atr-102]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — it can't judge the ±2 dB head bump, deep sub, true-peak from
> tape transients, the L↔R crosstalk image, or HF air. **Meters own this.** Verify every move with
> `[L] measure-spectrum` (centroid / tilt / third-octave), `[L] measure-loudness` / `measure-microdynamics`
> (crest/PLR = the glue), `[L] check-clipping`. **Record level raises level *and* saturates** — re-measure after
> every change, and A/B loudness-matched (`[L] render-ab`).

---

## TL;DR (the headline, measured)

1. **It's a color/glue insert, not a leveler — and the gloss is the TRANSFORMER (even/2nd), the tape is ODD
   (3rd).** A 1 kHz sine probe: driven, transformer **ON H2 = −55 dB** vs **OFF H2 = −70 dB** (+15 dB of 2nd
   harmonic from the transformer) while the tape's **3rd (H3 = −14 dB) is unchanged**. So the ATR's character =
   **tape's odd 3rd + transformer's even 2nd** — a richer blend than the A800. Drive it hard and the *odd* stack
   climbs (3rd → 5th → 7th) = harshness; the cure is **less Record level**.
2. **Default ATR darkens about like the A800.** REPRO/15 IPS/456/+6/½″/NAB at +10 dB drive pulled centroid
   **4266 → 3871 (Δ−395)** with **crest 25.0 → 22.4** (gentle tape compression). The A800 on the *same file*
   was Δ−341. They're close — the ATR's distinction is the **transformer's even-harmonic top** + the **tape-width
   / per-channel / crosstalk** feature set, not a wildly different tilt.
3. **WIDTH × SPEED is the signature combo.** **15 IPS = warm/full** (wider tape → *darker*); **30 IPS =
   bright/tight** (wider tape → *leaner, tighter low end*, band-low 0.63 → **0.53** at 1″). **1″ + 30 IPS = the
   most hi-fi master**; **½″ + 15 IPS = warm mixdown**.
4. **Default starting point:** `path=REPRO`, `ips=15 IPS` (warm) or `30 IPS` (clean master), `tape_type=456`,
   `cal_level=6.0`, `head_width=1/2` (or `1` for hi-fi), `emphasis_eq=NAB`, `transformer=True`,
   `wow_flutter/crosstalk/hiss=False` for a clean master (ON for vibe), `auto_cal=True` — then drive Record via
   `input_gain_db` and gain-match.

---

# Part A — measured on this rig

Probe: `uaudio_ampex_atr-102_tape.vst3` loaded via Pedalboard (stemmy-loops `vst` extra), processing
`projects/drums-kit/mix/bus_70s_balanced.wav` (the same 60 s drum bus the [[studer-a800]] doc used → a direct
sibling comparison) at +10 dB input gain unless noted, outputs **peak-normalized** before measuring so only
**spectral shape** is compared. Centroid (Hz) and 5-band tilt (dB/oct) from `[L] measure-spectrum`; crest from
`[L] measure-loudness`. Both are gain-invariant the way we use them. The **dry centroid measured 4266** — bit
for bit the A800 doc's dry number on this file, confirming same meter / same source.

### Renders headless — but watch the probe false-negative

The plugin **renders headless** (UADx native, no iLok — the `vintage-1960s` preset chain has used it for months).
⚠️ The generic param-response probe (`probe_plugin.py`) reports a **false `PASSTHROUGH`** because it toggles
`auto_gain` (a no-op on the spectrum at default drive) — its own note even shows the output already differs from
the input. Confirm it really processes by pushing a *tonal* param (`repro_hf_eq=0`, or Record drive) and
re-measuring, **not** by trusting the auto-probe.

### The real parameter surface (Pedalboard-exposed — 30 params: 28 audio/modeling params + the 2 control bools `power`/`master_bypass`)

Every parameter is an **enum** (Pedalboard exposes the ATR's controls as discrete value lists). Gains accept a
float that snaps to the nearest step; mode/speed/tape/width/EQ are string/bool enums. All of this must go
through the **[[vst-preset]]** harness — `apply-vst-chain`'s `parameters` dict is float-only and can't gain-stage.

| Param (Pedalboard key) | Values *(default)* | Role (UA name) |
|---|---|---|
| `path_select` | `SYNC` · `REPRO` · `INPUT` · `THRU` *(REPRO)* | signal path; **REPRO** = full record→tape→reproduce. INPUT = electronics, no tape. THRU = bypass (meters live). |
| `l_rec_level` / `r_rec_level` | −inf … +9.5 dB *(0.0)* | **Record = the DRIVE / primary color control** (more = saturation+compression; also raises level). Per channel. |
| `l_repro_level` / `r_repro_level` | −inf … +9.3 dB *(0.0)* | **Reproduce = playback make-up** (pull down as you push Record). Per channel. GUI sits LEFT of Record (faithful to hardware). |
| `auto_gain` | `False`/`True` *(True)* | links Record↔Reproduce for **unity output** while you change drive (built-in loudness-matched A/B). |
| `ips` | `3.75` · `7.5` · `15` · `30 IPS` *(15)* | tape speed — head-bump freq, HF roll-off, headroom, noise. (1/2″ & 1″ heads need ≥15 IPS.) |
| `tape_type` | `250` · `456` · `900` · `GP9` *(456)* | formula — saturation onset & headroom (250 earliest/warmest → GP9 cleanest). |
| `cal_level` | `3.0` · `6.0` · `7.5` · `9.0` *(6.0)* | operating level / reference flux over 185 nWb/m (+6 = 355 nWb/m, **10 dB below 3% THD MOL**); a **2nd drive/headroom lever**. |
| `head_width` | `1/4` · `1/2` · `1` *(1/2)* | **tape WIDTH** — headroom / noise / LF weight / "size". The signature lever the A800 lacks (1″ = aftermarket hot-rod). |
| `emphasis_eq` | `NAB` · `CCIR` *(NAB)* | playback emphasis curve. NAB = 50 Hz bass shelf (warmer/fuller lows, 60 Hz hum); CCIR/IEC = leaner/brighter (50 Hz hum). **AES-locked & inert at 30 IPS.** |
| `l_bias` / `r_bias` | `0.0` … `19.5 V` *(11.5)* | record-head AC bias — **over-bias (higher) = smoother/darker/less distortion; under-bias = brighter/spittier/more 3rd**. |
| `l_hf_eq` / `r_hf_eq` | 0 … 10 *(1.1)* | **Record HF EQ** card (pre-emphasis to tape) — a **brightness** control, *not* a de-harsher. |
| `l_shelf_eq` / `r_shelf_eq` | 0 … 10 *(5.2)* | **Record Shelf EQ** card (LF/weight to tape). |
| `l_repro_hf_eq` / `r_repro_hf_eq` | 0 … 10 *(2.6)* | **Reproduce HF EQ** (playback top trim) — the **strongest direct top-end control**. |
| `l_repro_lf_eq` / `r_repro_lf_eq` | 0 … 10 *(9.7)* | **Reproduce LF EQ** (playback low trim / head-bump level) — default high = full lows. |
| `transformer` | `False`/`True` *(True)* | output/isolation transformer — the **even-harmonic gloss** (see harmonic probe). OFF = cleaner/darker path. |
| `crosstalk` | `False`/`True` *(True)* | modeled L↔R leakage (hardware ≈ −45 dB) — narrows/blends the image; near-zero tonal effect. |
| `wow_flutter` | `False`/`True` *(True)* | modeled pitch instability — subtle (servo capstan); OFF for a clean master. |
| `hiss_hum` | `False`/`True` *(False)* | modeled noise floor + mains hum (60 Hz NAB / 50 Hz CCIR). Off by default. |
| `auto_cal` | `False`/`True` *(True)* | one-button align of **Bias + the 4 EQ cards** for the chosen tape/speed/cal/width. **Keep ON** unless mis-aligning for effect. |
| `stereo_link` | `False`/`True` *(True)* | couples L/R controls (normal stereo-bus mode; unlink for dual-mono / asymmetric). |
| `meter` | `Input` · `Output` *(Output)* | VU source (works even in THRU — a calibrated gain-staging bridge). |
| `power` / `master_bypass` | bool | — |

> Notable vs the A800: per-channel Record/Reproduce, the **Transformer** toggle, **head_width**, **crosstalk** and
> **wow_flutter** — the 2-track-mastering feature set. (The hardware/full plugin also has a tape-delay; it is not
> exposed in the Pedalboard surface.)

### Isolation / lever anchor (peak-normed, `[L] measure-spectrum` centroid; dry = 4266)

| setting (vs dry) | centroid | Δcen | tilt | band-low | band-hi | crest |
|---|---|---|---|---|---|---|
| **dry** balanced bus | 4266 | — | −2.69 | 0.579 | 0.0051 | 25.0 |
| **default** REPRO/15/456/+6/½″/NAB (+10) | 3871 | **−395** | −2.73 | 0.632 | 0.0060 | **22.4** |
| Studer A800 15/456/+6 *(from the A800 doc, same file)* | 3926 | −341 | — | — | — | — |
| more drive (+16) | 3881 | −385 | −2.45 | 0.590 | 0.0095 | **20.1** |
| **transformer OFF** | 3515 | **−751** | −2.91 | 0.699 | 0.0048 | — |
| tape 250 (vs 456) | 3974 | −292 | −2.65 | 0.629 | 0.0069 | — |
| emphasis CCIR (vs NAB) | 4334 | +68 | −2.42 | **0.516** | 0.0084 | — |
| `repro_hf_eq` → 0 (kill top) | 2132 | **−2134** | −3.94 | 0.640 | 0.0011 | — |
| `hf_eq` (record HF) → 10 *(power-method)* | (extreme brightener — biggest HF lift) | — | — | — | — | — |
| `repro_lf_eq` → 0 (lean the low) *(power-method)* | (band-low 0.62 → 0.32) | — | — | — | — | — |
| under-bias 5 V | 5243 | **+977** | −2.05 | 0.627 | 0.0176 | — |
| over-bias 16 V | 4410 | +144 | −2.64 | 0.580 | 0.0051 | 24.0 |

**Reading:** the default tape **darkens + gently compresses** (≈ the A800). The **transformer adds the top back**
(OFF → −751; ON → −395, ~+356 Hz recovered) — *that recovery is the ATR's gloss*. The **Reproduce HF card is the
nuclear top-end control** (−2134 at 0); the **Record HF card** is the strongest *brightener* (a brightness control,
not a de-harsher); **`repro_lf_eq` down** leans a boomy bottom; **CCIR strips bass** (band-low 0.58 → 0.52);
**under-bias = bright/spitty** (+977, hi-band ×3); the auto-cal default bias is already near the smooth optimum.

### Width × speed grid (controlled: REPRO/456/+6/NAB/transformer ON/clean, +8 dB, peak-normed)

| width | **15 IPS** centroid (band-low) | **30 IPS** centroid (band-low) |
|---|---|---|
| 1/4″ | 4064 (0.639) | 4327 (0.631) |
| 1/2″ | 3868 (0.640) | 4411 (0.578) |
| 1″ | 3799 (0.635) | 4329 (**0.531**) |

- **30 IPS is brighter than 15 IPS at every width** (~+450 Hz centroid) — the classic "30 IPS = extended/clean top."
- **At 15 IPS, wider tape = darker/fuller** (4064 → 3799; band-low ~flat) — the head bump dominates.
- **At 30 IPS, wider tape = leaner/tighter low end** (band-low 0.63 → **0.53**) at a bright, ~constant centroid —
  the **"1″ 30 IPS = tight, hi-fi, controlled bottom"** mastering character.

### ⚠️ Calibration gotcha (measured)

A *partial* param set that only changes `ips` can leave the repro-EQ **mis-calibrated for the old speed**: a
½″/30 IPS render that didn't re-assert the full set + `auto_cal` came out **3597** (dark), vs **4411** when the
full speed/tape/cal/width set + `auto_cal=True` was applied. **Set the whole calibration block explicitly and
keep `auto_cal:true` near the end of the params** (the harness applies them in order) — the A800's "re-run Auto
Cal after any tape/speed/cal change" rule, confirmed here.

### 1 kHz sine harmonic probe (dB rel. fundamental) — TAPE = odd, TRANSFORMER = even

| condition | even: H2 / H4 / H6 | odd: H3 / H5 / H7 |
|---|---|---|
| default (−6 dBFS in, operating level) | −56 / −88 / −102 | −52 / −47 / −55 *(essentially clean)* |
| **driven (+12 dB in)** | **−55** / −58 / −65 | **−14** / −29 / −74 *(3rd dominant)* |
| **driven, transformer OFF** | **−70** / −68 / −70 | −14 / −29 / −80 *(H2 drops 15 dB; odd unchanged)* |
| hot (+18 dB in) | −55 / −62 / −64 | −10 / −17 / **−23** *(full odd ladder 3 > 5 > 7)* |

**This settles it for this machine:** the **tape engine generates odd harmonics** (3rd dominant, climbing to
5th/7th as driven — the harshness ladder), and the **output transformer adds even harmonics** (toggling it moves
the **2nd ~15 dB**, the 4th/6th too; the odd 3rd is untouched). At operating level everything is ~clean; harshness
is a *driven* phenomenon and the cure is **less Record level**, not EQ. *(Nuance: the tape-engineering literature
says transformer distortion is "mainly 3rd-order, greatest at LF" — we probed only 1 kHz, where this UADx model's
transformer signature is clearly even/2nd; both can hold at different frequencies.)*

### The presets that came out of this (in `presets/vst/`)

- **`ampex-atr-master-glue.json`** — REPRO/**30 IPS**/456/+6/**1″**/transformer ON, clean (W&F/crosstalk/hiss OFF),
  +6 drive. Measured **centroid 4328, band-low 0.531, crest 24.93** (from dry 25.0 = *transparent dynamics*) — tight
  controlled bottom + slightly open top. Transparent 2-bus polish; drive harder for audible compression.
- **`ampex-atr-warm-2bus.json`** — **15 IPS**/456/+6/½″/NAB/transformer ON, +10 drive. **Centroid 3871 (Δ−395),
  crest 22.4** — warmer/fuller with ~2.6 dB tape compression.
- **`ampex-atr-drum-glue.json`** — 15 IPS/456/+6/½″/NAB, +12 drive, width 0.95. **Centroid 3871, crest 21.7**
  (~3.3 dB compression = the glue) — the smooth/mastering-deck counterpart to the A800 `tight-70s-*` punch presets.
- **`vintage-1960s.json`** — Pultec → Fairchild 670 → **Ampex ATR-102** (a fuller example chain).

---

# Part B — how the machine works (web-research synthesis, cited)

## 1. What it is / sonic identity

The **Ampex ATR-102** is a **2-channel analog tape recorder introduced at AES in spring 1976**, the 2-track member
of the ATR-100 series, built for **mastering and final stereo mixdown** — not multitrack tracking (mixonline,
Wikipedia). UA calls it "the most popular professional 2-track tape machine ever made … easier to list classic
albums that *weren't* mixed down on this machine" (uaudio.com). Its engineering signature is a **servo-controlled,
pinch-roller-less, direct-drive capstan** giving near-nonexistent speed drift and **ultra-low wow & flutter** —
the root of its "smooth, stable" reputation; **interchangeable head blocks** swap ¼/½/1″ in minutes (mixonline).
~3,000 built; TECnology Hall of Fame 2005.

Its sonic identity recurs across sources as **"smooth, polished, hi-fi"** — a glossy/open top, a **sweet low-end
head bump**, low-order saturation, and a euphonic **"glue"** that tightens and enlarges the stereo image; SOS notes
that at 15–30 IPS the coloration is **"really very mild"** — mastering-grade, not heavy color (pluginoise, SOS).
**Use it on the 2-bus / stereo mixdown / master** (cohesion, low-end weight, smoother top, image), and secondarily
on **lead vocal, solo guitar, drum bus**. Vs siblings: **ATR-102 = smooth mastering glue; [[studer-a800]] = punchy
multitrack color; Oxide = light, low-CPU quick finisher** (pluginoise). The UAD plugin shipped **Sept 1 2011**
(UAD-2 DSP), authenticated by Ampex, with presets from Chuck Ainlay / Richard Dodd / Buddy Miller / Mike Poole; a
**Native (VST3/AU/AAX) build** was later added — and **only the Native build renders headless** (the DSP build
needs Apollo hardware). *(That's the `uaudio_*.vst3` you must load — never the `UAD ….component` twin.)*

## 2. The control surface (UA naming)

- **Gain structure: −12 dBFS = 0 VU** (manual p24, verbatim) — the digital equivalent of +4 dBu / 0 VU on the
  hardware. Feed peaks near −12 dBFS for the "mastered" clean-glue tone; push well past the red marker and you walk
  up the odd-harmonic stack into grit (SOS). A −18-referenced feed therefore under-drives ~6 dB.
- **Record (Input)** = the **primary color control** — "lower Record = cleaner; higher = more harmonic saturation
  and coloration" (manual p26). **Reproduce (Output, −inf … +9.48 dB)** = playback make-up; pull it down for unity.
  Laid out **backwards** (Reproduce LEFT of Record), faithful to the hardware; knobs read 0–10 arbitrary units.
- **Auto Gain** links Record↔Reproduce to hold **unity output** while you change drive — a built-in loudness-matched
  A/B (uaudio).
- **Path Select**: **Repro** (default, off the repro head, fullest/most-accurate) · **Sync** (off the record head,
  less accurate response) · **Input** (machine electronics, **no tape** — our measure: crest stayed 26.2, i.e. no
  tape compression) · **Thru** (bypass, meters still live) (SOS).
- **Cal** = a **2nd drive/headroom lever**: lowering Cal reduces level into tape **without** changing Record's
  character (opens headroom / "broader sweet spot"); under-calibrating is a real technique (manual p29).
- **Clip LED = electronics clip only** — it **never** lights on tape overload (tape saturation is soft) (manual p25).
- **The 4 trim cards + Bias** (**Record Shelf EQ, Record HF EQ, Repro HF, Repro LF, Bias**) are exactly what **Auto
  Cal** aligns; the green LED lights only when all five sit at their calibrated null. De-cal them for tonal effect —
  the digital equivalent of a misaligned deck (UA).
- **Transformer / Crosstalk (−50…−10 dB, default −45) / Wow & Flutter / Hiss & Hum / Stereo Link / Meter In-Out**
  — modeled hardware behaviors, each toggleable (manualsdir, UA). Wow & Flutter scale with speed and are **not**
  touched by Auto Cal.

## 3. Tape WIDTH (1/4 vs 1/2 vs 1″) — the signature lever

The plugin models **three head-stack widths** the A800 plugin has no equivalent for; the real machine swapped
¼″↔½″ head blocks in minutes, and **1″ 2-track was an aftermarket "hot-rod"** especially prized by mastering
engineers at 15 IPS (help.uaudio, gearspace, Tape Op). The governing physics (Richard Hess): **each doubling of
track width adds ~6 dB signal but only ~3 dB noise → +3 dB net dynamic range / headroom per doubling** (noise is
uncorrelated, signal coherent). So:

| width | character |
|---|---|
| **1/4″** | grittier / more-colored / noisier / **least headroom** (saturates soonest); the standard mastering config |
| **1/2″** | the in-between, the plugin default |
| **1″** | **cleanest / quietest / most headroom**, best HF — the famous hi-fi mastering sound (esp. 1″ @ 15 IPS) |

**Important nuance the sources stress:** the ATR's "**bigger/fuller low end**" comes mainly from the **speed-dependent
head bump (15 IPS)**, *not* from width — width contributes "size" via **headroom / SNR / HF**, not a bass boost
(SOS). Our measured grid agrees: width's *tonal* move is modest and **interacts with speed** (15 IPS: wider →
darker; 30 IPS: wider → tighter/leaner low). **Width availability is speed-gated** — at 3.75/7.5 IPS only ¼″ is
selectable; ½″ and 1″ need 15/30 IPS (SOS, UA).

## 4. The output transformer & harmonic character (even vs odd)

The single most-corrected myth across every source: **magnetic tape's dominant distortion is ODD-order (3rd
harmonic), not "warm even-order."** Tape's B-H/hysteresis transfer curve is **symmetric** (a tanh/cubic S-curve),
and a symmetric nonlinearity produces **odd** harmonics — 3rd dominant, then 5th/7th (Sage Audio, Sweetwater, SOS
"Analogue Warmth"). The industry metric proves it: **MOL is *defined* as the level giving 3% *3rd*-harmonic
distortion of a 1 kHz tone**, and tape alignment uses 3rd-harmonic as the reference (SOS). Even-order content on
real tape is the **exception** — an artifact of DC offset / record-head asymmetry (the canonical IEEE paper is
literally "Even-order harmonic distortion in AC-bias recording") (CCRMA). **Even-order "warmth" is the tube/valve
signature**, not tape's.

The **Transformer toggle** models the ATR's isolation transformers; UA says leave it **ON** for most music ("Rock
and roll likes transformers!"), OFF for a cleaner classical/jazz path. The general literature says transformer
distortion is **also mainly 3rd-order and greatest at low frequencies** (SOS). **Our 1 kHz probe refines that for
this UADx model:** at 1 kHz the toggle's audible add is the **2nd harmonic (+15 dB ON-vs-OFF)** plus broadband
brightness — i.e. *on this model at 1 kHz the transformer reads even-order*, layered on top of the tape's odd 3rd.
Net: the ATR-102 is **fundamentally an odd-harmonic + compression + head-bump character device**, with the
transformer adding the gloss (even at 1 kHz here); it is **not** an "even-harmonic warmth box," and the smoothness
comes from **soft-knee tape compression + HF self-erasure/softening + the head bump**, not from harmonic order.

## 5. The sonic levers

**Lever 1 — IPS (speed).** Sets head-bump center (replay-head geometry, ~+2 dB, **doubles per speed-double**: ~50–60
Hz @15 → ~100–120 Hz @30; Ampex aligns 50 Hz @15, 100 Hz @30), HF extension, headroom, noise.

| Speed | Head bump | HF / noise | Character |
|---|---|---|---|
| 3.75 / 7.5 | biggest, lowest | most roll-off, most hiss | distinctly **lo-fi / colored** (¼″ only) |
| **15** | **~50–60 Hz** (≈+2 dB) | smooth top, ~3 dB more hiss | **warm / fuller lows** — rock/acoustic favorite |
| **30** | **~100–120 Hz** | extended top, ~3 dB quieter, flattest | **clean / pristine / tight** — the mastering speed (AES-locked EQ) |

**Lever 2 — Tape formula.** The plugin models **seven** types; the four marketed are exposed: **250 (+3, saturates
earliest = warmest/least headroom) · 456 (+6, the workhorse) · 900 (+9) · GP9 (+9, cleanest/highest headroom)**
(manual). "Lower Cal for each formula → higher level needed to saturate" (manual p28). Drive dominates formula
choice.

**Lever 3 — Cal + Record (operating level).** Cal sets reference flux over 185 nWb/m: **+3 = 251, +6 = 355, +7.5,
+9 = 502 nWb/m**; **456 @ +6 = 355 nWb/m = 10 dB below the 3% THD MOL** (manual p29). **Record** drives above/below
it (the color knob); **Auto Gain** keeps output unity. Many engineers run **Cal +7.5** as the punch-vs-saturation
sweet spot; **+9 over-saturates and loses punch** (uadforum).

**Lever 4 — Emphasis EQ (NAB vs CCIR; AES @30).** The replay pre/de-emphasis curve, a real tonal lever:

| | NAB (US) | CCIR/IEC (Europe) | AES @30 |
|---|---|---|---|
| LF | **50 Hz bass shelf** (warmer/fuller lows) | no shelf → more deep bass below 50 Hz, leaner in the shelf region | — |
| HF time-constant @15 | 50 µs (corner ~3150 Hz) | 35 µs (corner ~4500 Hz, **brighter top**) | ~17.5 µs |
| Hum | 60 Hz | 50 Hz | — |

WARM/fuller → **NAB**; leaner/brighter-top → **CCIR**. **No choice at 30 IPS (AES only).** Our measure: CCIR
band-low 0.58 → 0.52 (leaner) + slightly brighter — matches.

**Lever 5 — Bias.** AC bias (~40–150 kHz, models linearizing the recording) is a genuine tone control: **under-bias
= brighter, spittier, MORE 3rd-harmonic distortion**; **over-bias = duller/smoother top, LESS distortion** (set
against HF output; Wikipedia, tapeheads). Pro convention quotes ~1–3 dB over-bias at 10 kHz. Our measure: under-bias
(5 V) +977 centroid with hi-band ×3 = the spitty brightener; the auto-cal default (11.5 V) is near the smooth optimum.

## 6. Recipes

- **(a) Transparent mastering / 2-bus polish:** REPRO · **30 IPS** · 456 or GP9 · Cal +6 · **1″** · transformer ON ·
  W&F/crosstalk/hiss OFF · Auto Cal ON. Record only until crest drops **~1–2 dB**; Auto Gain or trim Reproduce to
  unity. Tight controlled bottom + open top, near-transparent dynamics (our `ampex-atr-master-glue`). It's a **color
  insert before the limiter**, not the limiter.
- **(b) Warm fuller mixdown:** REPRO · **15 IPS** · 456 · Cal +6 · **½″** · **NAB** · transformer ON, W&F/crosstalk
  ON for vibe. More Record drive for audible warmth + light compression (our `ampex-atr-warm-2bus`). 1″ for a more
  hi-fi version.
- **(c) Drum-bus glue/color (smooth):** 15 IPS · 456 · ½″ · NAB, drive to ~3–4 dB crest drop (our
  `ampex-atr-drum-glue`). Smoother/glossier than the A800; for punchy/dry American-console drums use
  [[api-vision-channel-strip]] / [[kit-bb-a5]] instead.
- **(d) Tame harshness with tape:** **Reproduce HF down** (strongest) > **less Record** > **over-bias** > **wider
  tape / 30 IPS**. Place the tape **before** the bus comp so it absorbs spikes. **Don't** reach for the Record HF
  card (it re-adds brightness). Tape can't fix a true sibilance hotspot — use `[L] de-ess` / `suppress-resonances`.
- **Noise/W&F/crosstalk:** OFF for clean mastering; ON for vintage vibe. Higher Cal / HF boosts raise the audible
  hiss floor. Mind the **upsampling latency** with linear-phase tools.

## 7. Why driven tape gets harsh + ATR-102 vs A800

As Record rises the **odd-harmonic stack climbs from 3rd toward 5th/7th**; higher odd orders map to increasingly
**dissonant intervals** (3rd = octave+fifth, musical; 5th/7th = gritty/buzzy), and worse, **intermodulation
distortion** generates **inharmonic** sum/difference tones that **no EQ notch fixes** — "harshness" on dense
material is largely IMD (Sage Audio, KERN, sound-au). **Cures:** less Record drive (#1), higher speed (30 IPS),
higher-headroom formula (GP9/900) or wider tape, lower Cal, over-bias, parallel/dry-wet blend.

**ATR-102 vs Studer A800:** the ATR is the **smoother/glossier 2-track *mastering* deck** (2-bus glue, low-end
weight, smoother top, image firming — "mastering-grade final-mix glue"); the **A800 is the punchier, cleaner
*multitrack*** (drum/bass/guitar punch + per-element color, Gang Control, lighter CPU) (pluginoise). They share the
250/456/900/GP9 formulas; the ATR adds **3.75 IPS**, the **¼/½/1″ widths**, the **Transformer/crosstalk/wow-flutter**
modeling, **Auto-Cal/Auto-Gain**, and per-channel control. On our drum bus the two darkened almost identically
(Δ−395 vs −341); reach for the **ATR on the master/2-bus**, the **A800 on tracking/drum punch**.

## 8. Pitfalls & gotchas

- **−12 dBFS = 0 VU** — gain-stage so peaks land near the red marker. Record **saturates *and* raises level** — use
  Auto Gain / trim Reproduce and **A/B loudness-matched**. **Cal ≠ volume** (raising Cal makes the same Record
  distort more).
- **30 IPS removes the NAB/CCIR choice** (AES-locked) and is brighter/tighter, not warmer; **15 IPS** is the warm,
  big-low speed. **Head bump is level-independent** (it's the speed, not the drive) — lean it with `repro_lf_eq` /
  30 IPS, not by backing off Record.
- **Width is gated by speed** (¼″ only at 3.75/7.5) and **interacts with speed** — don't treat it as cosmetic.
- **Re-assert Auto Cal with the full tape/speed/cal/width set** or repro-EQ stays mis-aligned (measured ~−800 Hz at
  30 IPS). Wow & Flutter are **not** auto-cal'd.
- **The probe lies** — `probe_plugin.py` false-flags PASSTHROUGH (it toggles `auto_gain`); the plugin renders. Verify
  with a tonal param.
- **Two builds / two editions** — load **`uaudio_ampex_atr-102_tape.vst3`** (UADx Native, renders headless); the
  `UAD Ampex ATR-102.component`/legacy DSP twin **passes audio through** offline. The hardware-accelerated edition
  is CPU-heavy; the native build adds upsampling latency.
- **Tape can't do surgery, and isn't a limiter** — glue + tilt + harmonic color only. Hand loudness/ceiling to
  `render-mastered` ([[master-track]]); hand sibilance/resonance to `de-ess` / `suppress-resonances` / [[mix-balance]].
- **Myths debunked:** tape ≠ even-order warmth (it's odd/3rd); "tape is gentle vs digital clipping" only holds at
  modest drive (hysteresis also smears transients); over-bias does **not** brighten (it darkens/smooths).

---

## Sources

UA Ampex ATR-102 manuals (help.uaudio.com — Master Tape Recorder, Mastering Tape Recorder, LUNA extension) ·
uaudio.com product page · Sound on Sound ATR-102 review + "Analogue Warmth" / "Analogue Tape Machines" ·
Tape Op review · ManualsLib / manualsdir ATR-102 manual pages · pluginoise (UAD Ampex vs Studer) · gearspace
(15-vs-30, width, 1″ hot-rod threads) · uadforum (Cal +7.5) · Sage Audio / Sweetwater / CCRMA (Kadis) / Wikipedia
(tape & transformer physics, odd-harmonic, head bump, bias) · richardhess.com (track-width SNR) · MRL / pSpatial /
AnalogRules (NAB vs IEC, alignment tones) · mixonline + Wikipedia (ATR-100 hardware history). Plus **our own
isolation / width×speed / 1 kHz-harmonic measurements** (Part A) on `uaudio_ampex_atr-102_tape.vst3` via Pedalboard.
