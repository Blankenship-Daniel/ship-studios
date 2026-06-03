# UADx Pultec MEQ-5 — field guide: passive tube MID-RANGE EQ, headless (measured)

How to drive the **UADx Pultec MEQ-5 EQ** (`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_meq-5.vst3`) — UA's
model of the **Pultec MEQ-5 "Mid-Range Equalizer"**: a **passive LC (inductor) EQ + tube make-up amp +
transformers** that works *only* in the midrange (≈200 Hz–7 kHz). Three overlapping sections — **LOW PEAK**
boost, a **DIP** cut, and a **HIGH PEAK** boost — plus an output trim. The **MIDRANGE** member of UA's Pultec
Passive EQ Collection, next to the lows+air [[pultec-eqp-1a]] and the HP/LP-filter [[pultec-hlf-3c]]; a **broad,
musical** "colour" EQ, not surgical. **Part A** is *measured on this rig* (the real Pedalboard param surface +
our own transfer-function / THD / render results); **Part B** is a *web-research synthesis, adversarially
verified, cited*. The skill [[pultec-meq-5]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the tilt/centroid/crest
> that prove a tonal move. Verify every move with `[L] measure-spectrum` / `measure-loudness`. A render that
> "sounds" EQ'd but shows a 0.00 spectrum delta is a **passthrough** (you loaded the wrong build).

---

## TL;DR (the headline, measured)

1. **It renders headless — load the `uaudio_` build.** `uaudio_pultec_meq-5.vst3` loads + processes (UADx native;
   hm_peak=10 @3 kHz moved the signal **0.285 max-abs** vs flat). `master_bypass=True` is the **only TRUE null**
   (bit-identical to the dry input). Never load a `UAD …`/`Legacy .component` twin (passthrough offline). iLok
   account, no dongle — **re-verify on a new machine** ([[uadx-uaudio-build-renders-headless]]).
2. **The MEQ-5 0–10 dial is ROUGHLY dB here** — the key distinction from the [[pultec-eqp-1a]] (nonlinear,
   not-dB) and [[hitsville-eq-mastering]] ("8 ≈ +5 dB") knobs. Measured: **LOW PEAK ≈ +1 dB/unit → +10.7 dB max**;
   **HIGH PEAK ≈ +0.9/unit → +8.8 dB max** (matches the hardware's documented **+8 dB** ceiling, Part B); the
   **DIP is nonlinear/saturating** (−1.4 @2, −4.9 @4, −8.9 @6, **−11 dB max**, ~flat past 7).
3. **Three sections, fixed-stepped frequencies, broad overlapping bells (passive).** LOW PEAK **200/300/500/700/
   1000 CPS**; DIP **200/300/500/700 CPS · 1/1.5/2/3/4/5/7 KCS** (11 steps); HIGH PEAK **1.5/2/3/4/5 KCS**. Boost
   bells are ~1.5–2 octaves wide; the DIP ~1 octave (a touch more focused); the **HIGH PEAK narrows at higher
   settings** (5 KCS = a focused presence bell, 1.5 KCS = broad). `CPS`=Hz, `KCS`=kHz (vintage cycles-per-second).
4. **Boost + DIP at the same frequency does NOT cancel — it focuses.** Measured LOW PEAK 700 @10 + DIP 700 @10 →
   **+2.3 dB @700** with slightly scooped shoulders = a tighter, more resonant midrange peak. (The MEQ-5 does this
   with **two separate sections**, not the EQP-1A's single-band boost+atten — Part B §3.)
5. **It's the MIDRANGE box — no real lows or air.** Nothing below 200 Hz, nothing above 5 kHz (boosts) / 7 kHz
   (DIP). For sub/low-shelf weight + 10–16 kHz air → [[pultec-eqp-1a]]; HP/LP filtering → [[pultec-hlf-3c]];
   surgical notches → [[fabfilter-pro-q-4]].
6. **At unity it's near-transparent in MAGNITUDE; the colour is a gentle level-dependent harmonic, driven by
   INPUT.** Engaged-flat vs bypass = ±0.04 dB across the band (+0.15 dB @200, a soft top roll to −0.5 dB @15 kHz)
   — so the large time-domain non-null is **phase + harmonic, not tone**. Harmonic THD rises with input level
   (**0.012 % @−18 → 0.096 % @0 dBFS**, even-order; Part B: 2nd-harmonic from the tube make-up amp). The **`output`
   trim is a CLEAN post-gain that does NOT saturate** → to drive it for colour, raise the **input**, not the output.
7. **All 10 params are enums — but the three AMOUNT knobs are float-settable and the rest are string enums.**
   `lm_peak` / `mid_dip` / `hm_peak` (floats 0–10) DO set via `apply-vst-chain`'s float dict; the **frequency
   selectors** (`lm_freq`/`mid_freq`/`hm_freq`), `output`, and `enable` are **string enums it silently drops** →
   a float-dict build keeps the DEFAULT freqs (lm 200 / mid 700 / hm 1.5 k) and your LOW/HIGH PEAK land on the
   wrong bands. **Use the [[vst-preset]] harness** for any real patch.

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin(".../uaudio_pultec_meq-5.vst3")` →
`name="UADx Pultec MEQ-5 EQ"`, `is_instrument=False`, renders (EQ moves change the audio). The default load
comes up **engaged + flat** (`enable=In`, all amounts 0, `lm_freq=200 CPS`, `mid_freq=700 CPS`,
`hm_freq=1.5 KCS`, `output=0.0 dB`) — no leftover-GUI-state footgun, but still **set every param explicitly** in
a preset for reproducibility. Measurement rig: `scripts/mix/meq5_sweep.py` (Welch cross-spectral transfer on a
fixed white-noise buffer + 1 kHz-sine THD); param dump: `presets/vst/dump_params.py`. Tonal/preset validation on
`projects/watercolors/mix/bus_punchy_pre.wav` (the 60 s dry, measured-balanced drum bus the other per-plugin docs
use), peak-normalized −1 dBFS so only spectral shape is compared.

### The real parameter surface (Pedalboard-exposed — authoritative; **10 params, all enums**)

| GUI control | Param | Values *(default)* | Role (measured) |
|---|---|---|---|
| LOW PEAK freq | `lm_freq` | `200·300·500·700·1000 CPS` *(200)* — str | **LOW PEAK** boost centre (low-mid body) |
| LOW PEAK (boost) | `lm_peak` | `0.0 … 10.0` *(0)* — float | LOW PEAK amount — **≈ +1 dB/unit, +10.7 dB at 10** |
| DIP freq | `mid_freq` | `200·300·500·700 CPS · 1·1.5·2·3·4·5·7 KCS` *(700)* — str | **DIP** cut centre (de-box/de-honk; 11 steps) |
| DIP | `mid_dip` | `0.0 … 10.0` *(0)* — float | DIP amount — **nonlinear, saturates ~−11 dB by ~7** |
| HIGH PEAK freq | `hm_freq` | `1.5·2·3·4·5 KCS` *(1.5)* — str | **HIGH PEAK** boost centre (presence/attack) |
| HIGH PEAK (boost) | `hm_peak` | `0.0 … 10.0` *(0)* — float | HIGH PEAK amount — **≈ +0.9 dB/unit, +8.8 dB at 10** |
| IN/OUT lever | `enable` | `In·Out` *(In)* — str | EQ engage (`Out` ≠ a true null — use `master_bypass`) |
| Output knob (small, far-right) | `output` | `OFF·−12.0…+12.0 dB` *(0.0 dB)* — str | **clean** ±12 dB output trim (UA addition; OFF = mute) |
| (header) | `power` / `master_bypass` | bool | unit power / plugin bypass — **`master_bypass=True` = true null** |

> ⚠ **`apply-vst-chain`'s float dict sets only the three AMOUNT knobs** (`lm_peak`/`mid_dip`/`hm_peak`); it
> **silently drops** the string enums (`lm_freq`/`mid_freq`/`hm_freq`/`output`/`enable`). A float-dict build keeps
> the **default** freqs (lm 200 / mid 700 / hm 1.5 k) — so a "LOW PEAK 500 / HIGH PEAK 3 k" you asked for lands on
> 200 / 1.5 k instead. **Build every patch with the [[vst-preset]] harness** (`apply_vst_preset.py`, `setattr`
> handles all enums). `parameters_set` is **not** proof it took.

### Render-proof / null / always-on imprint

| check | result | reading |
|---|---|---|
| `hm_peak=10 @3 KCS` − flat | **0.285 max-abs** | RENDERS headless ✓ |
| `master_bypass=True` − dry input | **0.000000** | the **true null** (bit-identical) |
| `enable=In`, all 0 − `master_bypass` (time-domain) | 0.198 max-abs | NOT a null — but it's **phase + harmonic**, not tone (see magnitude ↓) |
| `enable=In`, all 0 / bypass — **magnitude** | +0.15 @200, ±0.04 elsewhere, **−0.21 @10 k, −0.48 @15 k** | near-flat with a gentle top roll = a faint passive imprint, not EQ |

### Amount → dB calibration (single band, FFT-Δ vs flat at the band centre)

| amount | **LOW PEAK @500** | **DIP @1 k** | **HIGH PEAK @3 k** |
|---|---|---|---|
| 2 | +1.61 | −1.38 | +1.56 |
| 4 | +3.28 | −4.86 | +3.02 |
| 6 | +5.35 | −8.87 | +4.75 |
| 8 | +8.07 | −10.65 | +6.92 |
| 10 | **+10.68** | **−10.97** | **+8.84** |

The **boosts are ~linear, accelerating** (LOW PEAK ≈ +1.07 dB/unit → +10.7 dB; HIGH PEAK ≈ +0.88 dB/unit →
+8.8 dB — the **+8 dB hardware ceiling**, Part B). The **DIP is nonlinear and saturates** — most of its cut is in
by ~6, and 8→10 barely moves (−10.65 → −10.97). So treat amounts as **roughly the dB you'll get** for boosts, but
dial the DIP by ear/meter (4–6 ≈ a strong, musical scoop). **The "8" on the MEQ-5 is much closer to dB than the
Hitsville/EQP-1A knobs** — that's this plugin's signature.

### Curve shapes (amount 10, FFT-Δ dB vs flat — proves the bell width/centre)

| | below | centre | above | shape |
|---|---|---|---|---|
| **LOW PEAK @200** | +4.7 @80 · +8.0 @125 · +9.8 @160 | **+10.5 @200** | +10.0 @250 · +8.8 @300 · +6.5 @400 · +4.9 @500 · +1.7 @1 k | broad bell (~1.5–2 oct) |
| **LOW PEAK @1000** | +5.4 @500 · +8.5 @700 · +9.7 @800 | **+10.7 @1 k** | +9.6 @1.25 k · +7.8 @1.5 k · +5.3 @2 k · +2.8 @3 k | broad bell |
| **DIP @3 KCS** | −5.9 @2 k · −9.2 @2.5 k | **−11.0 @3 k** | −9.9 @3.5 k · −7.9 @4 k · −5.0 @5 k · −2.5 @7 k (lows ~0) | ~1-oct notch |
| **HIGH PEAK @1.5 KCS** | +5.8 @1 k · +8.1 @1.25 k | **+8.5 @1.5 k** | +6.6 @2 k · +4.5 @2.5 k · +3.2 @3 k | broad |
| **HIGH PEAK @5 KCS** | +1.0 @3 k · +3.6 @4 k | **+8.8 @5 k** | +1.8 @7 k · +0.5 @10 k | **focused** (narrows at HF) |

So: LOW PEAK = broad low-mid bell; DIP = a moderately broad (~1 oct) mid notch; HIGH PEAK = broad at 1.5 k →
focused/resonant at 5 k. All bells **interact** (passive) so stacked moves aren't strictly additive.

### The boost + DIP overlap (the "Pultec-style" mid move)

`lm_freq=700 lm_peak=10` + `mid_freq=700 mid_dip=10` (boost + cut the SAME 700 CPS) does **not** cancel → net
**+2.3 dB @700** with mildly scooped shoulders (−0.26 @1.25–1.5 k). The LOW PEAK bell is a touch stronger/narrower
at the exact centre while the DIP's broader skirts pull the surround down → a **tighter, more focused/resonant
midrange peak**. The MEQ-5's frequency switches deliberately overlap so you can do this on any shared Hz (Part B §3).

### Output trim (clean broadband gain)

`output='6.0 dB'` → **+5.97 dB** flat across 100 Hz–8 kHz; `output='-6.0 dB'` → **−6.04 dB** flat. Confirmed a
**clean** ±12 dB output trim (with an OFF/mute position) — **not** a saturating drive (THD unchanged vs unity).

### Harmonic colour (1 kHz sine, THD% by input level)

| input | bypass | enable In, flat | output +6 |
|---|---|---|---|
| −18 dBFS | 0.000 | **0.012** | 0.012 |
| −12 dBFS | 0.000 | **0.028** | 0.028 |
| −6 dBFS | 0.000 | **0.059** | 0.059 |
| 0 dBFS | 0.000 | **0.096** | 0.096 |

Gentle, **level-dependent** harmonic generation from the modeled tube/transformer make-up amp — ~0.1 % at 0 dBFS
(Part B: even-order / 2nd-harmonic; the hardware spec is ≤0.15 % @ +10 dBm). **`output +6` ≡ `enable In` THD** →
the output trim is a clean post-gain that does **not** add colour. **To drive the MEQ-5 for harmonic warmth, raise
the INPUT** (`input_gain_db` in the harness), then trim back — not the `output` knob.

### Preset validation (`bus_punchy_pre.wav`, peak-normalized −1 dBFS; `[L] measure-spectrum` / `measure-loudness`)

| preset | low | low-mid | mid | high-mid | centroid (Hz) | crest (dB) | read |
|---|---|---|---|---|---|---|---|
| **dry** | 0.589 | 0.327 | 0.0360 | 0.0346 | 2223 | 21.61 | source |
| **drum-presence** (LP 200@3 · DIP 500@4 · HP 3k@5) | 0.610 | 0.307 | **0.0182** | **0.0510** | 2261 | 20.97 | forward attack + de-boxed (high-mid up, mid down), centroid ↑ |
| **mid-scoop** (LP 200@2 · DIP 700@5 · HP 4k@3) | 0.604 | 0.334 | **0.0114** | 0.0374 | 2270 | 20.38 | the signature de-honk/de-box (mid crushed) |
| **warm-body** (LP 300@4 · DIP 2k@4 · HP 5k@4) | 0.519 | **0.433** | 0.0219 | 0.0182 | **2069** | 22.01 | low-mid forward + honk scooped → **warmer** (centroid ↓), crest held |

> **Overlap caveat, measured live:** an earlier warm-body dipped **3 KCS** while boosting **5 KCS** — the DIP's
> ~1-octave skirt ate most of the 5 kHz boost (the 5 kHz third-octave barely moved). Moving the DIP to **2 KCS**
> keeps it clear of the boost. Whenever you boost + dip near each other, **re-measure** — the broad passive bells
> interact. (And on a bass-heavy drum bus a strong low-mid LOW PEAK dominates the centroid → "warm," not "smile.")

### Presets (`presets/vst/`)

- **`pultec-meq5-mid-scoop.json`** — DIP 700 @5 + HIGH PEAK 4 k @3 + LOW PEAK 200 @2: the signature **de-honk/de-box**.
- **`pultec-meq5-drum-presence.json`** — LOW PEAK 200 @3 + DIP 500 @4 + HIGH PEAK 3 k @5: **forward attack + cleared box**.
- **`pultec-meq5-warm-body.json`** — LOW PEAK 300 @4 + DIP 2 k @4 + HIGH PEAK 5 k @4: **low-mid warmth/body**.

Apply with `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in> <out>`.

---

# Part B — How the EQ works (web-research synthesis)

> Scope: this part is the cited *research synthesis* — what the MEQ-5 is, how its circuit and curves behave, and how engineers use it. The **measured Pedalboard param surface, isolation/shootout renders, and headless-render verdicts live in Part A** (the measured deep-dive); where this part states a number it is from a cited source, and divergences between hardware spec and the UAD plugin are flagged inline.

## 1. What it is — the Pultec MEQ-5

The **MEQ-5 is the Pultec "Mid-range Equalizer"** — a passive, tube-amplified program EQ that works *only* in the mids, the "power region" where most program energy sits. It is the midrange specialist of the Pultec family: the **EQP-1A** owns lows + highs, the **EQH-2** is a simpler high/low EQ, and the MEQ-5 handles **two midrange boost bands flanking one midrange dip (cut) band** — the region the others deliberately leave alone.

| Fact | Value | Notes |
|---|---|---|
| Maker | **Pulse Techniques Inc.** ("Pultec") | Founded **Feb 1953** by Eugene "Gene" Shenk + Ollie Summerland (AudioScape spells it "Summerlin"). Teaneck, NJ; ~29 yrs of hand-built units. |
| Type | Passive LC program EQ + tube make-up amp | Mid-only: 2 boost ("PEAK") + 1 cut ("DIP") |
| Release year | **1955** *(single-source, unverified)* | Only the Vintage Digital archive states a year; the manufacturer page gives none. Treat as plausible, not corroborated. |
| Topology | Passive inductor/cap filter; insertion loss restored by a tube line amp | Vintage Digital spec sheet, verbatim: *"Loss: None. Passive equalizer loss is restored by amplifier. Overall result is no loss and no gain."* |
| Tubes (original) | **1× 12AX7 (ECC-83), 1× 6AQ5, 1× 6X4 (rectifier)** | Vintage Digital's vintage-unit listing names only **12AX7 + 6AQ5** plus two 1N1731 diodes (no 6X4) → tube count is **version-dependent**. |
| I/O | **600 Ω** input + output transformers | |
| Specs | Noise < **−75 dBm**; THD **≤ 0.15 % @ +10 dBm / 600 Ω**; response **20 Hz–20 kHz, +0 / −1 dB** ref 1 kHz | |
| Solid-state variant | **MEQ-5-SS** (early 1970s) | Same input transformer + passive EQ; tube gain stage swapped for an op-amp (API 2520) → Triad output transformer. |

> **"LC" is an inference** from "passive / inductor" — the literal phrase "LC" is not printed in the fetched spec sheets, though it is the correct circuit description. The often-repeated **Western Electric** lineage applies (per AudioScape) to the *make-up amp's negative-feedback topology being licensed from Western Electric*, **not** to the EQ circuit, which was Shenk's own design — do not assert a broader Western Electric connection.

## 2. The three sections in detail

Three independent control sets, each = a stepped **frequency-select switch** + a continuous **boost/cut amount knob**. The frequency knobs are stepped rotary switches (5 / 11 / 5 positions); the amount knobs are continuous and faceplate-numbered **0–10** — that **0–10 is a relative scale, not a dB readout.** *(CONFIRMED — verdict 1, all three frequency sets verbatim from Pulse Techniques; CONFIRMED — verdict 2, the dial-is-not-dB point.)*

| Section | Selectable frequencies | dB range | Curve |
|---|---|---|---|
| **LOW PEAK** (boost, low-mids) | **200, 300, 500, 700, 1000 Hz** | **0 to +10 dB** | broad bell |
| **DIP** (cut, mids) | **200, 300, 500, 700 Hz and 1, 1.5, 2, 3, 4, 5, 7 kHz** (11 steps) | **0 to −10 dB** | narrower / more surgical bell |
| **HIGH PEAK** (boost, high-mids) | **1.5, 2, 3, 4, 5 kHz** | **0 to +8 dB** | broad bell |

**Critical correction (verdicts 1, 2, 4):** the boost knobs are **NOT all 0–10 dB.** Low Peak and Dip reach **±10 dB**; **High Peak tops out at +8 dB** — its 0–10 *dial* maps to a 0–**8** dB electrical range. There is **no band that reaches ~12 dB**; the maximum anywhere is 10 dB. Any source claiming the High Peak does +10 dB is wrong against the manufacturer spec.

**Curve width / proportional-Q.** No source publishes a numeric Q or bandwidth for any section — this is the weakest-sourced part of the picture. The consistent reviewer consensus: the **boosts are broad and gentle (low Q); the dip is narrower and more useful for surgical work.** **Proportional Q** (curve narrowing as gain increases) is *typical of passive Pultec-type filters* and plausible here, but **no source explicitly asserts it for the MEQ-5** → treat "proportional Q" as **inferred, not cited.** Unlike the EQP-1A's high-boost band, the **MEQ-5 has NO bandwidth/Q control** — width is fixed by the circuit.

**The "0–10 dial is not dB" caveat.** The amount knobs are graduated 0–10 as a magnitude scale; the dB values above are the *electrical* ranges. The UAD manual gives the frequencies and an output gain but **does not publish the per-section dB ranges** — so the plugin's section maxima (0–10 / 0–10 / 0–8 dB) are **inferred to match the hardware**, not separately documented by UA.

## 3. The overlap / "Pultec-style" midrange move

The MEQ-5's signature is running **boost + dip together** to sculpt the mids — and the frequency switches are deliberately **overlapping** so you can do this at the same or adjacent frequency. *(CONFIRMED — verdict 3.)*

- The **DIP frequencies overlap both boost bands**: 200/300/500/700/1000 Hz are shared with LOW PEAK, and 1.5/2/3/4/5 kHz are shared with HIGH PEAK. So you can **boost and dip the same nominal frequency** (e.g. HIGH PEAK +3 kHz with DIP −3 kHz), producing a **narrow boost sitting inside a broader surrounding cut** — "a musical, resonant peak with a gentler surrounding scoop."
- **Mechanism caveat (verdict 3):** on the MEQ-5 this uses **two separate band sections** (a Peak band + the Dip band), *not* one shared boost/cut control. That differs from the EQP-1A's famous low-end trick (one band, one shared frequency switch, separate boost & atten knobs). The move is *analogous in spirit*, not identical in circuit.
- **Source contradiction, resolved.** Manufacturer / AudioScape / circuit views say the overlap is real and even enables ~10 "Pultec tricks" across the mids; UA's own blog says the MEQ-5 *"operates with fixed separate bands — you cannot overlap boost and dip frequencies on the same point."* **Engineering read: the frequencies *are* shareable across the two sections, so functionally you CAN boost and dip the same Hz.** UA's "cannot overlap" is best read as applications shorthand (the MEQ-5 lacks the EQP-1A's single-knob-pair offset trick), **not a circuit limitation.**
- **Scooping / honk control.** The dip alone pulls boxiness/honk out of the 300–500 Hz region; flanking that scoop with the two boosts is how you "cut to add presence" — the presence is largely *relative contrast* (dip the box while the high-mid PEAK lifts), not an actual presence boost. The classic worked move (MusicRadar): **boost a little at 700 Hz, dip substantially at 500 Hz, boost again at 3 kHz.**

## 4. MEQ-5 vs EQP-1A vs HLF-3C — why they chain

The three Pultec passive boxes divide the spectrum and chain because each covers what the others can't:

| Box | Covers | Bands | Has a true midrange? |
|---|---|---|---|
| **EQP-1A** | Lows + highs (program EQ) | LF shelf boost/atten **20/30/60/100 Hz**; HF peak boost **3/4/5/8/10/12/16 kHz** with a **Bandwidth (Q)** knob; HF-shelf atten **5/10/20 kHz** | **No** |
| **MEQ-5** | **Mids only** ("power region") | 2 mid boosts + 1 mid dip (see §2) | **Yes — this is its whole job** |
| **HLF-3C** | Band-limiting filters | Passive **12 dB/oct** high-cut + low-cut, no EQ bands, no tube amp | n/a (filters) |

- **Why MEQ-5 chains after EQP-1A:** the EQP-1A has **no dedicated midrange band**, so the MEQ-5 fills exactly the gap the EQP-1A leaves. AudioScape: *"Used in concert, the EQP-1A and MEQ-5 offered a highly musical solution… across the entire frequency spectrum, with a great deal of control over the critical mid-range. And this combination is exactly how the two designs were meant to be used."* Pulse Techniques calls the MEQ-5 the *"richly colorful tube-amplified companion piece to the EQP-1A."*
- **Chain order is engineer preference, not mandated.** No primary source dictates a fixed MEQ-5-after-EQP-1A sequence. The load-bearing fact is **functional complementarity** (lows/highs on the EQP-1A, mids on the MEQ-5), not a required order *(unverified as a rule)*.
- **HLF-3C** completes the trio as the **steep high/low-cut filter** (rumble/hiss removal, band-limiting, telephone effects) — the EQP-1A/MEQ-5 shape tone, the HLF-3C carves the edges. Its cutoff lists (low-cut 50 Hz–2 kHz, high-cut 1.5–15 kHz) are **dealer-sourced**, not confirmed on a manufacturer spec sheet *(treat as dealer-sourced)*.

> **EQP-1A spec caveats:** the max-dB figures (+13.5 / −17.5 dB LF; +18 dB HF peak; −16 dB HF shelf) are from a dealer page (Vintage King), widely repeated but **not manufacturer-verified here**. The HF-peak frequency list **3/4/5/8/10/12/16 kHz** (7 steps) is authoritative (manufacturer compare table); Sound on Sound's abbreviated "3/5/8/10/12 kHz" is a summary, not the full list.

## 5. Character / tone

The MEQ-5 is a **broad, musical, forgiving, broad-stroke tone-shaper** — not a surgical notch tool.

- **Why it's hard to make sound bad.** The EQ section is **entirely passive** (inductors/caps/resistors) with **broad curves**; even fully boosted, the boost "still has a smooth and natural character… the reason for this is the Pultec's broad EQ curves" (Marc Mozart). Stepped frequencies + limited ±dB mean there's **no narrow-Q resonance to dial in by accident.**
- **Harmonic colour comes from the make-up amp, not the EQ.** The passive filter loses level; the **tube + transformer make-up stage restores it and adds saturation/warmth.** On the closely-related EQP-1A, Sound on Sound *measured* "a steady progressive rise in **second harmonic** distortion with increasing input level… all other harmonics remain pretty much constant" → the colour is **predominantly even-order (2nd harmonic), increasing with drive** — it **fattens rather than fuzzes.** The MEQ-5 spec gives only the blanket **≤0.15 % THD @ +10 dBm**; its **harmonic-vs-drive curve is unstated** for the MEQ-5 specifically.
- **Topology nuance (single-sourced).** AudioScape describes the MEQ-5 make-up amp as **single-ended** (which "naturally features more second-order harmonics… especially flattering to the midrange"), versus the EQP-1A's push-pull amp. This **single-ended claim is from one source and is not in the manufacturer spec** (which lists only tube types) → **plausible but unverified.** There is also an **unresolved contradiction** over whether the MEQ-5 line amp is unique to it (AudioScape) or shared with the EQH-2 (Gearspace/UltimatePreset).
- **Hardware vs plugin.** A Sound on Sound A/B found the hardware had "a slightly more involving character and a more natural-sounding high end" than the UAD plugin — close but not identical *(UAD caveat)*.
- The **original manual said boost and cut "shouldn't be used simultaneously"** — in practice they almost always are; the simultaneous use *is* the sound.

## 6. Concrete usage moves

dB amounts are **almost universally unstated** in the practical sources — engineers describe the *frequency + direction*; gain is "to taste." Where a dB number exists it is noted. **Frequencies below 200 Hz are not on the MEQ-5** (lowest boost AND lowest dip = 200 Hz), so any "100 Hz" recipe is loose language / a different unit in the chain.

| Source | Move | dB | Confidence |
|---|---|---|---|
| **Bass — forward + clarity** (UA's own) | boost **1 kHz** + dip **300 Hz** | to taste | high (UA) |
| **Vocal — warmth** (M. Mozart) | broad boost **200–500 Hz** (up to 700; never below 200) | small | high |
| **Vocal — presence** | high-mid PEAK **1.5–5 kHz** | to taste | med |
| **Snare — crack / pop** | boost **1.5–3 kHz** | to taste | med |
| **Lo-fi clicky snare** (MusicRadar) | **+700 Hz**, big dip **500 Hz**, **+3 kHz** | to taste | high |
| **Heavy rhythm gtr — balance** | boost **300 Hz** + cut **500 Hz** | to taste | med (blog) |
| **Guitar bus — de-mud** | broad cut **300–500 Hz** | to taste | med |
| **Mix bus — body** (M. Mozart) | sweep boost **200–700 Hz** to find what the mix lacks | **+2 to +3 dB max** | high |
| **Mix bus — energy** (M. Mozart) | boost **1.5k–7k** | small | high |

- **Drums / drum bus:** good for "shaping low-mids, cutting overtones, pushing upper mids without harshness" — body via LOW PEAK, snap/presence via HIGH PEAK, boxiness out via the DIP. Pulse Techniques lists snares and toms among recommended sources. Jack Douglas reportedly called the MEQ-5 his go-to "for guitars of any type" *(widely repeated in gear copy, not verified to a primary interview)*.
- **Mix-bus positioning:** reviewers frame it more as a **group/bus and instrument sculptor** than a primary mastering EQ — *"happy with your mixbus but need more sculpting on groups? The MEQ may just be the ticket"* (AudioScape).

## 7. UAD / UADx specifics

- **The Pultec Passive EQ Collection** bundles three plugins — **EQP-1A, MEQ-5, HLF-3C** — marketed as "the world's only *authentic* emulations." UA models **the entire electronic path — tube amplifiers and transformers — for colorful, highly-musical distortion** plus the "unique filter interactions." *(CONFIRMED — verdict 4: collection membership, native/iLok, control mirroring.)*
- **Native (UADx):** runs natively on **macOS and Windows** (AAX / AU / VST3), or accelerated on Apollo / UAD-2 DSP. The **native build became available July 12, 2022** via UAD Spark (M1 support; Windows native to follow). A purchase grants both native + DSP licenses.
- **Authorization:** an **iLok account is required** to manage native licenses; an **iLok USB dongle is optional (not required).** 3 activations per license; 14-day demo. *(DSP/Apollo versions authorize via UA hardware.)*
- **Added control — Output / Bypass-Gain.** The modeled (non-Legacy) plugin adds an **output gain control not on the hardware** — the UA manual describes a dual-purpose **Bypass/Gain knob, ±12 dB output gain**, fully counter-clockwise = bypass. *(Confirmed for the Collection generally; the per-MEQ-5 Output is strongly implied because UA flags it as **absent** on the EQP-1A **Legacy** plugin, but not separately quoted from a primary MEQ-5 spec — the official manual returned HTTP 403 this pass, so treat the exact MEQ-5 Output spec as strongly-implied, **unverified verbatim**.)*
- **No Headroom / no Mix (parallel) control** is mentioned for the MEQ-5 in any source → **absent/unstated**; don't assume EQP-1A-style extra knobs exist.
- **Legacy vs modeled fork (matters for tone).** The old **Legacy** plugins (built for the UAD-1) **did NOT model the transformer/tube distortion** — cleaner, lower-DSP. The modeled Collection adds that nonlinearity so it "breathes." **Presets are NOT cross-compatible** between Legacy and modeled versions. Title inventory: UADx native = "Pultec MEQ-5 EQ"; UAD-2 DSP = "Pultec MEQ-5" / "Pultec-Pro Legacy."
- **Plugin parameter ranges undocumented.** UA's manual publishes the frequencies and the ±12 dB output gain but **omits the per-section dB ranges** — those are inferred to match the hardware (0–10 / 0–10 / 0–8 dB). The UA manual is the source to retrieve for the definitive plugin control list; it returned **HTTP 403** to every fetcher in this research pass.

> **UA build / headless caveat (general — verify against Part A's render results).** As a general UA pattern, there are commonly two installed bundles: a **UADx native VST3** (`uaudio_*.vst3`) that *processes audio headless offline*, and a **"UAD …" `.component` / `.vst3` twin** that is **passthrough offline** (it expects the UA host/DSP and self-bypasses without a GUI). For a headless render, load the **`uaudio_*.vst3` build**, never the `UAD ….component` twin — and **verify it actually renders** (measure detail, not just `changed:true`). This is the documented behavior for other UADx plugins in this repo *(e.g. the `uaudio_*` builds for Helios, Fairchild, Hitsville)*; **confirm it specifically for the MEQ-5 in Part A** rather than assuming. Likely **iLok-account-gated** like the rest of the Collection.

## 8. Pitfalls & gotchas

- **High Peak is +8 dB, not +10/+12.** The most common spec error. Only LOW PEAK and DIP reach 10 dB; nothing reaches 12.
- **The 0–10 dial is a magnitude scale, not dB.** Don't read knob "5" as "5 dB."
- **No frequency below 200 Hz, no frequency above 7 kHz (DIP) / 5 kHz (boosts).** Recipes citing "100 Hz on the MEQ-5" are imprecise or describe a different box. The MEQ-5 cannot touch sub-200 Hz or above 5 kHz on its boost bands.
- **No Q/bandwidth control and no published Q numbers.** "Broad boosts, narrower dip" is reviewer consensus; **proportional-Q is inferred, not cited.** Don't quote a Q figure.
- **Boost+dip overlap is two bands, not one shared control** — pick a frequency present on *both* a Peak band and the DIP. UA's "can't overlap" blog line is applications shorthand, not a circuit fact.
- **Colour lives in the make-up amp, and rises with drive (2nd harmonic).** Pushing input level is how you get the "fatten"; the EQ curves themselves are clean. The MEQ-5's specific harmonic-vs-drive curve is **unstated** — measure it (Part A), don't assume the EQP-1A's plot transfers.
- **Legacy ≠ modeled:** the Legacy plugin omits the transformer/tube colour and won't sound like the hardware; presets don't carry across.
- **Headless render:** load the `uaudio_*.vst3` build and verify it renders (the `UAD ….component` twin likely passes audio through offline — confirm in Part A).
- **Plugin Output knob (±12 dB, CCW = bypass) is a plugin-only convenience** absent on the hardware; the hardware has no output trim.
- **Single-sourced / uncertain points to treat with caution:** 1955 release year (Vintage Digital only); single-ended make-up-amp topology (AudioScape only); whether the line amp is shared with the EQH-2 (conflicting); the Jack Douglas guitar quote (gear-copy repetition).

## 9. Sources

- Pulse Techniques (manufacturer) — MEQ-5 spec: https://pulsetechniques.com/products/tube-equalizers/meq-5/
- Pulse Techniques — Compare (EQP-1A / MEQ-5 / EQH-2 control tables): https://pulsetechniques.com/compare/
- Universal Audio — Pultec Passive EQ Collection (product): https://www.uaudio.com/products/pultec-passive-eq-collection
- Universal Audio — Pultec Collection Tips & Tricks: https://www.uaudio.com/blogs/ua/pultec-collection-tips-and-tricks
- Universal Audio — Pultec Passive EQ Collection Manual *(HTTP 403 this pass; the definitive plugin control/range source to retry)*: https://help.uaudio.com/hc/en-us/articles/7183176266260-Pultec-Passive-EQ-Collection-Manual
- Universal Audio — Spark / native launch press release (2022): https://www.uaudio.com/press/releases/2022/spark-pultec-addition/
- Universal Audio — Pultec Passive EQ Collection press: https://www.uaudio.com/blogs/press/pultec-passive-eq-collection
- AudioScape — A History of the Pultec Passive Equalizer: https://www.audio-scape.com/news/2025/5/30/a-history-of-the-pultec-passive-equalizer
- AudioScape — Do You Need An MEQ Equalizer?: https://www.audio-scape.com/news/why-you-need-an-meq-equalizer
- Vintage Digital — The Superb Pultec MEQ-5 (vintage spec sheet): https://www.vintagedigital.com.au/pultec-meq-5/
- Sound on Sound — Pulse Techniques EQP-1A (measured distortion / circuit teardown): https://www.soundonsound.com/reviews/pulse-techniques-eqp-1a
- MusicRadar — How to get the most out of the EQP-1A and MEQ-5: https://www.musicradar.com/how-to/how-to-get-the-most-out-of-the-classic-pultec-eqp-1a-and-meq-5
- Mixed by Marc Mozart — Classic EQs and how to use them: https://mixedbymarcmozart.com/2015/04/02/classic-eqs-and-how-to-use-them-in-your-mix/
- Kiive Audio — What's So Special About the Pultec EQ?: https://www.kiiveaudio.com/blogs/learn/what-s-so-special-about-the-pultec-eq
- audiospectra.net — Pultec EQ Explained: https://audiospectra.net/pultec-eq/
- UltimatePreset — Understanding the Pultec Equalizer: https://www.ultimatepreset.com/pultec-equalizer-guide/
- Front End Audio — Pultec MEQ-5 (hardware dealer spec): https://www.frontendaudio.com/pultec-meq-5-midrange-equalizer/
- Vintage King — Pultec EQP-1A / HLF-3C (dealer specs): https://vintageking.com/pultec-eqp-1a-program-equalizer · https://vintageking.com/pultec-hlf-3c-passive-high-low-filter-10484-vintage
- illdigger — Trio de Pultec from scratch Pt.2, The MEQ-5 (DIY build / stepped-switch detail): https://illdigger.wordpress.com/2018/02/27/trio-de-pultec-from-scratch-pt-2-the-meq-5/
- Gearspace — UAD plugin differences (Legacy vs bought) / EQH-2 vs EQP-1A: https://gearspace.com/board/music-computers/1041429-uad-plugin-differences-legacy-vs-bought.html · https://gearspace.com/board/high-end/650820-how-does-pultec-eqh-2-compare-eqp-1a.html
- Production Expert — Pultec plugin coverage: https://www.production-expert.com/production-expert-1/the-5-best-pultec-plugins-in-2022