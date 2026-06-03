# UADx Manley Variable Mu — field guide: vari-mu tube glue, CLEAN/transparent, M/S, headless

How to drive the **UADx Manley Variable Mu** (`/Library/Audio/Plug-Ins/VST3/uaudio_manley_variable_mu.vst3`)
— Universal Audio's model of the **Manley Labs Stereo Variable Mu® Limiter Compressor**, the all-tube
variable-mu (vari-mu) bus/mastering compressor (Manley's flagship since 1994). It's the **CLEAN / transparent**
vari-mu glue counterpart to the thicker, more colored [[fairchild-660]] (the other UAD vari-mu here), the VCA
glue of [[ssl-bus-compressor-2]], and the tube/tape color of [[ampex-atr-102]] / [[studer-a800]] — the
measured deep-dive behind the [[manley-variable-mu]] skill and a plugin-specific specialization of
[[vst-compress]].

**Part A** is *measured on this rig* (real Pedalboard param surface + our render results); **Part B** is a
*web-research synthesis, cited* (the Manley owner's manual + UA's plugin manual, fact-checked).

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness / peak / stereo and the crest / LRA /
> spectrum that prove "glue, not crush." Verify every move with `[L] measure-loudness` /
> `measure-microdynamics` / `measure-spectrum` / `measure-stereo`. A "glued" feel that doesn't move crest /
> LRA is a level illusion ([[gemini-audio-understanding]]).

---

## TL;DR (the headline, measured)

1. **It's the CLEAN vari-mu — it levels macro-dynamics and keeps transients.** On the Watercolors warm drum
   bus the signature glue (`manley-vari-mu-drum-glue`) **raised crest 17.17→17.39** (transients *more* intact)
   while **tightening LRA 2.44→2.07**, with only a hair of low-mid thickening (0.179→0.184) and **low-band
   punch held** (27.15→27.30), true-peak −0.98. Compare the Fairchild 660 on the *same* bus, which *dropped*
   crest to 16.90 and thickened more — **Manley = cleaner leveler, Fairchild = thicker color.**
2. **No ratio knob — it's a vari-mu.** Ratio is program-dependent and set by **COMP vs LIMIT** + how hard you
   drive it. **COMP ≈ 1.5:1 soft knee; LIMIT ≈ 4:1 climbing to ~20:1 past 12 dB.** Measured at thresh 4:
   **LIMIT pulled −5.8 dB vs COMP's −2.2 dB** — much more GR for the same threshold, crest still ~17.3.
3. **THRESHOLD maps directly (NOT inverted like the Fairchild's enum): LOWER `l_thresh` = MORE GR.** Default
   **10 = MAX = least compression**; drop toward 0 for more. As it levels, **crest rises** (16.84→17.49).
4. **`dual_input` is a SINGLE shared drive/level** (0–10, default 6) — the "amount + color" lever. in3 →
   rms −33.8, in6 → −19.6, in10 → +4.0 dBFS (clips). Crest held ~17. **Drive it to hit the tubes for color.**
5. **ATTACK: 0 = SLOW (punch, crest 17.4) … 10 = FAST (clamp, crest 16.4).** Flat until ~7 then it grabs.
   **RECOVERY (5-pos): `Med` = most open (crest 17.38); `Fast` = densest/pumps (16.40).**
6. **HEADROOM is the inverted DRIVE lever (4–28 dB, default 16):** LOWER value = hotter into the tubes (more
   saturation, *less* GR for a fixed input); HIGHER = cleaner with MORE GR. Measured: **HR4 ≈ no GR + most
   color (crest 16.90); HR28 = −5.8 dB GR, crest collapses to 15.96.** Dial to the meter.
7. **Tube color is EVEN-harmonic (2nd) and LEVEL-dependent.** A 1 kHz sine is clean at −18 dBFS (0.03–0.05 %
   THD) and only colors when driven hot: **−6 dBFS → 0.21 % THD with H2 ~10 dB above H3.** So you add color
   by driving the *level* in (`dual_input` ↑ / `headroom` ↓), not by lowering the threshold.
8. **HP SIDECHAIN `In` (fixed −3 dB @ 100 Hz) = less bass-triggered GR** (+0.8 dB out) — engage it on
   bass/kick-heavy material so the low end stops pumping the comp.
9. **Real M/S — the move the mono 660 can't do.** `in_matrix`/`out_matrix` = `M-S` with `ctrl_link` +
   `sc_link` **Unlinked** → **L-channel controls = MID, R-channel = SIDE.** Squeezing the mid harder than the
   side **widens** the master (measured: correlation 0.977→0.933, width −19.2→−14.5 dB). **Linked M-S == L-R**
   (no imaging change — the unlink is the whole point).
10. **MIX (0–100) is built-in parallel** (100 = wet). Crush a hot/fast wet in LIMIT, blend dry back ~40–50 %
    for a NY smash that keeps the slam.
11. **Tooling gotcha:** **all 23 params are enums** (numeric values AND string switches) — `apply-vst-chain`'s
    float-only dict can't set the string enums (`recovery` / `comp_lim` / `hp_sc_filt` / matrices / links) →
    use the **[[vst-preset]] harness** (`presets/vst/apply_vst_preset.py`).
12. **Renders headless via the `uaudio_*.vst3` UADx native build** (`RENDERS ✓`). The
    `/Components/UAD Manley Variable Mu.component` twin **PASSES THROUGH** offline (`PASSTHROUGH ✗`) — never load it.

---

## Part A — measured on this rig (Pedalboard 0.9.23)

**Loads + processes headless.** `load_plugin(".../uaudio_manley_variable_mu.vst3")` → `name="UADx Manley
Variable Mu Compressor"`, `probe_plugin.py` = **RENDERS ✓** (`pushed l_output → Δ`, native build). The
`/Components/UAD Manley Variable Mu.component` twin = **PASSTHROUGH ✗** (ignores params offline) — load the
`uaudio_*.vst3` build only ([[vst-verify]] / [[vst]]). UADx native = no-iLok lineage, but
re-verify `RENDERS ✓` on a new machine.

**Param surface (Pedalboard snake_case — what you set in code/the harness). All 23 are ENUMs:**

| Param | Type | Range / values (measured) | GUI control |
|---|---|---|---|
| `dual_input` | enum num | `0.0 … 10.0` (0.01 step), **default 6** | DUAL INPUT (shared drive) |
| `l_thresh` / `r_thresh` | enum num | `0.0 … 10.0` (0.01), **default 10** (=MAX=least comp) | THRESHOLD (MIN…MAX), per ch |
| `l_attack` / `r_attack` | enum num | `0.0 … 10.0` (0.01), **default 5** | ATTACK (SLOW 0 … FAST 10), per ch |
| `l_recovery` / `r_recovery` | enum str | `'Slo' 'Med Slo' 'Med' 'Med Fast' 'Fast'`, **default 'Med Fast'** | RECOVERY (SLOW…FAST), per ch |
| `l_output` / `r_output` | enum num | `0.0 … 10.0` (0.01), **default 5** | OUTPUT (makeup), per ch |
| `l_comp_lim` / `r_comp_lim` | enum str | `'Comp' 'Limit'`, **default 'Comp'** | COMPRESS / LIMIT, per ch |
| `l_hp_sc_filt` / `r_hp_sc_filt` | enum str | `'Flat' 'In'`, **default 'Flat'** | HP SC (sidechain HPF), per ch |
| `l_bypass` / `r_bypass` | enum str | `'Bypass' 'In'`, **default 'In'** | IN / BYPASS, per ch |
| `in_matrix` | enum str | `'M-S' 'L-R'`, **default 'L-R'** | IN matrix (L-R / M-S) |
| `out_matrix` | enum str | `'M-S' 'L-R'`, **default 'L-R'** | OUT matrix (L-R / M-S) |
| `sc_link` | enum str | `'Unlink' 'Link'`, **default 'Link'** | SIDECHAIN link |
| `ctrl_link` | enum str | `'Unlink' 'Link'`, **default 'Link'** | CONTROLS link |
| `mix` | enum num | `0 … 100` % (1), **default 100** (=wet) | MIX (DRY…WET) |
| `headroom` | enum num | `{4,8,12,14,16,18,20,24,28}` dB, **default 16** | HEADROOM (drive, inverted) |
| `power` | bool | default **True** | IN (power) |
| `master_bypass` | bool | default **False** | (host bypass) |

> **`dual_input` is SHARED** (one DUAL INPUT knob feeds both channels); **threshold / attack / output /
> recovery / comp-lim / hp-sc / bypass are PER-CHANNEL** (`l_*` + `r_*`). In **L-R** mode keep L and R
> identical for a stereo bus; in **M-S** mode `l_*` is the MID and `r_*` the SIDE.
>
> **Enum gotcha (the big one).** `[L] apply-vst-chain`'s `parameters` dict is **float-only** — it can't set
> the string enums (`l_recovery`, `l_comp_lim`, `l_hp_sc_filt`, `*_matrix`, `*_link`, `*_bypass`) or the bools,
> and snaps numerics unpredictably. **Drive this through `presets/vst/apply_vst_preset.py`** ([[vst-preset]]),
> which `setattr`s every param and snaps numeric targets to the nearest valid value.

### Bypass + bare-load (does it impose a tone?)

| config | rms dBFS | crest | vs source |
|---|---|---|---|
| source excerpt | −17.75 | 16.75 | — |
| `master_bypass=True` | −17.75 | 16.75 | **true null** |
| `l/r_bypass='Bypass'` | −17.75 | 16.75 | **true null** |
| defaults (thresh 10, in 6, out 5) | −17.14 | 16.81 | **+0.6 dB makeup, crest ~unchanged** |

**Bypass is a true null** and a **bare engaged plugin at defaults (thresh 10 = MAX) is near-transparent** — it
applies the output makeup but barely compresses. Safe to load (unlike [[fabfilter-pro-q-4]] you don't need to
"flatten" it; unlike [[pultec-eqp-1a]] it imposes no curve).

### Threshold map — the GR control (input 6, att 5, Med, Comp, out 5; 20 s drum-bus excerpt, raw)

| thresh | 10 | 8 | 6 | 4 | 2 |
|---|---|---|---|---|---|
| rms dBFS | −17.14 | −17.24 | −18.77 | −19.93 | −20.34 |
| crest | 16.84 | 16.80 | 17.05 | 17.38 | 17.49 |

**LOWER `thresh` = MORE gain reduction** (rms drops ~3 dB from 10→2) and **crest RISES** (it pulls the body/RMS
more than the peaks — vari-mu leveling that keeps transients). Threshold 8→10 barely changes (10 = MAX = the
comp only kisses the loudest peaks). Direct mapping — **opposite of the Fairchild's inverted `thresh` enum.**

### Dual Input map — shared drive + level (thresh 5, att 5, Med)

| dual_input | 3 | 5 | 6 | 8 | 10 |
|---|---|---|---|---|---|
| rms dBFS | −33.85 | −24.66 | −19.61 | −14.21 | −13.07 |
| crest | 16.83 | 16.96 | 17.29 | 17.55 | 17.11 |

`dual_input` is the **primary level/drive** (and a stepped input attenuator on the hardware). Toward 0 it
starves the path (quiet, clean); toward 10 it slams the tubes (in10 hit **+4.0 dBFS** — clips in float).
Crest held ~17 across most of the range. **Use it to set how hard the tubes are hit for color** (with `headroom`).

### Attack map — SLOW(0)…FAST(10) (thresh 4, input 6, Med)

| attack | 0 | 2.5 | 5 | 7.5 | 10 |
|---|---|---|---|---|---|
| rms dBFS | −19.86 | −19.86 | −19.93 | −20.62 | −22.03 |
| crest | **17.39** | 17.39 | 17.38 | 17.20 | **16.35** |

**Slow attack (0–5) lets transients through (crest 17.4 = punch); fast attack (10) clamps them (crest 16.4) +
pulls 2 dB more GR.** It's essentially flat 0→5 and only grabs past ~7. (Hardware: 25 ms fast → 70 ms slow.)
**For punch keep attack low; to control transients push it past 7.**

### Recovery map — the 5-position release (thresh 4, input 6, att 5)

| recovery | Slo | Med Slo | Med | Med Fast | Fast |
|---|---|---|---|---|---|
| rms dBFS | −19.76 | −19.86 | −19.93 | −20.02 | −20.18 |
| crest | 17.06 | 17.25 | **17.38** | 17.16 | **16.40** |

**`Med` is the most open (crest 17.38); `Fast` is the densest and pumps (16.40).** Slow holds GR longer (steady
leveling, crest a touch under Med). Hardware times by position: **Slo ≈ 8 s, Med Slo ≈ 4 s, Med ≈ 0.6 s,
Med Fast ≈ 0.4 s, Fast ≈ 0.2 s** (note the big jump Med↔Med Slo). **Slower = more transparent glue; faster = more "breathing"/pump.**

### Comp vs Limit (input 6, att 5, Med)

| config | rms dBFS | crest |
|---|---|---|
| Comp, thresh 4 | −19.93 | 17.38 |
| **Limit, thresh 4** | **−23.55** | 17.34 |
| Comp, thresh 2 | −20.34 | 17.49 |
| Limit, thresh 2 | −24.28 | 17.49 |

**LIMIT pulls far more level than COMP at the same threshold** (−5.8 vs −2.2 dB at thresh 4) — it's the
higher-ratio mode (≈4:1 → 20:1 past 12 dB vs COMP's ≈1.5:1). Crest stays ~17.3 in both — even LIMIT is smooth.
**COMP for glue; LIMIT for heavier leveling / peak control / parallel smash.**

### HP Sidechain (thresh 3, input 6, att 5, Med)

| hp_sc | Flat | In |
|---|---|---|
| rms dBFS | −20.18 | −19.41 |
| crest | 17.45 | 17.09 |

Engaging **`In`** rolls lows out of the **detector** (fixed −3 dB @ 100 Hz, 6 dB/oct; audio path untouched) →
the kick/bass stop triggering GR → **output rises +0.8 dB** and the bus stops pumping. Engage on bass-heavy
material. (It's a simple on/off here, not a sweepable corner.)

### Headroom map — the inverted DRIVE lever (thresh 4, input 6, att 5, Med)

| headroom (dB) | 4 | 16 | 28 |
|---|---|---|---|
| rms dBFS | −17.64 | −19.93 | **−23.57** |
| crest | 16.90 | 17.38 | **15.96** |

**Inverted vs the dB label:** **HR 4 ≈ no net GR (loud) + the hottest drive into the tubes** (most
saturation); **HR 28 = −5.8 dB GR + crest collapse** (cleaner per-sample but compressing hardest). UA's manual
says lower value = *more* internal headroom = you push a hotter signal in before it compresses — which is why,
at fixed input, **HR4 compresses least and colors most; HR28 compresses most.** Treat it as a coarse
**drive/amount** trim that interacts with threshold, and **dial to the meter.** Default 16 is neutral.

### Mix / parallel (thresh 2, input 8, att 8, Fast — a hard wet)

| mix % | 100 | 75 | 50 | 25 |
|---|---|---|---|---|
| rms dBFS | −15.83 | −16.33 | −16.82 | −17.30 |
| crest | 16.00 | 16.21 | 16.42 | 16.60 |

**MIX blends the wet under the dry** (100 = fully wet). As it drops, the dry transients return and crest
recovers. **Crush hard first (hot input + LIMIT + fast attack/recovery), then blend ~40–50 %** for a NY smash.

### The harmonic signature — even/2nd-harmonic, level-dependent (1 kHz sine, H2..H5 rel. fundamental)

| probe | THD | H2 (even) | H3 (odd) | H4 | H5 |
|---|---|---|---|---|---|
| clean (thr10, in3, HR28, −18 dBFS) | 0.031 % | −70.0 | −101.7 | −138 | −132 |
| nominal (thr5, in6, HR16, −18 dBFS) | 0.049 % | −66.3 | −85.1 | −117 | −112 |
| driven (thr3, in9, HR4, −18 dBFS) | 0.034 % | −69.5 | −87.3 | −114 | −114 |
| **driven (thr3, in9, HR4, −6 dBFS)** | **0.208 %** | **−54.1** | −63.9 | −110 | −102 |
| limit (thr2, in9, HR4, −6 dBFS) | 0.093 % | −60.7 | −86.9 | −105 | −111 |

**Predominantly 2nd-harmonic (even) tube/transformer color, and it only appears when the signal is HOT.** At
−18 dBFS it's clean (~0.03–0.05 % even driven); push the *level* to −6 dBFS and THD jumps to 0.21 % with H2
~10 dB above H3. **To add color, drive `dual_input` up and/or `headroom` down so the tubes see a hot signal —
lowering the threshold alone just levels.** (Hardware spec: <0.1 % THD @ 1 kHz; clean unless deliberately driven.)

### M/S vs L-R (measure-stereo; renders peak-trimmed to −1 for a fair compare)

| config | correlation | width dB | low-mid width | note |
|---|---|---|---|---|
| source | 0.975 | −18.92 | −12.58 | — |
| L-R both (thresh 4, linked) | 0.977 | −19.25 | −12.97 | image unchanged |
| M-S both (thresh 4, **linked**) | 0.977 | −19.23 | −13.04 | **== L-R (no change)** |
| **M-S, UNLINKED, mid(L) thr3 / side(R) thr8** | **0.933** | **−14.48** | −8.33 | **wider** |

**In M-S mode `l_*` = MID, `r_*` = SIDE.** **Linked M-S behaves identically to L-R** — the imaging move
*requires* unlinking `ctrl_link` + `sc_link`. **Compress the MID harder than the SIDE → the image widens**
(corr 0.977→0.933, width +4.8 dB). Compress the SIDE harder to narrow/centre. This is the Manley's real
differentiator over the **mono** Fairchild 660 (you'd need the 670 for M/S there).

### Validated renders (real MCP meters, full Watercolors warm drum bus → `projects/watercolors/mix/`)

Source: **−17.18 LUFS · crest 17.17 · true-peak −0.98 · LRA 2.44 · low-band punch 27.15 · low-mid ratio
0.179 · correlation 0.975 · width −18.92 dB.**

| preset | key settings | LUFS (Δ) | crest | LRA | character |
|---|---|---|---|---|---|
| **manley-vari-mu-drum-glue** ★ | in 6 · thr 5 · att 3 · **Med** · Comp · HP-SC In | −17.40 (−0.21) | **17.39** | 2.44→**2.07** | crest UP, LRA tighter, low-mid 0.179→0.184, punch held (27.30) |
| **manley-vari-mu-bus-glue** | in 6 · thr 6 · att 2 · Med Slo · Comp · HP-SC In | −17.29 (−0.11) | 17.29 | 2.44→2.18 | ~1 dB transparent cohesion |
| **manley-vari-mu-parallel-smash** | in 8 · thr 2 · att 8 · Fast · **Limit** · **MIX 45** | −16.57 (+0.61) | 16.59 | 2.30 | denser, low-band punch 27.15→25.99, attack kept by dry |
| **manley-vari-mu-master-ms-glue** | **M-S unlink** · mid thr 6 / side thr 9 · att 2 · Med Slo · Comp | −17.59 | **17.65** | 2.44→**1.93** | **corr 0.975→0.956, width −18.9→−16.4 (wider)** |

Textbook *clean* vari-mu: it tightens the macro-dynamic ride (LRA down) while **keeping or raising crest**
(transients intact), thickens the low-mids only slightly, and stays true-peak safe. The contrast with the
Fairchild 660 on the *same* bus (`fc660-drum-color`: crest 17.17→**16.90**, low-mid →0.188) is the whole story:
**Manley = transparent leveler/glue; Fairchild = thicker color.** Always A/B loudness-matched ([[level-match]] /
`render-ab`) — it adds level + harmonics, so "bigger" can be "louder."

---

## Part B — how it works (web-research synthesis, cited)

> Compiled from the **Manley Variable Mu owner's manual** and **UA's plugin manual**, fact-checked against
> Sound on Sound, Tape Op, Attack Magazine and engineer forums. Several secondary sources **conflate the
> Variable Mu with the cheaper hybrid Nu Mu** and **mis-cite forum quotes** — those are flagged/dropped below.
> This is a **modeled, non-deterministic tube/transformer plugin** — treat any harmonic/GR figure as
> plugin-version-dependent and verify on-rig with [[vst-verify]].

### What it is

The **Manley Stereo Variable Mu®** is an **all-tube, fully-differential, transformer-coupled** stereo
limiter/compressor — Manley Labs' flagship since **1994**. Gain reduction is performed by **"remote cut-off"
(re-biasing)**: a signal-derived, **vacuum-tube-rectified** sidechain control voltage shifts the grid bias of
a variable-gain dual-triode, so the tube smoothly changes **its own gain** (no VCA, opto, or FET). "**Mu**" =
tube slang for gain; *variable mu* = variable gain. It is a **feedback-topology** design (Manley's manual
explicitly; they consider feedforward "unmusical"), which is why **there is no Ratio knob** — ratio is
program-dependent and rises with drive. Its original marketing name was the **"10 dB Limiter"** (up to ~10 dB
of GR meant to be largely inaudible). The balanced/symmetrical circuit cancels distortion and hum, so it stays
**clean across a wide input range unless the engineer deliberately drives it for color** — matching the
measured "even-harmonic, only-when-hot" signature in Part A.

**Vari-mu lineage:** the remote-cutoff principle traces to the **RCA BA-6A (1951)** and **Fairchild 660 (1959)
/ 670 (1960)**; Manley emphasises the **670** connection. The 660/670 are the [[fairchild-660]] siblings in
this repo — same family, different voice.

**Tubes & history:** the **gain (vari-mu) tube is the 5670 dual-triode** (×2; or 6BA6 ×4 with the factory
**T-Bar mod**); the full per-channel complement is **5670 (gain) + 5751/12AX7 (amp) + 12BH7 (output) + 12AL5
(sidechain rectifier)** = 8 tubes in the stereo unit. The original **1994** unit used the **GE 6386** dual-triode
(the Fairchild tube); Manley switched to the **5670 in June 1996** (6386 supply/matching problems). **The
plugin models the 5670-era unit.** Up to ~6 dB of limiting the 6386 and 5670 sound alike; past that the 5670
sounds more "squashed" while the 6386 / T-Bar tubes push further before THD builds.

### Controls (hardware + UA mapping)

| Control | Origin | What it does |
|---|---|---|
| **Input Level** (plugin `dual_input`) | original | Stepped attenuator **ahead of the tubes** — the primary **amount + color/drive** control (hardware steps −8…+8 dB, 12:00 = unity; plugin = a shared 0–10 DUAL INPUT). CW = more threshold/saturation/tube warmth; CCW = transparent. |
| **Threshold** | original | Where GR begins. **MIN (fully CCW) = MOST compression.** (Plugin enum: **lower value = more GR**; default 10 = MAX = least.) In COMP the range *looks* small only because the ratio is low — Manley's fix is "turn up Input," not crank threshold. |
| **Attack** | original | Continuously variable **25 ms (Fast) – 70 ms (Slow)**; Med ≈ 50 ms. Slowest (CCW) lets most percussion pass uncompressed. (Plugin: **0 = slow … 10 = fast.**) |
| **Recovery** | original | **5-position switch: Slo ≈ 8 s · Med Slo ≈ 4 s · Med ≈ 0.6 s · Med Fast ≈ 0.4 s · Fast ≈ 0.2 s.** (Plugin enum labels by position; the big jump is Med↔Med Slo.) |
| **Comp / Limit** | original | **COMPRESS = 1.5:1 soft knee.** **LIMIT = 4:1 sharper knee, rising up to ~20:1 only past 12 dB** of limiting (heavy limiting becomes *more* compressor-like, not harsher). GR curve is a soft "round knee": ~2 dB GR ≈ 1.5:1, ~5–6 dB ≈ 2:1, ~10 dB ≈ 5:1. |
| **Output (Attenuate)** | original | The **only gain make-up**; active **only in IN mode** (not bypass). |
| **HP SC** (sidechain HPF) | original | Gentle **6 dB/oct 1-pole, −3 dB @ 100 Hz** (down 1–3 dB @100, 4–6 dB @50). Rolls lows out of the **detector** so bass doesn't drive the whole comp. Lowering the corner also lowers total limiting. *(The "−3 dB @ 70 Hz" some sources quote is **wrong** — every authoritative spec says 100 Hz.)* |
| **Link** | original | **MONO/SEP** = channels independent; **LINK** = both reduced by the same dB (preserves the stereo image; both channels must be in the **same** COMP/LIMIT mode with matched threshold). |
| **Headroom** | **UA-added** | Sets the **internal operating/reference level** — the plugin's **drive / gain-staging** lever, **inverted**: **lower dB value = more headroom = a hotter signal is pushed into the tubes before it compresses** (more saturation; essential to hit the modeled color without clipping your DAW channel). Values 4/8/12/14/16/18/20/24/28 dB, default 16. (Part A confirms: HR↓ = hotter/more color.) |
| **Mix (Dry/Wet)** | **UA-added** | Built-in **parallel** compression (0 = dry, 100 = wet). |
| **Mid/Side (in/out matrix)** | **UA-added/improved** | M/S better than the hardware's option: **Channel One = Mid, Channel Two = Side.** In SEP/unlink, set width via the thresholds (compress the Mid more → wider; more Mid → narrower). **Not adjustable in LINK.** |
| **Dual input/output** | UA | Two fully independent channels (dual-mono). |

### Technique & recipes (cited; Part-A presets translate these to this rig)

The Manley is a **glue / leveling / coloring** stage, **not** a transient/punch tool (its 25–70 ms attack
passes transients) and **not** a brickwall — mix *into* it and hand off to a real limiter ([[master-track]] /
[[fabfilter-pro-l-2]]).

| Goal | Mode | Target GR | Key settings |
|---|---|---|---|
| Cleanest bus glue | COMP | 2–4 dB | Threshold near MIN, **fast Attack**, drive Input, **slow Recovery**, trim Output |
| Mix-bus glue | COMP | 1–3 dB | both Thresholds equal, **slow Attack + slow Recovery**, LINK on |
| Mastering glue/"sheen" | COMP | ~2 dB (~1.5:1) | slow Recovery (4–8 s), **LINK on**, gentle |
| Drum bus (keep punch) | COMP | 2–4 dB | **slow Attack** (let transients through), Med Recovery, HP-SC In |
| Aggressive drums | COMP/LIMIT | 4–8 dB | medium/fast Attack + medium/fast Recovery |
| Parallel smash | LIMIT | crush | drive Input, low Threshold, then blend **Mix** ~40–50 % |
| Stereo width / master | COMP, **M-S unlink** | 1–3 dB | compress **Mid** more to widen, **Side** more to narrow |

### Manley vs Fairchild (which vari-mu?)

Both are tube vari-mu; the choice is a **coloration/control trade, not better/worse** (impressions from
forums/blogs, corroborated by Part A's measurements):

- **Manley** = more **transparent**, slightly **brighter HF**, **cleaner low-mids**, feels faster; the
  2-bus/mastering choice for **transparent glue + "sheen,"** stays clean even pushed. *Not punchy* (slow attack).
  **Has real M/S + Mix + Headroom.** → measured: keeps/raises crest, barely thickens.
- **Fairchild ([[fairchild-660]])** = compresses **harder**, **more adjustable** (time constants), sounds
  **rounder / deeper / more 3D / more colored**, thickens the low-mids. **660 is mono** (670 for stereo/M-S).
  → measured: drops crest, thickens more.

Reach for the **Manley** when you want clean glue / mastering cohesion / stereo-width control; the **Fairchild**
when you want vintage weight, thickness and "larger-than-life" color.

### Pitfalls

- **It colors + adds level even at low GR — always A/B at matched loudness** ([[level-match]] / `render-ab`).
- **No ratio knob** — sculpt with COMP/LIMIT + Input + Threshold + Headroom; ratio is program-dependent.
- **Color is level-dependent** — to get the tube sound, drive `dual_input`↑ / `headroom`↓ so the signal is
  hot; lowering threshold alone just levels (clean).
- **Not a punch tool** — its slow attack passes transients (good for keeping punch, useless for *adding* it).
  For punch use [[drum-punch]] / a FET/VCA comp / the Fairchild.
- **LINK needs matched channels** (same mode + threshold); **linked M-S == L-R** (no imaging change — unlink for M/S).
- **HEADROOM is inverted** (lower value = hotter/more color/less GR) — the most misread control; dial to the meter.
- **Plugin ≠ hardware:** Headroom / Mix / improved M/S / dual I-O are digital-only; the most-cited
  hardware-vs-plugin difference is low-end 3-dimensionality. **Load the `uaudio_*.vst3` native build**, not the
  passthrough `/Components` twin. **All 23 params are enums → use the preset harness, not the float dict.**
- It's a **color/glue stage, not a master** — hand off to [[master-track]] for loudness/limiting.

## Sources

- https://help.uaudio.com/hc/en-us/articles/18737967080340-Manley-Variable-Mu-Manual — **UAD Manley Variable Mu plugin manual** (authoritative plugin source: Headroom/Mix/M-S, control mapping, HP-SC −3 dB @ 100 Hz)
- https://www.manley.com/products/pro-audio/dynamics/variable-mu · Manley owner's manual (REV 5.2.1, squarespace PDF) — hardware spec, tubes, topology, ratios, recovery times, HP-SC, M/S, history
- https://images.equipboard.com/uploads/item/manual/28965/manley-stereo-variable-mu-manual.pdf — Manley Stereo Variable Mu manual (controls, GR curves, T-Bar mod, link)
- https://www.recordingmag.com/resources/featured-reviews/universal-audio-manley-variable-mu-plug-in/ — Recording Magazine plugin review (Headroom essential for drive; price $299; low-end 3D)
- https://www.soundonsound.com/reviews — Sound on Sound (UAD v7.11 launch; Nu Mu ratio spec, used to disambiguate)
- https://tapeop.com/reviews/gear/124/ — Tape Op #124 (the "1.2:1 rising" ratio measurement — **of the Nu Mu**, not the Variable Mu; do not attribute to this unit)
- https://attackmagazine.com — Manley Vari-Mu character ("transparent sheen and silk… punchy it is not")
- https://www.zenproaudio.com/manley-variable-mu · https://www.sageaudio.com/articles/top-10-analog-mix-bus-compressors — Manley FAQ reproduction + bus-comp roundup (Manley-vs-Fairchild character)
- https://producelikeapro.com/blog/understanding-vari-mu-compressors-history-and-functionality/ — vari-mu history (RCA BA-6A → Fairchild → Manley)
- Headless VST3 hosting / Pedalboard — https://spotify.github.io/pedalboard/reference/pedalboard.html
