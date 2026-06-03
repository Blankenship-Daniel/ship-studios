# KIT BB N73 — field guide: the Blackbird Neve 1073 channel, warm + weighty, headless

How to drive the **KIT Plugins BB N73** (`KIT BB N73.vst3`) — a sampled emulation of the **Neve 1073**
mic-pre + 3-band EQ, modeled from twelve vintage 1073s in the private collection at **Blackbird Studio**,
Nashville. This is the **classic, weightier 1073** Neve — the simpler 3-band sibling of the 4-band
**[[kit-bb-n105]]** (Neve 8078 / 31105) and the warm counterpart to the punchy API **[[kit-bb-a5]]** /
**[[api-vision-channel-strip]]**. **Part A** is *measured on this rig* (the real Pedalboard param surface +
isolation numbers from our own renders); **Part B** is a *web-research synthesis* (cited, adversarially
verified). The skill **[[kit-bb-n73]]** is the measured workflow.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the crest that
> proves "punch." Verify with `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` /
> `check-clipping`. Mic-mode drive raises level *and* true-peak — re-measure after every change, A/B
> loudness-matched.

---

## TL;DR (the headline, measured)

1. **It RENDERS headless here — proven, not assumed.** `KIT BB N73.vst3` loads via Pedalboard, is iLok
   **machine-authorized** on this Mac, and **responds to its params** (push `output_gain` → output differs
   by Δ=1.95, not passthrough). **But loads≠renders is the standing rule — re-screen with [[vst-verify]] on
   any other host** (iLok Cloud / unlicensed nodes demo-silent; see §B7).
2. **It's a 1073, not a 31105 — 3 EQ bands only.** A **fixed 12 kHz** high shelf (gain only, *no* freq
   selector), a **sweepable mid bell** (`360 / 700 / 1.6k / 3.2k / 4.8k / 7.2k`), a **sweepable low shelf**
   (`35 / 60 / 110 / 220`), and a steep **HPF** (`50 / 80 / 160 / 300`). **No low-mid band, no LPF, no Hi-Q.**
   That's the whole difference from the N105 (which is 4-band + LPF + Hi-Q). All three EQ bands are **±18 dB**.
3. **The Neve color is MIC-MODE ONLY.** In **Line** mode (the default) `pre_amp_sensitivity` *and*
   `pre_amp_saturation` are **inert — byte-identical, 0.00 % THD at every setting**. Switch
   `pre_amp_mode="Mic"` for the transformer/preamp drive: sensitivity adds **a lot** of gain
   (**−80 = max, ~+23 dB over −20**).
4. **`pre_amp_saturation=TRUE` is mandatory in Mic mode.** With saturation **ON** the Mic stage is the
   controlled soft-transformer path (**~0.2–0.3 % THD**, level-managed). With saturation **OFF** the Mic
   preamp is a raw high-gain amp that **digitally CLIPS when driven** (**23 % THD @ sens −50, 46 % @ −80**) —
   only reach for sat-off as a deliberate overdrive effect. *(This is the opposite emphasis from the N105,
   where Mic was always gentle.)*
5. **On a real drum bus, Mic drive = WEIGHT + warmth, not sheen.** It added low-end weight **beyond the EQ
   alone** (low ratio 0.542 → **0.671**, vs 0.605 from the same EQ in clean Line mode), stayed **dark**
   (centroid +81 Hz, vs +571 for clean Line), and **kept crest** (23.6 → 23.1). Warmth from the transformer,
   **not from an EQ air boost** — exactly the house **warm + tight** preference.
6. **`master_bus_toggle` IS host-exposed here** (it wasn't on the N105): `MST On` = a subtle 8058/8078
   master-buss **glue** (~1.9 % THD on a sine, faint density, crest −0.2). **No host Auto-Gain.**
7. **Every param is an enum.** Numeric controls accept a **float** (rounded to 0.1) — gains reach via
   `apply-vst-chain`. **Frequencies / modes / switches are string/bool enums** the float dict can't set →
   use the **[[vst-preset]]** harness.

---

# Part A — measured on this rig

Probe: `KIT BB N73.vst3` via Pedalboard, processing `projects/watercolors/mix/bus_warm_pre_dry.wav` (a
measured-balanced, dry drum bus) plus deterministic noise/sine for isolation. Spectral comparisons are
peak-normalized so only **shape / crest** is judged.

### The real parameter surface (Pedalboard-exposed — authoritative for this build)

**18 params, all enum-valued.** Default: `eq="EQ On"`, `pre_amp_mode="Line"`, `pre_amp_saturation=False`,
all EQ bands `OFF`/0 dB, `hpf="OFF"`, `hum=True` (L1), `master_bus_toggle="MST Off"`, trims/gains 0, `bypass=False`.

| Param | Values *(default)* | Role |
|---|---|---|
| `pre_amp_mode` | `Line` · `Mic` *(Line)* | input stage — **Mic = where the drive/saturation lives** |
| `pre_amp_sensitivity` | −80 … −20 dB, 0.1 step *(−20)* | Mic gain/drive (**−80 = MAX gain**, −20 = min/unity). **Inert in Line.** |
| `pre_amp_saturation` | `True`/`False` *(False)* | transformer saturation. **Inert in Line.** In Mic: **True = controlled soft path, False = raw clip when driven.** |
| `high_shelf_gain` | ±18 dB, 0.1 *(0)* | **HF band — FIXED 12 kHz shelf** (gain only, **no frequency selector** — that's the 1073) |
| `mid_gain` / `mid_frequency` | ±18 dB / `OFF,360,700,1.6k,3.2k,4.8k,7.2k` *(OFF)* | **mid bell**, broad musical Q |
| `low_gain` / `low_frequency` | ±18 dB / `OFF,35,60,110,220 Hz` *(OFF)* | **low shelf** |
| `hpf_frequency` | `OFF,50,80,160,300 Hz` *(OFF)* | **high-pass** corner (top = 300 Hz, steep) |
| `phase` | `Normal`·`Reversed` | polarity flip (the `ph` button) |
| `eq` | `EQ On`·`EQ Off` *(EQ On)* | EQ in/out (the `eq` button) |
| `input_trim` | −36 … +36 dB, 0.1 *(0)* | clean input trim (the top **"In"** knob) — linear |
| `output_trim` | −36 … +36 dB, 0.1 *(0)* | clean output trim (the top **"Out"** knob) — linear |
| `output_gain` | −40 … +20 dB *(0)* | output **fader** (the big right slider) — linear |
| `master_bus_toggle` | `MST Off`·`MST On` *(MST Off)* | **8058/8078 master-buss saturation/glue** (the `MSTR BUSS` button) — **host-exposed** |
| `hum` / `hum_level` | bool *(True)* / `1`·`2`·`3` *(1)* | analog hum (~60 Hz). **Negligible offline.** |
| `bypass` | `False`/`True` | true bypass |

> **Three gain stages, one colored.** `pre_amp_sensitivity` (the red **Mic** knob) is the *only* nonlinear
> gain — and only in Mic mode. `input_trim` / `output_trim` (top "In"/"Out" knobs) and `output_gain` (right
> fader) are **linear**. The GUI **"Saturation"** block = `pre_amp_mode` + `pre_amp_saturation`.
>
> **Not host-exposed:** Auto-Gain, Continuous (un-stepped gain), Oversampling (Low/Med/High), Tooltips/Fader,
> instance-linking — **GUI-only** (only the 18 above automate). No Auto-Gain → compensate Mic drive by hand.
>
> **Setting params:** numeric gains/trims (`*_gain`, `*_trim`, `pre_amp_sensitivity`, `output_gain`) accept a
> **float** — `apply-vst-chain`'s float dict reaches those. **Frequencies (`"60 Hz"`,`"3.2 kHz"`), modes
> (`"Mic"`), `eq`, `phase`, `hum`, `master_bus_toggle` are STRING/bool enums** → set via [[vst-preset]].

### Render proof + console color at unity (Line, all bands flat)

| | crest | centroid | note |
|---|---|---|---|
| bypass | 13.54 | 12037 | source (hot noise) |
| default flat (Line, EQ on, hum off) | 11.98 | 11508 | **near-transparent in tone**; a faint always-on **peak-rounding** (crest −1.5 on hot noise) — the Class-A EQ/output stage colors gently even flat |
| push `output_gain` extreme | — | — | **responds to params → RENDERS ✓** (Δ=1.95 vs default) |

The tone shape is essentially unchanged at unity (per-band Δ within ~1 dB after peak-norm); the only real
effect is a gentle transient rounding — the analog-stage character is **opt-in**, not forced.

### Preamp: Line is inert, Mic is the color — and `saturation` flips it (1 kHz sine, THD + gain)

| config | THD @0.25 in | THD @0.9 in | read |
|---|---|---|---|
| **Line** clean / SAT / any sens | **0.00 %** | 0.18 % | **all identical — Line preamp is INERT** (the 0.18 % @ hot in is the output stage) |
| **Mic** clean (sat OFF) sens −50 | **23.6 %** | 29.3 % | raw high-gain pre **CLIPS** (+18 dB of gain, uncompensated) |
| **Mic** clean (sat OFF) sens −80 | **46.0 %** | 44.6 % | max drive — hard digital clip (+23 dB) |
| **Mic** SAT (sat ON) sens −50 | **0.18 %** | 0.18 % | **controlled soft path** — clean, level-managed to ~−1 dBFS |
| **Mic** SAT (sat ON) sens −80 | 0.18 % | 0.32 % | max drive, still controlled (≈ +6 dBFS) |

**Mic sensitivity adds gain:** at a −12 dBFS sine, output peak (sat off) ran −11.6 (sens −20) → +6.1 (−50)
→ +11.2 (−80): a **~+23 dB** span. **Takeaway:** for usable Neve drive use **Mic + `pre_amp_saturation=True`**
(the gentle, gain-managed transformer path, sub-1 % THD). **Mic + sat OFF, driven, is a clipping overdrive**
(creative use only). **Line mode: skip the preamp section entirely** (it's a clean EQ console). Per Part B the
harmonics are a **rich 2nd+3rd blend** (not "odd-order"), euphonic in the lows.

### EQ / filter isolation (peak-normalized noise, Δ band-energy vs flat)

| move | sub | low | lomid | mid | hi | air | read |
|---|---|---|---|---|---|---|---|
| HF shelf +12 (fixed 12k) | — | — | — | −5.7 | −0.8 | **+1.0** | air shelf; centroid 11508→**12827** |
| MID +12 @360 | — | **+5.0** | **+7.6** | — | — | — | broad low-mid bell |
| MID +12 @700 | — | — | **+5.7** | +3.7 | — | — | de-box / body bell |
| MID +12 @1.6k | — | — | +1.5 | **+5.0** | — | — | presence |
| MID +12 @3.2k | — | — | — | +1.6 | **+2.0** | — | edge/attack |
| MID +12 @7.2k | — | — | — | — | **+1.0** | — | top presence (still below 12k) |
| MID −12 @700 | — | — | **−6.8** | −4.5 | — | — | symmetric de-box cut |
| LOW shelf +12 @35 | **+10.5** | +5.6 | — | — | — | — | sub weight |
| LOW shelf +12 @110 | +10.3 | **+9.2** | +1.5 | — | — | — | low weight |
| LOW shelf +12 @220 | +9.1 | +8.8 | **+4.2** | — | — | — | broad warmth |
| HPF @80 | **−8.2** | −1.0 | — | — | — | — | gentle low-cut |
| HPF @160 | **−32.5** | −3.5 | — | — | — | — | steep |
| HPF @300 | **−57.6** | **−19.2** | −0.9 | — | — | — | very steep (≈18 dB/oct family, 1073) |

Every band does exactly what a 1073 should: a broad musical mid bell that sweeps 360→7.2k, broad low/high
shelves, and a steep classic HPF. The HF shelf hinges at a **fixed 12 kHz** (no freq control) — the
defining 1073 trait. Boosts are wide and forgiving (proportional-style), not surgical.

### Master Buss + analog hum

- **`master_bus_toggle="MST On"`** adds **+0.17 dB broadband** density, **~1.9 % THD** on a 1 kHz sine,
  and a slight peak-round (crest 11.98 → 11.80) — a **subtle bus-glue saturation** (the 8058/8078 output
  stage). It's gentle; reach for it for cohesion on a bus, leave it off on a single channel.
- **analog hum:** broadband RMS **unchanged** across `hum` Off / L1 / L3 on a −60 dBFS signal — **negligible
  in an offline render.** Leave it off for clean stems.

### Real dry drum bus → the warm recipe (full bus, stemmy meters, peak-norm −1 dBFS)

| | LUFS-I | true-peak | crest | centroid | tilt dB/oct | low | low-mid | high |
|---|---|---|---|---|---|---|---|---|
| dry | −25.4 | −5.99 | 23.64 | 3128 | −2.26 | 0.542 | 0.378 | 0.0115 |
| line-clean (same EQ, **no drive**) | −20.0 | −0.92 | 23.08 | **3699** | −2.20 | 0.605 | 0.327 | 0.0120 |
| **n73-warm** (Mic sat sens −47) | −20.2 | −0.97 | **23.11** | **3209** | −2.22 | **0.671** | **0.267** | 0.0122 |
| n73 +air (HF +2 @12k) | −20.3 | −0.96 | 23.28 | 3420 | −2.06 | 0.670 | 0.257 | 0.0157 |
| n73 +MST glue | −19.4 | −0.97 | 22.22 | 3209 | −2.22 | 0.674 | 0.263 | 0.0122 |
| n73 more drive (sens −55) | −20.7 | −0.99 | 23.47 | 3193 | −2.20 | 0.725 | 0.218 | — |

The warm recipe (Mic sat sens −47 + 50 Hz HPF + 60 Hz low shelf +3 + 700 Hz −2 de-box, HF **off**,
output −12) **added low weight, de-boxed the low-mids, stayed dark, and kept crest.** The decisive proof
that the warmth is the *transformer*, not EQ: with the **identical EQ** in clean **Line** mode the low ratio
only reached 0.605 and the centroid jumped to **3699** (brighter); **Mic drive** pushed the low ratio to
**0.671** and held the centroid at **3209** (dark, warm). → preset `bb-n73-warm-drum-bus.json`.

> **N73 vs N105 (both measured on this same bus):** the **N105** Mic drive *tightened* the sub and added
> **sheen** (centroid +411, crest **up** 23.6→24.5); the **N73** Mic drive *adds low **weight*** and stays
> **dark** (centroid +81, crest ≈ flat). Pick **N73** for thick, classic-1073 weight; **N105** for a
> cleaner 4-band Neve with more top sheen + surgical Hi-Q.

### Preset (`presets/vst/`)

- **`bb-n73-warm-drum-bus.json`** — the warm-weighty 1073 drum bus above (Mic transformer drive + weight +
  de-box + HPF, HF off). Apply with the harness. Variants in the preset notes: `high_shelf_gain=2.0` for
  "Neve air," `master_bus_toggle="MST On"` for glue, `hpf_frequency="80 Hz"` + `low_gain` +2 for a tighter low.

---

# Part B — how the console works (web-research synthesis, cited, adversarially verified)

> Where Part A measured something Part B could only flag as uncertain, **Part A is authoritative** and noted
> inline.

## 1. What it is / lineage

The **KIT Plugins BB N73** emulates the **Neve 1073** mic-preamp + EQ module (Rupert Neve, **1970**, first
laid out for the Wessex A88 console), modeled from **twelve vintage 1073s** in **Blackbird Studio**'s
(Nashville; John McBride) private collection, captured with KIT's **Full Range Modeling (FRM)** (10 Hz–96 kHz).
*(HIGH.)*

- **BB N73 = 1073** (single discrete-Class-A preamp + **3-band** EQ). **BB N105 = 8078 / 31105** (a later,
  1081-derived console channel — **4-band** parametric + HPF *and* LPF). **Genuinely different Neve modules
  — don't transfer band counts, frequencies, or param names between them.** *(HIGH — confirmed.)*
- The N73's **master/output stage is *not* a 1073 part:** KIT's page cites a **Neve 8058** output buss; Sound
  on Sound says the latest version models the **8078** output transformers. Sources conflict on the donor
  console; both agree it adds *console* output character the bare 1073 lacks. **Part A: this stage is the
  host-exposed `master_bus_toggle` ("MST On") — a subtle saturation/glue, ~1.9 % THD on a sine.** *(donor #
  MEDIUM; host-exposure HIGH via Part A.)*
- **Formats:** VST3, AU (macOS), AAX, 64-bit; macOS 10.14+ (Intel + Apple Silicon), Win 7+. Headless: load the
  **VST3** (cross-platform) or **AU** (macOS-only). *(HIGH.)*

## 2. Signal flow & controls

Input (**Mic / Line**) → preamp **saturation** → 3-band EQ (HF/MF/LF, `eq` in/out, `ph` polarity) → **HPF** →
**Output** fader; plus **Analog Hum** (off + 3 levels) and a **Master-Buss** output stage.

- **Mic mode** — the red mic-gain knob is live; **this is where saturation is generated.** **Line mode** — the
  mic knob is disabled; use the input/output trims to place level. **Part A confirms: Line is fully inert for
  drive/saturation; the color is Mic-only** (settling KIT's marketing claim of "saturation in both modes" —
  Sound on Sound's "mic-only" read is correct). *(HIGH via Part A.)*
- **EQ:** the **HF shelf is continuously variable** (fixed 12 kHz, no individual bypass); the **mid bell, low
  shelf, and HPF** each switch off via their `OFF`/frequency selector; plus an overall **EQ in/out**. The 1073
  EQ is **proportional/forgiving** (a boost causes a small adjacent dip). *(HIGH.)*
- **Top-bar utilities — GUI-only here (Part A: not host-exposed):** **Auto-Gain** (rides output down as mic
  gain rises — loudness-matched drive), **Continuous** (un-steps the mic gain), **Oversampling** (Low/Med/High).
  **No host Auto-Gain → compensate Mic drive with `output_gain`/trims by hand.** *(HIGH via Part A.)*

## 3. The EQ surface (matches Part A's probe exactly)

| Band | Type | Frequencies | Gain |
|---|---|---|---|
| **HF** | shelf, **fixed**, continuously variable | **12 kHz** (only) | **±18 dB** ¹ |
| **MF** | peaking **bell**, fixed/self-narrowing Q | **360 / 700 / 1.6k / 3.2k / 4.8k / 7.2k** | **±18 dB** |
| **LF** | shelf | **35 / 60 / 110 / 220 Hz** | **±18 dB** ¹ |
| **HPF** | high-pass, **18 dB/oct** (3rd-order) | **50 / 80 / 160 / 300 Hz** | filter |

¹ **dB-range settled:** AMS Neve *hardware* spec is HF/LF shelves ±16 dB, mid ±18 dB; Sound on Sound said the
*plugin* reads all ±18. **Part A's param dump confirms all three bands are ±18 dB** in this build (KIT extends
the shelves). The mid/low/HPF frequency sets are **unanimous** across AMS Neve, Sound on Sound, UAD, Vintage
King (no source disagreement). **No LPF and no separate low-mid band** — those are the 31105/1081 (the N105).
*(HIGH.)*

## 4. The "Neve" character

The tone is **transformer + discrete-Class-A preamp saturation**, not an EQ curve — the **Marinair input
transformer** (later St Ives/Carnhill) + gapped **LO1166 output transformer** + Class-A path. AMS Neve credits
the transformers with "the balanced, subtle harmonic saturation for which the 1073 is famous." *(HIGH.)*

- **Harmonic signature — corrected lore:** the 1073 is **NOT predominantly odd-order.** Bench measurements of
  faithful 1073s show **roughly equal 2nd + 3rd harmonics (3rd slightly greater)** at very low THD
  (~0.002 % min gain → ~0.02 % driven). Transformer = the odd (3rd), Class-A transistor = the even (2nd). Call
  it a **rich, mostly low-frequency 2nd+3rd blend** — warm with a touch of edge, not "odd-order." *(HIGH —
  corrected.)* *(Part A note: the **gentle analog regime** is `Mic + saturation ON` at sub-1 % THD; the 23–46 %
  THD figures Part A measured are the **sat-OFF digital-clip** regime, a different, harsher beast.)*
- **Tonal result:** full rich **bottom**, **forward mids**, **silky top**; discrete Class-A = no
  crossover/switching distortion, so driven 1073s stay **smooth, not buzzy**. On drums it reads as **forward
  punch + density on transients without dulling attack.** Coloration is **gain-driven** (push the mic stage,
  trim back) and **mostly low-frequency** — it flatters **kick / snare body / toms** more than cymbals. *(HIGH;
  band-dependent nuance LOW.)*

## 5. Using it on drums (Neve = warm/weighty; API = punchy; SSL = clean glue)

Use only the 1073's real bands (fixed 12 k HF shelf, mid bell 360–7.2k, low shelf 35–220, HPF 50–300):

- **Kick:** **HPF OFF** (keep the lows); low shelf **+ @ 110** for weight (or **60** for sub-thump); small
  mid **@ 1.6 / 3.2 k** for beater click; Mic drive for transformer weight. *(MEDIUM.)*
- **Snare:** **HPF ~80**; low shelf/body **@ 220**; mid **@ 3.2 k** for snap; lift **12 k** for air; the
  1073 smooths the snare-top transient while keeping it forward. *(MEDIUM.)*
- **Overheads:** **reduce mic gain** (hot source); **12 k** shelf for air; little drive — pushed top colors
  less euphonically (see §6). *(MEDIUM.)*
- **Room:** lean in — drive harder for grit/density; **HPF 160–300** to kill boom; mid bell for presence.
- **Drum bus:** small moves — low shelf **+1–3 @ 60–110** (weight), **12 k** for sheen, modest Mic drive +
  optional **MST On** glue. House **warm + tight**: use the N73 as **tone + weight**; reach for
  [[api-vision-channel-strip]] / [[drum-punch]] for transient punch. → preset `bb-n73-warm-drum-bus.json`.

## 6. Harshness — why & what to move

- **Mid bell at 3.2 / 4.8 / 7.2 k** (±18 dB, Q narrows as you boost) is the prime edge source → pull back or
  step to **1.6 k**.
- **Fixed 12 k shelf** over-lifted on bright cymbals/hats reads brittle → reduce the shelf, not the mids.
- **Driving Mic hard on a bright source** pushes grit into the harsh band (saturation is gentler up top than
  in the lows) → back off `pre_amp_sensitivity`, recover level with `output_gain`. **Sat OFF + driven = a
  clipping fizz** (Part A) — keep saturation ON unless you want that.
- **Master-Buss over-engaged** smears transients → it's subtle here, but back off if crest drops too far.
- Mirrors the house hi-hat note (lift air but de-harsh 5–7 k); for surgical residue use [[de-harsh]] /
  [[fabfilter-pro-q-4]].

## 7. Licensing & headless/offline rendering

- **iLok / PACE only** (free iLok account + License Manager; no serial alternative). **2 activations** per
  license; perpetual, **list $150** (intro $75; 14-day trial). *(HIGH.)*
- **Headless = conditional.** Offline rendering works **only** via an offline-capable activation — **Machine
  activation or iLok USB dongle**. **iLok Cloud needs continuous internet** → unusable on air-gapped nodes.
- **Local ground truth:** on **this Mac** it's machine-licensed and **Part A proved it renders headless** and
  responds to params. **Elsewhere, re-verify** — an unlicensed iLok plugin instantiates in **demo/silent**
  mode (loads≠renders), and a PACE wrapper bug can **hang headless scanners**. Pin versions; persist
  `dump_state`; screen with [[vst-verify]] (measure *detail* — THD/spectrum — not just `changed:true`).
  >2 render nodes exceed the 2-activation cap.

## 8. Pitfalls & gotchas

- **N73 ≠ N105.** 1073 (3-band, fixed 12 k HF, no LPF, no low-mid, no Hi-Q) vs 31105/8078 (4-band + LPF + Hi-Q).
- **Line preamp is inert** — switch to **Mic** for any drive; **keep `pre_amp_saturation` ON** in Mic (off =
  raw clip when driven). **No host Auto-Gain** → compensate level with `output_gain`/trims.
- **HF is a fixed 12 kHz shelf** (no freq selector). **No LPF.** All three EQ bands **±18 dB**. **HPF top = 300 Hz.**
- **`master_bus_toggle` is host-exposed** (subtle glue); **Auto-Gain / Continuous / Oversampling are GUI-only.**
- **All params enum** — float for gains/trims, **strings for freq/mode/switch** → [[vst-preset]] (the float
  dict silently misses every string enum — the documented KIT/SSL trap).
- **analog hum negligible offline.** **Loudness-match before any A/B** — Mic drive + boosts raise level.
- A channel strip is per-track/bus tone, **not** mastering — keep it off the master 2-bus ([[vst-master]]).
- **Still unverified from public sources:** the donor console for the output stage (8058 vs 8078), the mid
  band's numeric Q, the Low/Med/High→oversampling-factor map, and whether KIT's V-update changed the audio model.

> Pure-DSP approximation (no VST): 1073-style warmth ≈ `[L] saturate-loop` (tape/tanh); the 3-band 1073 grid
> ≈ `[L] apply-eq` (12 k shelf + mid bell + low shelf) + HPF; prove warmth kept punch (crest/PLR) with
> `[L] measure-microdynamics`.

---

## Sources

KIT Plugins (kitplugins.com/products/bb-n73 · /kit-bb-n105 · /bb-a5) · Sound on Sound (BB N73, BB N105,
Neve 1073N / 1073LB / 1073 SPX, BAE 1073 DMP reviews) · AMS Neve official (1073 Mic Preamp & Equaliser
spec; About Marinair; 1084) · Universal Audio (Neve 1073 Preamp EQ manual; "overdriving the 1073" tips) ·
Vintage King (1073 mic-pre; modern 1073 reproductions) · Sweetwater (1073 history; KIT activation
instructions) · help.ilok.com (Cloud vs Machine/USB offline) · paceap.com (iLok Cloud) · gearspace (1073
harmonic-distortion analysis). Plus **our own param-enumeration / isolation / sweep / shootout
measurements** (Part A) on `KIT BB N73.vst3`.
