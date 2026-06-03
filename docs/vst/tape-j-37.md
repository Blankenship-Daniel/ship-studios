# Arturia Tape J-37 — field guide: the Sgt. Pepper tape machine (DAW-only here)

How to drive the **Arturia Tape J-37** (`Tape J-37.vst3` / `.component`) — a neural-modeled emulation of
the **Studer J37** 4-track valve tape recorder (Abbey Road / *Sgt. Pepper*). Two halves: **Part A** is
*measured on this rig* (the real Pedalboard param surface **plus the headline finding that it does NOT render
headless here**); **Part B** is a *web-research synthesis* (cited) of how the machine works and how to dial it.
The skill [[tape-j-37]] is the workflow over this doc.

> **Name note:** the user's screenshot titles it "Ampex Tape J-37", but the **J37 is a Studer**, not an Ampex
> (Ampex made the ATR-102 / MM-1200). For an *Ampex* master-tape that **does** render headless in this pipeline,
> use [[ampex-atr-102]]; the punchier headless multitrack tape is [[studer-a800]].

---

## TL;DR (the headline — read this first)

1. **It does NOT render through `apply-vst-chain` / the headless pipeline on this rig.** Measured: the plugin
   loads and accepts/echoes every parameter, but its **DSP never engages — it passes audio through unprocessed**
   (only a fixed latency offset). A 1 kHz sine at **drive 50 / Color4** came out at **0.00 % THD**; `output_level_db
   = −24` produced **no level change**; `noise_db = +20` added **no noise**; a `+15 dB` low-shelf produced **no
   spectral change**; **drive 0 ≡ drive 40 ≡ Bypassed, bit-for-bit**. Cause: Arturia's ASC licensing self-bypasses
   in an unattended, no-GUI subprocess. **Do not "tape" a render with this plugin in the pipeline — you will ship a
   passthrough and not know it.** (Control: IK `Tape Machine 80` distorted the same sine to **40.6 % THD** — the
   method is sound; the passthrough is J-37-specific.)
2. **Use it where it works: in the DAW** (exactly as the screenshot shows). Dial it on the channel/bus, **print/
   bounce to a WAV**, drop that into `projects/<track>/`, then re-enter the ship-studios pipeline to **measure /
   loop / master**. The plugin is the *creative* tape stage; ship-studios is the *measurement + delivery* stage.
3. **For a tape stage INSIDE the headless pipeline**, reach for a verified-headless option instead:
   [[studer-a800]] (punchy multitrack), [[ampex-atr-102]] (glossy 2-bus/master), IK `Tape Machine 80/440/99/24`,
   `UAD Oxide Tape`, or the pure-DSP `[L] saturate-loop` ([[vst-saturate]]).
4. **Meters own tone** (Gemini hears ~16 kbps mono): judge any J-37 bounce with `[L] measure-spectrum`
   (tilt/centroid), `measure-loudness` (crest/PLR), `measure-stereo` (ST Offset hurts mono — check correlation),
   `check-clipping`. A/B loudness-matched with `[L] render-ab` so "tape sounds better" isn't just "louder".

---

# Part A — measured on this rig

Probe: `Tape J-37.vst3` loaded via Pedalboard (stemmy-loops `vst` extra), processing
`projects/watercolors/mix/bus_warm_pre_dry.wav` (a drum bus) and a synthetic 1 kHz / −12 dBFS sine.

### The verdict: loads, echoes params, **renders passthrough** (does not process)

| test | expectation if processing | measured | reading |
|---|---|---|---|
| param set + read-back (`tape_drive_db=40`, `tape_color='Color4'`, `speed='7p5IPS'`) | accepts | **accepts & echoes** | the param interface is live |
| drive 0 vs drive 40 vs `on_off='Bypassed'` | very different | **bit-identical (Δ=0.00000)** | DSP never engages |
| `output_level_db = −24` | RMS −24 dB | **RMS unchanged** | no output stage |
| `noise_db = +20` | noisy | **no added noise** | no noise gen |
| `eq_low_shelf_gain_db = +15 @ 120 Hz`, `eq_on_off=True` | lows balloon | **low-band fraction unchanged** | no EQ |
| **1 kHz sine @ drive 50 / Color4** | several % THD | **0.00 % THD, level unchanged** | **no saturation at all** |
| *control:* IK `Tape Machine 80`, same sine, driven | distorts | **40.6 % THD** | method is valid |

**Conclusion:** the Arturia Tape J-37 is **GUI/DAW-only** in this environment. It is *not* on the headless-safe
**render** list — only the load probe passes. This is the textbook **"loads ≠ renders"** trap the repo warns about
(`docs/vst/README.md`): a plugin instantiates, takes parameters, even reports a latency, yet passes audio through
untouched. The cause is Arturia's licensing (ASC), which the unattended subprocess can't satisfy, so the plugin
self-bypasses. *If* Arturia ever ships offline-render-friendly auth, re-confirm with [[vst-verify]] (the sine→THD
test above) before trusting it — `changed:true`/an LUFS delta is **not** enough proof for a tape unit.

### The real parameter surface (Pedalboard-exposed — for reference / a future fix)

125 params total; the rest are NKS/MPE/hardware-controller cruft (`vst_programchange_*`, `mpe_*`, `hw_*`,
preset-browser navigation) — ignore those. The **audio** params, all reported as `ENUM` by Pedalboard (numeric
ones accept a float snapped to the nearest step; the **string/bool** ones — `speed`, `tape_color`,
`tape_modern_mode`, `eq_mode`, the `*_on_off` bools — would need the [[vst-preset]] harness, never
`apply-vst-chain`'s float-only dict — *moot while it passthroughs*):

| Param | Values *(default)* | GUI control |
|---|---|---|
| `on_off` | `Active` · `Bypassed` *(Active)* | global bypass |
| `tape_drive_db` | `0.0 … 50.0` (0.05 step) *(**15.0**)* | **DRIVE** — input drive into the tape, **with auto-gain compensation** (level stays ~constant; you hear saturation/compression, not volume) |
| `tape_color` | `Color1 … Color4` *(Color1)* | **COLOR** — tape/calibration recipe (see Part B §2) |
| `tape_modern_mode` | `Vintage` · `Modern` *(Vintage)* | **MODERN** — Modern removes the natural HF+LF tape filtering (cleaner/more defined) |
| `speed` | `7p5IPS` · `15IPS` *(15IPS)* | **SPEED** — 7.5 = darker/warmer, 15 = brighter/cleaner |
| `tape_stereo_offset` | `False` · `True` *(**True**)* | **ST Offset** — models inter-channel dispersion → **wider** (⚠️ check mono) |
| `output_level_db` | `−24.0 … +24.0` *(0.0)* | OUTPUT trim |
| `eq_on_off` | bool *(True)* | Advanced EQ enable (flat by default → inaudible) |
| `eq_mode` | `Pre` · `Post` · `Emphasis` *(Emphasis)* | EQ placement vs the tape stage |
| `eq_low_shelf_*` | freq 20–20k *(50)* · gain ±15 *(0)* · reso 0.1–12 *(0.707)* | low shelf |
| `eq_bell_*` | freq *(500)* · gain *(0)* · reso *(0.707)* | mid bell |
| `eq_high_shelf_*` | freq *(5000)* · gain *(0)* · reso *(0.707)* | high shelf |
| `calibration_on_off` | bool *(True)* | enables the noise + instability (wear) modeling |
| `noise_db` | `−20.0 … +20.0` *(**−20.0** = min)* | tape hiss level |
| `instability_instability` | `0.0 … 100.0` *(0.0)* | wow & flutter / mechanical wear amount |
| `delay_loop_on_off` | bool *(**True**)* | the tape-echo Delay Loop |
| `delay_time_unsynced_ms` / `delay_time_synced` | 10–1000 ms *(100)* / `1/32…8` *(1/4)* | delay time (free / synced) |
| `delay_highpass_filter_hz` / `delay_lowpass_filter_hz` | *(125 / 7500)* | delay-path band-limit |
| `delay_stereo_offset` / `delay_feedback` | 0–100 *(0 / 0)* | delay width / repeats |
| `tape_stop` / `tape_start_mode` / `tape_stop_time_selection_bar` | `Play`·`Stop` *(Play)* / `Instant`·`Fast Forward` / `8…1/4` | tape-stop transport FX |

> **Defaults to mind** (when you do dial it in the DAW): **DRIVE defaults to 15 dB** (already a real amount of
> saturation, not unity); **ST Offset is ON** (widens — verify mono); the **Delay Loop reports ON** by default
> (feedback 0 — confirm it isn't adding a slap in your session). `VU CALIB` (the GUI's −8 dB in the screenshot)
> is the **metering 0-VU reference** for gain-staging, not a Pedalboard param.

---

# Part B — how the machine works (web-research synthesis, cited)

## 1. What it is / the hardware it models

The **Studer J37** is a 1-inch **4-track valve (tube)** recorder, designed by Willi Studer and released in the
early 1960s — Studer's first multitrack. Abbey Road bought **four in 1965** and tracked on them until 8-track
arrived in 1969; it is the machine George Martin and The Beatles bounced between for **Sgt. Pepper** (track-to-track
reductions to free up tracks), so its sound is baked into that era. EMI's modified units had the **EQ locked to the
CCIR (European) curve** — which is exactly why the J-37's cleanest **Color1 is "European calibration"** (see §2).
Tube electronics + magnetic tape = the J37's signature: harmonic richness, natural compression, and a soft top —
~18 kHz bandwidth. Arturia's plugin reproduces it with a **neural / machine-learning model** of the device's
non-linearities (tube distortion + tape magnetics), not a circuit sim.

The real, modeled effects of tape (same physics as [[studer-a800]] — pull that doc for the deep theory):

- **Head bump** — an LF rise (~+1–4 dB, ~octave wide), speed-dependent (center freq doubles when speed doubles).
  This "fattens" drums/bass and is **not** distortion.
- **HF softening** — loud highs don't survive magnetic recording; the top gets "less brash", more so at 7.5 IPS.
- **Saturation / harmonics** — predominantly **odd-order (3rd)** from the symmetric tape curve, plus the J37's
  **tube** stage adding its own (more even-order) color. The "tape = warm even harmonics" myth is mostly wrong for
  the tape itself; here the **tube electronics** are what soften the odd-harmonic edge.
- **Tape compression** — gentle, program-dependent transient rounding → glue; drums benefit most.
- **Wow & flutter** + **hiss** — modeled (`instability_instability`, `noise_db`), **off/min by default**.

## 2. The COLOR modes (Arturia's own descriptions)

Four "tape + calibration + bias" recipes; C1→C4 climbs in age, grit, and saturation. Marketing names map roughly
**Pristine / Warm / Driven / Dirty**, but use Arturia's literal descriptions:

| Mode | Arturia description | Character | Reach for |
|---|---|---|---|
| **Color1** | fresh **SM911** tape, **European (CCIR)** calibration | cleanest, **leaner lows**, most clarity — the EMI/Abbey-Road CCIR config | transparent glue; bright sources you don't want fattened |
| **Color2** | **SM911** tape, **American (NAB)** calibration | **warmer/fuller lows** (NAB's bass shelf), still clean | the default "warm tape" — drums, bus, mix glue |
| **Color3** | **decade-old SM468** tape | **grittier, vintage** — more texture, softer top | lo-fi character, vintage drums, attitude |
| **Color4** | **over-biased SM468** | **most saturated/textured/dirty** | heavy color / FX; back off Drive or it gets harsh |
| **Modern** (toggle) | "removes natural high and low filtering" | **cleaner, more defined** — keeps the harmonics, drops the tape EQ shaping | when the tape coloration is too much but you want the saturation |

> The **Color1=European/CCIR vs Color2=American/NAB** split is the same NAB-vs-CCIR lever documented for the
> Studer A800 ([[studer-a800]] §Lever 4): NAB has a ~50 Hz bass shelf (fuller), CCIR doesn't (leaner). So
> **Color1 = clarity / Color2 = warmth** is physics, not marketing.

## 3. The other levers

- **DRIVE** (`tape_drive_db`, default 15) — input drive **with auto-gain compensation**, so it changes
  *saturation + compression*, not loudness. More drive → more 3rd-harmonic + transient rounding → eventually
  edge/IMD (the harsh-when-overdriven signature; cure = less drive). Because of auto-gain you must **A/B
  loudness-matched** to judge it honestly.
- **SPEED** (`speed`) — **15 IPS** = brighter, cleaner, higher head-bump (~tighter lows); **7.5 IPS** = darker,
  warmer, bigger/lower head bump + more HF rolloff (more "vibe", more colored). Warmth → 7.5; fidelity → 15.
- **ST Offset** (`tape_stereo_offset`, default ON) — models the slight L/R dispersion of real tape → **wider,
  livelier stereo**. Great on polysynths/stereo busses; **a mono-compatibility risk** — always check
  `[L] measure-stereo` correlation / mono-sum loss, and turn it **off** for mono-critical material.
- **EQ** (Advanced) — 3-band (low shelf / bell / high shelf) placeable **Pre / Post / Emphasis** of the tape.
  *Pre* drives the tape differently (shapes what hits the saturation); *Post* shapes the result; *Emphasis* is the
  record/playback emphasis curve. Subtle tone-shaping in the box.
- **Noise / Instability** (Advanced, gated by `calibration_on_off`) — `noise_db` adds modeled hiss (min by
  default), `instability_instability` adds wow & flutter / mechanical wear. Character salt; both **off/min** unless
  you want overt lo-fi. Noise stacks across instances.
- **Delay Loop** (Advanced) — a tape echo (sync'd or free, band-limited, with feedback): subtle flanging → slapback.
- **VU + THD meter / VU CALIB** — the VU reads input level; the **THD** read shows how hard you're driving the
  tube/tape; **VU CALIB** sets where 0 VU sits (the screenshot's −8 dB) for gain-staging. Drive until THD/VU sits
  where the sound is right, not by a number.

## 4. Recipes (GUI settings — dial these in the DAW, then bounce)

These are **starting points from Arturia's descriptions + tape physics**, **not measured on this rig** (it won't
render headless to measure). Verify by ear in the DAW and by meter on the **bounce**.

| Goal | COLOR | SPEED | MODERN | DRIVE | ST Offset | Notes |
|---|---|---|---|---|---|---|
| Warm drum bus (heft + glue) | Color2 | 15 | Vintage | ~moderate (12–18) | taste (check mono) | the user's warm lane; back off if the top spits |
| Fat / vintage drums | Color3 | 7.5 | Vintage | moderate | on | grit + bigger low bump |
| Transparent bus glue | Color1 | 15 | Vintage/Modern | low (6–12) | off for mono safety | leanest, cleanest |
| Dirty / lo-fi FX | Color4 | 7.5 | Vintage | high | on | add Noise/Instability to taste |
| Saturation without tape EQ | any | 15 | **Modern** | to taste | taste | keeps harmonics, drops coloration |
| Mix-bus warmth (2-bus) | Color2 | 15 | Vintage | low (THD just tickling) | off (mono-safe) | gentle; mind latency with linear-phase tools |

*Default to dial from:* **Color2 · 15 IPS · Vintage · Drive ~12–15 (auto-gain on) · ST Offset off until you
verify mono · Noise/Instability off · Delay off.**

## 5. Pipeline integration (the part that matters here)

Because the plugin is DAW-only in this environment, the workflow is **hand-off, not insert**:

1. In the DAW, insert Tape J-37 on the channel/bus, dial a recipe (§4), **print/bounce** to WAV (24-bit).
2. Drop the bounce into `projects/<track>/mix/` (or `stems/`).
3. **Measure** it: `[L] measure-spectrum` (did tilt/centroid move warmer, or did 2–5 kHz rise = overdriven?),
   `measure-loudness` (crest dropped a touch = glue, not squashed), `measure-stereo` (ST Offset → correlation/
   mono-sum — reject if it collapses in mono), `check-clipping`.
4. **A/B honestly:** `[L] render-ab` (loudness-matched) the dry vs the tape bounce — so the verdict isn't just
   "louder". For a perceptual read, `[G] compare-to-reference` on the loudness-matched pair.
5. Continue the normal pipeline ([[loops-to-deliverables]], [[master-track]], etc.).

## 6. Pitfalls & gotchas

- **#1: it passthroughs headless.** Never put `Tape J-37.vst3` in `apply-vst-chain` / a `presets/vst/` harness
  chain expecting tape — you'll get an unprocessed copy (plus latency) and a false `changed:true`. There is
  deliberately **no `presets/vst/tape-j-37-*.json`** for this reason.
- **Auto-gain hides the drive** — Drive won't get louder; you must A/B loudness-matched to hear if it's helping.
- **ST Offset is ON by default and widens** — a mono-fold landmine on a mono-critical mix; verify with
  `[L] measure-stereo` and disable for mono.
- **Drive 15 is the default, not unity** — even "Default" is already saturating; pull Drive down for a clean tape.
- **Overdriven = harsh** — too much Drive (esp. Color4) adds 2–5 kHz edge + IMD no EQ fixes; the cure is **less
  Drive / a higher-headroom Color / Modern mode**, same as any tape.
- **Don't EQ-fix a balance problem with tape** (or vice-versa); set levels first ([[mix-balance]]).
- **It's a Studer, not an Ampex** — for an Ampex master tape that renders headless use [[ampex-atr-102]].

## 7. When to use the J-37 vs the headless tapes

| Want | Use |
|---|---|
| The specific J37 / Sgt-Pepper tube-tape vibe, hands-on in the DAW | **Tape J-37** (this) → bounce → pipeline |
| Tape *inside* the headless pipeline, punchy multitrack | [[studer-a800]] (`uaudio_studer_a800.vst3`) |
| Tape *inside* the pipeline, glossy 2-bus / mastering | [[ampex-atr-102]] |
| Cheap, deterministic, no-plugin tape-style color | `[L] saturate-loop` ([[vst-saturate]]) |
| Other headless tapes | IK `Tape Machine 80/440/99/24`, `UAD Oxide Tape` |

---

## Sources

Arturia Tape J-37 product/overview + Downloads & Manuals (arturia.com; manual v1.0.0, 2024-12-11) ·
Arturia support FAQ (support.arturia.com) · MusicRadar & MusicTech Tape J-37 coverage · Waves "Behind the J37"
+ Abbey Road "Studer J37 #GearThatMadeUs" + vintagedigital.com.au (J37 hardware: 1″ 4-track valve, Abbey Road
1965, CCIR-locked, Sgt. Pepper) · tape physics cross-referenced from [`docs/vst/studer-a800.md`](studer-a800.md)
(head bump / odd-harmonic saturation / NAB-vs-CCIR). Plus **our own Pedalboard load + render measurements** on
`Tape J-37.vst3` (Part A) — the passthrough finding.
