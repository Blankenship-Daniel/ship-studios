# Oxide Tape Recorder (UAD/UADx) — field guide: the simple, fast tape finisher (warmth + glue, 8 knobs)

How to drive the UAD/UADx **Oxide Tape Recorder** plugin (`uaudio_oxide_tape.vst3`) — UA's **affordable,
low-CPU, stripped-down tape machine** (engineered by the same team behind the [[ampex-atr-102]] and
[[studer-a800]], with AES magnetic-recording expert Jay McKnight). It models a generic professional tape deck
with only the **essential** controls: one **Input** drive knob, one **Output** make-up, **7.5 / 15 IPS**,
**NAB / CCIR** EQ, a **Noise Reduction** switch, and an **Input / Repro** path. Two halves: **Part A** is
*measured on this rig*; **Part B** is a *web-research synthesis* (cited). The skill [[oxide-tape]] is the
measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — it can't judge the head-bump lows, the tape compression, the
> HF air, or true-peak from transients. **Meters own this.** Verify with `[L] measure-spectrum`
> (centroid / tilt / bands), `[L] measure-loudness` / `measure-microdynamics` (crest = the glue),
> `[L] measure-distortion` (THD = the drive), `[L] check-clipping`. **Input raises level *and* saturates** —
> A/B loudness-matched (`[L] render-ab`).

---

## TL;DR (the headline, measured)

1. **The whole plugin is one color knob (Input) + two voicing switches (IPS, EQ).** There is no tape type, no
   bias, no width, no transformer toggle, no wow/flutter, no per-channel control — it's the Ampex/Studer engine
   with everything but the essentials removed. `input_level` and `output_level` are **numeric** (drivable from
   `apply-vst-chain`'s float dict); `path_select` / `ips` / `emphasis_eq` / `noise_reduct` are **string/bool
   enums** → use the [[vst-preset]] harness for those.
2. **It's a near-NEUTRAL color box at low drive that BRIGHTENS as you push it** — the opposite of the
   default-darkening Ampex/A800. At `+0` Input the default Repro/15/NAB barely moves the tone (centroid
   3007 → 2990) and adds ~0.3 dB compression. As Input climbs `+0 → +24`, **crest falls 14.3 → 11.1** (tape
   compression, the glue) while **centroid RISES 2990 → 3800** (the odd-harmonic stack lighting up). The color
   *is* the drive.
3. **Tape = ODD/3rd harmonics (real tape).** 1 kHz probe (Repro/15): `+12` = **7.7% THD, H3-dominant**; `+18`
   = 24%; `+24` = 38% with the full odd ladder (3rd → 5th). Harshness is a *driven* phenomenon — the cure is
   **less Input**, not EQ. The **Input (electronics-only) path is EVEN/2nd, near-clean (0.19% THD) and does NOT
   compress** — the "machine on, tape not running" sheen.
4. **NAB vs CCIR is the strongest tone lever, and it's a BRIGHTNESS switch:** at `+6`, CCIR pushed centroid
   **3027 → 3475 (+448)** and HF energy up — NAB = warmer/fuller, CCIR = brighter/leaner top.
5. **15 IPS = the warm, full-low setting; 7.5 IPS = the "more colored / frequency-shift" setting** (leaner lows,
   more upper energy). Note this **inverts** the textbook "slower = bigger bass head-bump" — on this model 15 IPS
   carries the low-end weight.
6. **Default starting point:** `path_select=Repro`, `ips=15 IPS`, `emphasis_eq=NAB`, `noise_reduct=true`, then
   drive `input_level` and pull `output_level` down to gain-match.

---

# Part A — measured on this rig

Probe: `uaudio_oxide_tape.vst3` via Pedalboard (stemmy-loops `vst` extra), processing
`artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav` (a 104 BPM drum loop — the file open in
the screenshot). Drum renders are **peak-normalized** before measuring so only **shape** is compared; crest is
gain-invariant. `scripts/mix/oxide_sweep.py` reproduces every number.

### Renders headless

The plugin **renders headless** (UADx native, no iLok dongle — authorized on this rig). **`bypass` == dry
bit-for-bit** (centroid 3007 both) so the A/B is honest. As always with UADx, load **`uaudio_oxide_tape.vst3`**
— the **`UAD Oxide Tape.component`** twin passes audio through unprocessed offline.

### The real parameter surface (Pedalboard-exposed — 8 params)

| Param (Pedalboard key) | Values *(default)* | Role (UA name) |
|---|---|---|
| `input_level` | −12.0 … **+24.0** dB *(0.0)* | **INPUT = the DRIVE / primary color** — record level to tape. More = saturation + tape compression (and louder). The one knob that matters. **Numeric.** |
| `output_level` | −24.0 … +12.0 dB *(0.0)* | **OUTPUT = playback make-up** — pull down as you push Input for unity. **Numeric.** |
| `path_select` | `Input` · `Repro` *(Repro)* | **Repro** = full record→tape→reproduce (tape sonics). **Input** = machine electronics only, **no tape** (no compression; 2nd-harmonic sheen). String enum. |
| `ips` | `7.5 IPS` · `15 IPS` *(15)* | tape speed. **15 = warm/full lows**; **7.5 = more colored / frequency-shift, leaner low**. String enum. (No 30 IPS — unlike the ATR/A800.) |
| `emphasis_eq` | `NAB` · `CCIR` *(NAB)* | playback emphasis. **NAB = warmer top, 60 Hz hum**; **CCIR/IEC = brighter top, 50 Hz hum**. String enum. The strongest tone lever. |
| `noise_reduct` | `False` / `True` *(**True**)* | removes the modeled tape hiss + electronics hum from the output. **Tonally transparent on real program** — a noise-floor switch, not a tone knob. Bool enum. |
| `power` / `master_bypass` | bool | — |

> No `tape_type`, `cal_level`, `head_width`, `bias`, `transformer`, `crosstalk`, `wow_flutter`, `auto_cal`,
> `stereo_link`, or per-channel L/R — that's the whole point of Oxide. If you need those levers, reach for
> [[ampex-atr-102]] (mastering) or [[studer-a800]] (multitrack).

### Isolation / lever anchor (peak-normed; dry centroid = 3007, dry crest = 14.63)

| setting (vs dry) | centroid | band-low (20–200) | band-hi (4–16k) | crest |
|---|---|---|---|---|
| **dry** / **bypass** | 3007 | 0.918 | 0.0098 | 14.63 |
| **default** Repro/15/NAB, Input +0 | 2990 | 0.945 | 0.0071 | 14.33 |
| **Input mode** (electronics only) +0 | 3003 | 0.917 | 0.0098 | **14.71** *(no compression)* |
| Repro/15/NAB **+6** | 3027 | 0.944 | 0.0073 | 13.68 |
| Repro/**7.5**/NAB +6 | 3032 | **0.912** | **0.0127** | 14.27 |
| Repro/15/**CCIR** +6 | **3475** | 0.946 | 0.0101 | 13.30 |
| Repro/15/NAB +6 **NR-on** | 3027 | 0.944 | 0.0073 | 13.68 *(== NR-off)* |

**Input-drive sweep (Repro/15/NAB):**

| Input | centroid | band-low | band-hi | crest |
|---|---|---|---|---|
| +0 | 2990 | 0.945 | 0.0071 | 14.33 |
| +6 | 3027 | 0.944 | 0.0073 | 13.68 |
| +12 | 3145 | 0.942 | 0.0081 | 12.45 |
| +18 | 3394 | 0.928 | 0.0099 | 11.82 |
| +24 | 3800 | 0.897 | 0.0129 | 11.11 |

**Reading:** default tape adds **LF weight** (band-low 0.918 → 0.945) and gentle compression while leaving the
centroid near dry. **Input is everything** — it trades crest for harmonics, and as it does the tone gets
**brighter** (more odd HF), not darker. **CCIR is the big brightener** (+448 centroid). **7.5 IPS** leans the
low and lifts the top (the "color/frequency-shift" speed). **NR is tonally inert** on a hot bus — it only
matters when the modeled hiss/hum floor is audible.

### 1 kHz sine harmonic probe (dB rel. fundamental) — TAPE = odd, ELECTRONICS = even

| condition | THD% | balance | H2 | H3 | H4 | H5 |
|---|---|---|---|---|---|---|
| Repro +0 | 0.16% | ODD | −66 | −65 | −103 | −58 *(≈ clean)* |
| Repro **+6** | 1.67% | ODD | −62 | **−36** | −85 | −55 |
| Repro **+12** | 7.68% | ODD | −61 | **−22** | −69 | −50 |
| Repro **+18** | 23.66% | ODD | −67 | **−13** | −67 | −25 |
| Repro **+24** | 38.48% | ODD | −69 | **−9.5** | −72 | **−15** *(odd ladder 3>5)* |
| **Input mode +12** (electronics) | 0.19% | **EVEN** | **−54** | −159 | −155 | −157 *(2nd only, no tape)* |

**This settles it:** the **tape (Repro) engine generates odd harmonics — 3rd dominant, climbing to 5th as
driven** (the harshness ladder, classic tape); the **electronics-only (Input) path adds a faint 2nd harmonic
and nothing else** (near-clean, no odd, no compression). Harshness is a *driven* phenomenon; the cure is **less
Input**, not EQ.

### The presets that came out of this (in `presets/vst/`)

- **`oxide-warm-drum-glue.json`** — Repro/15/NAB/NR-on, Input **+7**. ~1 dB glue (crest 14.6 → 13.7) + LF
  weight. The fast warm finisher; lighter/lower-CPU cousin of the ATR/A800 drum-glue presets.
- **`oxide-lofi-color.json`** — Repro/**7.5**/NAB/NR-off, Input **+14**. ~7–10% odd-3rd THD + tape compression
  (crest → ~12) — the grit/character setting.
- **`oxide-master-glue.json`** — Repro/15/NAB/NR-on, gentle Input **+4**. Near-transparent dynamics — a color
  insert **before** the limiter on a 2-bus.

---

# Part B — how the machine works (web-research synthesis, cited)

## 1. What it is / sonic identity

The **Oxide Tape Recorder** is UA's **stripped-down, affordable, low-CPU** tape-emulation plug-in — "UA's
revolutionary magnetic tape technology in a simple package with all of the essential features," engineered by
the **same team behind the UAD Ampex ATR-102 and Studer A800**, designed in conjunction with **AES magnetic
recording expert Jay McKnight** (uaudio.com). It is not a model of a single named deck; it captures the generic
**"sound of tape"** — clarity, punch, warmth, and gentle compression-style **glue** — with a tiny control set
aimed at *speed of use*. Reviewers consistently praise it as **fast, predictable, and "good enough that I reach
for it over the Ampex/Studer"** for everyday warming because it has no setup overhead (audiopluginguy). Use it on
the **drum bus, master/2-bus, and individual tracks** for instant cohesion; reach for the ATR-102 ([[ampex-atr-102]],
mastering levers) or A800 ([[studer-a800]], multitrack punch + per-element control) when you need the full feature
set. It ships as **UAD-2 (DSP) and UADx (Native VST3/AU/AAX)** — only the Native `uaudio_*.vst3` renders headless.

## 2. The control surface (UA naming)

- **Input** — *the* parameter. "The Input control adjusts the signal level recorded to tape and is therefore the
  primary color parameter. As with hardware tape recorders, lower VU levels result in a cleaner, warmer sound with
  more headroom, while increasing VU levels results in more tape saturation, compression, and bite" (UA manual).
  The reviewer's rule of thumb: **peak the VU around 0** and push for more color (audiopluginguy).
- **Output** — playback make-up gain; trim it down as you drive Input so you A/B at matched loudness (there is no
  Auto-Gain on Oxide — do it by hand or let the harness peak-trim).
- **IPS (7.5 / 15)** — tape speed: "each having a distinct frequency shift, head bump (low-frequency rise), and
  distortion characteristics" (UA manual). **15 IPS = warmer, considerable low-end boost, higher fidelity, lower
  noise; 7.5 IPS = much more colored, much greater frequency shift** (audiopluginguy). *(No 30 IPS — that's the
  ATR/A800.)*
- **EQ (NAB / CCIR)** — the playback **emphasis** (pre/de-emphasis) curve: **NAB** is the American standard (hum
  at **60 Hz**, slightly duller top); **CCIR/IEC** is the European standard "made famous on British records,"
  considered technically superior (hum at **50 Hz**, perceived brighter) (UA manual). It is a genuine tonal lever.
- **NR (Noise Reduction)** — "removes the not-always-desirable tape hiss and electronics hum inherent in analog
  tape systems from the processed signal … a way to cut some of that noise if it gets distracting" (UA manual).
  It is a **noise-floor** switch, not a tone control; default **ON**.
- **Path (Input / Repro)** — **Input** "emulates the sound of the circuit through the machine electronics only,
  without tape sonics (the machine in live-monitoring with the transport not running)"; **Repro** "models the
  complete sound of the signal being recorded to tape through the record head and played back through the
  reproduction head, plus all corresponding machine electronics" (UA manual). Repro = the tape sound; Input = a
  clean electronics-only sheen.

## 3. Why the levers do what they do

- **Saturation / glue (Input):** tape's B-H hysteresis transfer curve is a soft symmetric S-curve → it generates
  **odd-order (3rd-dominant) harmonics** and **soft-knee compression** as you drive it. Both scale with Input.
  Magnetic-recording lore (and the ATR/A800 docs) confirm tape distortion is **odd/3rd**, not "even-order warmth"
  (that's tubes/transformers). Our probe matches exactly.
- **IPS:** slower speed = more colored + a frequency shift; faster = cleaner/extended + lower noise. (On this UA
  model 15 IPS also carries the bigger low-end weight — the head-bump behavior is voiced so 15 reads "warm/full,"
  7.5 reads "colored/leaner-low.")
- **NAB vs CCIR:** different replay time-constants and a different LF shelf → CCIR sits brighter/leaner in the
  top, NAB warmer/fuller. The hum frequency (60 vs 50 Hz) follows the regional standard.

## 4. Recipes

- **(a) Quick warm drum/instrument bus:** Repro · 15 IPS · NAB · NR on · Input to taste (~+6…+10 = ~1–2 dB
  glue). Trim Output to match. (`oxide-warm-drum-glue`.)
- **(b) Transparent 2-bus / master polish:** Repro · 15 IPS · NAB · NR on · Input gentle (~+3…+5) until crest
  drops ~0.5–1 dB, then stop. A color insert **before** the limiter, never the limiter. (`oxide-master-glue`.)
- **(c) Lo-fi / driven color:** Repro · **7.5 IPS** · NAB (or CCIR for brighter) · NR off (vibe) · Input hot
  (~+12…+18) for audible odd-3rd grit + compression. (`oxide-lofi-color`.)
- **(d) Clean electronics sheen (no tape):** Path = **Input** · Input drive modest — a faint 2nd-harmonic lift
  with **no** tape compression.
- **(e) Tame harshness with tape:** it can't — driving Oxide *adds* odd HF. For a darker tape use less Input or
  15/NAB; for real de-harshing use `[L] de-ess` / `suppress-resonances`.

## 5. Pitfalls & gotchas

- **Input both saturates AND raises level** — there's no Auto-Gain, so trim Output (or let the harness peak-trim)
  and **A/B loudness-matched** (`[L] render-ab`).
- **Driven = brighter + grittier, not darker** — the odd-harmonic stack climbs (3rd → 5th). Past ~+16 on a full
  mix it spits; back off. This is the opposite of the default-darkening ATR/A800.
- **NR is not a tone control** — it only removes the modeled hiss/hum floor (inaudible on a hot bus). Leave it on
  unless you *want* the noise for vibe.
- **No 30 IPS, no tape type / bias / width / transformer / wow-flutter** — if you need those, use the
  [[ampex-atr-102]] or [[studer-a800]].
- **String/bool enums need the harness** — `path_select` / `ips` / `emphasis_eq` / `noise_reduct` can't be set by
  `apply-vst-chain`'s float-only dict (it silently keeps the defaults); only `input_level` / `output_level` are
  drivable directly. Use [[vst-preset]] / `apply_vst_preset.py` for the full recipe.
- **Two builds** — load **`uaudio_oxide_tape.vst3`** (UADx Native, renders headless); the **`UAD Oxide
  Tape.component`** twin passes audio through unprocessed offline.
- **It's a color insert, not a limiter** — hand loudness/ceiling to `render-mastered` ([[master-track]]).

---

## Sources

UA **Oxide Tape Recorder manual** (help.uaudio.com) · uaudio.com Oxide product page · **Audio Plugin Guy**
review (IPS/EQ/Input character, "prefer it to the Ampex/Studer") · Bedroom Producer Gear / ADSR / Sweetwater /
zZounds product pages · UA Ampex ATR-102 manual + tape/transformer physics from the [[ampex-atr-102]] /
[[studer-a800]] docs (odd-harmonic, head bump, NAB/CCIR). Plus **our own isolation / drive-sweep / 1 kHz
harmonic measurements** (Part A) on `uaudio_oxide_tape.vst3` via Pedalboard (`scripts/mix/oxide_sweep.py`).
