# KIT BB N105 V2 — field guide: the Blackbird Neve 8078 channel, warm + tight, headless

How to drive the **KIT Plugins BB N105 V2** (`KIT BB N105 V2.vst3`) — a sampled emulation of a **Neve
8078** console channel (the **31105** input/EQ module) from Studio A at **Blackbird Studio**, Nashville.
This is the **warm, thick, Neve** counterpart to the forward/punchy API console ([[api-vision-channel-strip]])
and the warm Neve/tape master stage ([[studer-a800]]). **Part A** is *measured on this rig* (the real
Pedalboard param surface + isolation numbers from our own renders); **Part B** is a *web-research
synthesis* (cited, adversarially verified). The skill [[bb-n105-channel-strip]] is the measured workflow.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the crest that
> proves "punch." Verify with `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` /
> `check-clipping`. Mic-mode drive raises level *and* true-peak — re-measure after every change, A/B
> loudness-matched.

---

## TL;DR (the headline, measured)

1. **It RENDERS headless here — proven, not assumed.** `KIT BB N105 V2.vst3` loads via Pedalboard, is
   iLok **machine-authorized** on this Mac, and **responds to its params** (push HF +12 dB → output
   differs from default by 3.06 — not passthrough). Unlike the UAD `.component` trap, this KIT/iLok
   plugin actually processes. **But loads≠renders is the standing rule — re-screen with [[vst-verify]] on
   any other host** (iLok Cloud / unlicensed nodes will demo-silent; see §B7).
2. **The Neve color is MIC-MODE ONLY.** In **Line** mode (the default, and the obvious bus insert),
   `pre_amp_sensitivity` and `pre_amp_saturation` are **inert — byte-identical at every setting**. Switch
   `pre_amp_mode="Mic"` to get the transformer/preamp drive: sensitivity adds real gain (**−70 = max,
   ~+16 dB hotter than −15**) and a **gentle** saturation (≤~1.4 % THD, odd-harmonic) that grows with drive.
3. **Mic drive = the Neve "tighten lows + add sheen" move.** On the real drum bus it **trimmed sub
   (−2 to −3 dB), added air (+2 dB), and raised crest (23.6 → 24.5)** — it does *not* squash transients.
   Warmth from the transformer, not from an EQ boost (matches the house **warm + tight** preference).
4. **No Auto-Gain in the host.** The GUI Auto-Gain / Continuous / Master-Buss / Oversampling are **not
   exposed as params** — only 23 controls are automatable (preamp/EQ/filters/phase/eq/output/analog).
   Driving Mic sensitivity gets loud → compensate by hand with `output_gain` (measured exactly linear).
5. **Every param is an enum.** Numeric gains accept a **float** (coerced to the nearest 0.1 dB step), but
   **frequencies / modes / switches are string enums** `apply-vst-chain`'s float dict can't set → use the
   **[[vst-preset]]** harness.

---

# Part A — measured on this rig

Probe: `KIT BB N105 V2.vst3` via Pedalboard 0.9.23, processing `projects/watercolors/mix/bus_warm_pre_dry.wav`
(a measured-balanced, dry drum bus) plus deterministic noise/sine for isolation. Spectral comparisons are
peak-normalized so only **shape / crest** is judged.

### The real parameter surface (Pedalboard-exposed — authoritative for this build)

**23 params, all enum-valued.** Default state: `eq="EQ On"`, `pre_amp_mode="Line"`, `pre_amp_saturation=False`,
all EQ bands `OFF`/0 dB, `analog=True` (hum L1), `output_gain=0`, `bypass=False`.

| Param | Values *(default)* | Role |
|---|---|---|
| `pre_amp_mode` | `Line` · `Mic` *(Line)* | input stage — **Mic = where the drive/saturation lives** |
| `pre_amp_sensitivity` | −70 … −15 dB, 0.1 step *(−15)* | Mic gain/drive (**−70 = MAX gain**, −15 = min). **Inert in Line.** |
| `pre_amp_saturation` | `True`/`False` *(False)* | transformer saturation on/off. **Inert in Line; gentle in Mic.** |
| `high_gain` / `high_frequency` / `high_mode` | ±15 dB / `OFF,15k,10k,6.8k,4.7k,3.3k` / `Shelf`·`Peak` | **HF band** (shelf or bell). **Tops at 15 kHz.** |
| `hi_mid_gain` / `hi_mid_frequency` / `hi_mid_hi_q` | ±15 dB / `OFF,1.5k…8.2k` (10) / `Hi-Q Off`·`Hi-Q On` | **HMF bell** (Hi-Q narrows) |
| `lo_mid_gain` / `lo_mid_frequency` / `lo_mid_hi_q` | ±15 dB / `OFF,220…1200 Hz` (10) / `Hi-Q Off`·`Hi-Q On` | **LMF bell** (Hi-Q narrows) |
| `low_gain` / `low_frequency` / `low_mode` | ±15 dB / `OFF,33,56,100,180,330 Hz` / `Shelf`·`Peak` | **LF band** (shelf or bell) |
| `hpf_frequency` | `OFF,27,47,82,150,270 Hz` *(OFF)* | high-pass corner (**top = 270 Hz**, settles the 240-vs-270 dispute) |
| `lpf_frequency` | `OFF,18k,12k,8.2k,5.6k,3.9k` *(OFF)* | low-pass corner |
| `phase` | `Normal`·`Reversed` | polarity flip (the `ph` button) |
| `eq` | `EQ On`·`EQ Off` *(EQ On)* | EQ in/out (the `eq` button) |
| `output_gain` | −40 … +20 dB *(0)* | output fader (**measured exactly linear**) |
| `analog` / `analog_level` | bool *(True)* / `1`·`2`·`3` *(1)* | analog hum (~60 Hz). **Negligible offline — see below.** |
| `bypass` | `False`/`True` | true bypass |

> **Hi-Q is mids-only.** There is **no `high_hi_q`** — only `hi_mid_hi_q` / `lo_mid_hi_q`. The GUI "hi-q"
> button sitting near the HF knob actually belongs to the **HMF** band (matches the real 31105: Hi-Q is a
> mid-band feature). **Not host-exposed:** Auto-Gain, Continuous, Master-Buss, Oversampling, fader-cap colour.
>
> **Setting params:** numeric gains (`*_gain`, `pre_amp_sensitivity`, `output_gain`) accept a **float**
> (pedalboard rounds to the 0.1 step) — `apply-vst-chain`'s float dict can reach those. **Frequencies
> (`"56 Hz"`,`"15 kHz"`), modes (`"Shelf"`/`"Peak"`/`"Mic"`), Hi-Q, phase, eq, saturation are STRING/bool
> enums** → set via [[vst-preset]] (`apply_vst_preset.py`).

### Render proof + console color at unity (Line, all bands flat)

| | crest | centroid | note |
|---|---|---|---|
| dry (bypass) | 23.6 | 3128 | source |
| default flat (Line, eq on, hum L1) | 23.6 | 3128/3373¹ | **near-transparent** at unity |
| push HF +12 @10k | — | 12007→13904 | **responds to params → RENDERS ✓** (Δ=3.06 vs default) |

¹ full-bus centroid was 3373 vs dry 3128 with the default-flat path (≈ within measurement noise on this
material); on deterministic noise the default-vs-bypass centroid was 12002 vs 12007 — i.e. **the strip is
clean at unity; the character is opt-in.**

### Preamp: Line is inert, Mic is the color (1 kHz sine, THD proxy)

| config | THD (in 0.25) | THD (in 0.9) | THD (in 6.0) | note |
|---|---|---|---|---|
| Line clean / SAT −15 / SAT −70 | 0.00 % | 0.00 % | 0.43 % | **all three identical — Line preamp is inert** (the 0.43 % at hot input is the output stage, same with sat off) |
| Mic clean | 0.02 % | 0.23 % | 1.37 % | Mic transformer is *always* mildly non-linear when driven |
| Mic SAT, sens −45 | 0.23 % | 0.43 % | 0.43 % | saturation engaged |
| Mic SAT, sens −70 | 0.43 % | 0.43 % | 0.43 % | max drive — still **gentle** (a warmer, not a fuzz box) |

**Mic sensitivity adds gain:** at a −12 dBFS sine, peak went −10.3 (sens −15) → +3.3 (−45) → +6.4 (−70):
~16 dB span. Per Part B the harmonics are **odd-order** (Neve). **Line mode: skip the preamp section entirely.**

### EQ / filter isolation (peak-normalized noise, Δ band-energy vs bypass)

| move | sub | low | lomid | mid | hi | air | read |
|---|---|---|---|---|---|---|---|
| LF **shelf** +12 @100 | +13.7 | +12.0 | +4.2 | — | — | — | broad low shelf |
| LF **peak** +12 @100 | +9.2 | +12.0 | +4.8 | — | — | — | tighter (bell) |
| HF shelf +12 @10k | −15 | −14 | −14 | −6.9 | — | +2.4 | air shelf (centroid 12007→13904) |
| HMF +12 @3.3k **Hi-Q Off** | −7.2 | −5.1 | −2.8 | +5.1 | +5.5 | −2.6 | wide presence bell |
| HMF +12 @3.3k **Hi-Q On** | −5.4 | −3.6 | −2.8 | +4.6 | +5.4 | −2.6 | **narrower** (Hi-Q tightens) |
| LMF −12 @470 | — | −5.0 | **−11.4** | −4.3 | — | — | de-box cut |
| HPF @270 | **−22.2** | −11.3 | ≈0 | — | — | — | high-pass |
| LPF @3.9k | — | — | — | — | −2.9 | **−17.9** | low-pass |

Every band does exactly what it's labelled. **Filter slope (measured):** corner sits at ~**−2 dB**, then
~6–11 dB drop in the first octave past it, steepening beyond — consistent with the 80-series **~18 dB/oct**
family spec (not brick-wall, not gentle 6 dB/oct).

### analog hum (silent / −60 dBFS input)

Broadband floor **unchanged** across `analog` Off / On-L1 / On-L3 (−63 dB on a −60 dBFS sine). **The hum
is negligible in an offline render** — treat it as cosmetic; leave it off for clean stems.

### Real dry drum bus → the warm-tight recipe (full bus, stemmy meters)

| | LUFS-I | true-peak | crest | centroid | tilt dB/oct | low ratio | low-mid ratio |
|---|---|---|---|---|---|---|---|
| dry | −25.4 | −5.99 | 23.6 | 3128 | −2.26 | 0.542 | 0.378 |
| **n105-warm** (Mic drive, HF off) | −21.3 | −0.96 | **24.5** | 3539 (+411) | −1.90 | **0.588** | **0.327** |
| n105 + air variant (HF +2 @15k) | — | — | 24.8 | 3973 (+845) | −1.57 | — | — |

The warm recipe (Mic sat sens −42 + 47 Hz HPF + 56 Hz LF shelf +2 + 470 Hz −2 de-box, HF **off**,
output −13) **raised low weight, de-boxed the low-mids, tightened the sub (25 Hz −7 dB), nudged crest UP,
and kept the tilt warm** — the transformer (not an EQ air boost) supplies the only top lift (centroid +411,
not +845). → preset `bb-n105-warm-drum-bus.json`. The `+air` numbers show the cost of reaching for the
15 kHz shelf if you want brightness instead.

### Preset (`presets/vst/`)

- **`bb-n105-warm-drum-bus.json`** — the warm-tight Neve drum bus above. Mic-mode transformer warmth +
  weight + de-box + HPF, HF EQ off. Apply with the harness; for a brighter "Neve air" version add
  `high_frequency="15 kHz"`, `high_gain=2.0`.

---

# Part B — how the console works (web-research synthesis, cited, adversarially verified)

## 1. What it is / lineage

The **KIT Plugins BB N105** (free **V2** update) emulates **one channel of John McBride's Neve 8078 console**
in **Studio A at Blackbird Studio**, Nashville — specifically the **Neve 31105** input/EQ module (the "**105**"
in the name). Built by **KIT Plugins** (Nashville; founder Matthew Kleinman) with McBride; **"BB" = Blackbird,
"N" = Neve.** The 8078 was originally built for the L.A. Motown studio, later owned by Donald Fagen. *(HIGH
confidence — SoS, Mixonline, Everything Recording all name the 31105.)*

- **31105 ≠ 1073.** The 31105 is an 80-series Class A/B mic-pre + **four-band parametric** EQ + HPF/LPF — a
  bigger tone circuit than the 3-band 1073. **KIT's separate BB N73 *is* the 1073** (and BB N54 = Neve 2254
  comp). **Don't conflate them.** Tape Op calls the EQ a "1081" — the **31105 shares the 1081/1083/1095/1093
  4-band EQ family**, so the surfaces are spec-twins, but the modeled *module* is the 31105.
- **DSP is KIT's own in-house "Full Range Modeling (FRM)" sampling** (10 Hz–96 kHz), captured through the
  desk to **Master Bus B** into Burl A/D. **No third-party engine** (not Brainworx/United/Acustica); the
  low-level toolkit is undisclosed. *(MEDIUM→HIGH.)*
- **V2 = UI/workflow, not a re-modeled core** *(LOW confidence it changed the audio)*: resizable 3D GUI,
  numeric gain readout (0.1 dB), **Auto-Gain**, optional **Continuous** input-gain (V1 was stepped),
  selectable **oversampling** (4×/8×/16×, GUI-labelled Low/Med/High), new presets, fader-cap colour.
- Formats AAX/VST3/AU; iLok auth (see §7). *(Sampled channel "Channel 21" is **unverified** — don't assert it.)*

## 2. Signal flow & controls (hardware/GUI view)

Input (**Mic/Line**) → preamp **saturation** → 4-band EQ (HF/HMF/LMF/LF, `eq` in/out, `ph` polarity) →
combined **HPF/LPF** filter → **Output** fader; plus **Analog Hum** (on/off + level 1/2/3). The V2 top bar
adds **Auto-Gain**, **Continuous**, oversampling, resize/Options.

> **Part A correction:** in this build the **Auto-Gain, Continuous, Master-Buss and Oversampling are GUI-only
> — not host-automatable.** The marketing **"Master Buss" control is API-derived** (an API master-buss amp
> from Blackbird's API Legacy console), *not* Neve — and it isn't exposed to Pedalboard here anyway.

## 3. The EQ surface (matches Part A's probe exactly)

Four bands + combined HPF/LPF, all **±15 dB**, tracking the 31105/1081 hardware:

| Band | Type | Frequencies | Hi-Q |
|---|---|---|---|
| **HF** | shelf↔peak | 3.3 / 4.7 / 6.8 / 10 / **15 kHz** (top) | — |
| **HMF** | bell | 1.5 / 1.8 / 2.2 / 2.7 / 3.3 / 3.9 / 4.7 / 5.6 / 6.8 / 8.2 kHz | **yes** (narrows + interacts with gain) |
| **LMF** | bell | 220 / 270 / 330 / 390 / 470 / 560 / 680 / 820 / 1000 / 1200 Hz | **yes** |
| **LF** | shelf↔peak | 33 / 56 / 100 / 180 / 330 Hz | — |
| **HPF** | high-pass | 27 / 47 / 82 / 150 / **270 Hz** | — |
| **LPF** | low-pass | 3.9 / 5.6 / 8.2 / 12 / 18 kHz | — |

*(Reviews split 240 vs 270 Hz for the HPF top — **Part A settles it: 270 Hz**. The "1081 EQ" claim is the
spec-twin family, the module is the 31105. Numeric Hi-Q values + exact slope aren't published — Part A
measured slope ≈ 18 dB/oct family.)*

## 4. The "Neve" character

Color = **transformer/preamp saturation + the rounded 80-series tone curves**, not just EQ. The drive is
strongest in **Mic mode** and adds the classic Neve **odd-order** thickness/forward mid (SoS). Because KIT
sampled the whole path (input → Master Bus B → A/D), the model carries the channel's cumulative non-linearity,
not an ideal EQ. **Driving it:** push input gain (Mic mode) → harmonics build, lows thicken, upper-mids get
present/grit; the GUI **Auto-Gain** is the intended honest-audition tool (level-matches drive) — **but it's
GUI-only here, so in the pipeline compensate with `output_gain`.** *(Part A: drive is gentle, ≤~1.4 % THD,
trims sub + adds sheen + raises crest.)*

## 5. Using it on drums (Neve = warm/thick; API = punchy; SSL = clean glue)

Starting points using the *exact* available steps:

- **Kick:** LF shelf +2–4 @ **56/100** (weight); LMF cut **330–470** (de-box); HMF **2.7–3.9 k** for beater
  click; HPF **27**; a touch of Mic drive thickens.
- **Snare:** LF bell (toggle off shelf) **180–330** body; LMF cut **470–680** if honky; HMF **2.2–3.3 k**
  crack; HF shelf **6.8–10 k** snap; Hi-Q on mids for surgical pings.
- **Overheads:** HPF **150–270** to lose kick spill; HF shelf **10–15 k** sheen (**watch §6**); little/no drive.
- **Room:** lean in — Mic drive for grit, LMF push **220–470** body, light HF shelf.
- **Drum bus:** small moves — LF shelf **+1–2 @ 56–100**, modest Mic saturation for glue. For the house
  **warm + tight** sound, use the N105 as **tone + saturation** (reach for [[api-vision-channel-strip]] or
  [[drum-punch]] for transient punch). → preset `bb-n105-warm-drum-bus.json`.

## 6. Harshness — why & what to move

- **Upper-mid forwardness from drive** (odd harmonics into **2–5 kHz**): back off Mic drive / switch to
  Line before EQ.
- **HMF over-boost** at **2.7/3.3/3.9 k** reads brittle on cymbals/snare → **cut** there (Hi-Q narrow),
  don't dull the whole top.
- **HF shelf brittleness** at **10–15 k** raises edge/hiss → smaller shelf, or move to a **6.8 k bell**.
- **LPF @ 12/8.2 k** as a fizz safety net. (Mirrors the house hi-hat note: lift air but de-harsh 5–7 k.)

## 7. Licensing & headless/offline rendering

- **iLok / PACE.** Supports **iLok Cloud, iLok USB (gen 2/3), or Machine activation**; **2 activations** per
  license; perpetual (~$99.99, no subscription); "**no dongle required**" (SoS). *(HIGH.)*
- **Headless = conditional.** Offline rendering works **only** via an offline-capable activation — **Machine
  activation or USB dongle**. **iLok Cloud needs continuous internet** → unusable on air-gapped nodes.
- **Local ground truth:** on **this Mac** it's machine-licensed and **Part A proved it renders headless** and
  responds to params. **Elsewhere, re-verify** — an unlicensed iLok plugin instantiates in **demo/silent**
  mode (loads≠renders), and a PACE wrapper bug has been documented to **hang headless plugin scanners**.
  Pin versions; persist `dump_state`; screen with [[vst-verify]]. >2 render nodes exceed the 2-activation cap.

## 8. Pitfalls & gotchas

- **N105 ≠ N73** (31105 vs 1073). **Master-Buss is API**, not Neve (and GUI-only here). **HPF top = 270 Hz.**
- **Line preamp is inert** — switch to **Mic** for any drive/saturation; compensate level with `output_gain`
  (no host Auto-Gain).
- **HF EQ tops at 15 kHz** (12 kHz is LPF/LMF only). **Hi-Q is mids-only.** **analog hum negligible offline.**
- **All params enum** — float for gains, **strings for freq/mode/switch** → [[vst-preset]].
- **Loudness-match before any A/B** — Mic drive + boosts raise level.
- **Unverified upstream** (no public V2 manual): even-order harmonic content, exact Hi-Q Q values, the
  Low/Med/High→4×/8×/16× oversampling map, whether V2 changed the audio model, the sampled channel number.

> Pure-DSP approximation (no VST): odd-harmonic Neve warmth ≈ `[L] saturate-loop` (tape/tanh); the 4-band
> 31105 grid ≈ `[L] apply-eq` shelves/bells; tighten ≈ HPF in `apply-eq` + `[L] shape-bands`; prove warmth
> kept punch (crest/PLR) with `[L] measure-microdynamics`.

---

## Sources

KIT Plugins product page (kitplugins.com/products/kit-bb-n105) · Sound on Sound (KIT BB N105 review) ·
MusicTech (BB N105 V2 review) · Mix (BB N105 V2 review) · Everything Recording (BB N105 review) · Tape Op
(BB N105 V2) · Vintage King (Neve 31105 / 1081 spec) · AMS Neve 1073 & 1084 (official, 18 dB/oct filter
spec) · help.ilok.com (Cloud vs Machine/USB offline) · Steinberg forum (PACE headless-scan hang). Plus
**our own param-enumeration / isolation / sweep / shootout measurements** (Part A) on `KIT BB N105 V2.vst3`.
