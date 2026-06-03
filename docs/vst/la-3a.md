# UADx Teletronix LA-3A — field guide: solid-state opto LEVELING + odd-harmonic grit, headless

How to drive the **UADx Teletronix LA-3A** (`/Library/Audio/Plug-Ins/VST3/uaudio_la3a.vst3`) — Universal
Audio's model of the **Teletronix LA-3A Audio Leveler**, the 1969 **solid-state electro-optical (T4)**
successor to the tube LA-2A. It's the **solid-state opto LEVELER** counterpart to the tube COLOR of the
[[fairchild-660]] and the VCA glue of the [[ssl-bus-compressor-2]] — the measured deep-dive behind the
[[la-3a]] skill and the plugin-specific specialization of [[vst-compress]].

**Part A** is *measured on this rig* (real Pedalboard param surface + our render results); **Part B** is a
*web-research synthesis, cited* (UA documentation + the hardware literature).

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness / peak / stereo and the crest / LRA /
> spectrum that prove "leveling, not just louder." Verify every move with `[L] measure-loudness` /
> `measure-microdynamics` / `measure-spectrum`. A "tighter" feel that doesn't move crest / LRA is a level
> illusion ([[gemini-audio-understanding]]).

---

## TL;DR (the headline, measured)

1. **It is a REAL leveler — it REDUCES crest** (the opposite of the crest-*holding* tube [[fairchild-660]]).
   On the Watercolors warm drum bus, **Peak Reduction** dropped crest 17.2→14.2 at pr 4 (~3 dB GR) and
   →12.8 at pr 6 (~11 dB). It levels transients; that's the job.
2. **No ratio / attack / release knobs** — an opto with **program-dependent** attack/release. Sculpt with
   **PEAK REDUCTION** (amount), **COMP/LIM** (gentle vs hard), **HF EMPHASIS** (the drum control), **GAIN**
   (clean makeup), **MIX** (parallel).
3. **PEAK REDUCTION has a DEAD ZONE** (pr 0–2 = no GR here); it bites from ~pr 3–4. More PR = more GR + lower
   crest + **lower output** → make up with **GAIN**.
4. **HF EMPHASIS (0–100, default 0) is the signature control** and runs the useful way: raising it **takes the
   low end out of the detector** so the kick/bass stop driving GR — hf 0 = full-range = **most GR, darkest,
   most pumped**; hf 25–100 = **less GR, crest recovers (12.8→15.7), kick punches through, balance tilts UP
   into low-mid body + presence**. It's the LA-3A's built-in sidechain HPF.
5. **COMP vs LIM: Limit clamps harder + slightly darker** than Comp at the same Peak Reduction.
6. **It colors with ODD / 3rd-harmonic solid-state grit, NOT even-harmonic tube warmth** — H3 dominant
   (~−48 dB), H2/H4 at the noise floor; **~0 % THD until it's compressing, then ~0.37 %.** Clean-ish.
   **Engaged-flat (pr 0) is clean** except makeup gain (not a colored passthrough).
7. **GAIN is perfectly clean makeup** (~4.9 dB/unit). **MIX is built-in parallel** and **blends AFTER the
   makeup gain** — for a parallel smash you must drive GAIN up or the crushed (quiet) wet adds nothing.
8. **Tooling:** 8 params, all enums. `peak_reduction`/`gain`/`hf_emphasis`/`mix` are numeric (float dict can
   set them), but **`comp_limit` and `meter` are STRING enums** → use the **[[vst-preset]] harness** for any
   Limit-mode recipe.
9. **Renders headless via the `uaudio_la3a.vst3` UADx native build.** The
   `/Components/UAD Teletronix LA-3A.component` legacy UAD-2 twin **passes audio through** offline — never load
   it. **LA-3A = MONO** (dual-mono on a stereo bus).

---

## Part A — measured on this rig (Pedalboard 0.9.x)

**Loads + processes headless.** `load_plugin(".../uaudio_la3a.vst3")` → `name="UADx LA-3A Compressor"`,
renders (`RENDERS ✓` via `probe_plugin.py`, large measured deltas). UADx native is the **perpetual / no-iLok-
dongle** lineage — but re-verify on a new machine. **Load the `uaudio_la3a.vst3` build, not the
`/Components/UAD Teletronix LA-3A.component` twin** (legacy UAD-2 → passthrough offline →
[[vst-verify]] / [[vst]]).

**Param surface (Pedalboard snake_case — what you set in code/the harness). All 8 are ENUMs:**

| Param | Type | Range / values (measured) | GUI control |
|---|---|---|---|
| `peak_reduction` | enum num | `0.0 … 10.0` (0.1 step), **default 3.6** | PEAK REDUCTION (amount/threshold) |
| `gain` | enum num | `0.0 … 10.0` (0.1 step), **default 5.0** | GAIN (makeup output) |
| `comp_limit` | enum str | `'Comp' / 'Limit'`, **default 'Comp'** | COMP / LIM switch |
| `meter` | enum str | `'Off' / 'GR' / 'Output'`, **default 'GR'** (display only) | meter mode switch |
| `hf_emphasis` | enum num | `0 … 100` (1 step), **default 0** | HF (sidechain HF-emphasis) knob |
| `mix` | enum num | `0 … 100` (1 step), **default 100** (100 = wet) | MIX (parallel) |
| `power` | bool | `False / True`, **default True** | OFF / ON |
| `master_bypass` | bool | `False / True`, **default False** | (host bypass) |

> **Enum gotcha.** `[L] apply-vst-chain`'s `parameters` dict is **float-only** — it can set the four numeric
> enums but **NOT the string enums `comp_limit` / `meter`**. Any Limit-mode (or metered) recipe must go
> through **`presets/vst/apply_vst_preset.py`** ([[vst-preset]]), which `setattr`s every param. The numeric
> step is fine via the float dict for a quick Comp-mode move.

### Peak Reduction map — the amount (Comp, gain 5, hf 0; 20 s drum-bus excerpt, raw float, no trim)

| peak_reduction | 0 | 2 | 4 | 6 | 8 | 10 |
|---|---|---|---|---|---|---|
| RMS dBFS | −17.5 | −17.5 | −20.4 | −29.0 | −35.6 | −39.0 |
| crest | 17.2 | 17.2 | **14.2** | **12.8** | 13.1 | 13.4 |
| Δrms vs pr 0 (leveling) | 0 | 0 | −3.0 | −11.5 | −18.1 | −21.5 |

**pr 0–2 do nothing** (dead zone — below threshold for this material). Compression starts ~pr 3–4: crest
falls 17→14 at pr 4, bottoms ~12.8 at pr 6, and the output level drops steeply (make up with GAIN). This is a
**real downward leveler** — it reduces crest, unlike the crest-holding [[fairchild-660]].

### COMP vs LIMIT (gain 5, hf 0)

| | Comp pr 6 | Limit pr 6 | Comp pr 8 | Limit pr 8 |
|---|---|---|---|---|
| crest | 12.8 | **12.4** | 13.1 | **12.8** |
| RMS dBFS | −29.0 | −29.6 | −35.6 | −37.3 |
| centroid Hz | 179 | 176 | 176 | **169** |

**Limit clamps harder and a touch darker** at the same Peak Reduction (lower crest, lower output, lower
centroid). Comp = gentler leveling; Limit = firmer limiting / higher effective ratio.

### HF Emphasis map — the signature drum control (Comp, pr 6, gain 5)

| hf_emphasis | 0 | 25 | 50 | 75 | 100 |
|---|---|---|---|---|---|
| RMS dBFS | −29.0 | −26.4 | −24.5 | −23.2 | **−22.5** |
| crest | 12.8 | **15.7** | 15.1 | 14.6 | 14.4 |
| centroid Hz | 179 | **221** | 204 | 187 | 178 |
| low-mid ratio | 0.159 | **0.256** | 0.246 | 0.225 | 0.214 |

This is the most important control on drums and it runs **opposite to the naïve reading of the name**. At
**hf 0** the detector hears the full low end, the kick/bass hammer it → **maximum GR (−29 RMS), lowest crest
(12.8), darkest (centroid 179), most pumped.** Raising HF **de-emphasizes the lows in the detector** → the
bass stops triggering GR → **less total GR (output rises to −22.5), crest recovers (up to 15.7), and the
balance tilts UP into low-mid body + presence** (centroid jumps to 221 at hf 25). It is effectively the
LA-3A's built-in **sidechain high-pass**. **Raise HF to keep the kick punching + the bus open; leave it at 0
for dense, dark, pumped leveling** (ideal as the crushed layer in parallel).

> **Reconcile with Part B.** The UA manual describes the *detector's* intrinsic tilt (HF flat compresses highs
> *less* than lows; full-CW HF "attenuates 15 kHz 10 dB more than the lows"). The measured **darkening at
> hf 0** above is a *program* effect on this bass-heavy drum bus — the big low end hammers the full-range
> detector into heavy GR while the peaky mid/presence transients (snare/attack) get clamped, so the output
> reads bassier/darker. Raising HF pulls those lows off the detector → far less total GR → brighter + more
> punch. Both descriptions agree on the practical move: **HF up for punch/brightness, HF 0 for dense/dark.**

### Gain (makeup) linearity (pr 0, Comp, hf 0)

| gain | 3 | 5 | 7 |
|---|---|---|---|
| RMS dBFS | −27.2 | −17.5 | −7.7 |
| crest | 17.2 | 17.2 | 17.2 |

**~4.9 dB per unit, perfectly clean** — crest and band ratios unchanged. Pure makeup; gain ≈ 5 sits a touch
hot of unity on this source (+1.4 dB vs the dry).

### MIX / parallel (Limit pr 9, gain 5; raw)

| MIX % | 100 | 50 | 25 | 0 |
|---|---|---|---|---|
| RMS dBFS | −39.9 | −24.2 | −21.2 | −18.9 |
| crest | 13.5 | 16.9 | 17.0 | 17.1 |

`mix` blends the wet under the dry (0 = dry = the untouched source, 100 = wet). **It blends *after* the makeup
gain**, so when you crush hard (which drops the wet's level) you must **raise GAIN** to bring the crushed
layer back up, or blending it down adds almost nothing — see the parallel-smash preset.

### Rest state — does it color/level at rest? (raw)

`master_bypass`, `power off`, and `mix 0` all return the **source exactly** (RMS −18.9, crest 17.1, bands
unchanged). **Engaged below threshold** (`pr 0`, gain 5) is the source **plus the clean +1.4 dB makeup only** —
crest, centroid and band ratios identical to the dry. So unlike the Pultec (which colors when engaged-flat),
the **LA-3A only colors when it is actually compressing.**

### Harmonic signature — odd / 3rd, not tube-even (1 kHz tone)

| | source / bypass | Comp pr 3 | Comp pr 6 | Comp pr 9 | Limit pr 9 |
|---|---|---|---|---|---|
| THD % | 0.000 | 0.000 | **0.370** | 0.372 | 0.357 |

Harmonic breakdown (dB rel. fundamental, while compressing): **H3 ≈ −48 dB (dominant), H5 ≈ −60 dB; H2 and H4
at the −140 dB noise floor.** The LA-3A's distortion is **odd-order / symmetric** (the push-pull solid-state
signature) — a subtle 3rd-harmonic *grit/edge*, **not** the even-harmonic *warmth* of a tube/transformer box
([[fairchild-660]] / [[pultec-eqp-1a]] / [[ampex-atr-102]]). THD is **generated by the gain-reduction action**
(≈0 until it's working, then ~0.37 % and roughly flat) — not by input drive. A clean-ish opto.

### The tonal signature (full-render spectrum — HF flips dark ↔ bright)

On the full peak-normalized renders, **with HF raised** the leveling moves energy **out of the sub/low and up
into the low-mid body + presence**: source low 0.792 / low-mid 0.179 / centroid 1747 → **drum-glue** (hf 35)
0.758 / **0.209** / 1754, **bus-level** (hf 20) 0.767 / 0.198 / 1762 (tilt −2.67→−2.49). That's the
**presence/forwardness** the LA-3A is loved for. **With HF at 0** (parallel-smash) the lows hammer the
detector and the crushed layer instead **thickens the bottom** (low 0.792→**0.826**, low-band RMS +1.8 dB).
So HF is also a tone control: **up = body/presence, 0 = dark/weight.**

### Validated renders (real MCP meters, full warm drum bus → `projects/watercolors/mix/`)

Source: **−17.18 LUFS · crest 17.17 · true-peak −0.98 · LRA 2.44 · low-band block-crest 17.14 · low-band punch 27.15.**

| preset | key settings | LUFS (Δ) | crest | TP dBTP | LRA | character |
|---|---|---|---|---|---|---|
| **la3a-drum-glue** ★ | Comp · pr 4.5 · **hf 35** | −16.50 (+0.68) | 16.67 | −0.99 | 2.36 | kick tightened (low-band crest 17.1→14.8, punch held 26.6), **more body/forward** (low-mid 0.179→0.209, centroid +7) |
| **la3a-bus-level** | **Limit** · pr 6 · hf 20 | −16.08 (+1.10) | 16.26 | −0.98 | **1.72** | firm leveling, LRA notably tighter, presence up (centroid 1762) |
| **la3a-parallel-smash** | **Limit** · pr 9 · hf 0 · **mix 45** · gain 9.5 | −15.61 (**+1.57**) | 15.49 | −0.98 | 2.07 | thicker bottom (low 0.792→0.826, low-band RMS +1.8 dB), kick sustain filled (punch 27.1→22.1), **dry attack kept** |

Textbook opto leveling: crest comes down (it *levels*), LRA tightens, density up at the same peak, and the
tone goes **forward/present** when HF is up or **thick/weighty** when HF is 0. A/B loudness-matched (it adds
level + grit) — `[L] render-ab` (`la3a_drum-glue_ab.wav`) / [[level-match]].

---

## Part B — how it works (web-research synthesis, cited)

### What it is

The **Teletronix LA-3A Audio Leveler** is a 1969 **solid-state electro-optical compressor** — the transistorized successor to the tube-based LA-2A. It debuted at the 1969 New York AES show under UREI (which had absorbed the Teletronix brand) and stayed in production until roughly 1981. It is usually credited to **Brad Plunkett** (working under UA founder **Bill Putnam Sr.**); some accounts also place Putnam himself on the design, and the unit deliberately borrows transient/front-end ideas from Putnam's solid-state **1176**.

Gain reduction is done by a **T4(B) electro-optical attenuator** — the same opto-cell family the LA-2A uses. The T4B is a sealed module pairing an **electroluminescent panel** (which lights in proportion to the rectified sidechain/control signal) with **two cadmium-sulfide photoresistors**: one in the audio gain-reduction path, one driving the meter. The original cells were **Clairex CL-505L**; after that part was discontinued, modern reproduction/replacement T4B cells commonly substitute the **Silonex NSL-5910** (this is an aftermarket substitution, *not* a "later production version" of the original line — and builders note the NSL-5910 is measurably faster, so cells get sorted to recover vintage ballistics). Because the photocell's brightness-to-resistance response is inherently sluggish and history-dependent, **attack and release are program-dependent and not user-adjustable** — the cell, not a knob, sets the timing.

The LA-3A is fundamentally a **mono** unit (a 2U half-rack chassis), linkable for stereo. The UADx version is a **component-modeled emulation** of that hardware — it reproduces the T4 cell and the transistor stages — which means, like any analog model, it is **non-deterministic across plugin/software versions**: the exact sound can shift as UA refines the model (the 2021 "Classic Audio Leveler" remodel being the relevant modern build).

### Controls

| Control | Origin | What it does |
|---|---|---|
| **Peak Reduction** (0–10) | original hardware | The only "amount" control: simultaneously sets threshold and compression depth. CW lowers threshold → more gain reduction. Arbitrary scaling, not dB. |
| **Gain** (0–10) | original hardware | Clean makeup/output gain (up to ~+50 dB), compensating for level lost to compression. |
| **Meter switch** (GR / OUTPUT / OFF) | original hardware | GR shows gain reduction in negative dB; OUTPUT shows output level (0 VU = +4 dBm); OFF disables metering. |
| **COMP / LIM** | **disputed — see note** | Selects a gentler, low-ratio curve (COMP) vs. a much harder, near-limiting curve (LIM). On the UADx plugin this is a front-panel switch. |
| **HF (HF Emphasis / HF Contour)** | original hardware (rear-panel set-screw) | A high-frequency emphasis shelf in the **sidechain/detector** (not a program EQ): boosts the highs feeding the detector so gain reduction becomes more sensitive to highs. On hardware it's a rear set-screw, shipped FLAT; UA surfaces it as a continuous front-panel knob. |
| **MIX** (0–100%) | **UA-added (plugin-only)** | Dry/wet parallel-compression blend. No counterpart on the original hardware. |

There are **no ratio, attack, or release knobs** — ratio is fixed by mode, and timing is program-dependent via the T4 cell.

> **Disputed — COMP/LIM origin.** Research framed the COMP/LIM switch as standard original-hardware equipment. **Verification refutes this:** the original UREI/Teletronix LA-3A *Instruction Manual* lists only Gain, Peak Reduction, Meter Selector, and Power as panel controls, and describes **one fixed "combined compressor-then-limiter" curve** with no user ratio switch. A selectable Comp/Limit ratio is a documented **LA-2A** feature; on LA-3A-derived gear (the UAD plugin/reissue, and clones like the Golden Age Comp-3A and AudioScape DA-3A/V3A) it appears as a popular **mod or plugin addition**, not factory hardware. Secondary sources (MusicRadar, Sound on Sound) claim vintage units had a *rear-panel* comp/limit switch later moved to the front, but the primary manual does not support a factory switch. **In the UADx plugin you do get COMP/LIM regardless** — just don't bill it as original-stock hardware.

> **Disputed — HF/MIX as "digital-only."** Research grouped HF and MIX together as UA-added controls. **Verification corrects this:** only **MIX** is genuinely plugin-only. The **HF** knob models the hardware's real rear-panel **HF Contour** sidechain emphasis circuit (UA Manual 65-1301 documents it on the hardware) — so it is *newly exposed on the front panel*, not *absent from the hardware*.

### Dynamic behavior

The LA-3A has **no timing knobs**; the T4 opto cell sets everything from the program. **Attack is ~1.5 ms or less and level-dependent** — faster on large transients, slower on small ones. **Release is two-stage and program-dependent**: roughly **60 ms to ~50% recovery**, then a long **0.5–5 s** tail to full release, faster after brief compression and slower after sustained compression (this auto-release is what keeps it from pumping). One independent modeling measurement (Slate's SD-3A) — **verification-confirmed** — clocks the cell at **~60 ms to reach 90% of target gain reduction**, with ~150 ms to 50% release and up to ~10 s to full recovery; the 1.5 ms figure is the fast *initial onset*, the 60 ms figure is the time to *settle*, so the two coexist rather than contradict.

The **ratio is sliding and program-dependent**, nominally cited as **~3:1 in COMP**, rising toward higher ratios (and ~10:1 in deep gain reduction) and going to near-limiting in **LIM**. Treat the numbers as nominal:

- The **~3:1** figure is UA's modeling/help-article number, **not** a printed manual spec. The original Teletronix/UREI manual instead calls COMP "linear gain reduction" and quotes the LIM ratio as **"approaching 50:1"** (nominal) — not literal infinity:1.
- The curve has a **soft knee** and is **frequency-dependent** (a property of optical gain reduction), so a single ratio number is an approximation by definition.
- **COMP vs LIM differs audibly mainly in deep compression**; most users leave it in COMP.

The LA-3A is **faster and more aggressive than the LA-2A** — that part is well documented. **But the common attribution is imprecise** (verification, partly): the speed is *not* caused "specifically by the solid-state **gain stage**." Both units share the same T4 cell; in an opto leveler the **detector/sidechain and the front-end impedance that drives the cell** set attack ballistics, not the audio amplifier. The transistor gain stage mainly changes *tone* (transistor edge instead of tube coloration). The honest statement: "solid-state **circuitry/front-end** (borrowing from the 1176) makes it faster," with the faster attack applying chiefly to **large** transients while small-transient attack stays close to the LA-2A.

### The HF-emphasis signature

The LA-3A's detector is **frequency-dependent**, and this is its real signature — but two myths need correcting.

**Native behavior (HF flat, as-shipped).** **Verification-confirmed:** with the HF Contour flat (full CCW, the shipped state), the LA-3A compresses **highs LESS than lows**, level-dependently — so left alone it tends to clamp the low end harder, which is exactly why a tilted-up "brighter" character emerges under compression.

**The HF knob.** Turning HF up adds a **high-frequency boost into the sidechain only** ("NOT an EQ of the audible program material," per UA Manual 65-1301). That makes the detector **more sensitive to highs**, so it compresses the top more: at full CW the manual states it "**will attenuate 15 kHz 10 dB more than the lower frequencies.**" Functionally, raising HF also pulls **lows off the detector**, so kick/bass stop triggering gain reduction — which is why it's prized on **drum buses** (the kick punches through) and as a **quasi-de-esser** on vocals. **Verification-confirmed** its origin: it was designed to give **radio stations** control over broadcast HF content (taming FM pre-emphasis to avoid over-modulating the transmitter).

> **Refuted myth — "the LA-3A's detector is intrinsically HF-emphasized and clamps highs harder than the LA-2A."** Both units default to **flat** sidechains and behave comparably when flat (same T4 cell). HF emphasis is **opt-in** on both. And at maximum, the **LA-2A's** Emphasis (R37) can reach **~17 dB at 15 kHz** — a *deeper* sidechain HF boost than the LA-3A's ~10 dB — so if anything the LA-2A can be made *more* HF-sensitive. The LA-3A's "brighter/more aggressive" reputation is about **speed and midrange-forward character**, not a permanently HF-weighted detector.

> **Refuted myth — direction + cause.** A widely-copied line (originating in Slate's SD-3A copy) says the LA-3A "compresses highs less than lows **due to the opto cell**." Verification: the cell is genuinely level-dependent, but the *documented* frequency tilt is a **sidechain pre-emphasis shelf**, not an inherent opto property — and when the HF knob is engaged the unit compresses **highs MORE, not less**.

**How much it colors.** The LA-3A is a comparatively **clean, transparent** compressor — its solid-state stages add **minimal harmonic distortion** (the opposite of the tube LA-2A's "bright-sounding distortion"). Its brightness and bite on guitar/drums come from **faster response + optional HF detector emphasis, NOT from saturation**. (One caution on EL-panel folklore that surfaced in research and was **partly refuted**: claims that the T4B's "brightness rises with frequency to ~1 kHz" and "shifts green→blue above ~1500 Hz" describe **EL-lighting physics under AC excitation in general** — they do **not** describe how the cell operates in the compressor, where the panel is driven by the **audio control-signal amplitude (level)**, not a tuned drive frequency. The cell's real contribution to character is its **time constants**, not color-shift.)

### LA-3A vs LA-2A vs 1176

| | Technology | Speed (attack) | Aggression / ratio | Color | Best on |
|---|---|---|---|---|---|
| **LA-2A** | Tube + T4 opto | Slowest — ~10 ms fixed | Gentlest; ~3:1 COMP / ∞:1 LIM | Warm, "creamy/gooey" tube harmonics, band-limited | Vocals, bass — smooth, invisible leveling |
| **LA-3A** | **Solid-state + same T4 opto** | ~1.5 ms, program-dependent (faster than LA-2A on large transients) | Middle ground; ~3:1 COMP / high LIM (nominal) | Clean/transparent, bright, mid-forward; minimal added distortion | Drums, room/overheads, electric guitar, rock vocals |
| **1176** | FET (solid-state), no opto | Fastest — 20–800 µs | Most aggressive/colored; selectable 4/8/12/20:1 (+"all-buttons") | Distinctive FET grit/color | Drums, rock vocals, electric guitar, peak/transient control |

Shared lineage: LA-2A and LA-3A use the **same T4 ELOP cell** (tube vs. transistor amplification is the difference); the classic studio chain is **1176 → LA-2A** (fast peak catch into smooth leveling).

### Technique & recipes

| Source | COMP/LIM | Target GR | Notes |
|---|---|---|---|
| **Electric guitar** (the classic) | COMP (LIM for more grab) | ~2–4 dB | Mid-forward character sits guitars in the mix; fast attack tames pick transients. The LA-3A's signature use. |
| **Drums / parallel** | LIM (or COMP) | 6–12 dB on the crushed path | "New York" parallel trick: smash a copy, blend under the dry. Punch is preserved by the **dry path**, not the LA-3A (its ~1.5 ms attack actually *softens* transients) — that's the point of going parallel. ~7 dB is a defensible "thick but punchy" amount. Use **HF emphasis / sidechain HPF** so the kick doesn't trigger it. *(All taste, not spec.)* |
| **Lead vocal** | COMP | 3–5 dB (meter dancing −3 to −5) | UA recommends 3–6 dB for "invisible" compression; "Trust your ears" up to −10+. Tom Lord-Alge famously pushes ~20 dB then follows with a fast-attack SSL to tame the overshoot. |
| **Bass** | COMP | 3–6 dB | Midrange character + transparent leveling; can add grit/depth, often paired with a second compressor. |
| **Bus / stereo bus** | COMP | 1–3 dB | Gentle glue (1 dB is audible; ~2 dB buys ~2 dB extra average level). Use the plugin's **MIX** for parallel bus glue. Note it's a **mono** unit linked for stereo — for true stereo glue reach for a dedicated stereo comp. |

### Pitfalls

- **It's a modeled plugin → non-deterministic.** The analog model can change between UA software versions; A/B before relying on a specific render and re-verify behavior after updates.
- **Load the native build.** Use **`uaudio_la3a.vst3`** (UADx native — renders headless/offline). The legacy `…/Components/UAD Teletronix LA-3A.component` twin **passes audio through unprocessed** offline — never use it for headless rendering.
- **Mono unit.** It processes a single channel (dual-mono linked on a stereo bus). Fine for instrument/drum buses; not a true-stereo glue tool.
- **It colors and adds level — A/B loudness-matched.** Makeup gain and added density make it sound "better" just by being louder; match levels before judging.
- **No ratio knob.** You shape with **Peak Reduction** (amount/threshold) and **COMP/LIM** (curve) only — there is no continuous ratio control, and timing is fixed by the opto cell.
- **HF is a sidechain control, not an EQ.** It changes *what triggers* compression, not the program tone directly — reach for it to keep the kick out of the detector, not to brighten the audio.

## Sources

- https://www.uaudio.com/blogs/ua/teletronix-la-3a-origins
- https://www.uaudio.com/products/uad-la-3a
- https://help.uaudio.com/hc/en-us/articles/13925934548884-Teletronix-LA-3A-Compressor-Manual
- https://media.uaudio.com/assetlibrary/l/a/la-3a-manual.pdf
- https://thehistoryofrecording.com/Manuals/UREI/Urei%20LA-3A%20manual.pdf
- https://tile.loc.gov/storage-services/master/mbrs/recording_preservation/manuals/UREI%20(Teletronix)%20Model%20LA-3A%20Leveling%20Amplifier.pdf
- https://www.manualslib.com/manual/462001/Universal-Audio-La-3a.html
- https://help.uaudio.com/hc/en-us/articles/13197634336660-What-s-the-Difference-Between-UAD-Native-and-UAD-DSP-Apollo-Plug-Ins
- https://www.sweetwater.com/insync/universal-audio-la-2a-versus-la-3a/
- https://www.sweetwater.com/insync/la-2a-emphasis-control/
- https://slatedigital.com/the-sd-3a-story-how-we-modeled-the-classic-la-3a/
- https://www.mixonline.com/technology/field-test-universal-audio-la-3a-audio-leveler-370271
- https://tapeop.com/reviews/gear/49/la-3a-audio-leveler-reissue
- https://www.soundonsound.com/reviews/golden-age-project-comp-3a
- https://www.soundonsound.com/techniques/classic-compressors
- https://www.musicradar.com/news/blast-from-the-past-urei-la-3a
- https://mixdownmag.com.au/features/from-the-vault-la-3a-audio-leveler/
- https://vintageking.com/blog/around-the-shop-urei-la-3a/
- https://en.wikipedia.org/wiki/LA-2A_Leveling_Amplifier
- https://en.wikipedia.org/wiki/1176_Peak_Limiter
- https://www.justmastering.com/article-classiccompressorsguide.php
- https://www.sonarworks.com/blog/learn/get-the-most-from-optical-compressors
- https://www.proreplicas.com/t4b_cell.html
- https://www.audio-scape.com/news/t4b
- https://groupdiy.com/threads/t4-optical-attenuator-for-teletronix-la-2a-and-how-the-compressors-works.80210/
- https://www.advancedphotonix.com/wp-content/uploads/2022/03/DS-NSL-5910.pdf
- https://gearspace.com/board/so-much-gear-so-little-time/1182252-what-differences-btw-la2a-la3a.html
- https://gearspace.com/board/so-much-gear-so-little-time/130340-attack-release-times-la-2a-la-3a.html
- https://gearspace.com/board/high-end/70158-anyone-dig-la3a-drums-toms-perhaps-room-mics.html
