# SSL Native Channel Strip 2 — field guide: the clean SSL console strip, headless

How to drive the **SSL Native Channel Strip 2** (`/Library/Audio/Plug-Ins/VST3/SSL Native Channel Strip 2.vst3`)
— SSL's software channel strip modelled on the **XL 9000 K SuperAnalogue** console. It's the **clean / clinical**
member of the channel-strip family: the *glue-and-precision* counterpart to the warm Neve ([[studer-a800]] /
[[kit-bb-n105]]) and the punchy/forward API ([[api-vision-channel-strip]] / [[kit-bb-a5]]). **Part A** is *measured
on this rig* (the real Pedalboard param surface + our renders); **Part B** is a *web-research synthesis* (cited).
The skill [[ssl-native-channel-strip-2]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the crest that proves
> "punch." Verify with `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` / `check-clipping`.
> SSL is a clean console — its color is the EQ + comp, **not** drive, so **do not gain-stage into it** (unlike the
> API/tape units). Re-measure after every change, A/B loudness-matched.

---

## TL;DR (the headline, measured)

1. **Near-perfect passthrough at unity.** Strip in, every section at default → crest **24.91 → 24.91**, peak
   0.501 → 0.500. SSL is *transparent until you dial it*; the sound is the EQ/comp choices, not an always-on tone.
2. **EVERY param is a discrete enum in Pedalboard — the float-only `apply-vst-chain` dict can't drive this strip.**
   Numeric params (gains/thresholds/ratio/trims/Q/mix/width) accept a plain float via `setattr`, but the **string
   enums** (`eq_type` G/E, `lf_type`/`hf_type` Shelf/Bell, `compressor_peak` RMS/Peak, `compressor_fast_attack`,
   `gate_expander`, all routing/enable switches) and the **log-stepped frequencies** (`high_pass_filter_hz=40.0`
   → *"not in list"*) do **not**. **Use the `[[vst-preset]]` harness** (`apply_vst_preset.py`, `setattr` per param)
   or a `dump_state` blob — never `apply-vst-chain`'s `parameters`.
3. **The channel comp's NORMAL attack barely touches drums — FAST ATTACK is the working drum mode.** At 4:1 the
   non-fast (program/auto) attack grabbed only **~0.8–1.0 dB GR even at the lowest threshold** (it lets the
   transients straight through). Engage `compressor_fast_attack='In'` to actually compress drums (3 dB GR at
   thr −12). On this material fast attack + 0.1 s release **raised** crest (transient-emphasis), not squashed it —
   **measure GR + crest, don't assume.**
4. **E vs G EQ is real but SUBTLE.** Same +5 dB HF shelf @ 10 k: **G centroid 5224 Hz vs E 5098 Hz** (MCP) — **G a
   touch brighter / airier, E a touch warmer / fuller** in the upper-mids. Use **G** for broad bus tone, **E** for
   drums + surgical mid cuts (constant-Q at low gain).
5. **`lf_gain_db` is ±16.5 dB on this build, NOT the published ±20.** The measured Pedalboard surface caps the LF
   band at **−16.5 … +16.5** (the other three bands are ±20); a `lf_gain_db=20.0` is **off-grid** → `setattr`
   throws / the harness warns and leaves LF at default. Stay within ±16.5 (or reach for the GUI if you truly need
   ±20) — see Part A's LF-gain note.
6. **Meters own this** (Gemini hears mono): crest = punch/glue, correlation = tight, centroid/tilt = bright-vs-warm.

---

# Part A — measured on this rig

Probe: `SSL Native Channel Strip 2.vst3` (build **v2.9.8**, `com.SSL.SSLNativeChannelStrip2`) via Pedalboard,
processing `projects/drums-kit/mix/bus_70s_balanced.wav` (60 s dry, measured-balanced drum bus) — the same file
the [[api-vision-channel-strip]] doc used, so the two are directly comparable. Peak-normalized before measuring so
only **spectral shape / crest** is compared. It **renders headless** (no DAW, no GUI, no audio device; iLok
machine-authorized on this Mac).

### The real parameter surface (Pedalboard-exposed — authoritative, 51 params)

**Default flow: Input → FILTERS → EQ → DYNAMICS (comp ∥ gate) → Output.** `eq_in`, `dynamics_in`, `filters_in`
are all **In by default** (but at 0 gain / high threshold → no audible effect → the unity passthrough above).
**Every value below is a discrete enum** — the *type* column says whether a plain float is accepted via `setattr`.

| Param (Pedalboard name) | Type | Range *(default)* | Role |
|---|---|---|---|
| **`input_trim_db`** | float-grid | −20 … +20 dB, 0.1 step *(0)* | input gain stage |
| `polarity` | **str enum** | `Out` · `In` *(Out)* | phase invert (Ø) |
| `external_s_c` | **str enum** | `Out` · `In` *(Out)* | EXT external sidechain on/off |
| **`filters_in`** | **str enum** | `Out` · `In` *(In)* | FILTERS section in/out |
| `high_pass_filter_hz` | **log enum** | `OUT`, 20.0 … **500.0** Hz *(OUT)* | HPF cutoff (**18 dB/oct**). `OUT`=off. **Arbitrary floats throw** |
| `low_pass_filter_khz` | **log enum** | **3.00** … 22.0 kHz, `OUT` *(OUT)* | LPF cutoff (**12 dB/oct**). `OUT`=off |
| `filters_to_input` | **str enum** | `Out` · `In` *(In)* | filters at channel input vs adjacent-to-EQ |
| `filters_to_s_c` | **str enum** | `Out` · `In` *(Out)* | route filters into the **dynamics sidechain** |
| **`eq_in`** | **str enum** | `Out` · `In` *(In)* | EQ POWER |
| **`eq_type`** | **str enum** | **`G` · `E`** *(G)* | **the "E" button** — G-Series vs E-Series curves |
| `lf_type` | **str enum** | `Shelf` · `Bell` *(Shelf)* | LF band shape |
| `lf_frequency_hz` | log enum | 40 … 600 Hz *(185)* | LF freq |
| **`lf_gain_db`** | float-grid | **−16.5 … +16.5 dB** *(0)* | LF gain — **measured ±16.5, not ±20** (see note) |
| `lmf_frequency_khz` | log enum | 0.2 … 2.0 kHz *(0.8)* | LMF freq |
| `lmf_gain_db` | float-grid | −20 … +20 dB *(0)* | LMF gain |
| `lmf_q` | float-grid | 0.5 … 2.5 *(1.5)* | LMF Q |
| `hmf_freq_khz` | log enum | 0.6 … 7.0 kHz *(2.5)* | HMF freq |
| `hmf_gain_db` | float-grid | −20 … +20 dB *(0)* | HMF gain |
| `hmf_q` | float-grid | 0.5 … 2.5 *(1.5)* | HMF Q |
| `hf_type` | **str enum** | `Shelf` · `Bell` *(Shelf)* | HF band shape |
| `hf_freq_khz` | log enum | 1.5 … 22 kHz *(7.5)* | HF freq |
| `hf_gain_db` | float-grid | −20 … +20 dB *(0)* | HF gain |
| `eq_to_s_c` | **str enum** | `Out` · `In` *(Out)* | route EQ into the **dynamics sidechain** (key/de-ess) |
| **`dynamics_in`** | **str enum** | `Out` · `In` *(In)* | DYNAMICS POWER (comp + gate) |
| `compressor_peak` | **str enum** | `RMS` · `Peak` *(RMS)* | **detection + knee**: RMS = soft knee, Peak = hard knee |
| `compressor_fast_attack` | **str enum** | `Out` · `In` *(Out)* | **attack mode** (see crest map) |
| `compressor_ratio` | float-grid | 1.0 … **inf** *(6.0)* | ratio (∞ = limiting) |
| `compressor_threshold_db` | float-grid | −20 … +10 dB *(10)* | threshold (also drives auto make-up) |
| `compressor_release_s` | float-grid | 0.1 … 4.0 s *(0.1)* | release |
| `compressor_mix` | float-grid | 0 … 100 % *(100)* | dry/wet → parallel compression |
| `compressor_auto_make_up` | **str enum** | `False` · `True` *(True)* | auto make-up (no manual knob) |
| `compressor_auto_make_up_offset_db` | float-grid | −12 … +12 dB *(0)* | trim the auto make-up |
| `gate_expander` | **str enum** | `Gate` · `Exp` *(Gate)* | **EXPAND button**: gate (~40:1) vs expander (2:1) |
| `gate_attack` | **str enum** | `Regular` · `Fast Attack` *(Regular)* | gate attack (1.5 ms → 100 µs) |
| `gate_hold_s` | float-grid | 0.0 … **4.0** s *(0.25)* | hold (**max 4.0 s — measured**) |
| `gate_threshold_db` | float-grid | −30 … +10 dB *(10)* | gate open threshold (hysteresis) |
| `gate_range_db` | float-grid | 0 … 40 dB *(0)* | depth of attenuation (0 = gate off) |
| `gate_release_s` | float-grid | 0.1 … 4.0 s *(0.1)* | gate release |
| `dynamics_pre_eq` | **str enum** | `Out` · `In` *(Out)* | dynamics **before** EQ (default = after) |
| `s_c_listen` | **str enum** | `False` · `True` *(False)* | LISTEN S/C (audition the sidechain) |
| `fader_level_db` | float-grid | −∞ … +12 dB *(0)* | **VCA-modelled** channel fader |
| `output_trim_db` | float-grid | −20 … +20 dB *(0)* | **clean** output trim (use for loudness-match) |
| `width` | float-grid | 0 … 200 % *(100)* | M/S width: **0 = mono, 100 = normal, 200 = max** |
| `width_mode` | **str enum** | `Full` · `Low` · `High` *(Full)* | **frequency-selective width** (widen only highs / lows) |
| `width_frequency_hz` | log enum | 20 … 20000 Hz *(20)* | crossover for Low/High width mode |
| `pan` | enum | `L` … `C` … `R` *(C)* | pan (stereo only) |
| `legacy_cut` | **str enum** | `False` · `True` *(False)* | CUT (mute) |
| `legacy_solo` / `legacy_solo_safe` | str enum | *(False)* | solo / solo-safe |
| `bypass` | **str enum** | `False` · `True` *(False)* | master bypass |
| `groupsense` | float | (360 group/automation) | leave at default |

> **⚠️ The LF-gain discrepancy (measured vs documented).** This build's Pedalboard surface reports
> **`lf_gain_db` as ±16.5 dB** (ENUM with 331 steps, −16.5…+16.5) while the other three bands are ±20 dB. SSL's
> Channel Strip 2 user guide states **all four bands are ±20 dB**. We trust the **measured** surface for headless
> use — it's what the harness actually sets, and a `lf_gain_db=20.0` will be off-grid → `setattr` throws / the
> harness warns and leaves it at default. Cut/boost the LF within **±16.5** via the harness; reach for the GUI if
> you genuinely need the documented ±20.

### Console color at unity (everything default)

| | crest | rawpeak |
|---|---|---|
| dry (no plugin) | 24.91 | 0.501 |
| strip, all sections default (eq_in/dyn_in/filters_in In, 0 gain) | 24.91 | 0.500 |

**Transparent at unity** — the cleanest of the channel-strip family (cf. the API strip's +0.4 crest at unity, and
the Neve/tape units that color even idle). SSL = clean console; **the character is your moves, not the box.**

### Compressor: attack mode × detection → crest (the punch map)

Comp-only, EQ out, thresh −12, 4:1, release 0.10 s, **auto-makeup OFF**, peak-normalized. **Crest = punch proxy; dry = 24.91.**

| `compressor_peak` | normal attack (`fast_attack=Out`) | FAST attack (`fast_attack=In`) |
|---|---|---|
| **RMS** (soft knee) | 26.60  *(GR ≈ 0.8 dB)* | **29.94**  *(GR ≈ 3.0 dB)* |
| **Peak** (hard knee) | 26.99  *(GR ≈ 0.8 dB)* | **30.16**  *(GR ≈ 3.0 dB)* |

Two measured facts that overturn the textbook:
- **Normal attack can't grab a drum bus.** A threshold sweep at 4:1 (thr −12 → −20) moved GR only **0.8 → 1.0 dB**
  and crest 26.6 → 27.6 — the program/auto attack passes the transients almost entirely. **To compress drums,
  engage FAST ATTACK** (3 dB GR at thr −12). For *transparent leveling/glue at tiny GR*, that transient-preserving
  normal attack is exactly the tool.
- **Fast attack RAISED crest here** (≈30 vs ≈27), it did not squash it — fast attack + fast (0.1 s) release ducks
  the sustain between hits and recovers, acting as transient-emphasis on this material. **Peak vs RMS differed only
  marginally** (~0.2 crest, slightly more GR/aggression on Peak). **Measure GR + crest for your material.**

### EQ E vs G (the signature question) — MCP measure-spectrum

Same move, comp out, peak-normalized. **HF SHELF +5 dB @ 10 kHz:**

| | spectral centroid (Hz) | tilt (dB/oct) | read |
|---|---|---|---|
| dry | 3206 *(inline)* / — | — | source |
| **G**-Series | **5224** | −2.14 | slightly **brighter / airier** top |
| **E**-Series | **5098** | −2.08 | slightly **warmer / fuller** upper-mid |

**HMF BELL +8 dB @ 2.5 kHz** (inline centroid): **G 3456 vs E 3345** — same direction (G more focused/forward, E
broader/gentler). The difference is **subtle but consistent and measurable**, matching the documented behavior:
G-Series shelves overshoot near the corner (more aggressive) and its mid bells are proportional-Q; E removes the
overshoot and holds the mid bandwidth constant across gain (so high-Q surgical cuts stay usable at low gain).

### The validated drum-bus preset

`presets/vst/ssl-native-cs2-drum-bus.json` — applied through the real `[[vst-preset]]` harness (every `setattr`
took, no warnings): HPF 35 Hz, **E**-EQ (LF +3 bell @ 90, LMF −3 @ 450 de-box, HF +2.5 shelf @ 10 k air), comp
**FAST ATTACK** 4:1 thr −8 RMS auto-makeup, gate off. **MCP measure-loudness: crest 24.91 → 28.96 dB, true-peak
−0.99 dBTP** → adds punch + console tone, not just level. (Gentler mix-bus variant documented in the preset notes:
ratio 2:1, normal attack, ~1–2 dB GR, ±2 dB EQ.)

### Headless / render verification

- `[L] list-vst-plugins {name_contains:"channel strip"}` → VST3 at `/Library/Audio/Plug-Ins/VST3/SSL Native
  Channel Strip 2.vst3` (+ AU twin in `/Components/`, macOS-only). **Use the VST3.**
- Loads + **renders** headless via Pedalboard (`is_effect:true`, default params already alter the signal — a true
  render, not passthrough). It is **iLok/PACE** — authorized on *this* machine; **re-verify on any other node**
  (iLok is a render-farm landmine — see §9 Part B).
- Pin a patch with `dump_state=true` and re-apply via `state_path`; the `.vstpreset`/`.fxp` loader is unreliable.

---

# Part B — how the console works (web-research synthesis, cited)

## 1. What it is / heritage / version 2 / SSL 360

SSL Native Channel Strip 2 is Solid State Logic's software channel strip, **digitally modelled on the EQ and
Dynamics curves of the SSL XL 9000 K SuperAnalogue console** (the 9000-series successor to the classic 4000) — a
complete channel: input trim/polarity → fixed-slope filters → 4-band EQ → compressor/limiter ∥ gate/expander →
output (VCA fader, M/S width, pan, trim, solo/cut). US$149 perpetual (or Complete Access subscription).

- **The E/G switch is NOT a 4000-console emulation.** It toggles two characteristics of the *same* XL 9000K EQ
  model. SSL's dedicated 4000 E / 4000 G plugins are *separate* products — **don't** describe the E button as
  "switching to a 4000 desk."
- **Version 2 additions** (over the original Channel Strip): SSL's no-latency **anti-cramping** EQ DSP; a
  **VCA-modelled Fader Level** (−∞…+12 dB) in a new Output section; **Pan** and **M/S Width**; **Compressor MIX**
  (parallel); **HQ** 2× oversampling; DAW selected-track-follow + Solo/Cut sync; UC1-matched GUI; A/B compare;
  cross-platform presets; undo/redo + contextual Help.
- **SSL 360 ecosystem:** the **360 button** opens the **SSL 360 Plug-in Mixer** — a virtual SSL console
  aggregating every Channel Strip 2 / 4K B / Bus Compressor 2 instance, controllable from **UC1 / UF8 / UF1**
  hardware. In **Live / Studio One / REAPER (VST3)** it auto-follows the selected track and links Solo/Cut to the
  DAW. **SSL 360 does NOT need to run for the plugin to process audio** — only for the mixer/hardware (important
  for headless).

**SSL vs API vs Neve:** SSL = **clean / clinical / precise** (the glue + surgical EQ). API = fast/punchy/forward.
Neve/tape = warm/saturated. Reach for SSL when you want control and clarity, not added color.

## 2. Signal flow & routing

**Default order: `Input (Trim + Ø) → FILTERS → EQ → DYNAMICS → Output`** ("The default plug-in order is Filters >
EQ > Dynamics"). The three blocks (FILTERS / EQ / DYN) reorder via the routing arrows — **with one hard
constraint:** `EQ > DYNAMICS > FILTER` is **disallowed** (on the analog desk the filter sits directly after the EQ
unless "filter to input" is active → **filter and EQ stay adjacent**). DYN *can* move before EQ/filters.

- **Sidechain routing:** the **filters** (`filters_to_s_c`) and the **EQ** (`eq_to_s_c`) can each be diverted into
  the **dynamics detector** for frequency-conscious comp / de-essing. With both in the SC, the EQ precedes the
  filter. **EXT** (`external_s_c`) keys the detector from a DAW-routed external source (kick→bass ducking; pick the
  source in the DAW's plug-in sidechain header). **S/C LISTEN** (`s_c_listen`) solos the detector feed — turn it
  off before committing.
- Compressor and gate have **independent sidechains**. *(Uncertain: SSL documents EXT at the singular "dynamics
  sidechain" with a compressor-only example; whether one EXT source independently keys the gate too in this build
  isn't explicitly stated — verify in-plugin if it matters.)*

## 3. FILTERS

Two **fixed-slope**, sweepable-cutoff filters, first by default, traveling with the EQ (§2).

| Filter | Slope | Range | `OUT` = |
|---|---|---|---|
| High-Pass | **18 dB/oct (fixed)** | **20 Hz – 500 Hz** | disengaged (parked at extremity) |
| Low-Pass | **12 dB/oct (fixed)** | **3 kHz – 22 kHz** | disengaged |

Only the cutoff is variable (no slope selector). A common error conflates the two into "HP 20 Hz–3 kHz" — **wrong**:
3 kHz is the bottom of the **LP**, not the top of the HP. The small curve-icon switches **near** the filters are
the **EQ** LF/HF Shelf↔Bell toggles, *not* filter controls. Either filter can be routed to the dynamics sidechain.

## 4. EQ — 4-band parametric

| Band | Type | Frequency | Gain | Q |
|---|---|---|---|---|
| **HF** | Shelf → Bell | 1.5 k – 22 kHz | ±20 dB | shelf/bell, no Q |
| **HMF** | Bell (always) | 600 Hz – 7 kHz | ±20 dB | 2.5 – 0.5 |
| **LMF** | Bell (always) | 200 Hz – 2 kHz | ±20 dB | 2.5 – 0.5 |
| **LF** | Shelf → Bell | 40 Hz – 600 Hz | **±20 dB documented / ±16.5 measured** | shelf/bell, no Q |

- **HF & LF default to shelf, switch to bell** (per-band toggles). **HMF & LMF are always bell** with a Q knob.
- **The "E" button (global, default G):**
  - **Shelves:** G has overshoot/undershoot near the corner (the recognizable SSL flavor); **E removes it** + a
    gentler slope (cleaner). *(Measured: G slightly brighter than E for the same shelf — Part A.)*
  - **Mids:** G = bandwidth varies with gain (proportional-Q, sharpens on big moves); **E = constant bandwidth
    across gain** (high Q usable at low gain → surgical drum cuts). At max boost/cut E ≈ G.
  - Practical: **G** for broad/bus tone-shaping; **E** for drums + problem-frequency cuts. Re-touch mid Q after E↔G.
- **Anti-cramping** (v2): always-on, **zero-latency** correction of bell cramping near Nyquist (~15–20 kHz) — you
  do **not** need HQ for clean air-band moves. Separate from HQ (§8).

## 5. Compressor / limiter

Continuously-variable SSL channel comp (faster/grabbier than the SSL bus comp).

| Param | Range | Notes |
|---|---|---|
| Ratio | **1:1 – ∞:1** | ∞ = limiting; continuous (the stepped 2/4/10/X ratios belong to the **separate** Bus Comp) |
| Threshold | **−20 … +10 dB** | also drives **automatic make-up** — no manual makeup knob |
| Attack | **~3–30 ms auto/program** (FAST off) → **fixed 3 ms** (FAST on) | FAST off preserves transients; on = "smack" |
| Release | **0.1 – 4 s** | no AUTO on the channel comp |
| PEAK | RMS (soft knee) / Peak (hard knee) | **this is the knee switch** — no separate knee control |
| MIX | **0 – 100 % (def 100)** | parallel-compression blend |
| Metering | 5-LED yellow/red GR (marks 3/6/10/14/20) | left of the shared dyn meter |

*(Uncertain: a secondary "1 ms fast attack" figure circulates — trust SSL's published **3 ms**.)*

## 6. Gate / expander

Independent of the comp, runs simultaneously, own sidechain.

| Param | Range | Notes |
|---|---|---|
| EXPAND | Gate (~40:1) / Expander (2:1) | gate = steep; expander = gentle, breathing attenuation |
| Threshold | **−30 … +10 dB** | **hysteresis** (close threshold < open) → no chatter, natural decays |
| Range | **0 – 40 dB** | depth of close; **15–25 dB leaves natural bleed** (40 = sterile/choppy) |
| Hold | **0 – 4.0 s** *(measured max 4.0)* | bridges short dips before closing |
| Release | **0.1 – 4 s** | how fast it closes after Hold |
| Attack (FAST) | 1.5 ms → **100 µs** | engage Fast for steep drum edges |
| Metering | 5-LED green | right of the shared dyn meter |

Tune Range / Release / Hold as a **trio** — don't reflexively max the Range.

## 7. Channel / output

- **IN TRIM** ±20 dB (gain-stage in) · **Ø** polarity · **FADER LEVEL** −∞…+12 dB (VCA-modelled, the 360-mixer
  fader) · **OUT TRIM** ±20 dB (**clean** — use this for loudness-matched A/B, not the fader) · **WIDTH** 0–2 (M/S:
  0 mono, 1 normal, 2 widest; stereo only) · **`width_mode` Full/Low/High + crossover** (frequency-selective width
  — widen the highs while keeping lows mono; *measured feature*) · **PAN** L–C–R · **CUT** (mute) · **SOLO /
  SOLO SAFE** · **S/C LISTEN**.
- **Two output gains on purpose:** Fader (VCA, modelled) vs Out Trim (clean). **Loudness-match with OUT TRIM** so
  A/B is honest.

## 8. HQ / oversampling & A/B

- **HQ** = **2× oversampling** (fixed; the Bus Comp 2 offers 2×/4×) — less aliasing where the signal is distorted
  (the dynamics) + extra cramping relief, at higher CPU **and added latency**. **HQ ≠ anti-cramping** (the latter
  is always-on, zero-latency, EQ-only). Use HQ on a final render when the dynamics are driven hard.
- **A/B** toggles two full parameter snapshots (COPY X→Y to seed one from the other). Use it (not presets) for
  quick before/after; loudness-match with OUT TRIM first.

## 9. Headless / offline-render viability — licensing & risk (honest)

**Verdict: it CAN render headless and is verified doing so here — but it is iLok/PACE-gated, the real render-farm risk.**

- **Verified on this rig:** loads + renders via `apply-vst-chain` with no DAW/GUI/device; default params change the
  signal (true render, not passthrough); `dump_state` works. In the repo headless-safe inventory (`docs/vst/README.md`).
- **Paths:** VST3 `/Library/Audio/Plug-Ins/VST3/SSL Native Channel Strip 2.vst3` (use this); AU twin macOS-only.
  Formats VST3/AU/VST2/AAX, 64-bit; build here v2.9.8 (SSL current v2.9.11).
- **Licensing = iLok / PACE.** Free iLok account required; PACE License Support runtime must be installed +
  license activated **locally**. Activation is **machine activation (no dongle) OR a USB iLok — NOT iLok Cloud**
  for SSL plugins. Perpetual license = 2 activations.
- **SSL 360 need not be running** to process audio.
- **Render-farm landmine:** the plugin loads only if the license is activated **on that specific machine** with
  PACE installed — authorization does **not** travel with a disk image; **don't clone the iLok DB across nodes**.
  On a fresh node, install PACE + activate fresh, then re-verify headless. **Machine activation is the most
  reliable headless route** (works offline after the one-time online auth).
- **In this repo:** `apply-vst-chain` can only set *numeric* params and **can't** reach the SSL enums/bools (E/G,
  PEAK, EXPAND, Shelf/Bell, EXT, SC toggles, polarity, CUT, order arrows) → use the **`[[vst-preset]]`** harness or
  a `dump_state` blob. Always re-measure detail after applying ([[vst-verify]]).

## 10. Application recipes (concrete starting points — material-dependent)

Default chain Filter → EQ → DYN; set `dynamics_pre_eq='In'` to compress into your EQ boosts.

- **Drum bus / glue:** comp **4:1**, FAST off for transparent program glue at 2–4 dB GR *or* FAST on for 3–6 dB
  punch (measure crest); `compressor_mix` 40–60 % for parallel slam; **G**-EQ broad tone; route `filters_to_s_c`
  + HPF the detector so kick/bass don't over-trigger. (Our validated `ssl-native-cs2-drum-bus.json`: FAST, 4:1,
  thr −8, HPF 35, E-EQ → crest 24.9→28.96.)
- **Kick:** HPF ~30–50; LF shelf +3–6 @ 60–100; LMF −3/−4 @ 250–400 (de-box); HMF +2–4 @ 2–4 k (beater). **E**-EQ.
- **Snare:** HPF ~70–100; LMF +body @ 120–250; cut 400–800; HMF +crack @ 3–5 k; HF shelf @ 6–10 k. **Gate it:**
  EXPAND off, FAST attack on, threshold above the hat bleed, **Range −15…−25 dB** (not full), short Hold; for
  bleed, route `filters_to_s_c` to key off the snare (S/C Listen to tune, then off).
- **Overheads:** gentle HPF ~50–80; small box cut; HMF +5–7 k clarity; HF shelf pulled *down* if harsh. Prefer
  **EXPAND on (2:1)** over a hard gate to lower bleed naturally.
- **Vocals:** HPF ~100; LMF +250 body / −500 mud; HMF +4 k clarity; HF shelf +10 k air. **E**-EQ. Comp up to 8:1,
  FAST on, ~0.2 s. **De-ess:** `eq_to_s_c='In'`, boost the sibilant band in the EQ so the comp keys on it.
- **Bass:** HPF ~30–40; LF +90 weight; LMF/HMF +700 Hz–1 k definition; comp 4:1, **Peak on**, slow attack, fast
  release, 3–6 dB GR. Kick→bass duck: route the kick to the SC + enable **EXT**.
- **Mix bus:** comp **2:1**, FAST off, **2–4 dB GR max**; subtle **G**-EQ; `filters_to_s_c` HPF on the detector;
  **HQ** on for the final render; loudness-match with OUT TRIM.

*(Uncertain: the per-element numeric values are tutorial-derived starting points, not SSL-canonical.)*

## Pitfalls & gotchas

- **`apply-vst-chain` can't drive this strip** — every meaningful control is a string enum or log-stepped freq.
  Use the **`[[vst-preset]]`** harness / `dump_state`. (The float dict silently *can* set numeric gains, which is a
  trap — you'll think it worked while every enum stayed default.)
- **`high_pass_filter_hz` is log-stepped:** `35.0` is valid, `40.0` throws "not in list." Pick a value the plugin
  accepts; a miss makes the harness warn and leave the HPF at `OUT` (silently disabled).
- **LF gain ±16.5 measured, not ±20** — see Part A. A 20 dB LF value is off-grid.
- **Normal comp attack barely compresses drums** (~1 dB at min threshold). FAST ATTACK is the drum mode — and on
  drums it *raised* crest here. Measure GR + crest.
- **PEAK is the knee switch** (RMS soft / Peak hard), not a separate detector toggle alongside a knee control.
- **`EQ > DYN > FILTER` ordering is disallowed.** Filter and EQ stay adjacent unless filters → sidechain.
- **It colors only when dialed** — a quiet bus through it at unity is passthrough. Don't gain-stage into it for
  "tone"; SSL color = the EQ/comp choices.
- **iLok per-machine** — verify load+render on every new node; don't clone the iLok DB.
- **Loudness-match before any A/B** (OUT TRIM) — boosts/comp change level; "better" is often "louder."

## Decision table

| Goal | Filter | EQ (type) | Comp | Gate |
|---|---|---|---|---|
| Drum-bus glue | `filters_to_s_c` + HPF detector | G, broad | 4:1, FAST off, 2–4 dB GR (or FAST + MIX 50 % for parallel) | off |
| Punchy drum bus | HPF 35 | E: LF+3@90, LMF−3@450, HF+2.5@10k | **FAST**, 4:1, thr −8, 3–6 dB GR | off |
| Kick | HPF 30–50 | E: LF@60–100, −400, +3k | FAST off, 4:1, ~3 dB | off |
| Snare crack + gate | HPF 70–100 | E: +200, +4k, shelf 8k | 4:1 | EXPAND off, FAST, Range −15…−25 |
| Overhead de-bleed | HPF 50–80 | G: +6k, smooth top | light | EXPAND **on** (2:1) |
| Vocal | HPF 100 | E: +250, −500, +4k, +10k | up to 8:1, FAST, 0.2 s | — |
| Vocal de-ess | — | `eq_to_s_c`, boost sibilant band | keys harder on sibilance | — |
| Bass + kick-duck | HPF 30–40 | LF +90, +800 def | 4:1, Peak, slow att | EXT from kick |
| Mix bus | `filters_to_s_c` HPF detector | G subtle | 2:1, FAST off, ≤4 dB GR; HQ on | off |
| Surgical mid cut | — | **E** (constant-Q at low gain) | — | — |
| Air without cramping | — | HF shelf/bell (anti-cramping always on; no HQ needed) | — | — |

> Pure-DSP approximation (no VST): SSL-grid bells/shelves via `[L] apply-eq` (`phase=zero` on drums); frequency-
> conscious comp via `[L] apply-dynamic-eq` / sidechain before `compress-loop`; glue via `[L] compress-loop`;
> verify crest/PLR with `[L] measure-microdynamics`.

---

## Sources

SSL Native Channel Strip 2 product page + user guide (store.solidstatelogic.com; SSL Support article
6887173070877 + the downloadable Channel Strip 2 User Guide PDF) · SSL Native V6 User Guide PDF · SSL UC1 User
Guide · SSL 360 release notes · SSL iLok activation FAQ (machine activation vs dongle) · gearnews/Sound on Sound
coverage of the v2 release. Plus **our own Pedalboard param dump, isolation, comp-map, E/G and preset-render
measurements** (Part A) on `SSL Native Channel Strip 2.vst3` v2.9.8, cross-checked with the `[L]` meters.
*(SSL's support Zendesk returns HTTP 403 to automated fetch; doc facts were corroborated from SSL's downloadable
PDFs + store/spec pages + the measured surface.)*
