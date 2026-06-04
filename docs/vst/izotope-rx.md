# iZotope RX 10 — field guide: the offline-repair modules as headless inserts

How to drive the **iZotope RX 10** repair modules (`RX 10 <Module>.vst3`) inside the ship-studios pipeline.
RX is iZotope's **offline audio-repair suite** — de-noise, de-click, de-ess, de-reverb, de-hum and a stack of
niche restorers — repurposed here as **real-time VST3 inserts** through `[L] apply-vst-chain` (Pedalboard, the
`vst` extra). This doc is the suite's ground truth: which modules **render headless** (and engage), which are
**passthrough / GUI-only**, and how to drive each. The skills below are the workflows over it.

> **One sentence:** most RX modules **process at their default** (they're repair tools — reduction/sensitivity
> already > 0 on load, so a bare load is *not* a passthrough), the params are **enums** (numeric reach the float
> dict, string/bool need the [[vst-preset]] harness), the **"Learn"/adaptive-profile** features need the GUI, and
> the headline trap is **Spectral De-noise NUKING musical highs at high settings**. RX has **no `vst-*` category**
> in this repo → each module routes to [[vst-chain]] + its nearest pure-DSP twin.

---

## TL;DR (read this first)

1. **Five modules render AND engage headless — use them, link the skills:** [[rx-10-voice-de-noise]] (broadband
   de-noise), [[rx-10-spectral-de-noise]] (FFT subtraction), [[rx-10-de-click]] (declicker), [[rx-10-de-ess]]
   (sibilance), [[rx-10-de-reverb]] (ambience). All authorized + render-verified on this rig — re-verify elsewhere
   with [[vst-verify]] (measure *detail*, not just `changed:true`).
2. **⚠ Spectral De-noise's headline gotcha:** at high `noise_reduction_db` on **music** it treats cymbals/air as
   "noise" and guts them (measured `=24` on a drum bus → centroid 3101→849, **−2252 Hz**). Use **4–10 dB gently**
   on music; reserve aggressive settings for problem material. See §gotchas.
3. **⚠ De-click vs transients:** a declicker can mistake a sharp drum attack for a click — keep `sensitivity` low
   on percussion (the repo's `[L] clean-loop` uses `declick=false` on drums for exactly this). See §gotchas.
4. **De-hum is PASSTHROUGH headless** — it self-bypasses (Δ=0 across all 6 params) → DAW-only [[rx-10-de-hum]].
5. **Repair Assistant** (AI/learn) and the **Monitor / Connect** utilities are **GUI-only / no-audio** — not
   pipeline inserts.
6. **Deltas are modest on a clean test bus** — these tools shine on **noisy / roomy / clicky problem material**.
   The small measured deltas below are the proof-of-engagement, not the use case; state that plainly to the user.
7. **Meters own tone** (Gemini hears ~16 kbps mono): judge any RX pass with `[L] measure-spectrum` (centroid/tilt)
   + `[L] measure-loudness` (crest/rms). Hear what's removed via each module's `output_*_only` monitor.

---

## The whole RX 10 set — render verdict + one-line use

Per-module render status on this rig (Pedalboard, isolated subprocess). **R&E** = renders *and* engages headless
(the float dict reaches the numeric enums; string/bool need [[vst-preset]]). **DAW** = loads but self-bypasses /
needs the GUI. **No-audio** = a meter/utility, not an insert.

| RX 10 module | Verdict | One-line use | Drive via |
|---|---|---|---|
| **Voice De-noise** | **R&E** | broadband adaptive de-noise (rumble/hiss/room tone) | [[rx-10-voice-de-noise]] |
| **Spectral De-noise** | **R&E** ⚠ | FFT spectral subtraction (surgical hiss/buzz/whine) — **nukes HF at high settings on music** | [[rx-10-spectral-de-noise]] |
| **De-click** | **R&E** ⚠ | clicks/pops/crackle/vinyl ticks — **keep sensitivity low on drums** | [[rx-10-de-click]] |
| **De-ess** | **R&E** | split-band / spectral sibilance control | [[rx-10-de-ess]] |
| **De-reverb** | **R&E** | de-reverb / ambience reduction (roomy capture, spill tail) | [[rx-10-de-reverb]] |
| **De-crackle** | **R&E** (niche) | dense crackle (vinyl surface noise) — no dedicated skill; drive like [[rx-10-de-click]] | [[vst-chain]] |
| **De-clip** | **R&E** (niche) | reconstruct clipped peaks — no dedicated skill; drive like [[rx-10-de-click]] | [[vst-chain]] |
| **De-plosive** | **R&E** (niche) | tame vocal "p"/"b" plosives — no dedicated skill; drive like [[rx-10-de-reverb]] | [[vst-chain]] |
| **Mouth De-click** | **R&E** (niche) | dialogue mouth clicks/saliva — no dedicated skill; drive like [[rx-10-de-click]] | [[vst-chain]] |
| **Breath Control** | **R&E** (niche) | duck vocal breaths — no dedicated skill; drive like [[rx-10-de-reverb]] | [[vst-chain]] |
| **Guitar De-noise** | **R&E** (niche) | guitar fret/amp noise/buzz — no dedicated skill; drive like [[rx-10-voice-de-noise]] | [[vst-chain]] |
| **De-hum** | **DAW** ⚠ | hum/buzz notch — **passthrough headless (Δ=0, self-bypasses)** | [[rx-10-de-hum]] (DAW-only) |
| **Repair Assistant** | **DAW** | AI multi-problem auto-repair — needs the GUI to learn/profile | — (GUI) |
| **Monitor** | No-audio | metering / loudness display only | — |
| **Connect** | No-audio | DAW↔RX-standalone bridge (no processing) | — |

> The six **niche renderers** (De-crackle, De-clip, De-plosive, Mouth De-click, Breath Control, Guitar De-noise)
> work headless but earn no dedicated skill — drive them exactly like their named sibling skill above
> (same enum/`[[vst-preset]]`/`output_*_only`/measure discipline), pointing `[L] list-vst-plugins` at the module
> name to confirm the on-disk path.

---

## Shared facts (carry into every module)

- **Renders headless, processes at its default.** RX is offline-repair software running as a real-time insert;
  most modules ship a non-zero default (reduction/sensitivity > 0) so a **bare load is not a passthrough**. Still
  **measure detail** after — `loads ≠ renders`, re-verify a new install with [[vst-verify]].
- **Params are enums (numeric + string).** `[L] apply-vst-chain`'s float dict sets the **numeric** ones
  (reduction, threshold, sensitivity, gains); the **string** enums (`algorithm`, `quality`, `optimize_for`,
  `filter_type`, `speed`) and bools (`output_*_only`, `adaptive_*`) need the **[[vst-preset]]** harness
  (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
- **Each module exposes an `output_*_only` monitor** (hear the REMOVED residual to dial it), a `global_bypass`,
  and input/output gain.
- **⚠ "Learn" / adaptive-profile capture needs the GUI.** Headless, the adaptive/learn features fall back to a
  default profile — for a specific noise/room/hum print, dial it in the RX standalone or DAW and bounce, then
  re-enter the pipeline to measure.
- **No `vst-*` category for RX.** Route each module to **[[vst-chain]]** + its nearest pure-DSP twin:
  `[L] clean-loop` (de-noise / de-click), [[de-ess]] (de-ess), [[bleed-gate]] (de-reverb / spill).
- **Meters own it** (Gemini mono codec under-reads highs / over-reads lows): verify with `[L] measure-spectrum` /
  `measure-loudness`; don't EQ off a mono "dark"/"harsh" vibe.

---

## Part A — measured on this rig

Probe: each `RX 10 <Module>.vst3` loaded via Pedalboard (stemmy-loops `vst` extra), processing an **8 s 48 kHz
stereo drum-bus** clip (baseline **crest 15.6, centroid 3101 Hz**) unless a row says "mix". Deltas are modest on
this clean material *by design* — these are problem-material tools; the numbers prove engagement.

| Module | Settings | Measured | Reading |
|---|---|---|---|
| **Voice De-noise** | `optimize_for='Music'`, `reduction=18`, `master_threshold=3` | low band **−1.3 dB**, rms −1.2, crest +0.7, centroid +171 | removes broadband rumble/hiss; gentle on a clean bus |
| **Spectral De-noise** ⚠ | `noise_reduction_db=24`, `quality='Advanced'` | 2–6 kHz **−16 dB**, >6 kHz **−17.5 dB**, centroid 3101→849 (**−2252 Hz**) | **NUKES musical highs** at 24 dB — treats cymbals as noise; use 4–10 dB on music |
| **De-click** | `sensitivity=7` | centroid −25, mid −0.4, crest **+0.0** | subtle on click-free drums; **did NOT eat transients** at sens 7 |
| **De-ess** | `algorithm='Spectral De-ess'`, `threshold=−28`, `cutoff_freq=6000` (full **mix**) | >6 kHz **−0.7 dB** | ducks sibilant/cymbal HF; modest on a non-sibilant mix |
| **De-reverb** | `reduction=16` | low **−0.8 dB**, rms −0.6, crest **+0.6** | removes ambience/tail, tightens; modest on a dryish bus |
| **De-hum** ⚠ | swept all 6 params | **Δ=0.00000 across the board** | **passthrough — self-bypasses headless** → DAW-only |

### The param surface (Pedalboard-exposed, by module)

All reported as `ENUM` by Pedalboard (numeric ones snap a float to the nearest step → float-dict reachable;
**string/bool** ones need the [[vst-preset]] harness).

- **Voice De-noise** (14): `threshold_1..6` (−120…−30, def −70), `master_threshold` (−20…+10, def 0), `reduction`
  (0…20, def 12), `adaptive_mode` (bool, def True), `optimize_for` (`'Dialogue'`/`'Music'`), `filter_type`
  (`'Surgical'`/`'Gentle'`), `input_gain_db`/`output_gain_db`, `global_bypass`.
- **Spectral De-noise** (27): `noise_reduction_db`/`tonal_reduction_db`/`linked_reduction_db` (0…40, def 12),
  `noise_threshold_db`/`tonal_threshold_db`/`linked_threshold_db` (−6…+6), `link_threshold`/`link_reduction`
  (bools), `quality` (`'Simple'`/`'Advanced'`/`'Extreme'`/`'Adv.+Extr.'`), `artifact_control`, `output_noise_only`,
  `adaptive_learning` (bool, **GUI-learn**) + `adaptive_learning_time`, `fft_size`, `multi_resolution`, `smoothing`,
  `release_ms`, `knee`, `synthesis`, `enhancement`, `masking`, `whitening`, gains, `global_bypass`.
- **De-click** (6): `algorithm` (`'Single-band'`/`'Multi-band (periodic clicks)'`/`'Multi-band (random clicks)'`/
  `'Low-latency'`), `sensitivity` (0.5…10, def 3), `output_clicks_only`, `frequency_skew` (−10…+10),
  `click_widening` (0…5), `global_bypass`.
- **De-ess** (9): `algorithm` (`'Classic De-ess'`/`'Spectral De-ess'`), `threshold` (−60…0, def −12),
  `cutoff_freq` (800…8000, def 2500), `spectral_shaping` (0…100), `spectral_tilt` (−100…+100), `speed`
  (`'Fast'`/`'Slow'`), `absolute_mode` (bool), `output_ess_only`, `global_bypass`.
- **De-reverb** (10): `tail_length` (0.5…4, def 1), `reduction` (−10…+20, def 10), `band_strength_low` / `_low_mid`
  / `_high_mid` / `_high` (0…10, def 6), `artifact_smoothing` (0…10), `enhance_dry_signal` (bool),
  `output_reverb_only` (bool), `global_bypass`.

---

## Part B — gotchas & doctrine

### #1 Spectral De-noise nukes musical highs

The marquee trap. On a near-silent capture, high `noise_reduction_db` (18–40 dB) + `quality='Extreme'` is the
right call. **On music it is a disaster** — the FFT subtractor cannot tell cymbal shimmer / air from broadband
noise and removes it, gutting the top (measured 24 dB on a drum bus → centroid **−2252 Hz**, 2–6 kHz −16 dB).
**On music keep it 4–10 dB**, watch the centroid before/after, and reach for it only on genuine hiss/buzz, not as
a tone shaper. The gentler broadband cousin is [[rx-10-voice-de-noise]]; the pure-DSP twin is `[L] clean-loop`.

### #2 De-click eats transients if pushed

A declicker interpolates samples it flags as a click. A sharp snare/kick attack *looks like* a click — push
`sensitivity` too high on percussion and it smooths the hits. Sens 7 held our drum transients (crest +0.0), but go
higher and crest collapses. This is exactly why the repo's pure-DSP `[L] clean-loop` runs `declick=false` on drums.
Always **watch crest** before/after and confirm with `output_clicks_only` that only ticks (not hits) are removed.

### #3 De-hum is passthrough headless → DAW-only

`RX 10 De-hum.vst3` loads and echoes params but **self-bypasses offline** — Δ=0 across all 6 params, the textbook
"loads ≠ renders" trap. For hum/buzz removal use the DAW-only [[rx-10-de-hum]] (dial in the RX standalone/DAW,
bounce, re-enter the pipeline), or the pure-DSP path: surgical notches via `[L] apply-eq` at the measured mains
multiples (and an expander, not a notch, where the hum overlaps the kick fundamental).

### #4 "Learn" / adaptive capture is GUI-leaning

Voice De-noise's adaptive mode and the manual reduction/threshold controls render fine, but the **noise-profile
"Learn"** (capturing a specific print from a silent region), Spectral De-noise's `adaptive_learning`, De-reverb's
adaptive tail capture, and the whole **Repair Assistant** want the GUI. Headless they fall back to a default
profile — drive the manual controls, or learn in the standalone and bounce.

### #5 The deltas are modest on clean material — say so

Every measured row above is small because the test source was clean. These are **repair** tools: their job is to
remove a problem that isn't there on a polished bus. When you report a result, lead with the proof-of-engagement
(the band/centroid/crest delta) and state plainly that the win lands on **noisy / roomy / clicky problem
material** — don't oversell a 0.7 dB move on a clean mix.

### #6 Pipeline integration

For the five R&E modules: insert via `[L] apply-vst-chain` (string enums via [[vst-preset]]), **measure detail
before/after** ([L] measure-spectrum/measure-loudness), A/B loudness-matched (`[L] render-ab` / [[level-match]]),
`dump_state=true` once dialed for a byte-stable re-render. Corrective inserts, never a master — hand the cleaned
file to [[master-track]] for loudness. For De-hum / Repair Assistant: dial in the DAW, bounce, re-enter.

---

## When to use RX vs the pure-DSP twins

| Want | Use |
|---|---|
| Broadband hiss/rumble removal, RX-grade | [[rx-10-voice-de-noise]] · pure-DSP twin `[L] clean-loop` |
| Surgical hiss/buzz/whine subtraction | [[rx-10-spectral-de-noise]] · twin `[L] clean-loop` |
| Clicks/pops/crackle | [[rx-10-de-click]] · twin `[L] clean-loop` (`declick=false` on drums) |
| Sibilance / cymbal spit | [[rx-10-de-ess]] · pure-DSP twin [[de-ess]] |
| De-reverb / ambience / room tail | [[rx-10-de-reverb]] · de-spill twin [[bleed-gate]] |
| Hum / buzz notch | [[rx-10-de-hum]] (DAW) · pure-DSP `[L] apply-eq` notches |
| Cheap, deterministic, no-plugin cleanup | `[L] clean-loop` (pure DSP) |

---

## Sources

iZotope RX 10 product/help (izotope.com) for the module roster + per-module controls (Voice/Spectral De-noise,
De-click, De-ess, De-reverb, De-hum, the niche restorers, Repair Assistant, Monitor, Connect) ·
the headless-safe doctrine + "loads ≠ renders" trap cross-referenced from [`README.md`](README.md) and
[`tape-j-37.md`](tape-j-37.md) (the passthrough archetype) · plus **our own Pedalboard load + render
measurements** on each `RX 10 *.vst3` (Part A) — the engagement deltas, the Spectral De-noise HF-nuke, the
De-click transient-safety read, and the De-hum passthrough finding.
