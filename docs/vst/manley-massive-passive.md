# UADx Manley Massive Passive (+ MST) — field guide: parallel passive tube EQ, headless

How to drive the **UADx Manley Massive Passive** — Universal Audio's model of the **Manley Labs Massive
Passive Stereo Tube Equalizer** (Chino, CA; introduced **1998**). UA ships **two** plug-ins: the **standard
Massive Passive** (`uaudio_manley_massive_passive.vst3` — ±20 dB, continuous controls; the unit in the screenshot
that names itself "MASSIVE PASSIVE STEREO EQUALIZER") and the **Massive Passive Mastering EQ (MST)**
(`uaudio_manley_massive_passive_m.vst3` — ±11 dB, fully detented/stepped + a recallable ±2.5 dB L/R trim). This
guide leads with the **standard** build and flags every standard-vs-MST difference. It's the broad/musical,
**parallel passive** tube EQ counterpart to the surgical [[fabfilter-pro-q-4]], the program-EQ
[[pultec-eqp-1a]], and the Motown graphic [[hitsville-eq-mastering]] — the measured deep-dive
behind the [[manley-massive-passive]] skill and a plugin-specific specialization of [[vst-eq]] / [[vst-master]].

**Part A** is *measured on this rig* (the real Pedalboard param surface + Welch transfer-function / THD render
results — `scripts/mix/massive_passive_sweep.py`). **Part B** is a *web-research synthesis, cited* (the Manley
owner's manual + UA's plugin manual + Sound on Sound / MusicRadar), **adversarially fact-checked** — corrected
claims flagged inline. Where the two meet they agree to the dB: the manual's "±20 dB only when narrowest,"
"BELL narrow = more gain," the "Pultec shelf overshoot," and "parallel bands don't sum" all reproduce in the
numbers below. **Where they differ, Part A wins for what renders.**

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness / peak / stereo / spectrum. This is an
> EQ, not dynamics, so verify tonal moves with `[L] measure-spectrum` / `compare-tonality`, and loudness-match
> every A/B with [[level-match]] / `render-ab` (the unit colours *even at flat* — only `master_bypass` nulls).

---

## TL;DR (the headline, measured on the STANDARD build)

1. **It renders headless — load the `uaudio_` build.** `uaudio_manley_massive_passive.vst3` (standard) and
   `…_m.vst3` (MST) load + process through Pedalboard 0.9.23. The `/Components/UAD Manley Massive Passive*.component`
   AU twins are the **passthrough** offline build — never load those ([[vst-verify]]).
2. **Every band defaults to `OUT` (out of circuit) → a bare load does NOTHING and `probe_plugin.py` FALSE-flags
   it as passthrough** (it pushes a gain on an OUT band). Set `*enable` to `BOOST`/`CUT` and verify with a real
   boost + `measure-spectrum`, not the canned probe.
3. **It's a PARALLEL passive EQ — bands INTERACT, gains DON'T sum.** Measured: lo+himid both-boost lands **1.4–2.0
   dB LESS than the sum** of each alone in the overlap. (The engineering root of the "everything sounds better"
   musicality — and exactly what Manley's manual claims.) Sculpt the *shape* and re-measure; don't reason
   band-by-band.
4. **The GAIN dial is steeply NONLINEAR and BANDWIDTH-COUPLED — dB = gain × bandwidth, not the dial number.**
   Dial **1–4 ≈ nothing; action is 6–16**. At default bandwidth a BELL reads dial 5 ≈ +1 dB, dial 10 ≈ +6, dial
   20 ≈ +11–12. The **full ±20 dB is only reached by NARROWING** (himid dial 20: bw 1.0 = +4.6, bw 2.0 = +11.8,
   bw 3.0 = **+20.9**).
5. **BANDWIDTH 1.0 = WIDEST/gentlest, 3.0 = NARROWEST/tallest** (reversed vs a normal Q, and gain-coupled — Manley
   calls it "damping/resonance," not bandwidth). Narrowing focuses the band *and* roughly **doubles–quadruples**
   the peak for the same dial.
6. **SHELF + NARROW bandwidth grows a resonant overshoot ("the shelves aren't shelves").** A low SHELF @47 at
   bw 3.0, dial 20 = **+15 dB @20 Hz, but DIPS to +0.4 @47 (the corner) then bumps +3.3 @150** — the modeled
   Pultec curve (big-but-tight) in a *single* band. Keep bandwidth WIDE for a clean textbook shelf.
7. **Signature moves (measured):** the **LOW-END TRICK** (low SHELF boost + low-mid BELL CUT — one band can't
   boost+cut) → weight + a low-mid scoop = "big but tight"; the **AIR TRICK** (hi SHELF @16k + hi-mid CUT @3.3k)
   → air up top **while the harsh presence drops** (the 16k/27k shelves are voiced with their dip ~8 kHz =
   "air without esses"). The **27 kHz** position is the supersonic "3D" air shelf — render it at **96 k** (at 48 k
   the corner folds near Nyquist into a midrange dip).
8. **Clean EQ, faint even-harmonic (H2-dominant), level-dependent make-up colour** — 0.03 % THD flat @−18 dBFS →
   0.24 % @0 dBFS; a big boost ≈ doubles it (and odd harmonics rise). **Crest is HELD** (it's EQ, not dynamics).
   **All 51 params are enums → [[vst-preset]] harness, set BOTH channels** (LINKED mirrors ch1→ch2; L/R + Link
   only, no built-in M/S).

---

# Part A — measured on this rig (Pedalboard 0.9.23)

**Loads + renders headless.** `pedalboard.load_plugin(".../uaudio_manley_massive_passive.vst3")` →
`name="UADx Manley Massive Passive EQ"`, `is_instrument=False`, renders (a lo SHELF BOOST g20 @68 moves the low
end +5.6 dB @68 / +17.3 @20 vs flat — Δ confirmed). The MST twin loads the same way
(`name="UADx Manley Massive Passive MST"`). Tested white-noise Welch transfer + 1 kHz-sine THD + the drum loop
`artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav` (mono, 48 kHz, crest 14.63, centroid 1593
Hz). Provenance: `scripts/mix/massive_passive_sweep.py [mst] [96000]`.

| Name | Path | Use |
|---|---|---|
| **UADx Manley Massive Passive EQ** | `/Library/Audio/Plug-Ins/VST3/uaudio_manley_massive_passive.vst3` | ✅ standard (±20 dB, continuous) — the screenshot |
| **UADx Manley Massive Passive MST** | `…/VST3/uaudio_manley_massive_passive_m.vst3` | ✅ MST mastering (±11 dB, stepped + L/R trim) |
| UAD Manley Massive Passive[ MST].component | `…/Components/UAD Manley Massive Passive*.component` | ❌ passthrough twin (offline) |

### The real parameter surface (51 enums — authoritative)

Per channel `ch1` / `ch2`, four bands `lo` / `lomid` / `himid` / `hi`, each five params; plus per-channel filters
+ trim + engage, plus three globals. **ALL 51 are Pedalboard enums.** Gain/bw/freq are *numeric* enums (an on-grid
float via `setattr` works); `*enable` / `*shape` / `*lopass` / `*hipass` / `ctrllink` / `power` are string/bool
enums → **harness only** (and those switches *are* the instrument).

| Param (per band, ×ch×4 bands) | Type | Values | Measured behaviour |
|---|---|---|---|
| `ch{n}{band}enable` | enum | `CUT` · **`OUT`** (default) · `BOOST` | band in/out + direction. **Default OUT = no effect** (the footgun) |
| `ch{n}{band}shape` | enum | `BELL` · `SHELF` | lo+hi default **SHELF**, lomid+himid default **BELL** — but all four can be either |
| `ch{n}{band}gain` | enum-num | std **0.0…20.0** (0.02 steps) · MST **0.0…11.0** (16 detents) | the dial — **nonlinear, bandwidth-coupled** (dB = gain × bw, NOT the dial) |
| `ch{n}{band}bw` | enum-num | std **1.0…3.0** (cont., dflt **2.0**) · MST 1.0…3.0 (16 steps, dflt **1.0**) | **1.0 = widest / 3.0 = narrowest+tallest** (reversed Q) |
| `ch{n}{band}freq` | enum-num | stepped Grayhill grid (below) | freq select — **stepped on both builds** |
| `ch{n}lopass` | enum | std `OFF·18·12·9·7.5·6 kHz` · MST `OFF·52·40·27·20·15 kHz` | passive LPF (std bites the audible band; MST is supersonic-edge) |
| `ch{n}hipass` | enum | std `OFF·22·39·68·120·220 Hz` · MST `OFF·12·16·23·30·39 Hz` | passive HPF (~18 dB/oct; MST is subsonic-only) |
| `ch{n}gain` | enum-num | std **−6.0…+4.0** (cont.) · MST **−2.5…+2.5** (0.5-dB steps) | **Master Gain-Trim — clean, linear dB** (std −6→−6.0, +4→+4.0) |
| `ch{n}enable` | enum | `OUT` · **`IN`** (default) | per-channel EQ engage (the blue "IN" LED) |
| `ctrllink` | enum | `UNLINKED` · **`LINKED`** (default) | **LINKED mirrors ch1→ch2** (measured: set only ch1 → ch2 follows) |
| `power` / `master_bypass` | bool | `True` / `False` | unit power / plugin bypass — `master_bypass=true` = the only **true null** |

**Frequency grids (Hz, measured = screenshot = Manley manual; identical on both builds):**
`lo` 22/33/47/68/100/150/220/330/470/680/1000 · `lomid` 82/120/180/270/390/560/820/1200/1800/2700/3900 ·
`himid` 220/330/470/680/**1000**/1500/2200/3300/4700/6800/10000 (11 steps — note the 1000 between 680 and 1500) ·
`hi` 560/820/1200/1800/2700/3900/5600/8200/12000/16000/**27000**.

### Footguns (proven on this rig)

1. **Bands default `OUT`** — nothing happens until `*enable = BOOST`/`CUT`. The #1 "it didn't work," and why the
   canned `probe_plugin.py` reads PASSTHROUGH (it pushes a gain on an OUT band). Verify with a real boost.
2. **The GAIN dial is not dB** — nonlinear (dead below ~4, action 6–16) **and bandwidth-coupled**: a wide-bw max
   boost is only ~+2–5 dB; you reach the ±20 dB ceiling (±11 on MST) only by narrowing. Measure, don't read the dial.
3. **`apply-vst-chain`'s float dict can't set the character switches** (`*enable`, `*shape`, `*lopass`, `*hipass`,
   `ctrllink`) — those *are* the instrument. Drive it with the **[[vst-preset]]** harness; set **both** channels.
4. **There is no built-in M/S** — it's L/R + Link only (unlike the [[manley-variable-mu]]). For M/S do it via DAW
   routing (the EQ is prized for it — see Part B §6).
5. **"Engaged flat" is magnitude-near-transparent but NOT a true null** — it adds a faint even-harmonic colour
   (THD 0.03 % @−18 → 0.24 % @0 dBFS) + a ~+1 dB lift @16–18 kHz (std) + a near-Nyquist rolloff. Only
   `master_bypass` nulls. **Loudness-match every A/B.**
6. **Wrong build = silent passthrough.** Load the `uaudio_*` VST3; the `.component` twins pass audio through.

### Measured: render-proof + the engaged-flat null (standard, dB vs `master_bypass`)

| state | 20 | 100 | 1k | 5k | 10k | 16k | 18k |
|---|---|---|---|---|---|---|---|
| lo SHELF **BOOST g20 @68** | +17.3 | +10.4 | +0.5 | +0.2 | +0.7 | +0.9 | +1.1 | → renders ✓ |
| engaged flat (all OUT, EQ IN) | +0.0 | −0.0 | +0.0 | +0.2 | +0.6 | +0.9 | +1.1 | → +1 dB top lift, not flat |
| `master_bypass` | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | → the true null |

(MST engaged-flat is *flatter*: ~+0.2 @18k — more transparent than the standard's +1.1.)

### Measured: the GAIN dial (nonlinear) — BELL boost at default `bw 2.0`, dial → actual peak dB

| band @freq | dial 2 | 5 | 10 | 15 | 20 |
|---|---|---|---|---|---|
| `lo` BELL @68 | ~0 | +0.8 | +5.6 | +7.6 | **+10.4** |
| `lomid` BELL @560 | ~0 | +0.8 | +6.0 | +8.3 | **+11.7** |
| `himid` BELL @1500 | ~0 | +0.9 | +6.0 | +8.3 | **+11.6** |
| `hi` BELL @5600 | ~0 | +1.7 | +6.4 | +8.7 | **+12.2** |

Dial 1–4 ≈ dead; action 6–16. **CUT is near-symmetric** (lomid @560 bw2.0: dial 10 = −5.3 / +6.0; dial 20 = −10.8
/ +11.7). (MST is gentler/stepped: himid dial 11 bw1.0 = +4.8, near-symmetric cut −4.3.)

### Measured: GAIN × BANDWIDTH coupling — the dB ceiling depends on bandwidth

`himid` BELL @1500, dial 20: **bw 1.0 (widest) = +4.6 · bw 2.0 = +11.8 · bw 3.0 (narrowest) = +20.9**. This is
the manual's "±20 dB only at the narrowest bandwidth, ~6 dB at the widest," measured. **Narrowing ≈ doubles–
quadruples the peak for the same dial.** (On `lo` BELL the widest setting tops at only ~+2 dB even at dial 20 —
matching MusicRadar's "2 dB on the 22 Hz–1 kHz band.")

### Measured: the SHELF resonant overshoot ("the shelves aren't shelves") — `lo` SHELF BOOST @47, dial 20

| bw | 20 | 47 | 150 | 470 | shape |
|---|---|---|---|---|---|
| 1.0 (wide) | **+17.2** | +13.6 | +6.0 | +1 | clean broad shelf |
| 3.0 (narrow) | +15.0 | **+0.4** | +3.3 | +1 | **sub boost + corner DIP + low-mid bump** = the Pultec curve, one band |

So a narrowed shelf injects an opposing bell dip at/above the corner. A HI shelf mirrors it: **wide bw** = the rise
reaches down into the audible band (broad presence+air); **narrow bw** = steeper, pushed up top (pure >10 kHz air).
For the **air-without-esses** voicing the 16K/27K shelves drop their dip to ~8 kHz on purpose.

### Measured: filters, master trim, parallel non-additivity (standard)

- **HPF** (`hipass`, ~18 dB/oct): HP 22 → −0.9 @68 / −4.5 @20; HP 120 → −6.2 @100 / −15 @68; HP 220 → −16.8 @100 /
  −27 @68. **LPF** (`lopass`): LP 6k → −4.9 @6.8k / −18 @10k (with a small resonant bump ~+1.4 @4.7k before the
  cut); LP 18k → −1.4 @16k. (MST filters are mastering-voiced: subsonic HP 12–39 Hz, supersonic-edge LP 15–52 kHz.)
- **Master Gain-Trim** (`ch{n}gain`): linear, accurate — std −6 → −6.0, +4 → +4.0; MST is ±2.5 dB in clean 0.5-dB
  detents for precise L/R matching.
- **Parallel non-additivity** — `lo` BELL g10 @150 **+** `himid` BELL g10 @1500, vs the sum of each alone:

| freq | lo alone | himid alone | sum | **BOTH** | interaction |
|---|---|---|---|---|---|
| 470 | +4.19 | +3.15 | +7.33 | **+5.33** | **−2.00** |
| 680 | +3.03 | +4.39 | +7.42 | **+5.43** | **−2.00** |
| 1000 | +1.92 | +5.44 | +7.35 | **+5.94** | **−1.41** |

Two boosts land **1.4–2.0 dB below** their sum in the overlap → the bands genuinely interact (parallel passive),
exactly as Manley describes.

### Measured: harmonic colour (a CLEAN EQ) + supersonic air

1 kHz THD (H2-dominant = even-harmonic make-up colour, level-dependent): `master_bypass` 0.000 % (true null) ·
engaged flat 0.031 % @−18 → **0.244 % @0 dBFS** (H2 −52) · `himid` BOOST max @1k 0.255 % @−18 → **1.77 % @0 dBFS**
(odd harmonics rise — driving a big boost into the passive network + tube make-up). A genuinely **clean EQ** whose
colour is the inductor/transformer/valve make-up, scaling with level + boost — **not** a drive box. Crest held.

**Supersonic air** (hi SHELF g20 @27000, measured at **96 k**): +9.6 @14k, +12 @18k, +12.9 @23k air — but a
resonant **undershoot dip −14.8 @6.8k** at this extreme gain. The 27 kHz position is the famous "3D" air shelf;
**render at 96 k and dial gently** (at 48 k its corner folds near Nyquist; prefer the 16 kHz shelf at 48 k).

### Measured: the four shipped presets (Watercolors drum loop, peak-normalized A/B, `[L] measure-spectrum`)

| metric | dry | `drum-bus` (std) | `low-end-trick` (std) | `air-deharsh` (std) | `master-polish` (MST) |
|---|---|---|---|---|---|
| crest (dB) | 14.63 | 14.55 | 14.55 | 14.17 | 14.08 | (HELD — it's EQ) |
| centroid (Hz) | 1593 | 1849 | 1710 | **2038** | 1688 |
| tilt (dB/oct) | −2.71 | −2.55 | −2.62 | −2.42 | −2.69 |
| band_ratio low | 0.798 | **0.856** | **0.847** | 0.815 | 0.829 |
| band_ratio low-mid | 0.176 | **0.128** | **0.131** | 0.168 | 0.153 |
| band_ratio high-mid | 0.0113 | 0.0076 | 0.0115 | **0.0056** | 0.0081 |
| band_ratio high | 0.0043 | 0.0053 | 0.0050 | **0.0061** | 0.0044 |
| true-peak (dBTP) | −3.07 | −0.96 | −0.93 | −0.99 | −0.98 |

- **`massive-passive-drum-bus`** (std) — wide LOW SHELF @68 + LOW-MID BELL CUT @270 + HIGH SHELF @12k: weight (low
  0.798→0.856) + tight low-mids (0.176→0.128) + less harsh presence (high-mid 0.0113→0.0076) + air (high ↑). The
  broad "everything sounds better" bus tone.
- **`massive-passive-low-end-trick`** (std) — low SHELF @47 boost + low-mid BELL CUT @180: weight (0.798→0.847) +
  a low-mid scoop (0.176→0.131), top untouched = **big-but-tight**. (Single-band version: low SHELF @47, bw ~3.0.)
- **`massive-passive-air-deharsh`** (std) — hi-mid BELL CUT @3.3k + 16k HIGH SHELF: **air up while the harsh
  presence drops** (high-mid 0.0113→0.0056, high 0.0043→0.0061, centroid 1593→2038).
- **`massive-passive-master-polish`** (MST) — gentle 2-bus tilt: low weight + a 390 Hz de-mud + 16k air (low
  0.798→0.829, low-mid →0.153, a touch of air), crest 14.63→14.08. The mastering-version polish, *before* the limiter.

Crest is held in all four — the proof it's tonal EQ, not dynamics. A 0.00 spectrum delta = the `.component` twin loaded.

### How to drive it headless

Build a preset under `presets/vst/massive-passive-*.json` setting **every engaged band on BOTH channels**
(`*enable` BOOST/CUT, `*shape`, `*gain`, `*bw`, `*freq`) + `ctrllink`/`power`/`master_bypass`, and apply with the
**[[vst-preset]]** harness (it `setattr`s the string enums and peak-normalizes):
`../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
projects/<track>/mix/<stem>_mp.wav`. Re-measure (`[L] measure-spectrum`/`measure-loudness`) — the deltas land in
band-ratios/centroid/tilt with **crest held**. Dump the live surface with `presets/vst/dump_params.py massive_passive`;
re-run the full provenance with `scripts/mix/massive_passive_sweep.py` (add `mst` and/or `96000`). Regenerate the
3 standard presets with `scripts/mix/mp_presets.py`.

---

# Part B — how it works (web-research synthesis, cited)

> Compiled from the **Manley Massive Passive owner's manual** (primary), **UA's plugin manual / product pages**,
> and the **Sound on Sound** / **MusicRadar** reviews, **adversarially fact-checked**. Several common "facts"
> (designed by EveAnna Manley; Class-A; tube/MOSFET make-up; "wide bandwidth makes the bump"; MST = ½-dB band-gain
> steps; frequency-stepping is mastering-only; LINK is on the hardware) are **myths** — corrected and flagged.
> This is a **modeled, non-deterministic tube/transformer/inductor plug-in** — treat any harmonic/coloration
> figure as plugin-version-dependent and verify on-rig with [[vst-verify]].

### 1. What it is & why "passive"

A **stereo, 2-channel, 4-band-per-channel** EQ whose **tone-shaping filter network is built only from capacitors,
inductors and resistors** (no op-amps/tubes/ICs in the EQ path). Manley: *"Passive simply means no 'active'
(powered) parts… where gain is implied."* The 11-position Grayhill switches just select different C/L combos per
band; the "boost" pots are *reverse-log parallel dividers* — **a boost is really "less cut"** (the Pultec trick).

**FLAG — the unit is a HYBRID, not "all tube" and not "tube/MOSFET."** Classical passive EQ is cut-only with huge
insertion loss; the Massive Passive solves that with (a) a **solid-state input buffer** before the filters (a
Burr-Brown **OPA2604** + a near-class-A transistor pair, DC-servo'd, to drive the ~150 Ω network — Manley: *"not
an appropriate place for tubes"*), and (b) an **all-tube make-up amp** after the filters that restores the ~50 dB
loss so a flat setting is unity (*"Flat Gain! What goes in is what comes out"*). Tube complement: **standard 2×
5751 + 4× 6922; MST 2× 12AU7 + 4× 6922**, on a 300 VDC rail (headroom, not more clipping). **MOSFET was a
*reserved future* design, not in the shipping unit.** XLR out is transformer-balanced; the TRS tap is taken
*before* the transformer (and is out-of-phase). **Bypass keeps the input amp + output transformer in circuit** →
even "EQ disengaged" colours; only `master_bypass`/Power is a true null.

**Deliberate inductor colour:** under heavy LF boost the low-shelf inductor **saturates** (*"a cross between an EQ
and a low-freq limiter,"* odd harmonics that make bass sound louder while still measuring flat); in the bells it's
a slight **center-frequency modulation** with envelope (*"not harmonic distortion… more of a modulation effect"*).
Published specs (manufacturer, not bench-verified): THD+N 0.006 %, DR 123 dB, +35/+37 dBu max out, 20 kΩ in / 150 Ω
out (MST: THD 0.06 %, DR 120 dB).

### 2. Parallel, non-summing topology — why it "can't sound bad"

The four bands are wired in **PARALLEL, not series**: *"set all 4 bands to ~1 kHz, boost all 20 dB, the total is
20 dB rather than 80."* Consequences (all reproduced in Part A): **boosts don't stack**; **bands interact**
(a second band near the first "doesn't seem to do anything"); **gain knobs ≠ resulting curve** → dial by ear. The
parallel scheme keeps total insertion loss ~50 dB (vs >80 dB series), which Manley says sounds "more natural and
musical." **FLAG — "can't overload" is overstated**: the benefit is reduced gain-recovery, not impossibility; it's
still a finite-headroom tube unit. The reputation ("hard to make it sound bad even at extremes") comes from broad
constant-bandwidth curves + non-summing bands + no sharp-parametric ringing + the built-in ~6 dB wide-curve ceiling.

### 3. The signature tricks (the heart of the box)

- **The Pultec shelf overshoot (BANDWIDTH in shelf mode).** Fully CCW = a normal shelf; as you turn BANDWIDTH up
  you *add an opposing bell dip at the corner* — fully CW the dip is ~6 dB down and the slope steepens, max ~12 dB.
  *"These curves were modelled from Pultec EQP-1As and [are] largely responsible for the outrageous phatness."*
  (Part A: a narrow low shelf @47 = +15 @20 / +0.4 @47 / +3.3 @150.)
- **FLAG — BANDWIDTH is REVERSED and gain-coupled.** The most-mistaken fact online: *narrow* (CW) gives the biggest
  gain and the most pronounced overshoot; *wide* (CCW) gives a gentle ~6 dB curve. It is **NOT a true parametric** —
  GAIN and BANDWIDTH interact on purpose ("damping/resonance"). BELL max ≈ ±20 dB narrowest / ~6 dB widest (~2 dB
  on the 22 Hz–1 kHz band); SHELF is the inverse (max ±20 at widest, ~12 at narrowest). Part A confirms exactly.
- **Frequency-extreme inversion** (the "why did I lose highs?" gotcha): a narrow HF shelf's overshoot dip can land
  in the audible band while the shelf itself only lifts above audibility — *"20 dB of boost at 12K can sound like
  you lost highs."* Start WIDE.
- **Boost + cut across bands** (the generalized Pultec move): boost some, cut some — *"start with cutting,"* Manley
  advises. One band can't boost+cut (it's BOOST/OUT/CUT), so use two bands, or a single shelf's BANDWIDTH dip.
- **Air without esses:** the 16K/27K shelves drop their dip to ~8 kHz so a single band adds top while taming
  sibilance. **Low-end tighten:** the 22/33 Hz shelves re-voice BANDWIDTH toward a high-pass as you turn it CW
  (weight + tight); Manley's method is shelf-for-weight then the HPF to firm it.

### 4. Standard (MP) vs Mastering (MST) — every documented difference

Same four bands, same frequencies, same bell/shelf behaviour, same parallel passive topology. The MST is the
**same circuit made recallable + L/R-matchable** for mastering — trading range for precision:

| | Standard | MST |
|---|---|---|
| Band GAIN | ±20 dB continuous | **±11 dB, 16 detented steps** (variable dB/step — GAIN/BW interact, so NOT ½-dB) |
| BANDWIDTH | continuous | **16 detented steps** |
| Master Gain-Trim | −6…+4 dB continuous | **±2.5 dB in 0.5-dB steps** (true 11-position switch, L/R matching) |
| HIGH-PASS | 22/39/68/120/220 Hz | **12/16/23/30/39 Hz** (subsonic) |
| LOW-PASS | 18k/12k/9k/7.5k/6k (lower 3 with a ~1.5–2 dB pre-cut bump) | **52k/40k/27k/20k/15k** (supersonic-edge) |
| GAIN tubes | 2× 5751 | 2× 12AU7 |

> **FLAG myths:** *"MST = ½-dB band-gain steps"* — FALSE (16 *variable* detents; only the master trim is ½-dB).
> *"Frequency stepping is mastering-only"* — FALSE (Grayhill on **both**). *"Band 4 starts at 550 Hz"* — it's 560
> (UA/SoS round). The MST manual's "36 dB/oct filters" header contradicts its own spec (18 dB/oct, 52k at 30) —
> trust the spec.

### 5. How engineers use it

Reach for **broad, gentle, "phat"** moves and colour, **not** surgical notches (use [[fabfilter-pro-q-4]] for
those). EQ by ear/meter — the dial markings are deliberately non-literal. Concrete, sourced starting points:

- **Mix-bus (Moncarz):** all four bands "just under 6/10" then taste — Low 68 Hz, Low-Mid 390 Hz (or 180 Hz +
  CUT for mud), High-Mid 1 kHz (→1.5/2k), High **16 kHz SHELF** (sometimes 27 kHz); HPF 22 Hz to tighten.
- **Mastering 2-bus:** HPF 22 Hz, High-Mid 1 kHz→1.5/2k, air shelf **16 kHz** (or **27 kHz** for the "3D ahh"
  factor) — "expensive, open top." Keep moves small; *before* the limiter.
- **Low end:** shelf/bell boost @47–68 Hz for weight; the **Pultec move** = boost 100 Hz + CUT 180 Hz = big-but-tight.
- **Air:** stacked HF shelves (e.g. 3.3k +4 then 12k +10), or 10K/12K/16K/27K — the 8 kHz dip keeps esses down.
- **Mids/harshness:** broad 200 Hz–1 kHz scoop (~680 Hz de-box); a **wide bell CUT ~4.7 kHz** tames harshness.
- **Drums:** Low 150 Hz (fatten kick), Low-Mid 1 kHz (snare body), High-Mid 1.2 kHz (life), High 8 kHz (hats).
- **Bass:** Low-Mid 330 Hz fatten + a low shelf; bell-boost + HPF. **Vocal:** 220 Hz low-shelf warmth, 3.3/4.7 kHz
  presence, 10K/12K/27K air, HPF 68 Hz.
- **M/S (DAW routing):** HF shelf on the SIDE for air/width without centre harshness; low-shelf/HPF on SIDE to
  mono the bottom — *"the lack of phasy midrange makes it ideal in M/S."*

It's **EQ + colour, not dynamics** — no compressor; hand loudness/limiting to [[master-track]] / [[fabfilter-pro-l-2]].

### 6. Pitfalls / myths corrected

- **MYTH "all tube" / "tube-MOSFET"** → solid-state OPA2604 input buffer + **all-tube** make-up (5751/12AU7 + 6922);
  EQ network is passive C/L/R; MOSFET was future-only.
- **MYTH "wide bandwidth makes the bump"** → **backwards**: NARROW = more gain + more overshoot.
- **MYTH "knob dB markings = dB"** → they don't (parallel + gain/BW coupling). Dial by ear.
- **MYTH "boosts stack"** → parallel, non-summing (Part A: −1.4 to −2.0 dB in overlaps).
- **MYTH "designed by EveAnna Manley / Class-A"** → EveAnna drove concept/name/look (CEO from 1999); the **circuit
  is Craig Hutchison's**. The manual never says Class-A.
- **MYTH "LINK is on the hardware"** → plugin-only (hardware has 2 independent channels; the manual ships a
  *photocopy template* for hand-logging L/R). In the plugin, Unlink→Link copies ch1 onto ch2.
- **"Flat/bypass is clean"** → input amp + output transformer stay in circuit; loudness-match every A/B.
- **OUT (middle toggle) is a per-band bypass, not a cut**; FLAT = GAIN fully CCW (dial 0), not 12:00.
- **Hardware POWER has a ~20 s auto-mute warm-up** (irrelevant headless).

## Sources

- Manley Massive Passive owner's manual (the authoritative primary): https://static1.squarespace.com/static/582f5ce4e4fcb562b921bdc3/t/5fbbf9ad79b2823542cbb175/1606154684408/MSMPX_manual_nov2020-print.pdf · mirror https://images.thomann.de/pics/atg/atgdata/document/manual/166959.pdf — topology ("passive"/"parallel"), OPA2604 input buffer + all-tube make-up (5751/MST 12AU7 + 6922) + 300 VDC, the four bands, BOOST/OUT/CUT, SHELF/BELL + Pultec shelf dip, GAIN flat=CCW + non-dB scale + GAIN/BW interaction, MST ±11 dB/16 steps + ±2.5 dB ½-dB master trim, filters, EQ-IN imperfect bypass, special voicing of 22/33 Hz + 16K/27K shelves
- Manley product pages: https://www.manley.com/products/pro-audio/eqs/massive-passive-eq · https://www.manley.com/products/pro-audio/mastering/massive-passive-eq-mastering (band labels `22±1K`/`82±3K9`/`220±10K`/`560±27K`, 44 freq choices, ¼-octave)
- Sound on Sound UAD review: https://www.soundonsound.com/reviews/universal-audio-uad2-massive-passive (parallel filters, band ranges, MST ±11/stepped, mastering filters HP 12–39 / LP 52–15k, coloration when disengaged, inductor saturation + hysteresis)
- MusicRadar UAD review: https://www.musicradar.com/reviews/tech/universal-audio-manley-massive-passive-255111 (BELL max-gain-when-narrowest; ±6 dB widest / 2 dB on the 22 Hz–1 kHz band; MST trims −2.5…+2.5 / 0.5-dB)
- UA product/help: https://www.uaudio.com/products/manley-massive-passive · https://help.uaudio.com/hc/en-us/articles/18739889642388-Manley-Massive-Passive-EQ-Manual (two plug-in versions; all bands shelf-or-bell; EQ-IN behaviour)
- History: https://mixdownmag.com.au/features/gear-icons-manley-labs-massive-passive-equaliser/ (1998; Hutchison circuit, EveAnna concept/name) · https://en.m.wikipedia.org/wiki/Manley_Laboratories
- Headless VST3 hosting / Pedalboard: https://spotify.github.io/pedalboard/reference/pedalboard.html
