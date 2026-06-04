# Softube Tape — field guide: gain-compensated tape color, glue & lo-fi (measured)

How to drive the **Softube Tape** plugin (`/Library/Audio/Plug-Ins/VST3/Tape.vst3`) — the three-machine
tape emulation pictured in `Tape/…` sessions (deck + **RC-1 Remote Control** panel, AMOUNT/TYPE/TAPE SPEED).
Two halves: **Part A** is *measured on this rig* (real param surface + isolation numbers from our own
renders); **Part B** is a *web-research synthesis* (cited) of how the plugin actually works. The skill
[[softube-tape]] is the measured workflow over this doc.

> **Not an Ampex, not a UAD.** This is **Softube's own** "Tape" (Softube logo, "TAPE RC-1 REMOTE CONTROL").
> The faceplate's "MANUFACTURED IN SWEDEN / MARK II / CERAMIC CAPSTAN" is Softube's *own* branding (Softube
> is Swedish) — **not** the modeled machine's origin. The Ampex emulation is the separate
> `uaudio_ampex_atr-102_tape` ([[ampex-atr-102]]); the Studer is `uaudio_studer_a800` ([[studer-a800]]).
> A correction for the record: an early inventory search wrongly concluded "Softube makes no tape plugin /
> it isn't installed." It **is** installed and **renders headless** here (Part A) — that search only looked
> at the local docs, not the disk.

> **Repo caveat:** Gemini hears ~16 kbps mono — it can't judge the head-bump LF, deep sub, true-peak from
> tape transients, HF air, or stereo. **Meters own this.** Verify every move with `[L] measure-spectrum`
> (tilt / centroid), `[L] measure-loudness` (crest/PLR), `[L] measure-stereo` (crosstalk), `[L] check-clipping`.

---

## TL;DR (the headline, measured)

1. **FOOTGUN — the plugin's DEFAULT state is already hot.** A bare load = Amount **7.8**, Type **C**, fully
   **WET**, **+6 dB Input**, Crosstalk **50** → crest **−0.9 dB** out of the box. **A no-params `apply-vst-chain`
   applies a lot.** Always set Amount / dry_wet explicitly for subtle use.
2. **Amount is gain-compensated → it barely moves the tone; it moves the *crest*.** Sweeping Amount 2→10
   (peak-normalized) shifted spectral centroid only ~2218→2245 Hz, but crest fell **−0.2 dB (a2) → −0.9 dB
   (a8) → −4.9 dB (a10)**. So **read Amount as saturation + tape-compression, not brightness.** The knee is
   steep: ≤8 is gentle glue, **10 crushes** (and "spits" 3rd harmonic). The official guide is "drive until the
   THD meter reads ~1–1.4 %" — headless you can't see that meter, so **use crest drop + your ears (render-ab)**.
3. **The Types differ mostly in low-end weight (on drums).** At equal Amount 5: **A = most transparent**
   (centroid 2212 ≈ dry 2223), **B = darkest & fattest** (2113, most LF), **C = in between** with a touch
   more top. Pick by weight: A clean → C colored → B fattest.
4. **Faster IPS = brighter + tighter lows; 15 IPS = fattest** (head bump lands on the kick). Centroid: 15 IPS
   **2219** (warmest) < 3¾/7½ **2293** < 30 IPS **2404** (brightest). Slow speeds are the lo-fi/noise zone.
5. **High Freq Trim is the direct tone lever** — a real ±HF shelf: **CUT** centroid 1705 / FLAT 2219 / **BOOST**
   2785 (≈ ±560 Hz). Reach for this to brighten/darken, not for Amount.
6. **Crosstalk NARROWS — it never widens.** OFF→100 raised L-R correlation 0.983→**0.995** and dropped width
   −20.5→**−26.3 dB** (mono-sum loss 0.63→**0.30**). It's mono-glue / center-weight, **not** a stereo widener,
   and it does nothing on a true-mono source.
7. **It renders headless** via Pedalboard (Softube/iLok — authorized on this rig; re-verify elsewhere). Every
   one of its 13 string-enum params took effect in our renders.

---

# Part A — measured on this rig

Probe: `Tape.vst3` loaded via Pedalboard (stemmy-loops `vst` extra), processing a 60 s **stereo drum bus**
(`projects/watercolors/mix/bus_punchy_pre.wav`), each variant **peak-normalized to −1 dBFS** so only *shape* /
crest / stereo are compared. Sweep script: `artifacts/softube-tape-probe/sweep.py`. Centroid (Hz) is the
brightness proxy; crest (dB) is the saturation/compression proxy (THD% is unreliable on broadband drums — see
the note below).

### The real parameter surface (Pedalboard-exposed) — **13 of 15 params are string enums**

| Param (Pedalboard) | UI control | Values | default | Role |
|---|---|---|---|---|
| `color_amount` | **AMOUNT** | `0.0`…`10.0` (0.1 step) | **7.8** | saturation + tape compression; **gain-compensated** |
| `color_type` | **TYPE** | `A` · `B` · `C` | **C** | machine: A clean / B fat-transformer / C British-color |
| `tape_speed` | **TAPE SPEED** | `1 7/8` · `3 3/4` · `7 1/2` · `15` · `30 IPS` | **15 IPS** | speed → head-bump bass, top, distortion, noise |
| `dry_wet` | **DRY/WET** | `DRY` · `0.1`…`99.9` · `WET` (= %) | **WET** (100 %) | parallel blend |
| `speed_stability` | **SPEED STABILITY** | `STABLE` · `99.9`…`0.1` · `WOBBLY` | **STABLE** | wow **and** flutter (pitch + level wobble) |
| `high_freq_trim` | **HIGH FREQ TRIM** | `CUT` · `-4.9`…`4.9` · `BOOST` | **FLAT** (`0.0`) | mastering HF shelf |
| `crosstalk` | **CROSSTALK** | `OFF` · `0.1`…`100.0` | **50.0** | inter-channel bleed → **narrows/glues** |
| `input_db` | **INPUT** (Master) | `-∞` · `-48.0`…`+12.0` | **6.0** | drive (also raises level) |
| `output_db` | **OUTPUT** (Master) | `-∞` · `-48.0`…`+12.0` | **6.0** | make-up |
| `noise` | **NOISE** | `False`/`True` | **False** | tape hiss (grows as speed drops) |
| `playback` | **RUN/STOP** | `STOP`/`RUN` | **RUN** | tape start/stop ramp — keep **RUN** or no sound |
| `meter` | meter mode | `LEVEL`/`THD` | `LEVEL` | VU readout (cosmetic offline) |
| `view` · `reserved` · `bypass` | — | — | — | cosmetic / unused / bypass |

> **Harness is mandatory.** `apply-vst-chain`'s `parameters` dict is float-only, so it **cannot** set the
> string enums (`color_type`, `tape_speed`, `dry_wet`, `speed_stability`, `high_freq_trim`, `crosstalk`,
> `input_db`, `output_db`). Set everything through the **[[vst-preset]]** harness
> (`presets/vst/apply_vst_preset.py`, exact-string-then-snap). `color_amount` is a float-valued enum (0.1 grid)
> and *can* be set either way, but keep it in the harness with the rest.

### TYPE — which machine, by tone (Amount 5, 15 IPS, Crosstalk OFF, WET)

| Type | centroid | Δ vs dry | low-ratio | high-ratio | read |
|---|---|---|---|---|---|
| dry bus | 2223 | — | 0.589 | 0.0130 | reference |
| **A** | 2212 | −11 | 0.586 | 0.0133 | **most transparent** (≈ dry) — Hi-Fi / clean |
| **C** | 2219 | −4 | 0.629 | 0.0133 | middle — adds LF weight + a touch of top |
| **B** | 2113 | **−110** | **0.654** | 0.0101 | **darkest & fattest** — most LF, least top |

> On this kick-heavy bus the practical Type difference is **low-end weight** (A ≤ C ≤ B) — B's reviewed
> "smiley/boost-the-highs" did **not** dominate here; its LF lift won. Use **B for warmth/fat**, **A for clean**.

### AMOUNT — saturation/compression, not tone (Type C, 15 IPS, Crosstalk OFF)

| Amount | centroid | crest | Δcrest vs dry | read |
|---|---|---|---|---|
| dry | 2223 | 21.61 | — | reference |
| 2 | 2218 | 21.39 | −0.22 | barely there |
| 5 | 2219 | 21.38 | −0.23 | subtle glue |
| **7.8 (bare default†)** | 2261 | 20.68 | −0.93 | **obvious** — what a no-params load does |
| 8 | 2237 | 20.68 | −0.93 | obvious glue |
| **10** | 2245 | **16.69** | **−4.92** | **crushed / distorting** ("desired distortion") |
| 8, **DRY/WET 50 %** | — | 20.98 | −0.63 | parallel softens the squash (vs −0.93 full-wet) |

† the bare default also carries Crosstalk 50 + WET, so its centroid isn't directly comparable to the Crosstalk-OFF rows.

**THD% is not a usable saturation proxy here.** `measure-distortion` on this broadband drum bus returned
46–60 % non-monotonically (the "fundamental" is just the 70 Hz kick partial, swamped by program content), and
tape sometimes *lowered* it. **Trust crest** for the compression read; trust your ears (render-ab) for the
"spit." (The plugin's own GUI THD meter — the official drive guide — isn't readable headless.)

### TAPE SPEED — faster = brighter + tighter lows (Type C, Amount 5, Crosstalk OFF)

| Speed | centroid | low-ratio | high-ratio | read |
|---|---|---|---|---|
| 3 3/4 IPS | 2293 | 0.572 | 0.0157 | brighter, less LF than 15 (lo-fi/noise zone) |
| 7 1/2 IPS | 2293 | 0.572 | 0.0157 | ≈ 3¾ on this material |
| **15 IPS** | **2219** | **0.629** | 0.0133 | **fattest LF (head bump on the kick), darkest top** — studio default |
| **30 IPS** | **2404** | 0.578 | 0.0176 | **brightest + tightest lows** |

Faceplate-consistent: toward 30 = "treble / less bass", toward slow = "noise". **15 IPS fattens the kick;
30 IPS tightens + brightens.** (1⅞ IPS not swept — it's the darkest/crunchiest lo-fi extreme; turn Noise on.)

### HIGH FREQ TRIM — the direct tone lever (Type C, Amount 5, 15 IPS)

| Setting | centroid | Δ vs FLAT | high-ratio |
|---|---|---|---|
| **CUT** | 1705 | **−514** | 0.00594 |
| FLAT | 2219 | — | 0.0133 |
| **BOOST** | 2785 | **+566** | 0.0309 |

A genuine ±~560 Hz HF shelf — this, not Amount, is how you brighten (BOOST) or warm/de-harsh (CUT) the result.

### CROSSTALK — narrows & glues, never widens (Type C, Amount 5, 15 IPS, WET)

| Crosstalk | L-R corr | width dB | mono-sum loss | read |
|---|---|---|---|---|
| dry | 0.9808 | −20.09 | 0.63 | reference |
| OFF | 0.9827 | −20.52 | 0.63 | ≈ dry (tape itself barely narrows) |
| 50 | 0.9841 | −20.90 | 0.60 | a touch narrower / glued |
| **100** | **0.9953** | **−26.30** | **0.30** | strongly narrowed → near-mono, **best mono-compat** |

The top narrows most (high-band width −19.8 → −27.5 at 100). Use 40–50 % for center-weight/glue; expect it to
**tighten the image and improve mono-sum**, not widen. **Inert on a true-mono source.**

---

# Part B — how the plugin works (web-research synthesis, cited)

## 1. What it is

Softube **Tape** is a tape-machine emulation effect that adds analog cohesion / warmth / "glue" via
component-level + physical modeling of **three** vintage machines (it models the circuits, the head, and the
tape). It ships with presets by Grammy engineers **Joe Chiccarelli & Howard Willing**. It's regarded as
**subtler, more transparent and far more CPU-efficient** than UAD Studer A800 / UAD Ampex ATR-102 / Slate VTM /
Waves J37 — at the cost of fewer formulas / less deep control. [softube.com/plug-ins/tape · musicradar · pluginoise]

## 2. The three TYPES (Softube does **not** name the real machines)

Softube describes them only by region/circuit — "an essence of years of different circuits research." Model
attributions below are **online speculation, not confirmed.** [softube.com/user-manuals/tape]

| Type | Softube's words | Character (reviews) | Speculated (UNCONFIRMED) |
|---|---|---|---|
| **A** | "Swiss tape machine that gained popularity in the 60s" — precision/linearity | flattest / most neutral / Hi-Fi / brightest; least change to source | Studer A80 *(speculation)* |
| **B** | "transformer-based circuit … extra weight and cream to the low end" | warmest/most colored; weight + ~2 dB @ 50 Hz; reviewed as lows-**and**-highs "smiley" | Ampex ATR-102 *(speculation)* |
| **C** | "British tape machine with a distinct vintage vibe" | most aggressive/colored; pronounced tape compression + harmonic distortion; top-tilted + organic LF | EMI / British BTR *(speculation)* |

*Disputed:* whether B is "most colored" (majority) or "subtlest" (one review). **Our measurement says B is the
darkest/fattest on drums** — trust the meters for your material. [musicradar · unison · djbooth · productlondon]

## 3. Controls (official)

- **Amount** — saturation/coloration depth; **gain-compensated** (output auto-trimmed so louder ≠ "better").
  Official drive guide: raise until the **THD meter reads ~1–1.4 %** (~1–1.4 % subtle · ~2–3 % obvious · >4 %
  aggressive — the >4 % rung is reviewer interpretation). [softube manual]
- **Type / Tape Speed** — see §2; speed sets brightness, head-bump bass, distortion **and** noise *together*
  (30 & 15 IPS = mastering-grade; 7.5 and below = warm→lo-fi). [softube manual · musicradar]
- **THD / Level meter** — switch the VU between input-level and Total-Harmonic-Distortion readout (gain-staging).
- **Dry/Wet** — parallel blend; with Speed Stability → flanging/chorus. [softube manual]
- **Speed Stability** — wow **and** flutter (slow pitch drift + rapid pitch/level wobble), STABLE→WOBBLY. [softube · musicradar]
- **High Freq Trim** — mastering HF shelf, **FLAT / BOOST (sparkle) / CUT (darker/warm)**; one source places the
  corner "above 3 kHz" (single-source). [softube]
- **Crosstalk** — inter-channel magnetic **bleed** (L↔R); reinforces **center punch/weight + mono glue** (subtle
  ~50 Hz lift), can **narrow** the field; 40–50 % typical for mastering; **stereo-only**. [softube · dubspot]
- **Noise** — tape hiss on/off (off by default); louder/bassier as speed drops. [softube]
- **Input / Output (Master Levels)** — **Input is a second drive control** (more in = more saturation, the Types
  are input-dependent) **and** is *not* gain-compensated; **Output** trims final level — gain-match Output when
  A/B-ing. [softube]
- **Run / Stop** — emulate reel start/stop ramps (slower speed = longer ramp); **not** DAW transport. [softube]

## 4. Character — saturation vs compression; bright vs dark

- **Saturation = odd-order, 3rd-harmonic dominant** (magnetic-media/transformer signature) → edge/grit/cut, not
  even-order tube "warmth." Pushed hard (Amount/Input high, THD >~2–3 %), the 3rd harmonic lands in **2–5 kHz**
  and reads as **"spit," not warmth.** [sonalsystem · productlondon]
- **The "glue" is the gentle built-in compression + the LF head bump — NOT the harmonics.** Don't stack another
  compressor after it without care (double-compression). [izotope · productlondon]
- **Brighten/darken depends on Type *and* speed:** A neutral/brightest, B fat, C top-tilted-but-most-saturated;
  **faster speed = brighter + tighter lows, slower = darker + bigger head-bump bass + more hiss.** [musicradar]
- **Head bump** ~80–100 Hz (exact value disputed), bigger/lower at slower speeds. [pluginerds · masteryourtrack]

## 5. Recipes (research) — cross-checked against Part A

- **Drums (glue):** Type **B** (weight) or **C** (compression/grit) · **15 IPS** warm-punch / **30 IPS** tight ·
  Amount to ~1–1.4 % THD ≈ only ~1–2 dB transient (crest) reduction. [musicradar · productlondon]
- **Mix/master bus (transparent):** Type **A** · **30 IPS** · Amount for only ~1–2 dB crest reduction · HF Trim
  FLAT (or slight BOOST for air) · Crosstalk 40–50 % for cohesion. Peak-safe. [softube · musicradar]
- **Parallel thick (drums/bass):** drive hard (high Amount), pull **Dry/Wet** back to keep transients — the
  Chiccarelli/Willing kick/bass move; bass: Type B, ~15 IPS, ~50/50. [softube]
- **Lo-fi / character:** 7.5 IPS and below (1⅞ = darkest/crunchiest) · high Amount · raise **Speed Stability** ·
  **Noise on** · Type C. Creative, not mastering-grade. [musicradar]
- **Tame digital harshness (medium conf.):** light Amount (~3–5) · HF Trim toward **CUT** · Type A/C; don't
  over-drive (3rd-harmonic spit). [productlondon]

## 6. Pitfalls & gotchas

- **The bare default is hot** (Amount 7.8 / Type C / WET / +6 in / Crosstalk 50). Set Amount + dry_wet explicitly.
- **Input ≠ gain-compensated** (Amount is). Raising Input adds saturation **and** level → gain-match with Output,
  always A/B loudness-matched ([L] render-ab). Calibration is rumored ~−13 dBFS = 0 VU (vs the usual −18,
  single-source/unverified) → gain-stage conservatively.
- **Crosstalk narrows, needs stereo.** Don't expect width; at 100 it's near-mono. No effect on a mono file.
- **Speed couples tone+bass+noise+distortion** — pick speed for the *whole* character, not one attribute.
- **Don't double-compress** — tape already compresses; a comp after it can over-squash.
- **Type/model names are unofficial** — "Studer/Ampex/EMI" is speculation; Softube says only Swiss /
  transformer / British.
- **Headless can't read the THD meter** — substitute crest (`measure-loudness`) + render-ab for the official
  "drive to 1–1.4 % THD" method. **Speed Stability** is pitch/level modulation that spectra barely capture —
  judge it by ear.

## 7. Decision table

| Goal | Type | IPS | Amount | DRY/WET | HF Trim | Crosstalk | Noise |
|---|---|---|---|---|---|---|---|
| Warm/fat drum-bus glue | **B** | 15 | 5–6 (crest −0.5…−0.9) | WET | FLAT | 40–50 | off |
| Tight/modern drum bus | A or C | 30 | 4–5 | WET | FLAT/+ | OFF–40 | off |
| Transparent mix/master glue | **A** | 30 | 2–3 (crest −0.2…−0.5) | WET | FLAT (+ for air) | 40–50 | off |
| Parallel thick (drums/bass) | C (drums) / B (bass) | 15 | 8 (drive hard) | **50 %** | FLAT | OFF | off |
| Lo-fi / character | C | 3¾ or 1⅞ | 8–10 | WET | CUT | OFF | **on** |
| Tame digital harshness | A or C | 15 | 3–5 | WET | **CUT** | OFF | off |
| Bass weight + glue | **B** | 15 | 5–6 | 50–100 % | FLAT | OFF | off |

*Default starting point for drums:* Type **B** · **15 IPS** · Amount **5** · WET · HF FLAT · Crosstalk **OFF** ·
Noise off — then push Amount for more glue (watch crest), HF Trim for tone, Crosstalk for mono-glue.

---

## Sources

Softube Tape product page (softube.com/plug-ins/tape) · Softube Tape user manual (softube.com/user-manuals/tape)
· Sound on Sound (saturation strategies) · MusicRadar review · DJBooth review · Unison · ProductLondon ·
Bobby Owsinski · Harmony Central · AudioPluginGuy · Gearspace (Softube Tape; IPS-speed thread) · Dubspot ·
pluginoise (Softube vs UAD Studer) · pluginerds / pluginreviewlab (best tape emulations) · SonalSystem
(tube/tape/transistor harmonics) · iZotope (tape emulation) · KVR (forum + product) · keenlessons (vs Slate) ·
Reverb (tape shootout) · NailTheMix · vst-plugin.com · thegearforum (gain-staging) · masteryourtrack /
performermag (IPS) · Sweetwater · Plugin Boutique · babyaud.io (parallel; wow & flutter). Plus **our own
isolation/sweep measurements** (Part A) on `Tape.vst3` via Pedalboard (`artifacts/softube-tape-probe/sweep.py`).
