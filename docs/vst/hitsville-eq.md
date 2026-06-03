# UAD Hitsville EQ — field guide: the Motown 7-band graphic EQ, clean + forgiving, headless

How to drive the **UADx Hitsville EQ** (`uaudio_hitsville_eq.vst3`) — UA's emulation of the custom
**7-band graphic equalizer** built in-house at Motown's **Hitsville U.S.A.** studio in Detroit by chief
engineer **Mike McLean**. It's a **clean, characterful, hard-to-make-harsh tone EQ** — fixed Motown
frequencies, interactive proportional-Q bells, and a tiny ±8 dB range that keeps you out of trouble. The
forward/"butter" colour counterpart to the surgical [[fabfilter-pro-q-4]] and the saturating tape/console
stages. **Part A** is *measured on this rig* (the real Pedalboard param surface + isolation numbers from
our own renders); **Part B** is a *web-research synthesis* (cited, adversarially verified). The skill
[[hitsville-eq]] is the measured workflow.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the crest that
> proves "transients survived." Verify with `[L] measure-loudness` / `measure-spectrum` /
> `measure-microdynamics` / `check-clipping`. Re-measure after every change, A/B loudness-matched.

---

## TL;DR (the headline, measured)

1. **It RENDERS headless here — proven, not assumed.** `uaudio_hitsville_eq.vst3` (UADx native) loads via
   Pedalboard and **responds to its params** (push band 6 / 5 kHz +8 → +7.5 dB at 5 kHz vs bypass — not
   passthrough). Use the **`uaudio_*.vst3`** build, never the `UAD Hitsville EQ.component` twin (passthrough
   offline). No-dongle, machine-activated UA/iLok auth (see §B7).
2. **All 11 params are stepped enums — but the musical ones are NUMERIC.** The seven band knobs
   (`1_50`…`7_12500`) and `gain` are **−8…+8 dB in 1 dB steps**; a float reaches them, so — unlike the
   SSL/Neve/API console strips — **this EQ is fully drivable from `apply-vst-chain`'s float dict**. Only
   `bypass` (string `Off/Out/In`), `power` and `master_bypass` (bool) need the [[vst-preset]] harness, and
   their defaults are already correct.
3. **It's a CLEAN EQ — no saturation at mix level.** Measured **0.000 % THD** on a 1 kHz sine at
   −20/−6/−1 dBFS, flat and with a band boosted. The *only* distortion is the **GAIN makeup clipping** a
   hot signal (gain +8 on a −1 dBFS sine → 4.1 % THD = digital clip past 0 dBFS). Use GAIN to **compensate**
   boosts (cut), not to push level. The "Motown harmonic colour" reviewers cite needs you to **drive the
   input** — which `apply-vst-chain` can't do (no gain-stage); use the harness `input_gain_db` for that.
4. **Proportional-Q, interactive bands.** Bigger boost = narrower bell (measured peak:octave **1.1 → 1.8 →
   3.5** at +2/+5/+8 on the 5 kHz band). Bands **overlap** — a boost bleeds ~+1.5–2 dB into each neighbour.
   Small moves behave like a broad musical tilt; this is a vibe EQ, not a surgical one.
5. **The bypass knob is the 3-way IN/OUT/OFF hardware switch.** `In` = EQ engaged, `Out` = EQ bands
   bypassed but the unit stays in-circuit (the modelled transformer/amp path; measured +1.9 dB headroom
   signature, ≤0.2 dB tilt), `Off` = true hard bypass (0.00). Default `In`.

---

# Part A — measured on this rig

Probe: `uaudio_hitsville_eq.vst3` via Pedalboard, deterministic pink noise + 1 kHz sines for isolation,
plus the real `projects/watercolors/mix/bus_warm_pre_dry.wav` (a measured-balanced, dry drum bus) through
`[L] apply-vst-chain` + the preset harness. Spectral comparisons are peak-normalized so only **shape /
crest** is judged.

### The real parameter surface (Pedalboard-exposed — authoritative for this build)

**11 params, all enum-valued.** Default state: `bypass="In"`, `power=True`, `master_bypass=False`, all
bands `0.0`, `gain=0.0`.

| Param | Values *(default)* | Role |
|---|---|---|
| `1_50` | −8 … +8 dB, 1 dB step *(0)* | **Sub** band (50 Hz) — low bell |
| `2_130` | −8 … +8 dB, 1 dB step *(0)* | **Bass** band (130 Hz) — bell |
| `3_320` | −8 … +8 dB, 1 dB step *(0)* | **Lo Mid** band (320 Hz) — bell |
| `4_800` | −8 … +8 dB, 1 dB step *(0)* | **Mid** band (800 Hz) — bell |
| `5_2000` | −8 … +8 dB, 1 dB step *(0)* | **Hi Mid** band (2 kHz) — bell |
| `6_5000` | −8 … +8 dB, 1 dB step *(0)* | **Treble** band (5 kHz) — bell |
| `7_12500` | −8 … +8 dB, 1 dB step *(0)* | **Hi** band (12.5 kHz) — broad HF (air) bell/shelf |
| `gain` | −8 … +8 dB, 1 dB step *(0)* | master makeup/output (**measured exactly linear**) |
| `bypass` | `Off` · `Out` · `In` *(In)* | the hardware **IN/OUT/OFF** switch (see below) |
| `power` | `True`/`False` *(True)* | on/off (False = bypass) |
| `master_bypass` | `False`/`True` *(False)* | true bypass |

> **Setting params:** the 7 band knobs + `gain` are **numeric enums** — pedalboard accepts a float (snaps to
> the nearest 1 dB detent), so `apply-vst-chain`'s float dict reaches all of them (verified end-to-end:
> `{"1_50":3,...,"gain":-2}` rendered, `changed:true`). `bypass` is a **string enum**, `power`/`master_bypass`
> are **bool** → set via the [[vst-preset]] harness (their defaults are already `In`/on, so you rarely need to).

### Render proof + console colour at unity (flat, bands at 0)

| | input peak | output peak | note |
|---|---|---|---|
| flat (In, power on) | 0.50 | 0.41 | the unity path applies ~**1.7 dB of output headroom** (an amp/transformer cushion) |

Default-flat vs `Off` (true bypass), peak-normalized: band energy differs by only **≤0.2 dB across the whole
spectrum** (50 Hz +1.80 → 12.5 kHz +2.00 — i.e. **tonally flat**, a hair of bright tilt), but the waveforms
differ (max-abs-diff 0.49) because the modelled analog topology is **minimum-phase** (phase shifts even when
flat). **At unity it's clean and near-transparent in tone; the character is the curve, not a colour.**

### Per-band isolation (+8 dB), peak-normed band-energy Δ vs bypass (dB)

```
setting          50     130     320     800    2000    5000   12500
+8 @50       +6.73   +1.31   -0.21   -0.42   -0.44   -0.44   -0.38
+8 @130      +0.77   +6.69   +1.28   -0.31   -0.54   -0.58   -0.52
+8 @320      -0.63   +0.74   +6.97   +1.15   -0.43   -0.66   -0.64
+8 @800      -0.39   -0.14   +1.24   +7.44   +1.59   +0.00   -0.18
+8 @2000     -0.04   +0.03   +0.26   +1.51   +7.89   +2.05   +0.45
+8 @5000     -0.44   -0.39   -0.32   -0.09   +1.22   +7.51   +1.60
+8 @12500    -0.18   -0.14   -0.10   -0.03   +0.20   +1.53   +7.85
```

Every band peaks at its own center (~+7–8 dB) and bleeds **~+1.2–2.0 dB into the adjacent band(s)** — the
**overlapping, interactive** behaviour UA documents. Cuts (−8) mirror this (centers drop ~−5 dB peak-normed,
broadening as the renorm lifts the rest).

**Band shapes (peak-normed Δ vs bypass at +8):**
- **`1_50` is a low BELL** (peaks at 50): 25 Hz **+1.78**, 50 **+6.73**, 100 **+2.57**, 200 +0.24, 400 −0.32.
- inner bands **130–5000 are interactive bells** (~1.5-octave, per the table).
- **`7_12500` is a broad HF (air) bell/shelf**: 4 k +0.93, 8 k **+4.01**, 12.5 k **+7.85**, 16 k **+7.15**,
  19 k +5.55 — it plateaus 12.5–16 k (air without a single sharp peak).

### Proportional-Q (band `6_5000` at +2 / +5 / +8) — bigger boost = narrower

| setting | peak @5k | octave-down @2.5k | octave-up @10k | peak : octave |
|---|---|---|---|---|
| +2 | +3.25 | +2.92 | +3.04 | **1.1** (broad / nearly a tilt) |
| +5 | +5.64 | +3.09 | +3.49 | **1.8** |
| +8 | +7.51 | +2.12 | +2.67 | **3.5** (focused bell) |

Small settings are broad and gentle; large settings tighten into a bell. This is why tiny moves read as a
musical *tilt* and big moves as a *bell*.

### THD — it's a CLEAN EQ; only the GAIN clips

| 1 kHz sine | flat | gain +8 | band 800 +8 |
|---|---|---|---|
| in −20 dBFS | 0.000 % | 0.000 % | 0.000 % |
| in −6 dBFS | 0.000 % | 0.000 % | 0.000 % |
| in −1 dBFS | 0.000 % | **4.107 %** | 0.000 % |

The EQ path adds **no measurable harmonics** at mix level. The 4.1 % at gain +8 / −1 dBFS is the **makeup
gain clipping past 0 dBFS** (digital clip, not modelled saturation). **GAIN is otherwise perfectly linear**
(−8/−4/+4/+8 → −8.00/−4.01/+4.02/+8.03 dB). Take-away: use GAIN to **cut** (compensate boosts), and to get
the reviewers' "driven Motown colour" you must **gain-stage INTO** it (harness `input_gain_db`), which
`apply-vst-chain` cannot do.

### Bypass / power semantics (with band 6 / 5 kHz set +8)

| state | 5 kHz Δ vs bypass | meaning |
|---|---|---|
| `bypass="In"` | **+7.51** | EQ engaged (default) |
| `bypass="Out"` | **+1.94** | EQ bands bypassed, **unit still in-circuit** (transformer/amp path only) |
| `bypass="Off"` | **+0.00** | true hard bypass |
| `power=False` | +0.00 | off (bypass) |

`Out` ≠ `Off`: `Out` keeps the modelled iron/amp colour (a near-flat ~1.9 dB-denser signature), `Off`
removes everything. This **matches UA's documented 3-way switch exactly** (see §B2).

### Real dry drum bus → the presets (full bus, stemmy meters)

| | LUFS-I | true-peak | crest | centroid | tilt dB/oct | low | low-mid | high |
|---|---|---|---|---|---|---|---|---|
| dry | −25.4 | −5.99 | 23.6 | 3128 | −2.26 | 0.542 | 0.378 | 0.0115 |
| **motown-drum-bus** | (level-matched, gain −2) | −6.49¹ | **22.9** | 3531 (+403) | −2.00 | **0.661** | **0.248** | **0.0195** |
| **warm-drum-glue** | — | — | 21.8 | **3129 (≈dry)** | −2.43 | **0.696** | 0.249 | 0.0096 |
| **mix-glue** | — | — | 23.2 | 3337 (+209) | −2.13 | 0.592 | 0.325 | 0.0148 |

¹ the `apply-vst-chain` render kept native level (LUFS −25.4, TP −6.49); the harness peak-trims to −1 dBFS
(so LUFS/TP rise) — the **tonal ratios / centroid / tilt / crest are level-independent** and are the truth.

The three moves: **motown** = forward Motown colour (weight up, low-mids de-boxed, +403 centroid air,
transients kept — it's EQ, not compression); **warm** = the house warm/tight variant (same weight + de-box
but top pulled back → **centroid unchanged**, slightly darker tilt, never brittle); **mix-glue** = a gentle
broadband tilt for a bus/master. → presets in `presets/vst/`.

### Presets (`presets/vst/`)

- **`hitsville-eq-motown-drum-bus.json`** — 50 +3 / 130 +1 / 320 −2 / 2000 +1 / 5000 +2 / 12500 +2, gain −2.
  Forward Motown drum colour.
- **`hitsville-eq-warm-drum-glue.json`** — 50 +3 / 130 +1 / 320 −2, top restrained (5000 flat, 12500 +1),
  gain −1. The warm/tight house variant.
- **`hitsville-eq-mix-glue.json`** — 50 +2 / 320 −1 / 5000 +1 / 12500 +1, gain −1. Gentle bus/master tilt.

(All three are pure EQ — apply with `apply_vst_preset.py`, or set the same numeric params via
`apply-vst-chain`. For the **Mastering** twin's M/S, half-speed, Dip/Peak and disc-cutting filters, load
`uaudio_hitsville_eq_mastering.vst3` and dump its params — see §B3.)

---

# Part B — how it works (web-research synthesis, cited, adversarially verified)

### 1. What it is / lineage

The UAD **Hitsville EQ Collection** (UADx) emulates the custom equalizers built in-house at Motown's
**Hitsville U.S.A.** studio in Detroit, released **May 18, 2022** (UAD Software v10.1), **$299** perpetual
(also in the UAD Spark subscription). It is the **only Motown-gear emulation officially licensed by the
Motown Museum**. *(HIGH.)*

The original hardware was designed/built by **Mike McLean**, Motown's chief technical engineer (1961–72),
based on the **Langevin EQ 252a** (Arthur C. Davis), adapted from passive film-industry EQs — "essentially a
souped-up Langevin." His key innovation: isolating the passive LC EQ circuit and pairing it with a **built-in
makeup-gain amp**, so it didn't need an external preamp to recover the level a passive circuit loses. The
circuit used **21 inductors + 21 tone capacitors (3 per band)**, transformer-balanced. *(HIGH.)*

- **Do NOT assert "Studio A."** The custom-built, Motown-licensed, **Detroit** framing is confirmed, but **no
  authoritative source names "Studio A"** — Tape Op says the units were installed across Hitsville rooms in
  **Detroit *and* L.A.** It's a fleet of studio gear, not a named room. *(verdict: uncertain.)*
- **Rarity:** ~**46 Studio EQ** units and only **6 Mastering EQ** units ever built (sources vary 40–48). The
  serial-style plate on the GUI is period flavour. *(HIGH it's very rare; MEDIUM on the exact count.)*

### 2. Signal flow & controls

**Studio EQ** = single-channel, **inductor-based, proportional-Q, fixed-frequency graphic EQ**, seven bands,
each **±8 dB** (NOT ±10), **stepped in 1 dB increments** (17 detents per band; Tape Op: "so smooth they feel
continuous"). The seven fixed centers — confirmed digit-for-digit against UA's own manual: *(HIGH)*

| Band | Freq | Label | | Band | Freq | Label |
|---|---|---|---|---|---|---|
| 1 | **50 Hz** | Sub | | 5 | **2000 Hz** | Hi Mid |
| 2 | **130 Hz** | Bass | | 6 | **5000 Hz** | Treble |
| 3 | **320 Hz** | Lo Mid | | 7 | **12500 Hz** | Hi |
| 4 | **800 Hz** | Mid | | | | |

A master **GAIN** knob adds **±8 dB** (1 dB steps) of output/makeup trim. The engage control is a **3-way
IN / OUT / OFF** switch: **In** = bands active; **Out** = EQ curve bypassed but signal still runs through the
modelled **UTC/Freed transformers + makeup amps** (colour retained); **Off** = **true hard bypass**. So
*Out keeps the colour, Off removes it* — exactly what Part A measured. *(HIGH.)*

**Proportional-Q + interaction:** bandwidth **widens at small settings, narrows at extremes**; bands
**overlap ~1.5-octave ranges and interact** (adjacent bands sum). UA: "with the fixed Q and unique
interaction between bands, you just jump in and start turning knobs." *(HIGH — matches Part A.)*

**"Passive" nuance:** the EQ *band circuit* is passive/inductor-based, but the unit also has **active makeup
amps + transformers** — a passive-EQ topology with active makeup gain, not a wholly passive Pultec-style box.
The plugin models "the entire electronic path, including transformers, makeup amplifiers, EQ band
interactions, and internal clipped filter distortion." *(HIGH.)* *(Part A reconciliation: at ≤−1 dBFS the
harmonic content is below the measurement floor — 0 % THD; the "clipped filter distortion" engages only when
you drive it harder, and the makeup `gain` clips past 0 dBFS.)*

### 3. Channel vs Mastering version

The Collection ships **two models in one product** (sister models, not two SKUs):

- **Hitsville Studio EQ** (`uaudio_hitsville_eq.vst3`) — single-channel graphic EQ, above. Tracking/mixing.
- **Hitsville Stereo Disk Mastering EQ** (`uaudio_hitsville_eq_mastering.vst3`) — same 7 bands / ±8 dB /
  proportional-Q, **plus**: two channels switchable **L/R or Mid/Side** (the M/S is the one element **NOT** on
  the original hardware — UA added it); a **Controls Link** switch (gang/unlink channels); a per-band
  **Dip/Peak** switch (cut or boost); a **Half-Speed** mode that **halves every band center** (50→25, 130→65,
  320→160, 800→400, 2000→1000, 5000→2500, 12500→6250 Hz), per channel or per band — the disc-cutting
  workflow, functionally **expanding the frequency range**; and **"Motown Filters"** — a 4-way switch:
  **No Filter / 70 Hz HPF / 15 kHz LPF / combined 70 Hz+15 kHz band-pass** (steep transformer-based
  elliptical filters with some resonance). Intended for buses/subgroups/the 2-bus. *(HIGH.)*

### 4. The "Motown" character

Musical/forgiving **vibe, not surgical precision**: "a true character piece… vibe all the way" (Chycki);
"instantly adds character," "midrange stands out" (Gray); "density without being over the top" (Moshay);
"it sounds like butter… like a pat of butter on lobster — makes things better in a soft yet definable way"
(Tozzoli). *(HIGH for the consensus.)* The smooth tone is attributed to the broad overlapping passive bands +
transformer path + makeup amp (no harsh active EQ stage) — *(MEDIUM as a causal claim.)* **Driving the input**
adds desirable harmonic colour ("internal clipped filter distortion"; "turn the knobs surprisingly far with
no ill artifacts"). *(HIGH that drive adds colour — but you must gain-stage into it; see Part A.)*

### 5. Using it on drums / bus / master / vocals (source-cited moves)

Original units were used on **everything — drums, bass, keys, vocals**. Concrete cited moves:

- **Electric / DI guitar:** cut **5 kHz**, boost **2 kHz**, + overall GAIN — softens edge.
- **Air/warmth (strings, pads, drum overheads):** boost **12,500 Hz** (air, no upper-mid bite) + **130 Hz**
  (body). *(This is the canonical Hitsville "air" move.)*
- **Bass:** reviewer standout — the fixed centers (130/320/800 Hz) sit musically; "the choice of frequencies
  is spot-on."
- **Master low-end (Mastering EQ, half-speed):** boost **65 Hz** while slightly cutting **25 Hz** (130/50 Hz
  halved) — "balanced low-frequency cream."
- **Master HF (Mastering EQ):** boost **12.5 kHz** (L/R) + roll off **15 kHz** with the filter — "tape-like
  smoothness."
- **Buses/subgroups:** the Mastering EQ's steep-but-musical filters tighten subgroups; its **M/S mode is
  prized on the master bus** for "substance, grit, and width."
- **Placement:** put it **before the compressor**.
- **Drums (our measured starting points):** weight = `1_50` +2…+3; de-box = `3_320` −2; attack = `5_2000`
  +1; snap = `6_5000` +1…+2 (watch 5–7 kHz brittleness on hat/cymbals — the house hi-hat note); air =
  `7_12500` +1…+2; compensate with `gain` −1…−2. → `hitsville-eq-motown-drum-bus.json` / `-warm-drum-glue.json`.

### 6. Harshness & pitfalls

- **Hard to make harsh** — proportional-Q + broad overlapping bands + the **±8 dB cap** keep it forgiving.
- **Character/tone EQ, not corrective** — stepped 1 dB, ±8 dB ceiling, **fixed (non-sweepable) centers**, no
  notching. Need a frequency in between? That's what the Mastering EQ's **half-speed** is for; for surgery use
  [[fabfilter-pro-q-4]].
- **Bands interact** — adjacent moves sum (~1.5-octave overlap); don't expect independent bands.
- **GAIN clips past 0 dBFS** — the only distortion at mix level (Part A). Use it to cut, gain-stage elsewhere.
- **No saturation without drive** — for the "Motown harmonic yum," gain-stage INTO it (harness
  `input_gain_db`); `apply-vst-chain` can't, so via `apply-vst-chain` it's a clean EQ only.
- **Non-resizable GUI** (irrelevant headless). Low CPU.

### 7. Licensing & headless/offline

- **Two builds, one purchase:** a **native (UADx)** build + a **UAD-2/Apollo DSP** build; buying grants both.
- **UADx (native)** runs on the **host CPU, no UA hardware** (no Apollo/UAD-2), VST3/AU/AAX, listed as
  "UADx" — the headless-safe build. **Load `uaudio_hitsville_eq.vst3`**, never the `UAD Hitsville EQ.component`
  (passthrough offline). The **DSP/Apollo** twin needs UA DSP hardware — don't use it headless. *(HIGH.)*
- **iLok — be precise:** a **free iLok account is required** to manage native licenses (the license is
  **iLok/PACE-backed**), but **no physical iLok USB dongle is required**. Authorization is via **UA Connect**
  (UA-account login), which by default machine-activates perpetual UADx licenses. So it's *UA account + free
  iLok account, no dongle* — not "UA account only." *(verdict: the no-dongle / host-CPU parts confirmed; the
  "UA-account-only" shorthand is imprecise.)*
- **Offline:** since **March 25, 2025**, perpetual UADx licenses machine-activate to **up to 3 locations** and
  run **fully offline** after a one-time activation. iLok Cloud is **UAD Spark (subscription) only**. Net for
  a render farm: perpetual UADx, machine-activated, runs offline without a dongle — but it **is iLok/PACE-
  protected**, so plan activations across machines. **On THIS rig it renders headless (Part A proved it).**
- **Not in this collection:** **Hitsville Reverb Chambers** is a **separate, later** product (Nov 8 2022,
  $349) — **not** part of the EQ Collection. *(verdict: refuted that they shipped as one collection.)* The
  installed `uaudio_hitsville_chambers.vst3` is that separate reverb, not an EQ.

> **Pure-DSP approximation (no VST):** the 7 fixed Motown bells ≈ `[L] apply-eq` (bells at
> 50/130/320/800/2k/5k/12.5k, modest ±dB, broad Q); the forgiving "tilt" ≈ `[L] apply-eq` tilt; there's **no
> saturation to replace** (it's a clean EQ). For Motown-style harmonic warmth add a tape/console stage
> ([[studer-a800]] / [[ampex-atr-102]] / [[kit-bb-n105]] / [[helios-type-69]]).

---

## Sources

Universal Audio — Hitsville EQ Collection product page · UAD v10.1 press release · UA Hitsville EQ Collection
Manual (help.uaudio.com) · UA "UAD Native vs UAD DSP/Apollo" · UA Connect / native-license offline help · UA
Hitsville EQ reviews/quick-tips · Tape Op (Hitsville EQ Collection review) · Mixonline (real-world review +
product-of-the-week) · MusicTech · Sound on Sound (Heritage MotorCity EQ — the original-hardware lineage) ·
Recording Magazine (Mike McLean / Motown gear) · Sonicstate · Acme Audio (MTEQ-1) · gearspace · PR Newswire.
Plus **our own param-enumeration / isolation / THD / proportional-Q / bypass / real-bus measurements**
(Part A) on `uaudio_hitsville_eq.vst3`.
