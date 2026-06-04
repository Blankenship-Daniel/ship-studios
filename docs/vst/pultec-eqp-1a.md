# UADx Pultec EQP-1A — field guide: passive tube program EQ + the low-end trick, headless

How to drive the **UADx Pultec EQP-1A EQ** (`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_eqp-1a.vst3`) — UA's
end-to-end model of the legendary **Pultec EQP-1A "Program Equalizer"**: a **passive LC (inductor) equalizer**
followed by a **push-pull vacuum-tube make-up amplifier + transformers**. It's the iconic **broad, gentle,
musical vintage EQ** member of [[vst-eq]] / [[vst-master]] — next to the passive British [[helios-type-69]], the
Motown [[hitsville-eq-mastering]] / [[hitsville-eq]], and the clean surgical [[fabfilter-pro-q-4]]. Its two famous
moves are the **low-end trick** (boost + atten the *same* low frequency for big-but-tight bottom) and **"air
without fizz"** (boost one HF + atten a different HF). **Part A** is *measured on this rig* (the real Pedalboard
param surface + our own transfer-function / THD / render results); **Part B** is a *web-research synthesis,
adversarially verified, cited*. The skill [[pultec-eqp-1a]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the tilt/centroid/crest
> that prove a tonal move. Verify every move with `[L] measure-spectrum` / `measure-loudness`. A render that "sounds"
> EQ'd but shows a 0.00 spectrum delta is a **passthrough** (you loaded the wrong build).

---

## TL;DR (the headline, measured)

1. **It renders headless — load the `uaudio_` build.** `uaudio_pultec_eqp-1a.vst3` loads + processes through
   Pedalboard (UADx native). The `UAD Pultec EQP-1A.component` / `… Legacy.component` twins are the **passthrough**
   offline build — never load those ([[vst-verify]]). UADx native is **PACE/iLok** lineage
   but renders offline once locally authorized (no Apollo hardware needed).
2. **The Boost/Atten knobs are 0–10 DIAL POSITIONS, not dB**, and they're **nonlinear** — most of the action is
   between knob 4 and 8; 8→10 barely moves. Measured low boost @60 CPS: knob 4 ≈ +4 dB, knob 6 ≈ +11, knob 8 ≈ +15
   (peak, at ~30 Hz). Dial to the **meter**, not to a number.
3. **The low-end TRICK is real and measurable.** `lf_boost` + `lf_atten` at the *same* `low_freq` do **not** cancel:
   the boost shelf peaks *below* the CPS, the atten dips a region *above* it. Measured @60 CPS B7/A5 → **+12 dB @60
   with a −2.4 dB scoop @1k** — big tight low end with the boxy low-mids pulled. Higher CPS = broader bump reaching
   higher; lower CPS = tighter/lower.
4. **"Air without fizz" works** because the HF boost freq (`high_freq`/KCS) and HF cut freq (`hf_atten_freq`/ATTEN
   SEL) are **independent**. Measured: 16 KCS boost + 10 KCS atten → **+2.7 dB @16k air** while pulling 3–8k down.
5. **The colour is the CURVES, not saturation.** THD is tiny: **0.002 % @ −18 dBFS, ~0.01 % @ −6 dBFS**, faintly
   odd-harmonic. Unlike the Helios (53 % at Mic g40) or a tube comp, the Pultec is a near-hi-fi passive EQ — its
   magic is the broad musical shelf/bell shapes + a gentle insertion colour, not heavy drive.
6. **"Sounds good even flat" is the +1.1 dB insertion + a top-softening colour.** Engaged-but-flat = **+1.1 dB**
   broadband with a gentle top roll (1.1 dB @1k → 0.8 @20k). Our measured **+1.1 dB matches UA's documented
   ~1.13 dB insertion boost.** `enable=Out` is **NOT a null** (it's a hair *brighter*, +1.9 dB @8k — the
   transformer/tube amp path stays in); only `master_bypass=true` truly nulls. → **always loudness-match the A/B.**
7. **5 of 12 params are STRING enums → drive it with the [[vst-preset]] harness, not `apply-vst-chain`'s float
   dict.** `low_freq`, `high_freq`, `hf_atten_freq`, `enable`, `output` are string enums (the frequency selectors +
   engage + the dB trim) — exactly the controls that set the *character*. The float dict silently misses them.

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin(".../uaudio_pultec_eqp-1a.vst3")` →
`name="UADx Pultec EQP-1A EQ"`, `is_instrument=False`, renders (EQ moves change the audio). Tested with input
`artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav` (mono, 48 kHz). The default load comes up
**engaged + flat** (`enable=In`, all knobs 0, `low_freq=30 CPS`, `high_freq=8 KCS`, `hf_atten_freq=10 KCS`,
`output=0.0 dB`) — no leftover-GUI-state footgun, but still **set every param explicitly** in a preset for
reproducibility. Measurement rig: `scripts/mix/pultec_sweep.py` (Welch cross-spectral transfer on white noise +
1 kHz-sine THD).

`list-vst-plugins {name_contains:"Pultec"}` returns several entries — **use the VST3 `uaudio_` build**:

| Name | Path | Use |
|---|---|---|
| **UADx Pultec EQP-1A EQ** | `/Library/Audio/Plug-Ins/VST3/uaudio_pultec_eqp-1a.vst3` | ✅ this one (renders) |
| UAD Pultec EQP-1A | `…/Components/UAD Pultec EQP-1A.component` | ❌ passthrough twin (offline) |
| UAD Pultec EQP-1A Legacy | `…/Components/UAD Pultec EQP-1A Legacy.component` | ❌ passthrough twin + Legacy voicing (no tube/transformer model) |
| UADx Pultec EQP-1A (AU) | `…/Components/uaudio_pultec_eqp-1a.component` | AU twin (macOS-only) |

> **Siblings in the collection** (each its own plugin): **MEQ-5** midrange EQ (`uaudio_pultec_meq-5.vst3`) and the
> **HLF-3C** high/low filter (`uaudio_pultec_hlf-3c.vst3`). This doc covers the **EQP-1A** program EQ only.

### The real parameter surface (Pedalboard-exposed — authoritative for this build)

**12 parameters, all enums — all 12 are functional** (no reserved/cosmetic/cruft params on this surface; the count
is 10 audio controls — the EQ + `output` trim — plus the 2 control bools `power`/`master_bypass`). The frequency
selectors + `enable`/`output` are **string** enums; the Boost/Atten/Bandwidth knobs are **fine-grained numeric**
enums (`0.00–10.00` in 0.01 steps — effectively continuous *knob positions*, NOT dB).

| Param | Type | Values | Control / measured behaviour |
|---|---|---|---|
| `low_freq` | enum-str | `20 CPS` · `30 CPS` · `60 CPS` · `100 CPS` | LF shelf corner for **both** low Boost & Atten (default `30 CPS`) |
| `lf_boost` | enum-num | 0.0 … 10.0 | **low SHELF boost**, peaks *below* the CPS; nonlinear knob (see curves) |
| `lf_atten` | enum-num | 0.0 … 10.0 | **low SHELF cut**, reaches *higher* than the boost |
| `high_freq` | enum-str | `3·4·5·8·10·12·16 KCS` | HF **peak/bell** boost centre (default `8 KCS`) |
| `hf_boost` | enum-num | 0.0 … 10.0 | **HF peak boost** (broad, proportional-Q bell) |
| `hf_q` | enum-num | 0.0 … 10.0 | **BANDWIDTH** of the HF boost bell only: **0 = SHARP (tall/narrow)**, **10 = BROAD (lower/wider)** |
| `hf_atten_freq` | enum-str | `5·10·20 KCS` | HF **shelf-cut** corner (ATTEN SEL), **independent** of the boost freq (default `10 KCS`) |
| `hf_atten` | enum-num | 0.0 … 10.0 | **HF SHELF cut** (high-shelf; freq = the hinge) |
| `enable` | enum-str | `Out` · `In` | EQ engage. **`Out` ≠ a null** — the amp/transformer path stays in (slightly brighter than dry). Default `In`. |
| `output` | enum-str | `OFF` · `-12.0 dB` … `+12.0 dB` | **output trim** (clean; a UA addition — the hardware has none). Default `0.0 dB`. |
| `power` / `master_bypass` | bool | `True`/`False` · `False`/`True` | unit power / plugin bypass — **`master_bypass=true` is the only TRUE null** |

> **No tube on/off toggle exists.** The bottom-left lever in the GUI is engage/IN, not a tube defeat — the tube +
> transformer model is **always on** (drive `output` harder for a hair more colour; you can't switch it off).

### Footguns (proven on this rig)

1. **`enable=Out` is not a bypass.** Engaged-flat = **+1.1 dB** with a gentle top roll-off; `Out` = **+1.2…+1.9 dB**
   (brighter at 8–10 kHz) — the makeup amp + transformers stay in the path either way. Only **`master_bypass=true`**
   gives a 0.00 dB null. So *any* time the Pultec is loaded it imparts a faint colour + ~+1 dB makeup → **loudness-
   match every A/B** (the harness peak-normalizes; still `[L] match-loudness` / `render-ab` before judging tone).
2. **Boost/Atten knobs are 0–10 positions, not dB, and nonlinear.** Most action is knob 4→8. Reading a preset's
   `lf_boost: 5.0` as "+5 dB" is wrong — measure it. (Per-band dB curves below.)
3. **`apply-vst-chain`'s float dict can't set the frequency selectors.** `low_freq`, `high_freq`, `hf_atten_freq`,
   `enable`, `output` are **string** enums — the float-only dict silently misses them (it can nudge the boost/atten/
   q knobs if already valid). Drive it with the **[[vst-preset]]** harness (`setattr`).
4. **Wrong build = silent passthrough.** Load `uaudio_pultec_eqp-1a.vst3`. The `UAD …`/`Legacy .component` twins
   pass audio unprocessed offline — a 0.00 delta is the tell ([[vst-verify]]).
5. **Reset state between renders.** (Rig note, not a user gotcha.) When sweeping in one process, a left-on
   `master_bypass=true`/`enable=Out` from a prior call silently bypasses every later render — reset all 12 params per
   call. The shipped presets always set the full surface.

### Measured: insertion / flat / bypass (transfer dB, white-noise Welch)

| state | 30 | 60 | 100 | 1k | 5k | 10k | 16k | 20k |
|---|---|---|---|---|---|---|---|---|
| **engaged flat** (`In`, knobs 0) | +1.1 | +1.1 | +1.1 | +1.1 | +1.1 | +1.1 | +0.9 | +0.8 |
| `enable=Out` | +1.2 | +1.2 | +1.2 | +1.3 | +1.8 | +1.9 | +1.7 | +1.6 |
| `master_bypass=true` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

→ engaging the unit prints **~+1.1 dB makeup + a gentle top-softening** (the "sounds better flat" colour, matching
UA's documented ~1.13 dB insertion boost); `Out` keeps the path and reads brighter; only `master_bypass` nulls.

### Measured: LF BOOST (broad low shelf, **peaks below the selected CPS**)

Transfer dB at `lf_boost=10` (the max), per CPS — note the peak sits at ~30 Hz and the CPS sets how high the shelf
*reaches*:

| `low_freq` @ boost 10 | 30 | 50 | 60 | 100 | 200 | 300 | 500 |
|---|---|---|---|---|---|---|---|
| 20 CPS | +10.1 | +6.8 | +5.8 | +3.4 | +1.8 | +1.4 | +1.2 |
| 30 CPS | +14.8 | +12.1 | +11.1 | +7.7 | +4.0 | +2.7 | +1.7 |
| **60 CPS** | +16.6 | +15.2 | +14.6 | +11.7 | +7.4 | +5.1 | +3.0 |
| **100 CPS** | +17.2 | +16.6 | +16.2 | +14.4 | +10.5 | +7.9 | +5.0 |

Knob calibration (nonlinear, @60 CPS, dB at ~30 Hz): knob 2 ≈ +0.6, **4 ≈ +4.3, 6 ≈ +11, 8 ≈ +14.7**, 10 ≈ +15.5.
(Manufacturer nominal max ≈ +13.5 dB; the model's resonant sub-bump reads a touch higher.)

### Measured: LF ATTEN (broad low shelf-cut, **reaches higher than the boost**)

Transfer dB at `lf_atten=10`, per CPS:

| `low_freq` @ atten 10 | 30 | 60 | 100 | 200 | 300 | 500 | 1k |
|---|---|---|---|---|---|---|---|
| 30 CPS | −16.5 | −12.9 | −9.2 | −4.4 | −2.2 | −0.3 | +0.8 |
| 60 CPS | −18.6 | −17.2 | −14.9 | −10.5 | −7.6 | −4.2 | −0.9 |
| 100 CPS | −18.9 | −18.4 | −17.3 | −14.2 | −11.7 | −8.0 | −3.5 |

Knob (nonlinear, @100 CPS, dB @30): 4 ≈ −3.9, 6 ≈ −11.2, 8 ≈ −17.0, 10 ≈ −18.9. (Nominal max ≈ −17.5 dB.)

### Measured: the LOW-END TRICK (boost + atten at the same CPS = bump + scoop, no null)

Transfer dB:

| @ `low_freq` (B/A) | 30 | 60 | 100 | 200 | 300 | 500 | 1k | 2k |
|---|---|---|---|---|---|---|---|---|
| 60 CPS B4/A3 | +4.1 | +4.1 | +4.0 | +3.6 | +3.2 | +2.1 | +0.5 | 0.0 |
| **60 CPS B7/A5** | +13.5 | **+12.2** | +9.9 | +5.2 | +1.9 | **−2.1** | **−2.4** | −0.2 |
| 100 CPS B5/A5 | +6.5 | +6.4 | +6.2 | +5.3 | +4.1 | +1.6 | −2.1 | −1.6 |
| 100 CPS B8/A8 | +15.3 | +14.4 | +12.7 | +8.5 | +5.1 | −0.2 | −5.5 | −1.6 |

→ a low shelf **bump** (peaks ~30–60) **with a complementary scoop** (~300 Hz–1 kHz). The scoop deepens & climbs
with more atten / higher CPS. This is the "big but tight, no mud" sound — and it confirms the research mechanism
(boost corner *at/below* CPS, atten corner ~½ octave *above*).

### Measured: HF BOOST (broad proportional-Q bell at the KCS centre)

Transfer dB at `hf_boost=10`, `hf_q=5`, per KCS — the selected KCS sets the peak; lower KCS reaches into the upper
mids (presence/bite), 16 KCS is pure air:

| `high_freq` @ boost 10 | 1k | 2k | 3k | 5k | 8k | 10k | 12k | 16k |
|---|---|---|---|---|---|---|---|---|
| 3 KCS | +6.4 | +12.4 | **+14.7** | +11.0 | +6.9 | +5.4 | +4.4 | +3.0 |
| 5 KCS | +3.2 | +6.9 | +10.6 | **+14.7** | +11.0 | +8.7 | +7.0 | +4.9 |
| 8 KCS | +2.3 | +4.8 | +7.5 | +11.9 | **+14.7** | +13.7 | +12.2 | +9.4 |
| 10 KCS | +2.3 | +4.7 | +7.1 | +11.0 | +14.2 | **+14.7** | +14.2 | +12.2 |
| 16 KCS | +1.2 | +1.4 | +1.8 | +2.9 | +5.6 | +8.1 | +11.1 | **+14.4** |

Knob (nonlinear, @10 KCS peak): 2 ≈ +1, 4 ≈ +3.8, 6 ≈ +6.1, 8 ≈ +9.3, 10 ≈ +14.7. (Nominal max ≈ +18 dB.)

### Measured: BANDWIDTH (`hf_q`) — SHARP(0) = tall/narrow, BROAD(10) = lower/wider

Transfer dB at `high_freq=10 KCS`, `hf_boost=8`:

| `hf_q` | 2k | 3k | 5k | 8k | 10k | 12k | 16k |
|---|---|---|---|---|---|---|---|
| 0 (SHARP) | +3.2 | +5.0 | +8.4 | +11.6 | **+12.1** | +11.6 | +9.6 |
| 5 | +3.5 | +5.2 | +7.6 | +9.2 | +9.3 | +9.1 | +8.2 |
| 10 (BROAD) | +3.7 | +5.1 | +6.9 | +7.8 | **+7.9** | +7.7 | +7.2 |

→ as you go BROAD the peak gain *drops* (energy spreads); SHARP concentrates a taller, narrower peak. (Matches SoS's
"~9 dB more peak at narrow vs broad" — affects the **HF boost only**, not LF or HF atten.)

### Measured: HF ATTEN (high-shelf cut; the ATTEN-SEL freq is the HINGE)

Transfer dB at `hf_atten=10`, per `hf_atten_freq`:

| ATTEN SEL @ atten 10 | 1k | 2k | 3k | 5k | 8k | 10k | 16k | 20k |
|---|---|---|---|---|---|---|---|---|
| 5 KCS | −4.4 | −9.2 | −12.1 | −15.2 | −17.3 | −18.0 | −19.0 | −19.3 |
| 10 KCS | −1.1 | −4.4 | −7.1 | −10.8 | −13.9 | −15.3 | −17.5 | −18.3 |
| 20 KCS | +0.4 | −1.2 | −2.9 | −6.1 | −9.4 | −11.0 | −14.3 | −15.8 |

→ 5 KCS hinges ~1 kHz (darkens/de-harshes broadly), 20 KCS hinges ~5 kHz (shave only the extreme top). Knob
(nonlinear, @5 KCS @20k): 4 ≈ −2.0, 6 ≈ −4.7, 8 ≈ −8.5, 10 ≈ −19.3. (Nominal max ≈ −16 dB; the very top reads
lower.)

### Measured: AIR WITHOUT FIZZ (16 KCS boost + 10 KCS atten, independent freqs)

| | 1k | 3k | 5k | 8k | 10k | 12k | 16k |
|---|---|---|---|---|---|---|---|
| 16 KCS boost(6) only | +1.2 | +1.4 | +1.8 | +2.8 | +3.8 | +4.7 | **+5.4** |
| + 10 KCS atten(4) | +0.6 | −0.7 | −0.7 | +0.1 | +1.1 | +2.0 | **+2.7** |

→ the boost keeps the very top (+2.7 @16k), the independent atten pulls the 3–8k "fizz/harsh" region down. The whole
point of two independent HF freqs.

### Measured: harmonic colour (1 kHz sine — the Pultec colours via CURVES, not drive)

| input level | flat THD | with LF boost 10 | with HF boost 10 | notes |
|---|---|---|---|---|
| −18 dBFS | **0.002 %** | 0.002 % | 0.002 % | essentially clean |
| −6 dBFS | **0.010 %** | 0.013 % | 0.012 % | faintly **odd-harmonic** (H3 > H2 at this level) |

`output` ±6/±12 dB does **not** change THD (it's a clean post-trim, ratio-invariant). Bottom line: this model adds
only a whisper of harmonic colour even when pushed — far below the Helios/tube-comp range. **For obvious analogue
weight/glue, stack tape ([[ampex-atr-102]]) or a vari-mu ([[fairchild-660]]) after it.**

### Measured: the three shipped presets (real `apply_vst_preset.py` harness + `[L]` meters, on the drum loop)

| metric (`[L]`) | dry | `pultec-drum-lowend-glue` | `pultec-air-without-fizz` | `pultec-master-smile` |
|---|---|---|---|---|
| crest factor (dB) | 14.63 | **13.43** (−1.2) | **14.53** (held) | **14.45** (held) |
| PLR (dB) | 17.06 | 13.20 | 14.01 | 13.92 |
| integrated LUFS | −20.13 | −14.19 | −14.99 | −14.90 |
| true-peak (dBTP) | −3.07 | −0.99 | −0.99 | −0.99 |
| spectral centroid (Hz) | 1593 | **1231** (warm) | 1578 (≈held) | 1601 (≈held) |
| spectral tilt (dB/oct) | −2.71 | −3.54 | −2.78 | −2.75 |
| band ratio low | 0.798 | **0.877** | 0.804 | 0.806 |
| band ratio low-mid | 0.176 | **0.118** (scoop) | 0.176 | 0.173 |
| 5 k (rel dB) | −21.4 | −28.2 | **−23.2** (de-fizz) | −22.3 |
| 16 k (rel dB) | −41.0 | −45.7 | **−39.5** (+1.5 air) | **−40.1** (+0.9 air) |

- **`pultec-drum-lowend-glue`** — `60 CPS` B5/A4 + `16 KCS` boost4 (q8) + `5 KCS` atten2: the low-end trick →
  weighty + **tight** bottom (low ratio 0.798→0.877, low-mid scoop 0.176→0.118), warm top (centroid 1593→1231),
  **crest held** (it's EQ, not compression). The user's warm+tight drum tone, by EQ shape not boost.
- **`pultec-air-without-fizz`** — `16 KCS` boost6 (q8) + `10 KCS` atten4, low flat: **+1.5 dB @16k air** with 5–8k
  pulled down, centroid/low untouched, crest held. For overheads / cymbals / bright bus / vocal tops.
- **`pultec-master-smile`** — gentle `30 CPS` B3/A2 + `16 KCS` boost4 (q10), no HF cut: a true broad smile (low +,
  +0.9 dB @16k air, mids dip slightly), centroid held, crest held. 2-bus glue+smile *before* the limiter.

**The crest barely moves on any of them** — the Pultec is an EQ; the "glue" is tonal shaping + a faint insertion
colour, not dynamics. If crest drops a lot you drove something else.

### How to drive it headless

Use **[[vst-preset]]**'s `apply_vst_preset.py` (`setattr`s every param, strings included), setting **all 12** params
explicitly. `presets/vst/pultec-*.json` are ready. Apply:
`../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
projects/<track>/mix/<stem>_pultec.wav` (it peak-normalizes the output, absorbing the +1 dB insertion). Dump the
live surface any time with `presets/vst/dump_params.py uaudio_pultec_eqp-1a`; re-measure curves with
`scripts/mix/pultec_sweep.py`; set `dump_state=true` (via `apply-vst-chain`) for a byte-stable re-render.

---

# Part B — how the Pultec EQP-1A works (web-research synthesis, adversarially verified, cited)

> Claims graded by adversarial verdict; corrected where a check refined them. **Where the installed plugin's measured
> surface (Part A) differs, Part A wins for what renders.**

## 1. What it is

The EQP-1A is a **passive, inductor-based (LC) "Program Equalizer" followed by a push-pull vacuum-tube make-up
amplifier**. All boost/cut is done by a *passive* LC network (no active EQ elements), which is inherently lossy; a
tube gain stage then restores the insertion loss, leaving the unit ~unity. Because the tone path (passive LC) and the
gain/colour path (tubes + transformers) are physically coupled, **you can't separate "EQ" from "tube colour."** Tube
complement: **12AX7** (input/gain), **12AU7** (push-pull output → output transformer), **6X4** (rectifier). Amp spec
(manufacturer): in ~600 Ω, out ~50 Ω, THD ≤0.15 % @ +10 dBm, response 20 Hz–20 kHz ±0.5 dB. The hardware is **mono**
(1-in/1-out). [SUPPORTED]

## 2. Control surface (cross-check Part A for what renders; `CPS`=Hz, `KCS`=kHz)

- **Low Frequency** — CPS selector **20/30/60/100 Hz**, sets the corner for *both* low **Boost** (low shelf, 0→
  **+13.5 dB**) and low **Atten** (low shelf cut, 0→**−17.5 dB**). Boost & Atten are **separate, non-reciprocal
  circuits** sharing the CPS.
- **High Frequency Boost** — KCS selector **3/4/5/8/10/12/16 kHz**, a **peak/bell** boost 0→**+18 dB**, with a
  **Bandwidth** knob (**SHARP↔BROAD**) = the **Q of the HF boost bell only** (narrow→broad; even "SHARP" is broad by
  modern standards; ~9 dB more peak at narrow vs broad — SoS).
- **High Frequency Atten** — ATTEN SEL **5/10/20 kHz**, a **high-shelf cut** (~6 dB/oct) 0→**−16 dB**, **fully
  independent** of the boost (own freq, own amount). *(Disputed: some write-ups say ~−17.5 dB; prefer −16 dB.)*
- **Output Gain "dB" / OFF** — a **UA addition** (the hardware has no output knob): output trim **±12 dB** and bypass
  (full-CCW = OFF; the "0" label snaps to unity; a red lamp toggles IN). The 20 Hz / 4 & 16 kHz boost / 5 & 20 kHz
  atten positions were the **EQP-1A additions** over the original EQP-1.
- **No tube-defeat switch** — the tube/transformer model is always on; any bottom-left GUI lever is engage/IN.

## 3. The low-end trick (the load-bearing fact)

Select one **CPS**, then turn up **both** the low **Boost** and the low **Atten** at that freq — a move the original
manual warned against because on paper it should cancel. It doesn't, because the two run through **separate
non-reciprocal circuits with offset corners**: the **Boost** shelf corner sits **at/just below** the CPS (lifts the
fundamental/sub); the **Atten** shelf corner starts **~½ octave higher** (cuts the boxy low-mids); and the Boost has
**slightly more gain** than the Atten has cut. **Net = a low bump + a scoop ~an octave above** — e.g. select 30 Hz →
peak ~80 Hz, dip ~200 Hz. The "imperfection" is the feature. Rule of thumb: **20–30 Hz** = sub weight (kick/bass),
**60–100 Hz** = body + boxiness control (snare/vocal/mix). Start **Boost ≈ Atten**, re-check Boost after adding Atten
(interactive). [SUPPORTED, multi-source — SoS measured the ½-octave offset.]

## 4. The high-frequency moves

HF boost freq (KCS) and HF cut freq (ATTEN SEL) are **independent** → lift one band while shelving another:
- **Air without fizz:** boost a peak at **10–16 kHz** (broad/medium Bandwidth) while shelving HF Atten at **20 kHz**
  → open top without brittleness. 16 kHz is the legendary master "air"; 12 kHz is the safer, less-fragile lift.
- **HF de-harsh:** HF Atten **5 kHz** (or 10 kHz) shelf alone to tame harshness/sibilance/cymbal fizz, **without**
  touching the boost band.
- **HF "trick":** boost **12 kHz** gloss + cut **5 kHz** simultaneously → present, glossy top without edge.
- **Bandwidth (Q):** broad for musical air on a bus/master; narrower + higher for focused single-source presence
  (and to avoid emphasizing sibilant "ess").

## 5. How engineers use it — starting points (quantize to the real steps; verify by meter)

| Source | Moves (starting points) |
|---|---|
| **Kick — weight + tight** | low-end trick **30–60 Hz**, Boost ~4–5 / Atten ~4–5 (thump + clean low-mid scoop) |
| **Bass — tight + de-mud** | low-end trick **30 Hz** (or 60), Boost ≈ Atten 4–6 |
| **Snare — body + snap** | low Boost **100 Hz** body; HF Boost **5–8 kHz** crack |
| **Drum bus — glue** ★ | low-end trick **~60 Hz** (gentle) + HF Boost **~10–16 kHz** broad; HF Atten **5 kHz** to de-harsh |
| **Mix-bus smile** | broad **~100 Hz** + **~10 kHz**, ≤2 dB each |
| **Mastering — air** | HF Boost **10–16 kHz** (broad) + HF Atten **20 kHz** ("air without fizz") |
| **Mastering — glue** | tiny low (0.5–1 dB @30/60) + air (0.5–1 dB @12k); a touch more boost than cut |
| **"Tone print"** | EQ flat, run through — transformer/tube colour only (euphonic, tape-like glue) |

**Mastering rule:** keep moves fractions of a dB up to ~1–2 dB — the EQP-1A is a **broad tone tool, not surgery**;
pair it with a parametric EQ ([[fabfilter-pro-q-4]]) for notches. Place it **before the limiter** on the 2-bus.

## 6. Pitfalls / gotchas

1. **EQ-bypass still prints colour** — the in-plugin EQ "Out"/bypass only removes the passive EQ network; the
   transformers + tube makeup stay in (subtle saturation, fattened lows, excited highs). For a true null, remove the
   plugin / use `master_bypass` (Part A confirms `enable=Out` is *brighter*, not null).
2. **Loudness-match every A/B** — UA models a **~1.13 dB insertion boost** (Part A measured **+1.1 dB**) and Output
   adds ±12 dB more, so the Pultec flatters itself. `[L] match-loudness` / `render-ab` before any `[G]`
   compare/feedback ([[gemini-audio-understanding]]). Never trust `changed:true` or "louder" as "better".
3. **Drive = more colour** — pushing makeup/output harder drives the tube model into (a little) more saturation.
4. **Mono origin / stereo hygiene** — hardware is mono; the plugin runs mono / dual-mono. The stepped freq selectors
   match L/R easily, but Boost/Atten/Bandwidth/Output are continuous — mismatched L vs R shifts the image; link or set
   identical, and re-check `[L] measure-stereo` after a stereo pass.
5. **Collection = 3 plugins** — EQP-1A (this), **MEQ-5** (mid: 2 boost + 1 dip), **HLF-3C** (HP/LP filter), each its
   own instance. The current Collection models the tube+transformer distortion; the **Legacy** UAD-1/2 versions omit
   it.
6. **Upsampling latency** — internal ~176 kHz upsampling adds a small fixed latency (~13 samples below 100 kHz).
   **Unison** is Apollo-preamp-only and does **nothing** offline.
7. **iLok/PACE** — UADx native is PACE-protected but **renders offline** once authorized to the **local machine or an
   iLok USB** (avoid iLok-Cloud, which needs a live connection). **Loads ≠ renders** — verify with [[vst-verify]].
8. **Headless control trap (this rig)** — the string enums (`low_freq`/`high_freq`/`hf_atten_freq`/`enable`/`output`)
   need the **[[vst-preset]]** harness, not `apply-vst-chain`'s float dict; load the **`uaudio_*.vst3`** build.

> **Pure-DSP equivalents (no plugin, deterministic):** broad tilt/shelf EQ → `[L] apply-eq`; the low-end "trick" can
> be approximated with `[L] apply-eq` (a low shelf boost + a low-mid bell cut); air/presence without hiss → [[excite]];
> tube/tape colour → `[L] saturate-loop` / [[studer-a800]] / [[ampex-atr-102]]; surgical notches → [[fabfilter-pro-q-4]].
> Reach for the Pultec when you want *its* broad musical curves + the bump-and-scoop interaction + the faint passive
> tube colour specifically.

---

## Sources

Pulse Techniques (manufacturer EQP-1A spec sheet) · Wikipedia *Pultec EQP-1* (topology, EQP-1 vs EQP-1A additions,
tubes, mono I/O) · Abbey Road Institute *Demystifying the Pultec* · Front End Audio EQP-1A (passive + push-pull tube
makeup, amp specs, dB ranges) · Sound on Sound *Pulse Techniques EQP-1A* review (measured ½-octave corner offset,
~9 dB bandwidth delta, recipes) · Universal Audio *Pultec Collection Tips & Tricks* + product page + the **Pultec
Passive EQ Collection Manual** (controls, **~1.13 dB insertion boost**, upsampling/13-sample latency, Output/OFF,
Legacy vs current) + *Using Native UAD (UADx) Licenses Offline* (PACE/iLok machine vs USB vs cloud) · mix:analog
*Pultec EQ tutorial* (80 Hz peak / 200 Hz dip, 6 dB/oct HF shelf) · UltimatePreset Pultec guide · MusicRadar /
adesignsaudio / Song Mix Master (low-end-trick recipes) · Vintage King (EQ bypass leaves transformers/tubes in path)
· masteryourtrack / Sweetwater InSync (16 kHz air, ±12 dB output, broad 100 Hz + 10 kHz smile). Plus **our own
param-surface dump + transfer-function / THD / `[L]`-meter render results (Part A)** on
`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_eqp-1a.vst3` via Pedalboard (`scripts/mix/pultec_sweep.py`).
