# UADx Pultec HLF-3C — field guide: a passive high-pass / low-pass FILTER, headless

How to drive the **UADx Pultec HLF-3C EQ** (`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_hlf-3c.vst3`) — UA's model
of the **Pultec / Pulse Techniques HLF-3C**, the "Pultec Filter": a **passive high-pass + low-pass FILTER set**. It is
**not** a boost/cut tonal EQ — that is the **EQP-1A** ([[fabfilter-pro-q-4]] is the surgical-EQ skill; the UADx EQP-1A /
MEQ-5 are the boost-cut Pultecs) — the HLF-3C only *removes* the extremes. **Part A** is *measured on this rig* (the
real Pedalboard param surface + our own swept frequency-response / THD / render results); **Part B** is a *web-research
synthesis, adversarially verified, cited*. The skill [[pultec-hlf-3c]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the tilt/centroid/crest that
> prove a tonal or filter move. Verify every move with `[L] measure-spectrum` / `measure-loudness`. A render that
> "sounds" filtered but shows a 0.00 spectrum delta is a **passthrough** (wrong build, or `enable='Out'`).

---

## TL;DR (the headline, measured)

1. **It renders headless — load the `uaudio_` build.** `uaudio_pultec_hlf-3c.vst3` loads + processes through
   Pedalboard 0.9.23 (real filter values give up to ~69 dB of attenuation). The `UAD Pultec HLF-3C.component` /
   `/Universal Audio/…vst3` twins are the **passthrough** offline build — never load those
   ([[vst-verify]]). UADx native here = iLok *account*, **no dongle**.
2. **⚠️ The standard `probe_plugin.py` FALSE-flags it "PASSTHROUGH".** A false negative: the plugin exposes **no
   gain/level/drive** param, so the probe falls back to the first param (`low_cut`) and `extreme()` pushes it to its
   *first* enum value `'Off'` — which is the **default** → it compares **Off-vs-Off** → Δ0 → "ignores params." It
   absolutely renders; **verify by dialing a *real* value** (`low_cut='500 CPS'` → −59 dB @50 Hz, −0.3 @1 k).
3. **It is a PURE PASSIVE FILTER — it cannot warm / thicken / brighten / excite.** Only **4 params**, **no boost, no
   cut, no Q, no gain**, and **0.000 % THD** at every input level (just a +0.59 dB passband makeup gain). It
   *subtracts* frequencies, full stop. For tone/color/air/saturation use a different box (`[L] saturate-loop` ·
   [[excite]] · [[helios-type-69]] · tape) **before or after**.
4. **Slopes are passive, smooth, ~18 dB/oct — and the labels aren't −3 dB.** *LOW CUT (HPF):* the label reads ≈ the
   **−4 dB** point; the true **−3 dB sits ~6–12 % ABOVE** the label (50 CPS → −3 dB at ~59 Hz). Slope steepens from
   ~12 dB/oct at the knee to **~18 dB/oct** deep (50 CPS = −28 dB @20 Hz). *HIGH CUT (LPF):* label ≈ the **−3 dB**
   point; **gentlest at the very top** (15 KCS ≈ **12 dB/oct**, only −5 dB @15k) and **~18 dB/oct** lower down.
   **To cut more, step the frequency — don't expect a steeper slope.**
5. **All 4 params are enums → drive it with the [[vst-preset]] harness.** `low_cut`, `high_cut`, `enable` are
   **string** enums (`'50 CPS'`, `'5 KCS'`, `'In'`) that `apply-vst-chain`'s float dict silently misses.
   `enable='Out'` **and** `master_bypass=true` are both true bypasses (0.00 dB).
6. **Meters own it.** The proof of a filter move is the `measure-spectrum` band/centroid/tilt delta — and **crest is
   the tell**: band-limiting *raises* crest (rumble/sustain removed → more peaky).

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin(".../uaudio_pultec_hlf-3c.vst3")` →
`name="UADx Pultec HLF-3C EQ"`, `is_instrument=False`, renders (dialing real corners changes the audio; both knobs
`Off` or `enable='Out'` returns the input). Tested with **Pedalboard 0.9.23**, white-noise transfer-function
(output/input PSD ratio) for the slopes and the drum loop
`artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav` for the renders. The default load comes up
**flat** (`low_cut='Off'`, `high_cut='Off'`, `enable='In'`).

`list-vst-plugins {name_contains:"HLF"}` returns several entries — **use the VST3 `uaudio_` build**:

| Name | Path | Use |
|---|---|---|
| **UADx Pultec HLF-3C EQ** | `/Library/Audio/Plug-Ins/VST3/uaudio_pultec_hlf-3c.vst3` | ✅ this one (renders) |
| UAD Pultec HLF-3C | `…/Components/UAD Pultec HLF-3C.component` | ❌ passthrough twin (offline) |
| UADx Pultec HLF-3C (AU) | `…/Components/uaudio_pultec_hlf-3c.component` | AU twin (macOS-only) |

### The real parameter surface (Pedalboard-exposed — authoritative for this build)

**4 parameters, ALL enums.** That is the *entire* unit — no boost, no cut, no Q, no frequency-gain, no drive, no
output trim.

| Param | Type | Values | Control / measured behaviour |
|---|---|---|---|
| `low_cut` | enum | `Off` · `50` · `80` · `100` · `150` · `250` · `500` · `750` · `1000` · `1500` · `2000 CPS` | **high-pass** (CPS = Hz). Label ≈ −4 dB pt; ~18 dB/oct deep |
| `high_cut` | enum | `1.5` · `2` · `3` · `4` · `5` · `6` · `8` · `10` · `12` · `15 KCS` · `Off` | **low-pass** (KCS = kHz). Label ≈ −3 dB pt; 12 dB/oct @15k → ~18 dB/oct lower |
| `enable` | enum | `In` · `Out` | the **In/Out toggle** (the leftmost panel switch). `Out` = **true bypass** (0.00 dB) |
| `master_bypass` | enum | `false` · `true` | plugin bypass (also true bypass) |

> **If you reach for a param that isn't one of these four, you want a different plugin.** Boost/cut/shelf/peak → the
> UADx **EQP-1A** or **MEQ-5**; surgical/dynamic → [[fabfilter-pro-q-4]]; passive inductor EQ + drive → [[helios-type-69]].

### Footguns (proven on this rig)

1. **`probe_plugin.py` false-flags it as passthrough.** It has no gain/level param, so the probe's `pick_param`
   falls through to the first param `low_cut` and `extreme()` returns the first enum value `'Off'` = the default → it
   renders default-vs-default → Δ0 → "PASSTHROUGH ✗." **It renders.** Screen it instead by dialing a *real* corner
   (`low_cut='500 CPS'`) and re-measuring the spectrum ([[vst-verify]] with a real value).
2. **It's a filter, not an EQ.** No boost, no cut, no Q, no tone. It cannot add warmth, weight, air, or presence —
   only subtract. A "make it warmer/brighter" request is the **wrong tool**.
3. **Labels aren't −3 dB on the low-cut.** The labeled CPS reads ≈ the **−4 to −4.5 dB** point; the true −3 dB corner
   sits ~6–12 % above. And the **high-cut is weakest at 15 KCS** (~12 dB/oct). **To cut more, step the frequency**,
   not the slope.
4. **String enums need the harness.** `low_cut`/`high_cut`/`enable` are string enums — `apply-vst-chain`'s float-only
   dict silently misses them. Drive it with the **[[vst-preset]]** harness (`setattr`).
5. **`enable='Out'` / `master_bypass=true` = no effect** (0.00 dB) even with corners dialed — keep `enable='In'`.
6. **Wrong build = silent passthrough.** Load `uaudio_pultec_hlf-3c.vst3`; the `UAD …`/`/Universal Audio/` twins pass
   audio unprocessed offline — a 0.00 delta is the tell ([[vst-verify]]).

### Measured: LOW CUT (high-pass) frequency response

White-noise transfer function, dB relative to the passband (≈ unity at 1–2 kHz):

| `low_cut` | @20 Hz | @50 | @100 | @200 | @500 | @1k | true −3 dB | slope (deep) |
|---|---|---|---|---|---|---|---|---|
| **50 CPS** | −27.7 | **−4.5** | −0.5 | −0.1 | 0 | 0 | ~59 Hz | ~15→18 dB/oct |
| **100 CPS** | −43.5 | −16.3 | **−4.3** | −0.5 | −0.1 | 0 | ~111 Hz | ~17 |
| **250 CPS** | −69 | −41.2 | −24.8 | −8.4 | −0.3 | 0 | ~281 Hz | ~17.5 |
| **500 CPS** | −85 | −59.1 | −42.5 | −24.7 | **−4.4** | −0.3 | ~557 Hz | ~17 |
| **1000 CPS** | −93 | −78.3 | −61.3 | −43.2 | −19.5 | **−3.9** | ~1061 Hz | ~18 |

The bold cell is the labeled frequency (≈ −4 to −4.5 dB). It's a smooth ~18 dB/oct (3-pole-ish) passive high-pass —
the labeled value is the *knee*, not the −3 dB corner.

### Measured: HIGH CUT (low-pass) frequency response

| `high_cut` | @1k | @2k | @5k | @10k | @15k | @18k | true −3 dB | slope |
|---|---|---|---|---|---|---|---|---|
| **15 KCS** | 0 | 0 | −0.1 | −0.9 | **−5.0** | −8.7 | ~13.1 kHz | **~12 dB/oct** (gentlest) |
| **10 KCS** | 0 | 0 | −0.1 | **−3.1** | −11.5 | −16.2 | ~10.0 kHz | ~18 |
| **5 KCS** | −0.1 | −0.2 | **−3.8** | −18.0 | −28.0 | −32.4 | ~4.7 kHz | ~17 |
| **3 KCS** | −0.2 | −1.0 | −13.7 | −30.6 | −39.6 | −42.6 | ~2.75 kHz | ~17 |
| **1.5 KCS** | −1.0 | −8.8 | −30.7 | −46.0 | −49.6 | −49.5 | ~1.41 kHz | ~17 |

The high-cut label ≈ the −3 dB point. The **top setting (15 KCS) is a soft "air trim"** (~12 dB/oct); everything
below is a firmer ~18 dB/oct low-pass.

### Measured: coloration (THD) — it's a CLEAN filter

1 kHz tone in the passband (`low_cut=50`/`high_cut=15k`), several input levels:

| input | THD | H2 | passband Δlevel |
|---|---|---|---|
| −18 dBFS | **0.000 %** | −178 dB | +0.59 dB |
| −12 dBFS | 0.000 % | −153 dB | +0.59 dB |
| −6 dBFS | 0.000 % | −157 dB | +0.59 dB |
| −1 dBFS | 0.000 % | −154 dB | +0.59 dB |

**No useful saturation** — UA modeled the filter, not a driven amp/transformer character. The only level effect is a
constant +0.59 dB passband makeup gain (the harness peak-normalizes, so it's moot). **Color the signal elsewhere.**

### Measured: the three shipped presets (real `apply_vst_preset.py` harness + `[L]` meters, on the drum loop)

| metric (`[L]` meters) | dry | `drum-bus-shape` (50 / 15k) | `lofi-bandpass` (250 / 3k) | `tame-harsh-top` (off / 10k) |
|---|---|---|---|---|
| crest factor (dB) | 14.63 | **15.85** (+1.2) | **24.09** (+9.5) | 14.53 (≈) |
| spectral centroid (Hz) | 1593 | 1531 | 1363 | **1324** |
| spectral tilt (dB/oct) | −2.71 | −2.64 | −1.92 | **−3.48** |
| band-ratio low | 0.798 | 0.731 | **0.011** | 0.799 |
| band-ratio low-mid | 0.176 | 0.234 | **0.741** | 0.176 |
| 50 Hz (rel dB) | −7.6 | −9.6 | −32.6 | −7.6 |
| 10k / 16k (rel dB) | −28.8 / −41.0 | −28.0 / −44.4 | −42.7 / −65.0 | **−31.7 / −52.9** |
| dominant peak (Hz) | 70 | 70 | **199** | 70 |

- **`pultec-hlf-3c-drum-bus-shape`** (50 CPS / 15 KCS) — gentle musical band-limit: lows trimmed (ratio 0.80→0.73),
  top softened, **crest rises** (rumble between hits removed → more peaky). Subtle, "finished" drum bus.
- **`pultec-hlf-3c-lofi-bandpass`** (250 CPS / 3 KCS) — telephone/old-radio band: lows **gutted** (0.80→0.01), the
  dominant peak jumps 70→199 Hz, **crest 14.6→24.1** (sustained lows gone, transient midrange left). Best parallel/send.
- **`pultec-hlf-3c-tame-harsh-top`** (high_cut 10 KCS) — smooth top rolloff: centroid 1593→1324, tilt −2.7→−3.5,
  body below ~5 kHz **untouched**, crest unchanged (it darkens, it doesn't change dynamics).

**The crest direction is the proof:** band-limiting *raises* crest. A high-cut alone leaves crest flat (just darkens).
A 0.00 spectrum delta = the passthrough twin loaded (or `enable='Out'`).

### How to drive it headless

Use **[[vst-preset]]**'s `apply_vst_preset.py` (`setattr`s every param, strings included), setting **all 4** params
explicitly. `presets/vst/pultec-hlf-3c-*.json` are ready. Apply:
`../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
projects/<track>/mix/<stem>_hlf3c.wav`. Dump the live surface any time with
`presets/vst/dump_params.py uaudio_pultec_hlf-3c`; set `dump_state=true` (via `apply-vst-chain`) for a byte-stable
re-render. **Don't** screen it with `probe_plugin.py` (false passthrough) — verify with a real corner + a spectrum
re-measure.

---

# Part B — how the Pultec HLF-3C works (web-research synthesis, adversarially verified, cited)

> The *history / voice / usage* layer. Where it conflicts with **Part A (measured on this rig)**, **Part A wins** —
> and this section flags every collision inline. Uncertain claims are graded **(reported, unverified)**.

## 1. What it is — the Pultec filter

- **A dedicated passive high-pass + low-pass FILTER, not a boost/cut EQ.** The original **Pulse Techniques, Inc.**
  spec sheet titles it **"Program Improvement & Sound Effects Filter, Model HLF-3C."** It has exactly two
  selectors — **LOW CUT-OFF** (a *high-pass*) and **HIGH CUT-OFF** (a *low-pass*) — plus an **In/Out key** to throw
  the chosen filter pair in/out "on cue" (a broadcast/film need). It can only **attenuate** the band edges: **no
  gain, no peaking, no shelving boost.** [SUPPORTED — Part A confirms the 4-param surface] *(Pedantic note: a
  high/low-pass section is itself a kind of "cut"; "not a boost/cut EQ" means not a gain/peaking/shelving
  equalizer — which is exactly what it isn't.)*
- **Fully passive — no tube, no amplifier, no power.** Spec sheet: `POWER REQUIRED: None`. The topology is a
  **Constant-K LC ladder** (series caps + shunt inductor for the HPF; series inductors + shunt cap for the LPF),
  reverse-engineered as a **Butterworth Tee-LC** network at ~500–600 Ω, with shielded toroid coils and clickless
  11-position selectors. This is the opposite of Pultec's *program EQs* (EQP-1A / MEQ-5 / EQH-2), which boost **and**
  cut **and** carry a vacuum-tube make-up amp. **The HLF-3C adds essentially no colour of its own** — it *is* the
  filter. [SUPPORTED — Part A: 0.000 % THD]
- **The Pultec line & where this sits.** Pultec = **Pulse Techniques, Inc.**, founded ~1953 in Teaneck, NJ by
  **Eugene "Gene" Shenk** and **Ollie Summerlin**. The catalog centred on tube program EQs — EQP-1/EQP-1A (the
  iconic low-shelf boost-and-cut), MEQ-5 (midrange "power region" EQ), EQH-2, EQP-1A3 — and the **HLF-3C is the
  dedicated filter member**, for the jobs the gentle program EQs can't do: steep band-limiting (rumble/hum + hiss
  cleanup with minimal program loss) and **sound-effects** work. The original literature literally lists "telephone
  conversations, midget radios, sounds from outer space." Company closed 1981; brand revived ~2000 as **Pulse
  Techniques, LLC**. [SUPPORTED] *(The "MAVEC" name sometimes floated as a Pultec filter is **not a verifiable
  model** — the filter unit is the HLF-3/HLF-3C; treat MAVEC as spurious.)*
- **What UA modeled.** UA's HLF-3C ships only inside the **Pultec Passive EQ Collection** (with the EQP-1A + MEQ-5),
  in **two builds**: a UAD-2 **DSP** build ("Pultec HLF-3C," needs Apollo/Accelerator hardware) and a **UADx native**
  build ("Pultec HLF-3C EQ," CPU, AAX/AU/VST3 — the one this repo loads). The native build needs an **iLok *account***
  (free) but **no physical dongle**. [SUPPORTED] *(Strictly, all UADx natives need an iLok account; only the USB
  dongle is optional — so this doc says "iLok account, no dongle," not "no-iLok.")*

## 2. Filter specs — slopes & frequency points (reconciled with the measurements)

**Frequency points (manufacturer spec — trustworthy, and confirmed by Part A's enum dump):**

| Section | Control | Positions (10 active + Off) |
|---|---|---|
| high-pass | LOW CUT-OFF (CPS = Hz) | 50 · 80 · 100 · 150 · 250 · 500 · 750 · 1000 · 1500 · 2000 (+ Off) |
| low-pass | HIGH CUT-OFF (KCS = kHz) | 1.5 · 2 · 3 · 4 · 5 · 6 · 8 · 10 · 12 · 15 (+ Off) |

> **Source disagreement, resolved:** one secondary guide lists "HP 50–400 Hz / LP 3–12 kHz" — **wrong** (AI summaries
> echoed it). Trust the manufacturer set above (HP up to **2 kHz**, LP from **1.5 kHz**), which Part A's
> `low_cut`/`high_cut` enums match exactly. UA's docs say "eleven frequencies" but enumerate ten active values per
> band — the eleventh is the **Off** position (a counting artifact, not a hidden setting).

**Slope — lore vs. measured:**

- The **published nominal figure is 12 dB/octave (2nd-order)** for both sections, stated by UA's copy and echoed by
  the Red Rock Sound / Reason clones, Vintage King, and Gearspace. **But it is not a clean number:** the original
  spec sheet prints only `CIRCUIT: Constant K` (no dB/oct), the **Butterworth Tee-LC** topology has *three* reactive
  elements (→ 3rd-order → ~18 dB/oct asymptote), and UAD-forum analyzer traces report **~18 dB/oct** ("steeper than
  it seems because it's so smooth"). *(forum: reported, med confidence.)*
- **Part A reconciles them, and Part A wins:** the roll-off is **~12 dB/oct near the knee, steepening to ~18 dB/oct
  deep in the stopband** (low-cut everywhere; high-cut at the lower settings, **gentlest at 15 KCS ≈ 12 dB/oct**).
  **No source cites 6 dB/oct.** Two engine truths from Part A: (a) the **low-cut label is NOT the −3 dB corner** — it's
  ~the −4 dB point and the real corner sits a few % higher, so dial *one notch above* where you'd expect it; (b) the
  high-cut is frequency-dependent — `15 KCS` is a soft air-tilt, `1.5 KCS` is a near-telephone band.

## 3. Sonic character — why passive filters sound "musical"

- **Clean, non-resonant, no saturation.** No active stage / tube / transformer in the path → no harmonic generation
  (Part A: **0.000 % passband THD**, just a +0.59 dB makeup-gain rise). If a render shows colour *beyond* the filter
  curve, you loaded the wrong thing or are hearing something upstream.
- **Smooth, gentle knees.** A passive Butterworth-Tee LC network has a **maximally-flat passband with no Q peak at
  the corner** under proper termination, so it doesn't ring or whistle at cutoff — the "you don't hear it working"
  reputation. Passive R/L/C parts only *attenuate*; they can't self-resonate, whereas active op-amp filters use
  feedback that can build a resonant edge (even self-oscillate). The steepening to ~18 dB/oct happens *down in the
  stopband*, so the audible transition still feels gradual. [SUPPORTED in principle; med confidence that UA models
  it exactly as a textbook Butterworth — but Part A's smooth, peak-free curves are consistent with it.]
- **The colour mystique is the EQP-1A/MEQ-5, not this box.** "Sounds better just passing through," tube glow,
  transformer harmonics, the "Pultec low-end trick" (boost+cut the same low band) — all belong to the **tube program
  EQs**. The HLF-3C is the clean, surgical-but-musical band-limiter of the family.

## 4. How engineers use it (verify by ear/meter; quantize to the real steps)

| Source / job | Move (starting points) |
|---|---|
| **High-pass rumble/mud** | LOW CUT **50–80 Hz** (subsonic under a full mix/bass) · **100–150 Hz** (thin guitars/vox/OH, clear mud). |
| **Tame harsh/hiss/digital top** | HIGH CUT **10–15 KCS** (gentle analog roll-off on a bright mix/cymbals) · **5–8 KCS** (darker, vintage sources). |
| **Lo-fi / telephone / "midget radio"** | LOW CUT **300–500 CPS** + HIGH CUT **1.5–3 KCS** (the bandpass UA itself markets; the high LOW-CUT steps exist for this). |
| **Drum bus** | LOW CUT **80–100 CPS** *before* the bus comp (kick sub won't pump it) + HIGH CUT **10–15 KCS** to round cymbals/OH hiss. (UA ships a Jacknife Lee "Drum Buss Earth and Air" preset.) |
| **Bass** | LOW CUT **~50 CPS** (shed subsonic only, keep the fundamental); shape the body with the EQP-1A, not this. |
| **Guitars** | LOW CUT **100–150 CPS** (clear mud under bass/kick) + HIGH CUT **8–12 KCS** (tame amp/DI fizz); steep both ends = a lo-fi DI part (UA's own demo). |
| **Vocals** | LOW CUT **80–150 CPS** (rumble/plosives/proximity boom); telephone FX = LOW CUT ~300–500 + HIGH CUT ~3 KCS. |
| **Mix-bus / master (gentle)** | LOW CUT **50 CPS** (subsonic clean-up) + HIGH CUT **15 KCS** (subtle analog top-and-tail). Gentlest steps only; it's a corrective trim, not the loudness stage. |

**The "Pultec stack" (the idiomatic pairing):** EQP-1A does the low-end trick (boost + cut the same low band → a
tight resonant bump with a scoop above) and the 16 kHz "air" shelf; the **HLF-3C then high-passes the true subsonic
junk *below* that bump** (e.g. EQP-1A boost 60 Hz → HLF-3C LOW CUT 50 Hz) and can low-pass the air so it doesn't turn
to hiss. EQP-1A = colour + curves; HLF-3C = clean band-edge trim. [well-supported]

## 5. Pitfalls / gotchas

1. **It's a filter, not an EQ** — no boost/cut/Q/tone. It can't warm, thicken, brighten, or excite — only subtract.
2. **The probe lies here** — `probe_plugin.py` false-flags it passthrough (no gain param; Part A footgun 1). Verify
   with a real corner.
3. **Low-cut labels aren't −3 dB** (≈ −4 dB pt) and the **high-cut is weakest at 15 KCS** — to cut more, **step the
   frequency**, not the slope (there's no slope control).
4. **Don't over-filter** — removed lows/highs are gone; re-measure before stacking another cut.
5. **Wrong build / `enable='Out'` / `master_bypass`** = silent passthrough (0.00 dB) — load `uaudio_*.vst3`, keep
   `enable='In'`, and drive the string enums via the [[vst-preset]] harness.
6. **For *dynamic* harshness** (ringing, level-dependent spit) a static high-cut just dulls the whole thing — reach
   for [[de-harsh]] / [[de-ess]] / [[fabfilter-pro-q-4]] Spectral Dynamics instead.

> **Pure-DSP equivalents (no plugin, deterministic):** high/low-pass + tilt → `[L] apply-eq`; dynamic de-harsh →
> [[de-harsh]] / [[de-ess]]; air/presence → [[excite]]; saturation/warmth (the thing this box can't do) →
> `[L] saturate-loop` / [[helios-type-69]] / [[studer-a800]] / [[ampex-atr-102]]. Reach for the HLF-3C when you want
> *its* smooth, musical passive band-limit specifically — or the authentic Pultec lo-fi/telephone effect.

## Sources

UA — Pultec Passive EQ Collection manual (help.uaudio.com), Pultec Collection Tips & Tricks · Pulse Techniques /
Red Rock Sound HLF3C-PC clone spec · Vintage King — Pultec HLF-3C listings · Gearspace — Pulse Techniques HLF-3C ·
Wikipedia — Pultec EQP-1 · Sound on Sound — *Pulse Techniques EQP-1A* & *Warm Audio EQP-WA* reviews · Manley —
Pultec EQP-1A legacy page · AudioScape — MEQ-5 · A Designs / blog.mixanalog / nailthemix — Pultec-trick & HPF/LPF
technique · Magnetic / 2n3904blog — passive-LC / Butterworth & resonance theory. Plus **our own param-surface dump +
swept frequency-response / THD / meter render results (Part A)** on
`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_hlf-3c.vst3` via Pedalboard 0.9.23.

---
