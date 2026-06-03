# FabFilter Pro-Q 4 — field guide: surgical + dynamic + spectral EQ, headless

How to drive **FabFilter Pro-Q 4** (`/Library/Audio/Plug-Ins/VST3/FabFilter Pro-Q 4.vst3`) — a 24-band,
fully-parametric mix/master EQ with per-band **dynamic EQ**, the new **Spectral Dynamics** (a Soothe/Gullfoss-
style resonance/de-harsh mode), analog-style **Character** saturation, and three phase modes. It's the
**surgical/transparent** EQ of the [[vst-eq]] suite — the precise-curve counterpart to the vintage Pultec/Neve
and the air-only Maag. **Part A** is *measured on this rig* (the real Pedalboard param surface + our own render
results); **Part B** is a *web-research synthesis, adversarially verified, cited* (FabFilter's own docs + reviews).
The skill [[fabfilter-pro-q-4]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the tilt/centroid that
> prove a tonal move. Verify every EQ move with `[L] measure-spectrum` / `measure-loudness` (+ `measure-stereo`
> for M/S moves). A curve that "sounds" changed but shows a 0.00 spectrum delta is a passthrough.

---

## TL;DR (the headline, measured)

1. **It renders headless AND it's no-iLok** — uniquely safe here. Pro-Q 4 loads + processes through Pedalboard
   (param-response confirmed; our EQ move shifted the low band 97.2 → 91.2 dB). FabFilter uses a **simple
   license key, no iLok/PACE/UAD dongle** (offline-activatable, multi-machine), so unlike the [[vst-hosting-outside-daw]]
   landmines (iLok/UAD) it is a *clean* render-farm candidate. Use the **VST3** path; the AU `.component` twin
   and Pro-Q 3 are also installed — don't confuse them.
2. **A bare load is NOT flat — it restores FabFilter's last-saved GUI curve.** `load_plugin(...)` came up with
   the exact curve from the screenshot (band 1 Low Cut @30 Hz, band 2 Bell @202 Hz, band 3 Bell @4085 Hz). So
   any "fresh" render rides a leftover curve. **Flatten first** (disable all 24 bands → verified bit-exact
   bypass, 1.5e-16) then configure only the bands you want, or restore a `dump_state` blob.
3. **`apply-vst-chain`'s float dict can't really drive Pro-Q.** All 581 params are Pedalboard `valid_values`
   lists; the **string enums** (`band_N_shape`, `band_N_slope`, `band_N_used`, `processing_mode`, `character`)
   can't be set through a float-only dict, and you can't *enable an Unused band* through it. Our `band_8_gain=-12 @500 Hz`
   move via `apply-vst-chain` was a **no-op** (band 8 was Unused; only the restored bands 1–3 rode along). The
   real control path is the **[[vst-preset]]** harness (`apply_vst_preset.py`, `setattr` — reaches strings + bools).
4. **The standout features all render headless and measure.** Per-band **dynamic EQ** (with the new attack/release),
   **Spectral Dynamics** (`band_N_spectral_*`), and **Character** all work offline: our **Spectral Dynamics**
   de-harsh band ducked **5 kHz by 3.0 dB** while leaving **4 kHz (−0.1) and 8 kHz (+0.4) essentially untouched**
   — the surgical "only the offending frequencies" behavior a static cut can't do; `character="Warm"` added a
   measurable **+0.5 dB** broadband color on an otherwise-flat instance. **Meters own it** — read centroid/tilt/band-ratios.

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin("…/FabFilter Pro-Q 4.vst3")` → `name="Pro-Q 4"`,
`is_instrument=False`, renders (a configured EQ move changes the audio; disabling all bands == input). Tested
with **Pedalboard 0.9.23**, input `artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav`.

`list-vst-plugins {name_contains:"Pro-Q"}` returns four entries — **use the VST3 Pro-Q 4**:

| Name | Path | Use |
|---|---|---|
| **FabFilter Pro-Q 4** | `/Library/Audio/Plug-Ins/VST3/FabFilter Pro-Q 4.vst3` | ✅ this one |
| FabFilter Pro-Q 4 | `…/Components/FabFilter Pro-Q 4.component` | AU twin (macOS-only) |
| FabFilter Pro-Q 3 | `…/VST3/FabFilter Pro-Q 3.vst3` | prior version |
| FabFilter Pro-Q 3 | `…/Components/FabFilter Pro-Q 3.component` | prior version, AU |

### The real parameter surface (Pedalboard-exposed — authoritative)

**581 automatable parameters: 24 bands × 23 params + 29 globals.** Every parameter — even frequency/gain/Q —
is exposed as a Pedalboard **`valid_values` list** (a quantized grid), not a free `min/max` float. Numeric
params accept a `setattr` float and **snap to the grid** (gain step ≈ 0.06 dB, frequency on a log grid: we set
`band_2_gain=-5.0` → read back `-4.98`; `band_1_frequency=80.0` → `80.18`). String/bool params take the exact
enum value.

**Per-band params** (`band_1_…` through `band_24_…`):

| Param | Type | Values (grid) | Control |
|---|---|---|---|
| `band_N_used` | enum | `Unused` · `Used` | is the band slot active at all |
| `band_N_enabled` | bool | `False` · `True` | band on/off (disable all 24 = true bypass) |
| `band_N_frequency` | enum-num | 10 … 30000 Hz (1001 log steps) | centre frequency |
| `band_N_gain` | enum-num | −30 … +30 dB (1001 steps ≈0.06 dB) | gain (Bell/Shelf/Flat-Tilt) |
| `band_N_q` | enum-num | 0.025 … 40 (882 steps) | Q / bandwidth |
| `band_N_shape` | enum | `Bell`,`Low Shelf`,`Low Cut`,`High Shelf`,`High Cut`,`Notch`,`Band Pass`,`Tilt Shelf`,`Flat Tilt`,`All Pass` | filter shape (10) |
| `band_N_slope` | enum | `0 dB/oct` … `96 dB/oct` (fractional, 662 steps) + `Brickwall` | cut/filter slope |
| `band_N_stereo_placement` | enum | `Left`,`Right`,`Stereo`,`Mid`,`Side` | per-band L/R/M/S |
| `band_N_speakers` | enum | 15 (`All Speakers`,`All (excl. LFE)`,`LFE`,`Center`,`L/R (Front)`…) | surround/Atmos speaker scope |
| `band_N_dynamic_range` | enum-num | −30 … +30 dB | **dynamic EQ** amount (neg=compress, pos=expand) |
| `band_N_dynamics_enabled` | enum | `Dynamics Disabled` · `Dynamics Enabled` | turn the band dynamic |
| `band_N_dynamics_auto` | enum | `Dynamics Auto` · `Dynamics Manual` | auto vs manual attack/release |
| `band_N_threshold` | enum | `-90.0 dB` … `-0.1 dB` + `Auto` (681) | dynamic threshold |
| `band_N_attack` | enum-num | 0 … 100 (1001) | dynamic attack (**50 = auto centre**) |
| `band_N_release` | enum-num | 0 … 100 (1001) | dynamic release (**50 = auto centre**) |
| `band_N_external_side_chain` | bool | `False` · `True` | trigger from external SC |
| `band_N_side_chain_filtering` | enum | `Band` · `Free` | trigger band vs free SC filter |
| `band_N_side_chain_low_frequency` | enum-num | 10 … 20000 Hz | SC low-cut |
| `band_N_side_chain_high_frequency` | enum-num | 10 … 20000 Hz | SC high-cut |
| `band_N_side_chain_audition` | bool | `False` · `True` | listen to the trigger |
| `band_N_spectral_enabled` | bool | `False` · `True` | **Spectral Dynamics** on this band |
| `band_N_spectral_density` | enum-num | 0 … 100 (1001) | spectral selectivity (low=wide, high=surgical) |
| `band_N_solo` | bool | `False` · `True` | solo this band's range |

> **Note:** the per-band **Spectral Tilt** parameter that FabFilter added in the **4.02** point release is **not
> in the Pedalboard surface** here (we see `spectral_enabled` + `spectral_density` but no `spectral_tilt`) — the
> installed build may predate 4.02, or the tilt isn't automation-exposed. Don't script it; it's not reachable.

**Global params** (29):

| Param | Type | Values | Role |
|---|---|---|---|
| `processing_mode` | enum | `Zero Latency` · `Natural Phase` · `Linear Phase` | phase/latency mode |
| `processing_resolution` | enum | `Low`,`Medium`,`High`,`Very High`,`Maximum` | linear-phase quality (latency) |
| `character` | enum | `Clean` · `Subtle` · `Warm` | **analog saturation** (Subtle=transformer, Warm=tube) |
| `gain_scale` | enum-num | 0 … 200 % | scale ALL band gains proportionally |
| `output_level` | enum-num | −inf … +36 dB | output gain |
| `output_pan` / `output_pan_mode` | enum | … / `Left/Right` · `Mid/Side` | output pan / mode |
| `auto_gain` | bool | `False` · `True` | estimate make-up gain (NOT metered) |
| `output_invert_phase` | enum | `Normal` · `Inverted` | polarity |
| `analyzer_*` | mixed | range 60/90/120, resolution, speed, tilt 0/1.5/3/4.5/6, freeze, pre/post/ext, `analyzer_show_collisions` | spectrum analyzer + collision/masking |
| `spectrum_grab` | bool | `False` · `True` | drag-a-peak grab |
| `display_range` | enum-num | 3 · 6 · 12 · 30 dB | GUI scale (3/6 master, 12/30 mix) |
| `bypass` / `host_bypass` | enum | `Not Bypassed` · `Bypassed` | bypass |
| `solo_gain` | enum-num | −20 … +20 dB | solo-listen gain |
| `receive_midi`, `internal`, `midi_cc`, `pitch_bend`, `channel_pressure` | — | — | MIDI-learn plumbing (ignore) |

### Three footguns (proven)

1. **A bare load restores the last-saved GUI state, not a flat EQ.** Our first `load_plugin` came up exactly as
   the screenshot (band 1 Low Cut @30 Hz/72 dB/oct, band 2 Bell @202 Hz, band 3 Bell @4085 Hz, with dynamics
   on). On a drum loop that restored curve only nudged the tone (97.23→96.96 dB low) — small, but it means **you
   are never starting flat**. Always flatten, or restore a known `dump_state`.
2. **Disabling all 24 bands == bit-exact bypass** (`max|flat − dry| = 1.5e-16`). This is the deterministic clean
   slate: set `band_4_enabled=False … band_24_enabled=False`, then configure 1–3.
3. **`apply-vst-chain`'s float dict can't enable/shape a band.** Setting `band_8_gain=-12, band_8_frequency=500,
   band_8_q=2` via the tool reported `parameters_set` + `changed:true` — but the **500 Hz band didn't move**
   (−23.47 → −23.10 dB; that drift is just the restored bands 1–3). Band 8 was `Unused`, and the float dict
   can't set `band_8_used="Used"` / `band_8_enabled` / `band_8_shape` (string enums). **Conclusion: use the
   preset harness for any real Pro-Q move.** The float dict only works for tweaking a band that's *already*
   Used + enabled + the right shape in the restored/loaded state.

### How to actually drive it headless

Use **[[vst-preset]]**'s `apply_vst_preset.py` (it `setattr`s every param, strings included). The preset must
**flatten first** (disable unused bands) then fully configure each used band (`*_used="Used"`, `*_enabled=True`,
`*_shape`, `*_frequency`, `*_gain`, `*_q`, plus `*_slope` for cuts, `*_dynamics_enabled`/`*_dynamic_range`/
`*_threshold` for dynamic, `*_spectral_enabled`/`*_spectral_density` for spectral). Set `dump_state=true` (via
`apply-vst-chain`) once you like it, then re-render from the opaque `.state` blob for byte-stability.

### Measured result — the shipped de-harsh preset

`presets/vst/fabfilter-proq4-drum-deharsh.json` (flatten → HPF 35 Hz/24 dB/oct → −3 dB Bell @250 Hz → a
**Spectral Dynamics** Bell @5 kHz, gain 0 / dynamic_range −8 / density 70 / Auto threshold → Natural Phase, Clean),
applied to the Watercolors drum loop:

| third-octave / metric | dry | spectral de-harsh | Δ |
|---|---|---|---|
| 250 Hz | −17.4 | −19.9 | **−2.5** (the static −3 dB bell) |
| 4 kHz | −22.9 | −23.0 | −0.1 (spared) |
| **5 kHz** | −21.4 | −24.4 | **−3.0** (Spectral Dynamics ducked the ring) |
| 6.3 kHz | −22.1 | −23.6 | −1.6 |
| 8 kHz | −25.9 | −25.5 | +0.4 (spared) |
| <40 Hz | −28.6 | −31.3 | HPF removed sub |
| spectral centroid | 1593 Hz | 1655 Hz | (lows cut; only 5 kHz nipped) |
| spectral tilt | −2.71 | −2.56 | (slightly less steep) |

The Spectral Dynamics band is **surgical** — it ducked 5 kHz by 3.0 dB while sparing 4 kHz (−0.1) and 8 kHz
(+0.4), i.e. it pulled down only the ringing frequencies *inside* the band, not the whole 4–8 kHz region a static
−3 cut would dull. **Reproducibility gotcha (hard-won, a 4th footgun):** the band's `dynamic_range` must be set
**explicitly** — an unset `band_N_dynamic_range` silently inherits the restored state's value (an early render
hit a leftover −4.11 from the screenshot session, which inflated the result and made it non-reproducible). Set
`gain` (static base), `dynamic_range` (the spectral excursion), `dynamics_enabled`, `threshold`, `spectral_enabled`,
and `spectral_density` on the band, all explicitly. This is what `[L] suppress-resonances` / [[de-harsh]] and
`[L] apply-dynamic-eq` / [[dynamic-eq]] approximate in **pure DSP with no plugin** — reach for those when you
don't need Pro-Q's exact curve.

### Character knob (the new saturation) — measured

On an otherwise all-disabled instance, `character="Warm"` raised the loop ~**+0.5 dB broadband** (97.23→97.76
low, 69.72→70.26 high) — a real, measurable tube-style color, **not** bit-unity. So even with no EQ bands,
`character != Clean` processes. Re-measure; don't assume Clean-equivalent.

---

# Part B — how Pro-Q 4 works (web-research synthesis, adversarially verified, cited)

Released **December 12, 2024** (point release **4.02**, Feb 27, 2025); intro price EUR 169 / USD 179 / GBP 144.
Formats: VST, VST3, AU, **CLAP**, AAX Native, AudioSuite (+ an iOS app). 24 bands, 10 -30…+30 dB.

## 1. What is genuinely NEW in Pro-Q 4 vs Pro-Q 3

The #1 hallucination risk is calling a Pro-Q 3 feature "new." Verified split:

**NEW in Pro-Q 4:**
- **Spectral Dynamics** *(the marquee feature)* — per-band, frequency-selective dynamics; processes only the
  frequencies *inside* a band that cross the threshold, leaving the rest of the band untouched. Soothe/Gullfoss-
  adjacent. (§3)
- **Dynamic-EQ Attack & Release controls** — Pro-Q 3's dynamic EQ was auto-timing only.
- **Free side-chain filtering** per dynamic band — choose the frequency slice (or external source) that triggers
  the band (`Band` vs `Free`, with SC low/high-cut + audition). Pro-Q 3's external SC was whole-signal only.
- **Character modes** — `Clean` (transparent, = Pro-Q 3) · `Subtle` (transformer-style saturation, odd+even
  harmonics) · `Warm` (tube-style, strong 2nd harmonic). Pro-Q 3 had **no** saturation. Global, **no amount
  knob** (intensity fixed per mode) — apply selectively. (Product-page calls these "Gentle and Warm"; the help
  uses Clean/Subtle/Warm — same control.)
- **EQ Sketch** — drag a curve across the display in one gesture; Pro-Q instantiates matching filters (slope =
  gesture steepness).
- **Instance List** — view/control every Pro-Q 4 instance from one window (the cross-plugin reach to control
  Pro-C 3 / Pro-DS / Pro-G arrived in the **4.10** update, not the launch build), copy/paste curves between them;
  enables **cross-instance collision detection**.
- **Fractional / continuous slopes** to 96 dB/oct (e.g. 3.5 dB/oct) + **Brickwall** on Low/High Cut. Pro-Q 3
  was stepped (6/12/24/48/96).
- **All Pass filter shape** (phase-only) — *verified new in Pro-Q 4* (one source mis-filed it as carried-over;
  FabFilter's release notes + manual confirm it's new).
- Full **preset browser** (tags/favourites/search) + direct value-display editing; **CLAP** format.
- **4.02 added** a per-band **Spectral Tilt** (3 dB/oct, biases spectral triggering toward highs) — *note: not
  exposed in the Pedalboard surface on this rig (Part A).*
- **Improved:** linear-phase precision; analog matching in Zero-Latency/Natural-Phase modes.

**Carried over from Pro-Q 3 (do NOT call new):** up to **24 bands**; the three processing modes
(Zero Latency / Natural Phase / Linear Phase + resolution tiers); **dynamic EQ itself**; per-band **Mid/Side &
L/R**; **EQ Match**; **Spectrum Grab**; collision detection (single-source); **Piano Display** (note-quantized
frequencies — predates Pro-Q 3, back to Pro-Q 2); **Dolby Atmos up to 9.1.6** (Pro-Q 3 launched at 7.1.2, extended
to 9.1.6 in Dec 2021); MIDI Learn.

## 2. Architecture & controls

- **24 bands**, 10 shapes: Bell (parametric), Low/High Shelf, Low/High Cut, Notch, Band Pass, **Tilt Shelf**
  (shelf-tilt around a point), **Flat Tilt** (constant-slope tilt), **All Pass** (phase only, no gain).
- **Slopes** continuous 0–96 dB/oct + Brickwall (cuts only). Minimums are shape-dependent: Bell/Notch ≥ 12
  dB/oct; Low/High Cut & Band Pass down to 0; others 6 dB/oct. Gain −30…+30 dB (Bell/Shelf/Flat Tilt); freq
  10 Hz–30 kHz.
- **Per-band stereo placement** L/R/M/S (display colours: white=L, red=R, green=M, blue=S; a Split button
  duplicates a band for independent channels). Surround up to **9.1.6** with intelligent speaker selection.
- **Output:** output level, pan (L/R or M/S), **Gain Scale** (scale all gains; affects Bell/Shelf/Flat-Tilt),
  **Auto Gain** (estimated make-up — an *educated guess from the curve, NOT a metered* process; verify loudness
  with a meter).
- **Analyzer:** range 60/90/120 dB, resolution 1024–8192 pts, default **4.5 dB/oct** display tilt, Pre/Post/
  external, Speed, Freeze; **Frequency Collisions** red-glow vs an external/other-instance spectrum (FabFilter:
  "an indication, not exact science — use your ears"). **EQ Match** auto-generates a curve toward a reference;
  **Spectrum Grab** drags a peak into a band.
- **Gain-Q interaction** (optional analog coupling: Q narrows as Bell gain rises).

## 3. Dynamic EQ + Spectral Dynamics (the dynamics story)

- **Dynamic EQ** (Bell/Shelf/Flat-Tilt only): drag the **dynamic-range ring** around the Gain knob (−30…+30 dB;
  **negative = compress/duck on peaks, positive = expand/lift on dips**). Threshold **Auto ("A")** or manual
  (the trigger level is drawn in the slider; soft-knee starts slightly below). **NEW in 4:** manual **Attack/
  Release** (50 % = auto centre) and **Free side-chain filtering**. Linear-phase supports dynamic EQ only up to
  **High** resolution.
- **Spectral Dynamics** *(new)*: enable the spectral icon on a dynamic Bell/Shelf and the band stops moving its
  whole gain — instead it **compresses/expands only the individual frequencies inside the band that exceed the
  threshold**, leaving neighbours flat. **Spectral Density** = selectivity (*low = wide range, high = narrow/
  surgical*). **Spectral Tilt** (3 dB/oct, default on in 4.02) biases triggering toward highs. **Enabling
  spectral forces that band to linear phase** (adds latency by resolution — even when the global mode is
  Natural/Zero-Latency; other bands keep the global mode). Uses: de-harsh, de-ess, resonance taming — a built-in
  Soothe.

## 4. Phase modes & latency

| Mode | Phase | Latency | Use |
|---|---|---|---|
| **Zero Latency** | analog **magnitude** match, phase shifts (grows ≳18 kHz) | none, lowest CPU | everyday mixing; hundreds of instances |
| **Natural Phase** | matches analog **magnitude AND phase** (tiny dev >20 kHz) | negligible | best-quality default, esp. low-freq/high-Q; **transients/drums** |
| **Linear Phase** | magnitude only, phase untouched | **large** (resolution Low ~70 ms … Maximum ~1509 ms @44.1k), **pre-ring** | only to avoid phase cancellation (parallel sums, mastering crossfades) |

FabFilter: linear phase is **"not better, just different"** — a problem-solver. **Pre-ring softens transients
(a kick "loses its edge")**, so for drum/percussive material prefer **Natural Phase or Zero Latency**; reserve
linear phase for sustained/parallel/mastering work. Resolution: Medium = general default; High for high-Q low-end;
Very High/Maximum = best LF resolution but big latency + pre-echo (and dynamics not supported above High).

## 5. Character (saturation) & Auto Gain

- **Character:** `Subtle` = gentle, program-/frequency-dependent transformer color (quiet odd+even harmonics);
  `Warm` = obvious tube color (strong 2nd harmonic). Coloring is **program- and frequency-dependent and
  interacts with the EQ bands** — set EQ first, then audition Character on real material (a single-tone THD test
  won't characterize it). **No drive/amount knob** — pick the mode, apply it only where wanted. Both raise the
  noise floor vs Clean.
- **Auto Gain** estimates make-up from the curve — **not metered**; can be off, especially with dynamic/spectral
  bands or Character. For an honest A/B, level-match with a meter ([[level-match]]).

## 6. Practical recipes (technique blogs — starting points, tune by ear)

| Goal | Move |
|---|---|
| **Find a resonance** | Bell, narrow Q, boost +6…+12, sweep (use band **solo**), then **invert to a cut** (−3…−6 dB tonal at moderate Q; deeper at Q 10–20 for a stubborn ring). Level-dependent → make it **dynamic**; in Pro-Q 4, **Spectral** ducks only the ringing freq. |
| **De-mud vocal** | HPF 90–120 Hz (24 dB/oct, or 12 gentler; ~70 deep male, 100–150 female); wide cut 200–500 Hz; boxiness 200–350 Hz −2…−5 dB Q1.5–2; nasal 800–1500 Hz −2…−3 Q4–5. |
| **De-ess (no de-esser)** | **Dynamic** Bell 5–10 kHz, Q≈4–5, range −2…−6 dB, threshold so it only ducks the harsh esses. Pro-Q 4: switch to **Spectral** so only the sibilant freqs duck (less lisp). Pair any 8–12 kHz air shelf with this or air exaggerates sibilance. |
| **M/S master** | Band → M/S. **Side:** HPF (or low-shelf cut) to ~120–150 Hz to mono the lows; +~1.5 dB high-shelf from ~7 kHz for air/width. **Mid:** low-cut to clear lows, small −250 Hz cut. Use the 3/6 dB display range; small moves. |
| **Fix masking** | On the masked element, SC the other source as external spectrum, enable **collision detection**, cut the red-glow — or better, a **dynamic band with Free/external SC** so it ducks only when the other element plays (bass dips 60–120 Hz when the kick hits). |
| **EQ-match a reference** | SC the reference → **EQ Match** → simplify/tame the auto bands by ear (it produces a busy curve). Inverse-match for *separation* between two parts. *(For transparent reference matching with no plugin, `[L] match-eq` / [[reference-match]] is more controllable.)* |
| **Punchy drum bus / kick / snare** | Kick: HPF 30–40 Hz, +~100 Hz punch, −400 Hz box, +~3.5 kHz click; dynamic 50–80 Hz to tame only boomy hits. Snare: HPF ~70 Hz, body 150–200 Hz, −400 Hz (bleed), ~800 Hz ring, crack 2–5 kHz. Broad bus shelves in linear phase only if you need phase coherence for parallel — else Natural Phase to keep attack. |

## 7. Pitfalls & gotchas

- **Pro-Q 3 vs 4 confusion is the top error.** Dynamic EQ, M/S, EQ Match, Spectrum Grab, 24 bands, the three
  phase modes, Atmos 9.1.6, **Piano Display** are **Pro-Q 3** already. New in 4: Spectral Dynamics, dyn-EQ
  attack/release + free SC, Character, EQ Sketch, Instance List, fractional slopes, All Pass, CLAP, preset browser.
- **Don't trust a bare headless load to be flat** (it restores the last GUI curve) and **don't drive Pro-Q via
  the float dict** (can't set shapes/enable bands) — flatten + configure via the [[vst-preset]] harness, or a
  `dump_state` blob.
- **Spectral forces linear phase on that band** → latency/pre-ring even under Natural Phase; keep resolution
  Low/Medium, especially above ~1 kHz.
- **Character has no amount knob** and **Auto Gain isn't metered** — verify level with a meter before any A/B.
- **Linear phase isn't a free upgrade** — pre-ring softens transients; not for lead drum material.
- **Spectral Tilt (4.02)** isn't in the Pedalboard surface on this rig — don't script it.
- **No-iLok, but loads ≠ renders** — still screen a new install with `[[vst-verify]]` / `probe_plugin.py "Pro-Q 4"`
  and **measure detail** (a 0.00 spectrum/centroid delta = passthrough), then pin the version + persist `dump_state`.

> **Pure-DSP equivalents (no plugin, deterministic):** surgical/tilt EQ → `[L] apply-eq`; reference curve →
> `[L] match-eq` ([[reference-match]]/[[house-curve]]); dynamic per-band → `[L] apply-dynamic-eq` ([[dynamic-eq]]);
> Soothe-style de-harsh → `[L] suppress-resonances` ([[de-harsh]]); split-band de-ess → `[L] de-ess` ([[de-ess]]);
> tube/tape color → `[L] saturate-loop`. Reach for Pro-Q when you want its exact curve, its analyzer/collision
> workflow, or its Spectral Dynamics specifically.

---

## Sources

FabFilter Pro-Q 4 product page, press release & news (Dec 12 2024; 4.02 Feb 27 2025), and help/manual pages
(overview, band controls, processing mode, dynamic EQ, spectral dynamics, analyzer, stereo, output, character
mode, external sidechaining) · Production Expert (Pro-Q 4 expert review; Spectral Dynamics; "features you might
be overlooking") · Audio Plugin Guy, Pluginoise, Wavy Pro Audio (Pro-Q 3 vs 4) reviews · Sage Audio,
mixandmastermysong, songmixmaster, MusicGuyMixing (technique) · Apple App Store (Pro-Q 4 iOS) · FabFilter FAQ /
KVR (no-iLok licensing). Plus **our own param-surface dump + render/measure results (Part A)** on
`/Library/Audio/Plug-Ins/VST3/FabFilter Pro-Q 4.vst3` via Pedalboard 0.9.23.
