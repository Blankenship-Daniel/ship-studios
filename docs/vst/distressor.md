# UADx Empirical Labs Distressor — field guide: the do-anything knee compressor + distortion box, headless

How to drive the **UADx Empirical Labs EL8 Distressor** (`/Library/Audio/Plug-Ins/VST3/uaudio_distressor.vst3`) —
Universal Audio's officially-endorsed model of Dave Derr's **EL8 Distressor**, a 1990s "digitally-controlled
analog **knee**" compressor whose 8 selectable ratio *curves* range from silky leveling to a saturated
brick-wall, with a built-in **harmonic distortion** generator (Dist 2 / Dist 3). It's the **aggressive,
forward, can-do-anything** compressor in the dynamics family — a digitally-controlled-analog **knee** comp with
its own **harmonic-distortion** (Dist 2/3) colour, distinct from the tube COLOR of [[fairchild-660]], the
solid-state opto leveling of [[la-3a]], and the VCA glue of
[[ssl-bus-compressor-2]] — the measured deep-dive behind the [[distressor]] skill and a plugin-specific
specialization of [[vst-compress]] / [[vst-saturate]].

**Part A** is *measured on this rig* (real Pedalboard param surface + our render results); **Part B** is a
*web-research synthesis, cited* (Empirical Labs' manual + UA's docs + the hardware literature).

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness / peak / stereo and the crest / LRA /
> THD that prove what the Distressor did. Verify every move with `[L] measure-loudness` /
> `measure-microdynamics` / `measure-spectrum` / `measure-distortion`. The Distressor adds **both** gain
> reduction *and* harmonics, and the preset harness peak-normalizes to −1 dBFS, so "bigger/louder" is mostly
> the +LU density — judge by crest / LRA / feel, A/B at matched loudness ([[level-match]] / `render-ab`).

---

## TL;DR (the headline, measured)

1. **It's a compressor AND a distortion box.** The audio path adds harmonics on top of compression; the
   **INPUT knob drives both GR and THD together**, so it colors even at a few dB of reduction.
2. **RATIO is 8 *curves*, not 8 slopes — and it sets the threshold too (there is no threshold knob).** You
   drive *into* the fixed curve with INPUT. Measured crest on the warm drum bus (input 8, attack/release 5):
   dry **17.9** → 2:1 14.5, 4:1 16.3, 6:1 16.0, 10:1 14.7, **20:1 13.6 (hardest clamp)**, NUKE 14.3 (saturated
   brick-wall). **6:1 is the workhorse start.**
3. **ATTACK is the master punch control, and lower = faster.** At 10:1, input 8: **attack 0 → crest 10.0**
   (clamps the transient), **attack 5 → 14.7**, **attack 10 → crest 19.1** (transients punch *through*, above
   dry). Slow the attack (toward 10) for punch; speed it up (toward 0) to clamp. *Matches the 50 µs–30 ms spec.*
4. **RELEASE: lower = faster = denser/brighter/pumpier.** At 10:1: release 0 → crest 13.2, centroid 3396 Hz
   (fast recovery, aggressive); release 10 → crest 17.6, centroid 2922 (holds GR down, smoother, quieter).
5. **DETECTOR HP keeps the kick out of the sidechain → kick punches through + bus gets louder.** At 10:1/in8,
   HP raised RMS −20.2 → −16.3 dB and pushed the low band forward (it stops compressing on the lows). **Band
   Emphasis** (`Emp`) makes the detector overreact at ~6 kHz (built-in de-ess/de-harsh).
6. **Dist 2 = 2nd-harmonic warmth, Dist 3 = 2nd+3rd grit.** At a musical 6:1/in8 on a 1 kHz tone, Dist 2 lifts
   **H2 by +9 dB** (H3 untouched, THD 0.32→0.84 %); Dist 3 lifts **H2 +9 dB *and* H3 +4.5 dB** (THD 0.89 %).
   Slam INPUT and even **Norm clips** (odd/3rd-harmonic, THD → 24 %+) — input *is* the master distortion
   control. Clean at low drive (THD 0.2 %).
7. **MIX is built-in parallel** (Dry↔Comp). NUKE/in9, mix 100 → crest 15.2; mix 50 → 16.1; **mix 30 → 17.0**
   (dry transients restored) — crush + blend for a NY smash.
8. **Tooling gotcha:** `ratio` / `detector` / `audio` are **string enums** — `apply-vst-chain`'s number-only
   `parameters` dict **can't set them** (you can't pass `"10:1"`/`"HP"`/`"Dist 2"`). The four dials
   (input/attack/release/output/mix) + headroom *are* numeric and reachable, but ratio defines the whole
   sound → **use the [[vst-preset]] harness**. **British Mode is NOT exposed headless** (12 params, no Brit toggle).
9. **Renders headless via the `uaudio_distressor.vst3` UADx native build** (`changed:true`, probe Δ 1.5). The
   `/Components/UAD Empirical Labs Distressor.component` twin **passes audio through** offline — never load it.

---

## Part A — measured on this rig (Pedalboard, `uaudio_distressor.vst3`)

**Loads + processes headless.** `load_plugin(".../uaudio_distressor.vst3")` → `name="UADx Empirical Labs
Distressor"`, **renders** (`probe_plugin.py`: `RENDERS ✓`, pushed `output=0.0`, Δparam 1.51). UADx native is
the iLok-**account** (no-dongle) build — re-verify `changed:true` on a new machine. **Load the
`uaudio_distressor.vst3` build, not the `/Components/UAD Empirical Labs Distressor.component` twin**
(passthrough offline → [[vst-verify]] / [[vst]]).

**Param surface (Pedalboard snake_case — what you set in code/the harness). 12 parameters: 4 string enums + 6 numeric enums + 2 bools** (only the string enums — `ratio`/`detector`/`audio` (+ `bypass`) — are the `apply-vst-chain` settability problem; the numeric enums are float-settable):

| Param | Type | Range / values (measured) | GUI control |
|---|---|---|---|
| `bypass` | enum str | `'Off'`, `'Byp'` (default `'Off'`) | BYPASS |
| `ratio` | enum str | `'1:1' '2:1' '3:1' '4:1' '6:1' '10:1' '20:1' 'NUKE'` (**default `6:1`**) | RATIO |
| `detector` | enum str | `'Norm' 'HP' 'Emp' 'HP+Emp' 'Link' 'HP+Link' 'Emp+Link' 'HP+Emp+Link'` (default `Norm`) | DETECTOR |
| `audio` | enum str | `'Norm' 'HP' 'Dist 2' 'HP+Dist 2' 'Dist 3' 'HP+Dist 3'` (default `Norm`) | AUDIO |
| `input` | enum num | `0.0 … 10.5` (0.1 step), **default 5.0** | INPUT |
| `attack` | enum num | `0.0 … 10.5` (0.1 step), **default 5.0** | ATTACK (`Opto(n)` label at 10:1) |
| `release` | enum num | `0.0 … 10.5` (0.1 step), **default 5.0** | RELEASE (`Opto(n)` label at 10:1) |
| `output` | enum num | `0.0 … 10.5` (0.1 step), **default 6.5** (≈ "−10 gear") | OUTPUT |
| `mix` | enum num | `0 … 100` % (1 step), **default 100** (100 = fully Comp) | MIX (Dry↔Comp) |
| `headroom` | enum num | `{4, 8, 12, 16, 20, 24, 28}` dB, **default 16** | HR (plugin-only) |
| `power` | bool | `False / True`, default **True** | POWER |
| `master_bypass` | bool | `False / True`, default **False** | (host bypass) |

> **The dials are 0–10½ knob positions, not dB/ms.** They map to the hardware's 0–10 markings; the actual
> times are `attack` 50 µs (≈0) → 30 ms (≈10) and `release` 50 ms (≈0) → 3.5 s (≈10), stretching to ~20 s in
> the 10:1 Opto curve (Part B). **There is no threshold knob and no ratio *number* knob** — `ratio` picks a
> whole curve; **INPUT** drives into it.
>
> **Enum gotcha (the big one).** `[L] apply-vst-chain`'s `parameters` dict is **number-only**. It CAN set the
> numeric dials — verified: `{input:9, attack:2, output:7}` → `changed:true`, RMS −18.9→−14.7 — but it
> **cannot pass `ratio`/`detector`/`audio`** (string enums) or the bools. Since the ratio curve *is* the
> character, **drive this through `presets/vst/apply_vst_preset.py`** ([[vst-preset]]), which `setattr`s every
> param (string + numeric) and snaps to the nearest valid value.
>
> **British Mode is not in the headless surface.** The Pedalboard surface is exactly 12 params with **no
> British/Brit toggle** — the EL8-X "1176 all-buttons-in" mode (Part B) is **GUI-only here**. For that
> aggressive envelope headless, approximate with NUKE/20:1 + fast attack + Dist 3.

### RATIO / drive map — crest by ratio (input 8, attack 5, release 5, output 6.5; 20 s drum-bus excerpt, raw float, no trim)

| ratio | dry | 2:1 | 4:1 | 6:1 | 10:1 | 20:1 | NUKE |
|---|---|---|---|---|---|---|---|
| **crest** | **17.9** | 14.5 | 16.3 | 16.0 | 14.7 | **13.6** | 14.3 |
| RMS dBFS | −18.9 | −13.5 | −16.0 | −16.2 | −20.2 | −16.4 | −20.1 |

Higher ratio = harder clamp; **20:1 is the tightest** here and **NUKE** is the saturated brick-wall (peak
pinned, off-scale GR). The low ratios (2:1/3:1) are the silky soft-knee "leveling" curves; 4:1/6:1 begin to
grab; 10:1 is the Opto curve. (RMS swings because `output` is fixed at 6.5; compare crest, or loudness-match.)

### INPUT map — drive = level + GR + color (6:1, attack 5, release 5)

| input | 5 | 7 | 9 | 10 |
|---|---|---|---|---|
| RMS dBFS | −19.3 | −16.7 | −15.6 | −15.0 |
| crest | 15.6 | 15.7 | 15.8 | 16.0 |

INPUT pushes level/density (and, downstream, distortion) hard; at 6:1 the crest barely moves — the *ratio
curve* sets how hard it clamps, **INPUT sets how hot you run into it** (and how much THD). For more crush, go
to a higher ratio; for more color, raise INPUT (and add Dist 2/3).

### ATTACK map — the punch control (10:1, input 8; **lower number = faster**)

| attack | 0 (fast) | 5 | 10 (slow) |
|---|---|---|---|
| crest | **10.0** | 14.7 | **19.1** |
| centroid Hz | 3009 | 2986 | 2811 |

The biggest lever in the box. Fast attack (0) clamps the transient (crest 17.9→10.0); slow attack (10) lets it
punch *through* (crest → 19.1, above dry). Drums: keep attack ≥ ~3–4 to preserve transients.

### RELEASE map — density vs smoothness (10:1, input 8, attack 5; **lower = faster**)

| release | 0 (fast) | 10 (slow) |
|---|---|---|
| crest | 13.2 | 17.6 |
| RMS dBFS | −18.0 | −23.1 |
| centroid Hz | 3396 | 2922 |

Fast release recovers between hits → denser, **brighter** (the fast-recovery "attitude"), can pump. Slow
release holds GR down → smoother, but quieter (stays clamped). Fast release = the aggressive Distressor sound.

### DETECTOR map (10:1, input 8)

| detector | Norm | HP | Emp |
|---|---|---|---|
| crest | 14.7 | 12.4 | 12.7 |
| RMS dBFS | −20.2 | −16.3 | −17.5 |
| centroid Hz | 2986 | 2800 | 2821 |

`HP` (sidechain high-pass, ~100 Hz) takes the kick/lows **out of the detector** → it stops ducking on the bass,
overall GR drops (RMS up +3.9 dB), the **low band moves forward** (band-ratio low 0.79→0.87 in the validated
drum-glue render) and the detector now chases the snare/cymbal transients (crest down, slightly darker). `Emp`
boosts ~6 kHz in the sidechain → the comp overreacts to high-mid harshness (a built-in de-ess/de-harsh; output
EQ unchanged). These are the cures for LF pumping and harshness respectively.

### AUDIO / distortion — harmonics (1 kHz sine, H_k in dBc relative to fundamental, output 5)

**Isolated distortion stage (ratio 1:1, input 6 — gentle):**

| mode | H2 | H3 | THD % |
|---|---|---|---|
| Norm | −61 | −55 | 0.20 |
| Dist 2 | −56 | −48 | 0.45 |
| Dist 3 | −52 | **−35** | 1.74 |

**Musical comp + distortion (ratio 6:1, input 8):**

| mode | H2 | H3 | THD % |
|---|---|---|---|
| Norm | −50 | −58 | 0.32 |
| **Dist 2** | **−42** (+9 dB H2) | −58 (unchanged) | 0.84 |
| **Dist 3** | **−41** (+9 dB H2) | **−54** (+4.5 dB H3) | 0.89 |

The signature, measured: **Norm is near-clean** (THD 0.2 %); **Dist 2 adds the even/2nd harmonic** (warm,
octave, consonant); **Dist 3 adds the 2nd *and* the odd/3rd** (grittier, tape-like). Driving **INPUT** hot is
the master THD control — at 1:1/in10 even **Norm** hits THD 24 % and Dist 3 ~38 %, dominated by **odd**
harmonics (symmetric clipping of the over-driven stage). So: warmth = Dist 2 at modest drive; grit/aggression =
Dist 3 and/or more INPUT. On a drum bus (4:1/in7) Dist 3 also dropped crest most (16.5→14.1 — it softclips the
transients). On a steady NUKE'd tone THD reads ~0 because a constant sine has no transient to distort — THD
lives on transients/program peaks.

### MIX (parallel) map (NUKE, input 9, attack 5, release 5)

| mix | 100 (wet) | 50 | 30 |
|---|---|---|---|
| crest | 15.2 | 16.1 | **17.0** |

`mix` blends dry back in (0 = dry, 100 = fully compressed) — the built-in parallel control. mix 30 over a
NUKE'd layer restores the dry transients (crest back to ~dry) while keeping the crushed density underneath.

### Validated presets (Watercolors warm drum bus → `projects/watercolors/mix/distressor_*_demo.wav`; harness peak-trims to −1 dBFS, so density shows as +LU)

| Preset | ratio · in · atk · rel · audio · det · mix | crest 17.17→ | LUFS Δ | LRA 2.44→ | TP | character |
|---|---|---|---|---|---|---|
| **`distressor-drum-glue`** ★ | 2:1 · 5 · 8 · 5 · Dist 2 · HP · 100 | **15.06** (−2.1) | +2.0 | 1.96 | −0.99 | gentle musical glue + 2nd-harm warmth, low end forward (kept the feel) |
| **`distressor-aggressive-drums`** | 10:1 · 8 · 4 · 2 · Dist 2 · HP · 100 | **11.08** (−6.1) | +5.6 | 1.72 | −0.99 | dense, forward, in-your-face; the "Distressor on drums" attitude |
| **`distressor-parallel-smash`** | NUKE · 9 · 1 · 1 · Dist 3 · Norm · **30** | **14.43** (−2.7) | +2.6 | 2.16 | −0.99 | NY/room smash: crushed + gritty under the dry, transients kept by mix 30 |

Each ran headless via `uaudio_distressor.vst3` through `apply_vst_preset.py`. They sit on a **drum bus** here
but the same curves transfer to vocals / bass / guitar / room mics — see the Part B recipe table.

---

## Part B — web-research synthesis (cited)

### What it is & why it's iconic

The **Empirical Labs EL8 Distressor** (designed by **Dave Derr**, ex-Eventide H3000; first sold ~1995, company
founded 1996; **TECnology Hall of Fame 2016**; 38,000+ units) is a 1U single-channel **compressor/limiter +
distortion generator**. Its audio path is analog but the **control circuitry is digital**, which is what lets
one box produce **eight distinct compression *curves*** — each with its own threshold, knee shape and release
math, and for three of them (2:1, 10:1, NUKE) a *separate detector circuit*. Marketing line: "the speed of a
VCA, the personality of an FET, the warmth of an optical, the coloration of a tube." Reputation: "very
difficult to make it sound bad"; adds **mid-range bite that pushes a source forward**. Manufacturer's
near-foolproof start: **6:1, all four knobs at 5.** (Wikipedia loosely calls it a "VCA" — the manual's
"switchable knee/curve emulation" is more accurate.) **EL8-X** adds two retrofits the base EL8 lacks: **British
Mode** and **Stereo Image Link**.

### The RATIO curves

| Ratio | Character (cited) |
|---|---|
| **1:1** | No compression — audio passes the warming/distortion circuits only (use as a saturation box; also the hardware ratio from which British Mode is engaged). |
| **2:1** | Huge soft "parabolic" knee (15–30 dB), special detector; most transparent **leveling**, "silky." Tape-glue recipe: 2:1 + Dist 3, 1–3 dB GR. |
| **3:1** | Gentle parabolic soft knee like 2:1; general tracking, silky. |
| **4:1** | Steeper knee — starts to "nail" the signal. |
| **6:1** | The workhorse; easy slope then musically limits peaks. Manual's 1176 / Fairchild-IGFET emulation start. |
| **10:1 "Opto"** | Short-knee limiting + a huge knee with a **slow release tail up to ~20 s**, *separate opto detector* — emulates **LA-2A / LA-3A / LA-4A**. Canonical: **attack 10 (slow), release 0 (fast), Det HP on.** Keep attack ≥4 to keep the Opto flavour. |
| **20:1** | Near-brick-wall, hard knee; keeps signal within ~1 dB (clean 1176-20:1 emulation). |
| **NUKE** | Extreme brick-wall with a unique **logarithmic release**; built for **live drum room mics** (Bonham-style, 15–20 dB+ GR), parallel smash, density. Heavy GR drives the harmonic stages → "saturated brick-wall." |

**Opto (10:1)** is the famous smooth, program-dependent, anti-pumping mode (UAD re-labels the attack/release
knobs `Opto(n)` when 10:1 is selected — that's the readout in the GUI). **British Mode** (EL8-X) = a dedicated
switch recreating the **1176 "all-buttons-in"** aggressive envelope; on hardware engaged from the **1:1** ratio
but applicable to any ratio; keep attack < ~3–4 for the authentic 1176 grit. **British ≠ Opto ≠ NUKE.**

### ATTACK & RELEASE (authoritative spec)

- **Attack 50 µs – 30 ms** (among the fastest comps made; knob 0 = fast → 10 = slow). *Note: the common
  "attack up to 3.5 s" line conflates attack with release — attack tops out at 30 ms.*
- **Release 0.05 s – 3.5 s** (knob 0 = fast), stretching to **~20 s in 10:1 Opto** (logarithmic,
  program-dependent). Both interact with the chosen ratio curve. Slow attack = punch; fast attack = clamp
  (watch transients clipping into Dist 2/3); fast attack + fast release pumps; the cure for LF pumping at heavy
  GR is the **detector HP** (or slow down / use Opto).

### Distortion — Dist 2 / Dist 3, REDLINE & 1 % THD LEDs

The **AUDIO** button cycles `Norm → HP → Dist 2 → Dist 2+HP → Dist 3 → Dist 3+HP`. **Dist 2** = mostly **2nd
harmonic** (tube/Class-A warmth, ~0.05–3 % THD, hard to hear on single tracks). **Dist 3** = adds the **3rd**
(odd, tape-like, symmetric clip, ~0.1–20 % THD, hotter; not "3rd only" — 2nd is still present at light comp).
Two indicator LEDs: the panel **"1 % THD"** (yellow; body text says it actually trips ~0.25 %) and **REDLINE**
(~3 % THD) — a *guide, not a meter*; REDLINE is **not** hard-clip (a few dB more headroom past it). Warmth
lives around/below REDLINE.

### DETECTOR (sidechain) + the AUDIO HP

The **detector** is the sidechain — it changes *how much it turns down*, never the output tone directly. Two
**separate** high-pass filters:

- **Detector HP** (~**100 Hz, 6 dB/oct**, in the DETECTOR section) — keeps lows *out of the trigger* so bass
  doesn't duck the kit; cures LF pumping/plosives; the drum-bus staple (kick stays full + punchy).
- **Band Emphasis** ("the bump", ~**6 kHz** sidechain boost) — comp **overreacts to high-mids** = a built-in
  de-ess/de-harsh on vocals/guitars (no EQ on output).
- **Link** — couples detectors for matched stereo GR; the **"dead-patch" trick** (Link with nothing patched /
  mono) makes the detector see half-level → runs hotter + adds grunge.
- **Audio HP** (~**80 Hz, 18 dB/oct Bessel**, in the AUDIO section) — actually removes the lows **you hear**
  (mud/rumble), distinct from the detector HP.

### INPUT / OUTPUT / MIX / HR / GR meter

No threshold knob — each ratio is a fixed curve you drive into with **INPUT** (= drive + de-facto threshold +
color; harder in = more GR, steeper effective ratio, more THD). **OUTPUT** = calibrated makeup (pet levels:
**8 ≈ +4 tape**, **6.5 ≈ −10 gear**); hardware has *no output meter* — watch the GR bargraph (16 LEDs, ~0–24
dB, right-to-left, can run off-scale in NUKE; **active even in bypass**). **HR / Headroom** and **Dry/Comp
MIX** are **plugin-only** (the hardware did parallel comp via external multing) — HR sets the internal
operating reference (drive without INPUT's color, for A/B gain-matching); MIX is the built-in parallel blend.

### Application recipes by source (cited starting points — dial to the GR you hear)

| Source | ratio | attack | release | audio / dist | detector | target GR |
|---|---|---|---|---|---|---|
| Universal start | 6:1 | 5 | 5 | Norm | Norm | a few dB |
| Snare / kick / tom | 3:1–6:1 | 6 | 5 | Norm, Dist 2/3 for smack | HP if LF pumps | to taste |
| Kick / snare (opto) | 10:1 | 10 (slow) | 0 (fast) | Norm | HP | smack |
| **Room mics (NUKE)** | NUKE / 20:1 | 10 (or 4) | <3 = biggest | Dist 2/3 grunge | — | **15–20 dB+, off-scale** |
| Parallel drum smash | NUKE | 0–2 | 0–2 | Dist 2/3 | HP | 15–20 dB, blend ~30–50 % |
| Lead vocal | 6:1 (or 4:1) | 5 | 4 | Dist 2 for sheen | HP ± Emp | 3–10 dB |
| Vocal (smooth/opto) | 10:1 | 8–10 | 0 | Dist 2 | HP + Emp | 7–10 dB |
| Bass / DI | 4:1–6:1 | 5 | 4 | Dist 2/3 | Emp for "clack" | to taste |
| Electric guitar | 10:1 | quick | medium | — | Emp (solos) / HP (bright) | to taste |
| 2-bus / mix glue | 2:1 / 3:1 | 8–10 (slow) | fast-ish | Dist 2 light | HP | 1–4 dB |
| Digital→tape glue | 2:1 | fast | fast | Dist 3 | — | 1–3 dB |

Drums: keep attack > 3 for transients; NUKE was *built* for room mics (keep the room preamp 20–30 dB under the
close mics so NUKE doesn't lift the noise floor). 2-bus: gentle 2:1/3:1 glue with Det HP — **not** a mastering
limiter; reach for NUKE only as an effect. Hand the glued result to [[finalize-mix]] / [[master-track]].

### UAD/UADx plugin specifics

UA's officially-endorsed emulation (built with Dave Derr), released Nov 2017 (~$299). **UADx** = native (macOS
incl. Apple Silicon + Windows, no UA DSP hardware; **free iLok account, no dongle**); also a DSP UAD build for
Apollo/UAD-2. Models the EL8 controls + Dry/Wet **MIX** and **Headroom (HR)** as plugin-only additions. For
this repo's headless pipeline: load `uaudio_distressor.vst3`, set `ratio`/`detector`/`audio` via the preset
harness, verify the render actually changed (`changed:true` + measure *detail*).

---

## Recipe table (measured starting points — re-dial to your GR)

| Goal | ratio | input | attack | release | audio | detector | mix | Preset |
|---|---|---|---|---|---|---|---|---|
| **Musical drum glue** (keep feel) ★ | 2:1 | 5 | 8 | 5 | Dist 2 | HP | 100 | `distressor-drum-glue` |
| **Aggressive/forward drums** | 10:1 | 8 | 4 | 2 | Dist 2 | HP | 100 | `distressor-aggressive-drums` |
| **Parallel / NY smash** | NUKE | 9 | 1 | 1 | Dist 3 | Norm | **30** | `distressor-parallel-smash` |
| **Smooth opto leveling** (vocal/bass) | 10:1 | 5–6 | 9–10 | 0–1 | Dist 2 | HP(+Emp) | 100 | (recipe) |
| **Transparent 2-bus glue** | 2:1 | 4–5 | 9–10 | 4 | Dist 2 (light) | HP | 100 | (drum-glue, ratio 2:1) |
| **Room-mic explosion** | NUKE | 9–10 | 10 | 1–2 | Dist 3 | — | 100 | (parallel, mix 100) |

**Dials are 0–10½ knob positions** (attack/release: **0 = fast, 10 = slow**; input/output = drive/makeup).
Leave `power` on, `bypass`/`master_bypass` off; harness peak-trims to −1 dBFS.

## Pitfalls

- **Don't drive it through `apply-vst-chain` alone** — `ratio`/`detector`/`audio` are string enums the
  number-only dict can't pass (it'll silently leave the default `6:1`/`Norm`/`Norm`). Use the [[vst-preset]] harness.
- **British Mode is GUI-only here** — not in the 12-param headless surface. Approximate with NUKE/20:1 + fast
  attack + Dist 3; for the real thing, run it in a DAW.
- **Wrong build = passthrough** — the `/Components/UAD Empirical Labs Distressor.component` twin passes audio
  through offline. Load `uaudio_distressor.vst3`; verify `changed:true` + measure *detail* ([[vst-verify]]).
- **It compresses AND distorts** — it gets louder and thicker; **A/B at matched loudness** ([[level-match]] /
  `render-ab`); don't mistake +LU/THD for "better."
- **Attack direction trips people** — **lower = faster**. For punch, turn attack *up* (toward 10), not down.
- **Fast attack + heavy GR pumps on lows** — engage the **detector HP**, or slow the attack, or use 10:1 Opto.
- **NUKE lifts the noise floor / bleed** — expect off-scale GR; on room mics keep the source well below the
  close mics. NUKE/20:1 are effects, not a 2-bus master.
- **It's not a master** — color/glue/comp stage; hand off to [[finalize-mix]] / [[master-track]] for
  loudness/limiting. For a true-peak brick-wall use [[fabfilter-pro-l-2]] or `render-mastered`.

## Sources

- Empirical Labs — Distressor manual (PDF): https://www.empiricallabs.com/wp-content/uploads/distressor_manual.pdf · product page: https://www.empiricallabs.com/distressor/ · Brit-mode tips: https://www.empiricallabs.com/brit-mode-tips-and-tricks/
- Universal Audio — EL8 Distressor product page: https://www.uaudio.com/products/empirical-labs-el8-distressor-compressor · v9.4 release: https://www.uaudio.com/blogs/press/v9-4_distressorpr · 5-Min UAD Tips: https://www.uaudio.com/blogs/ua/5-min-uad-tips-empirical-labs-distressor · support manual: https://help.uaudio.com/hc/en-us/articles/18741515014676 · UAD manual EL8 chapter (HP 100 Hz/6 dB-oct, audio HP 80 Hz/18 dB-oct): https://hookup.co.jp/assets/upload/support/attachments/2023/12/4469/Empirical-Labs-EL8-Distressor_JP0803.pdf
- Sound on Sound review: https://www.soundonsound.com/reviews/empirical-labs-distressor · SonicScoop — Dave Derr tips: https://sonicscoop.com/inventor-insights-dave-derrs-tips-tricks-for-the-empirical-labs-distressor/ · Tape Op EL-8X: https://tapeop.com/reviews/gear/32/el-8x-distressor · Puremix vocal settings: https://www.puremix.com/blog/rich-kellers-vocal-distressor-settings · Nail The Mix: https://www.nailthemix.com/uad-distressor-plugin
- Wikipedia: https://en.wikipedia.org/wiki/Empirical_Labs_Distressor · Gearspace Dave Derr Q&A (10:1): https://gearspace.com/board/q-a-with-dave-derr-designer-of-the-distressor-compressor-/4440-10-1-ratio-distressor-what-should-one-use.html

## Related

- [[distressor]] — the workflow skill this field guide backs · [[vst-compress]] / [[vst-saturate]] — the generic skills it specializes
- [[fairchild-660]] — tube COLOR comp (holds crest) · [[la-3a]] — solid-state opto leveler · [[ssl-bus-compressor-2]] — VCA glue · [[fabfilter-pro-mb]] — multiband dynamics — the dynamics family
- [[vst-preset]] — apply enum chains (required here) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge ratio/attack variants
- [[finalize-mix]] / [[stem-master]] — stages this fits · [[fabfilter-pro-l-2]] — the brick-wall limiter that comes after · [[gemini-audio-understanding]] — why meters (not Gemini mono) own crest/GR/THD
- `scripts/mix/distressor_sweep.py` — the isolation/characterization sweep behind Part A
