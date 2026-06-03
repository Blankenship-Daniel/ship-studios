# SSL 4K E Channel Strip — field guide: British-console weight, punch & glue (measured)

How to drive the **SSL 4K E** (`/Library/Audio/Plug-Ins/VST3/SSL 4K E.vst3`) — SSL's own faithful model
of the **SL 4000 E** console channel. This is the **clean / weighty / controlled** "British console"
counterpart to API forwardness ([[api-vision-channel-strip]] / [[kit-bb-a5]]) and Neve/tape warmth
([[studer-a800]] / [[kit-bb-n105]]). **Part A** is *measured on this rig* (the real Pedalboard param
surface + isolation/shootout numbers from our own renders); **Part B** is a *web-research synthesis*
(cited). The skill [[ssl-4k-e]] is the measured workflow over this doc.

> **It's the 4K E, not Channel Strip 2.** The screenshot stacks two open SSL plugins; the visible GUI
> ("SOLID STATE LOGIC • SL4000 E") is the **SSL 4K E**. The tell is the **EQ COLOUR = Brown / Black /
> Orange** control — unique to the 4K E. `SSL Native Channel Strip 2` (also installed) instead models the
> 9000K EQ with an **E↔G** switch. Different plugins, different param surfaces — point the skill at the
> right `.vst3`.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the crest that
> proves "punch." Verify with `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` /
> `check-clipping`. The comp's auto-makeup raises level *and* true-peak — re-measure after every change,
> A/B loudness-matched.

---

## TL;DR (the headline, measured)

1. **EQ COLOUR is the signature lever, and the three are genuinely different at identical dial settings.**
   Same +4 LF / +3 HMF / +4 HF on the dry bus → **'02 Brown' brightest top + air** (centroid +202),
   **'242 Black' fattest lows + smoother top** (its "legendary low-end weight" — confirmed on the meter:
   most energy in the low band), **'132 Orange' (the rare passive EQ) gentlest top but nearly DOUBLES the
   2.5–5 kHz presence** (most forward mids). Pick the colour for the tone you want, *then* dial.
2. **The comp's FAST button is the punch lever — and it's TEXTBOOK here (the OPPOSITE of the API Vision
   strip).** FAST attack **OUT** (slower/auto attack) lets transients through → **crest UP** (4:1 → 23.1,
   10:1 → 25.1 vs dry 21.6 — punch). FAST attack **IN** (~1 ms grabby VCA) clamps them → **crest DOWN**
   (21.3), denser/brighter. For measured punch keep FAST **out**; engage FAST for aggressive control.
3. **Transparent at unity — color is opt-in.** All sections neutral ≈ dry (Δcrest <0.05, Δcentroid <2 Hz);
   `analogue_vca` on/off was negligible on this material. The character comes from the EQ colour, the comp
   envelope, and the **MIC preamp drive** — not an always-on saturation.
4. **Punch is the comp; weight is the EQ.** The Black LF-bell @ 80 + de-box @ 450 added weight without
   raising centroid; the slow comp added the crest. The E EQ is **constant-Q** (it will *not* auto-narrow
   like API/SSL-G proportional-Q) → a big top boost just gets bright, it won't sharpen into "snap."

---

# Part A — measured on this rig

Probe: `SSL 4K E.vst3` via Pedalboard, processing `projects/watercolors/mix/bus_punchy_pre.wav` (60 s dry,
measured-balanced drum bus), each variant **peak-normalized to −1 dBFS** so only **spectral shape / crest**
is compared (a single gain leaves crest invariant). Headline numbers are the repo meters
(`[L] measure-loudness` `crest_factor_db` / `measure-spectrum` `spectral_centroid_hz` + band ratios /
`measure-stereo` `correlation`). Render harness: `/tmp/ssl4ke_render.py` (provenance); render-probe +
param-dump tools: `presets/vst/probe_plugin.py` / `presets/vst/dump_params.py`.

**Renders headless ✓** — `probe_plugin.py "SSL 4K E"` → `RENDERS ✓` (Δparam 1.03). iLok/PACE-authorized on
this Mac; **re-verify on any other rig** (SSL/iLok is a render-farm landmine — see [[vst]]).

### The real parameter surface (Pedalboard-exposed — authoritative; 49 params)

Signal flow (GUI): **input/trim → filters → EQ → dynamics → fader/output**, with routing toggles to move
filters/EQ pre or post the dynamics and into the side-chain. **Almost every param is a discrete/enum**
(has `valid_values`) — see the headless gotcha below.

| GUI section / param | Values *(default)* | Role |
|---|---|---|
| **Input** `input_trim_db` | −20 … +20 dB *(0)* | IN TRIM (input gain) |
| `mic_db` | 0 … 50 *(0)* | **MIC preamp drive** (console grit; "spice on kick/snare/bass") |
| `pre` | Out · In *(Out)* | PRE (engage the preamp/input stage) |
| `polarity` | Out · In *(Out)* | Ø phase invert |
| `analogue_vca` | bool *(True)* | analog VCA path modeling (subtle here) |
| **Filters** `filters_in` | Out · In *(In)* | FILTERS engage |
| `high_pass_filter_hz` | `OUT` · 10.1 … 350 Hz *(OUT)* | **HPF corner, 18 dB/oct** (OUT = off) |
| `low_pass_filter_khz` | `OUT` · 34.5 … 3.0 kHz *(OUT)* | **LPF corner, 12 dB/oct** (OUT = off) |
| `filters_to_input` / `filters_to_s_c` | Out · In | filters **pre EQ/dyn** / filters → side-chain |
| **EQ** `eq_in` | Out · In *(In)* | EQ engage |
| `eq_colour` | **Brown · Black · Orange** *(Brown)* | **the EQ card** (02 / 242 / 132 — see table) |
| `eq_to_s_c` | Out · In | EQ → dynamics side-chain |
| `lf_frequency_hz` / `lf_gain_db` / `lf_type` | 30–450 / ±15 / Shelf·Bell | LF band (shelf↔bell) |
| `lmf_frequency_khz` / `lmf_gain_db` / `lmf_q` | 0.2–2.5 / ±15 / **3.0–0.5** | LMF bell (with Q) |
| `hmf_frequency_khz` / `hmf_gain_db` / `hmf_q` | 0.6–7.0 / ±15 / **3.0–0.5** | HMF bell (with Q) |
| `hf_frequency_khz` / `hf_gain_db` / `hf_type` | 1.5–16 / ±15 / Shelf·Bell | HF band (shelf↔bell) |
| **Dynamics** `dynamics_in` | Out · In *(In)* | DYN engage |
| `dynamics_pre_eq` | Out · In *(Out)* | dynamics **before** EQ |
| `compressor_ratio` | **'1.0' … '∞'** *(1.0)* | comp ratio (∞ = limiter) — **STRING enum** |
| `compressor_threshold_db` | 10 … −20 *(10)* | comp threshold (lower = more GR) |
| `compressor_release_s` | 0.1 … 4.0 s *(0.4)* | comp release |
| `compressor_fast_attack` | Out · In *(Out)* | **FAST attack** (~1 ms when In; see crest map) |
| `compressor_mix` | 0 … 100 *(100)* | **COMPRESS MIX** (parallel/dry-wet) |
| `compressor_auto_make_up` / `_offset_db` | bool *(True)* / ±12 | auto make-up + trim |
| `gate_range_db` | 0 … 40 *(0)* | gate/expander RANGE (depth; 0 = off) |
| `gate_threshold_db` | −30 … 10 *(−30)* | gate threshold |
| `gate_release_s` | 0.1 … 4.0 *(0.4)* | gate release |
| `gate_fast_attack` / `gate_expander` | Out · In | gate FAST attack / EXP (gate↔expander) |
| `s_c_listen` / `external_s_c` | bool / Out · In | LISTEN the side-chain / external S/C in |
| **Output** `fader_level_db` | '−∞' … '+12' *( '0.0')* | channel FADER — **STRING enum** |
| `pan` | 'L' … 'C' … 'R' *(C)* | PAN — **STRING enum** |
| `width` / `width_mode` / `width_frequency_hz` | 0–200 / Full·Low·High / 20 Hz–20 k | M/S WIDTH (+ frequency-selective) |
| `output_trim_db` | −20 … +20 *(0)* | OUT TRIM |
| `bypass` · `groupsense` | bool · (360 grouping) | master bypass · *(SSL 360 group ID — not audio)* |

> **There is no soft/hard knee and no separate attack-time knob** on the 4K E comp (unlike Channel Strip 2)
> — attack is the program-dependent default, switched fast by **FAST**. Likewise no `cut`/mute param is
> exposed (the GUI CUT button isn't automatable headless).

### ⚠ The headless gotcha (measured — read before scripting)

`apply-vst-chain`'s `parameters` is a **float dict**. It can set the **float-valued** discretes
(`lf_gain_db`, `*_frequency_*`, `*_q`, `compressor_threshold_db`/`release_s`, `mic_db`, `width`,
`input/output_trim_db`) — verified: `{lf_gain_db:8, hf_gain_db:8}` boosted RMS −22.6→−18.0. But it
**cannot** set the **string** enums (`compressor_ratio`, `fader_level_db`, `pan`, `eq_colour`,
`lf_type`/`hf_type`, every `Out`/`In` routing toggle): it **reports them `parameters_set` but the value
silently does not take.** Measured proof — `compressor_ratio=4` via the float dict gave crest **22.3**,
versus the preset harness's exact `'4.0'` string → **23.2** at the same threshold (and it overshot to
+0.16 dBTP). **`parameters_set` is not proof the value took** — re-measure detail. Use the **[[vst-preset]]
harness** (`presets/vst/apply_vst_preset.py`, exact strings; it also snaps log-stepped corners like the HPF
to the nearest valid value) for any chain that sets a ratio / colour / type / routing.

### Console color at unity (all sections neutral)

| | crest | centroid (FFT, inline) |
|---|---|---|
| dry (no plugin) | 21.57 | 3436 |
| strip, neutral, `analogue_vca` ON | 21.55 | 3437 |
| strip, neutral, `analogue_vca` OFF | 21.57 | 3436 |

**Near-transparent at unity** — the 4K E adds no audible always-on saturation; `analogue_vca` on/off was
negligible on this drum bus. Character is opt-in: the EQ colour, the comp, and the MIC preamp drive.

### EQ COLOUR: Brown vs Black vs Orange (identical +4 LF @100 / +3 HMF @3k Q1 / +4 HF @10k shelf)

| colour (card) | centroid | Δcentroid | low ratio | hi-mid (2.5–5k) | high ratio | character |
|---|---|---|---|---|---|---|
| dry | 2223 | — | 0.589 | 0.035 | 0.013 | source |
| **Brown** ('02) | 2425 | **+202** | 0.650 | 0.047 | **0.0186** | **brightest top + air**; "gritty/musical" original E |
| **Black** ('242) | 2378 | +155 | **0.658** | 0.040 | 0.0167 | **fattest lows**, smoother top; "legendary low-end weight" |
| **Orange** ('132) | 2290 | +67 | 0.574 | **0.068** | 0.0154 | gentlest top, **most forward 2.5–5 kHz**; the rare passive EQ, "great for kick & snare" |

The meter **matches the lore**: Black has the deepest low band, Orange almost doubles the presence band,
Brown lifts the air most. **Choose the colour, then the moves** — the same dial is a different EQ on each.

### Comp: FAST attack × ratio → crest (the punch map)

4:1 @ −14 (release 0.3, auto-makeup on) unless noted; peak-normalized. **Crest/PLR = punch; dry = 21.6/19.9.**

| comp setting | crest | PLR | read |
|---|---|---|---|
| dry | 21.61 | 19.88 | source |
| 4:1, **FAST out** (slow) | **23.11** | 21.37 | transients pass → **punch UP** |
| 4:1, **FAST in** (~1 ms) | 21.34 | 19.87 | transients clamped → ~dry crest, denser/brighter |
| 10:1, FAST out | **25.08** | 23.30 | body squashed, auto-makeup lifts it → big crest |

**Slow attack (FAST out) preserves/builds the transient; FAST attack tames it.** This is the textbook
result — and the *opposite* of the UAD API Vision strip, where Medium attack beat Slow (see
[[api-vision-channel-strip]]). Don't carry the API rule over; **measure the crest.**

### Full-strip drum-bus shootout (which is the SSL bus tone?)

| variant | crest | centroid | corr | read |
|---|---|---|---|---|
| dry balanced | 21.6 | 2223 | 0.981 | source |
| **E-glue** (Brown, 2:1 slow, gentle EQ) | 20.8 | — | 0.984 | gentle cohesion → `ssl-4k-e-glue.json` |
| **punch** (Black, 4:1 slow, LF-bell +3 @80 / de-box −2 @450 / +1.5 @3k) | **23.2** | **2272** | 0.983 | **weight + punch, stays warm — winner** → `ssl-4k-e-drum-bus.json` |
| par-glue (Brown, 10:1 FAST-in, MIX 40) | 20.6 | — | 0.985 | tightest L/R, denser, brighter |

**The punch variant won the SSL way**: crest **up** to 23.2 *and* centroid stayed warm (2272 vs dry 2223 —
**not** brighter), L/R corr 0.983, mono-sum loss 0.64 dB. Weight from the **Black** EQ, punch from the
**slow comp** — no top boost needed.

### Presets (`presets/vst/`)

- **`ssl-4k-e-drum-bus.json`** — the punch winner: Black EQ (LF-bell +3 @80, de-box −2 @450, +1.5 @3k),
  HPF 40, comp 4:1 @ −16, release 0.15, **FAST out**. Weighty/punchy/warm, mono-safe.
- **`ssl-4k-e-glue.json`** — Brown EQ (LF shelf +2 @60, de-box −2 @400, air +2 @12k), comp 2:1 @ −12 slow.
  Gentle bus glue (crest ≈ dry), the [[finalize-mix]] stage in one console box.

Apply with `presets/vst/apply_vst_preset.py <preset.json> <in> <out>` (the `vst` venv). Re-set the comp
threshold to your source level after recall.

---

# Part B — how the console / plugin works (web-research synthesis, cited)

## 1. What it is — the SL 4000 E

The **SSL 4K E** is SSL's own model of the channel strip of the **SL 4000 E** console (the desk behind a
huge swath of 1980s–2000s records) — **launched Nov 2023**, current line **1.5.x**, ~$329 perpetual (the
$149 you'll see is an intro/reseller price). It reproduces the channel's **high/low-pass filters, 4-band
EQ, VCA compressor/limiter, and gate/expander**, plus a modeled transformer **mic-preamp drive** and a
**dbx-202 "Gold Can" VCA fader** (driving the +12 dB fader adds colour too), and adds modern niceties
(M/S width, frequency-selective width, **HQ** oversampling, **360°** integration). It is a *different*
plugin from **SSL Native Channel Strip 2** (which models the later **9000 K** EQ with an E↔G switch and
"anti-cramping" — no preamp/saturation modeling); both are installed here, **360° siblings sharing the
4K-B-generation GUI but NOT a DSP engine** (each emulates a different console). SSL also ships the **4K B**
(a 4000-channel variant) and the **4K G** (with the G-series "Pink Knob '292" EQ + HMF×3 / LMF÷3) — all
combinable in the **SSL 360° Plug-in Mixer**.

## 2. The EQ — three cards, and "E vs G"

The 4K E's standout is that it includes **all three historical 4000-E EQ revisions** as the **COLOUR**
switch:

- **'02 Brown' knob** — the **original** E EQ, "renowned for its grit," **easy/musical** to dial. (Our
  meter: brightest top + air.)
- **'242 Black' knob** — the **cleaner / more surgical** EQ "with its **legendary low-end weight**." (Our
  meter: fattest lows.)
- **'132 Orange' knob** — the **rare passive** EQ; reviewers single it out as **"particularly useful for
  kick & snare."** (Our meter: most forward 2.5–5 kHz presence.)

All three are **4-band**: LF & HF **shelving** (switch to **Bell** via the BELL button), LMF & HMF fully
**parametric bells with a Q knob**. Band ranges (match our dump): **LF 30–450 Hz, LMF 0.2–2.5 kHz, HMF
0.6–7 kHz, HF 1.5–16 kHz.** The E-series EQ is **constant-bandwidth (constant-Q)** — the bandwidth does
**not** change with boost/cut, which gives "more presence and edge" and a forgiving, broad feel.

> **Gain range:** Pedalboard exposes **±15 dB** on every band (what you can automate — the Part A table is
> authoritative for our use). On the hardware the maxima are *card- and Q-dependent* (Black bell reaches
> ~±18 dB; the mid bell gain rises with Q) — so don't read ±15 as "the console's ceiling," just the
> plugin's exposed automation range.

**E vs G (if you reach for the 4K G / Channel Strip 2 instead):** the **G-series** EQ uses a **variable
proportional-Q** (bandwidth narrows as you boost) plus steeper filter slopes and HMF×3 / LMF÷3 frequency
multipliers — **more forward mids, top-end "pop," punchy/aggressive** (great on rock drums/bass/guitars).
**E = smoother, rounder, warmer** (pop/R&B/hip-hop, vocals, drums, guitars). Rule of thumb: **E to push
without it getting "too much"; G when you want bite and midrange shove.**

## 3. The filters

A **12 dB/oct low-pass** and a **high-pass** (~**18 dB/oct on the Black card, 12 dB/oct on the Brown** —
the slope tracks the EQ colour; medium-confidence, from reviews not the SSL manual), each defeatable
(`OUT`). Exposed corners (our dump): **HPF 10–350 Hz, LPF ~3–34 kHz.** They can be positioned **pre or
post EQ** (`filters_to_input`) and routed to the **dynamics side-chain** (`filters_to_s_c`) — e.g. HPF the
comp detector so the kick stops over-triggering the bus comp without thinning the audio. Hard console rule:
**EQ › DYN › FILTER is not possible** — the filter always sits just before the EQ unless filter-to-input
is active.

## 4. The dynamics — a fast, grabby VCA

- **Compressor/limiter** — continuously variable **ratio 1:1 → ∞:1** (∞ = limiter). The SSL channel VCA is
  famous for a **fast, grabby** character; the **FAST** button switches to an **~1 ms attack** for tight
  transient control, while FAST-out is the slower program-dependent attack that lets transients through.
  **Auto make-up** is on by default; **release 0.1–4 s**; the **COMPRESS MIX** knob blends dry/wet for
  **parallel** ("New York") compression on the channel itself.
- **Gate/Expander** — **RANGE** (depth of attenuation), threshold, release, FAST attack, and **EXP** to
  switch gate↔expander. Tames bleed/decay between hits.
- **Side-chain** — internal or **external** (`external_s_c`), with **LISTEN** (`s_c_listen`) to audition
  the detector, and the filters/EQ routable into it.

## 5. Input, output, 360 & HQ

- **MIC drive + PRE** — the modeled preamp adds **console grit/harmonics** ("spice on kick/snare/bass");
  it's the saturation source (the strip is otherwise clean at unity).
- **Output** — channel **FADER** (−∞…+12), **OUT TRIM**, **PAN**, and an **M/S WIDTH** with a
  **frequency-selective** mode (`width_mode` Full/Low/High + `width_frequency_hz` — e.g. widen only the
  highs, keep lows mono).
- **HQ** — intelligent **oversampling** (anti-alias) at higher CPU. **360°** — links the 4K E with Channel
  Strip 2 / 4K B / third-party plugins in the **SSL 360° Plug-in Mixer** (irrelevant to an offline render).

## 6. Practical technique (starting points)

- **Drum bus (weight + punch — the SSL way):** **Black** EQ, HPF ~40, LF **bell** +3 @ 70–90 (weight),
  de-box −2/−3 @ 400–500, optional +1–2 @ 3 k (attack); comp **4:1, FAST out, ~3–6 dB GR**, release
  0.1–0.2 s. Punch from the comp, weight from the EQ. (= `ssl-4k-e-drum-bus.json`.)
- **Bus glue:** **Brown** EQ small shelves + de-box; comp **2:1, FAST out, 2–3 dB GR**, MIX 100 — or
  **MIX ~40 with a high ratio** for parallel glue. (= `ssl-4k-e-glue.json`.)
- **Kick / snare:** try **Orange** (forward 2.5–5 kHz = attack/snap); HPF the kick ~30–40 and snare
  ~80–120; comp FAST-in for grab, or FAST-out to keep the hit.
- **Overheads / room:** HPF ~150–400; **Brown** HF shelf for air; gentle comp; widen highs with
  `width_mode=High`.
- **The "SSL sound":** controlled, weighty low end + a clean, slightly forward top, glued by the grabby VCA
  — *cleaner and more controlled* than API (forward/aggressive) or Neve/tape (warm/saturated).

## 7. Pitfalls & gotchas

- **String enums don't set via the float dict** (ratio/colour/type/routing/fader/pan) — use the preset
  harness with exact strings; `parameters_set` ≠ "it took" (Part A).
- **E EQ is constant-Q** — a big top boost just gets *bright*, it won't auto-narrow into "snap" the way API
  / SSL-G proportional-Q does. For attack, use the comp / Orange presence, not a huge HF boost.
- **Auto make-up raises level + true-peak** — loudness-match before A/B; re-set the threshold to *your*
  source level after recalling a preset (this set was tuned to a ~−23 LUFS dry bus).
- **FAST attack rule is the opposite of the API strip** — here FAST-out is the punchier (higher-crest)
  setting; FAST-in is denser/tamer. Measure.
- **Two different SSL strips** — `SSL 4K E.vst3` (Brown/Black/Orange) vs `SSL Native Channel Strip 2.vst3`
  (E/G switch). Don't cross the param surfaces.
- **iLok/PACE** — renders headless *here*; re-verify on any other machine (`probe_plugin.py`).
- **HQ/360 state** — oversampling and 360 grouping aren't audio params; capture the full patch with
  `dump_state` if you need an exact re-render.

## 8. Decision table

| Goal | EQ colour | HPF | EQ moves | Comp (ratio / FAST / GR) |
|---|---|---|---|---|
| Drum bus: weight + punch | **Black** | ~40 | LF-bell +3 @80, −2/−3 @450, +1.5 @3k | 4:1 / **out** / 3–6 dB |
| Bus glue | **Brown** | ~30 | +2 @60 shelf, −2 @400, +2 @12k | 2:1 / out / 2–3 dB |
| Parallel glue | Brown | ~30 | small | 10:1 / **in** / MIX ~40 |
| Punchy kick | **Orange** | 30–40 | +3–4 @60–80, +3 @3–5k (attack) | 4:1 / in for grab / 3–6 dB |
| Snare snap | **Orange** | 80–120 | +2–3 @200 body, +3–4 @3–5k | 4:1 / taste / modest |
| Air / open top | **Brown** | — | HF **shelf** +2–4 @ 10–12k | light |
| Warm / dark | **Black** | — | LF shelf +2–3, gentle top | light |
| Stop kick pumping the bus | (any) | filters_to_s_c + HPF detector | (audio EQ unaffected) | 4:1 / out / 3–6 dB |

> Pure-DSP approximation (no VST): place the EQ moves with `[L] apply-eq`; the slow-attack VCA punch with
> `[L] compress-loop` (low ratio, slow attack) or `[L] multiband-compress`; preamp grit with
> `[L] saturate-loop`; verify crest/PLR with `[L] measure-microdynamics`.

---

## Sources

SSL — *SSL 4K E Channel Strip Plug-in User Guide* (support.solidstatelogic.com) · *SSL 4K E* product page
(store.solidstatelogic.com) · *SSL Channel Strip 2 User Guide* + *Channel Strip Guide* · *SSL 360° / 360
Link* docs · Universal Audio — *SSL 4000 E Channel Strip Manual* (help.uaudio.com) · Brainworx *bx_console
SSL 4000 E* manual · Waves *SSL E-Channel/G-Channel* manual + "E-Channel or G-Channel?" · Production Expert
"SSL 4K E Plugin" review · Ten87 "SSL EQ types" · Develop Device "SSL Channel Strip Shootout" · SonicScoop
"SSL Channel Strip Roundup" · MusicRadar UA SSL 4000 E review. Plus **our own render-probe / param-dump /
isolation / shootout measurements** (Part A) on `SSL 4K E.vst3`.
