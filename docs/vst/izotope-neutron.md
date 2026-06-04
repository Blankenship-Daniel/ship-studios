# iZotope Neutron 4 — field guide: the per-module mixing suite (measured headless)

How to drive **iZotope Neutron 4** in this pipeline. Neutron 4 ships as a **mixing suite of per-module VST3s**
(`/Library/Audio/Plug-Ins/VST3/Neutron 4 <Module>.vst3`) — each module is its own plugin you can insert
independently: **Equalizer, Compressor, Gate, Exciter, Transient Shaper, Sculptor, Unmask, Visual Mixer** (plus the
all-in-one Neutron mothership, not covered here). This doc is **measured on this rig** — the real Pedalboard param
surface plus the headline finding that **four modules render & engage offline, the dynamics modules don't, and two
are single-instance no-ops**. The task skills [[neutron-4-equalizer]], [[neutron-4-transient-shaper]],
[[neutron-4-sculptor]], and [[neutron-4-exciter]] are the workflows over the modules that work.

---

## TL;DR (the headline — read this first)

1. **Four modules RENDER & engage headless: Equalizer, Sculptor, Transient Shaper, Exciter.** They load + process
   through the offline Pedalboard host (NI/iLok-account-authorized on this Mac). Use the task skills:
   [[neutron-4-equalizer]] · [[neutron-4-sculptor]] · [[neutron-4-transient-shaper]] · [[neutron-4-exciter]].
   **Re-verify on a new machine** with [[vst-verify]] — loads ≠ renders.
2. **The Compressor & Gate render but their dynamics are INERT headless** — measured `threshold −45 / ratio 10 /
   auto-gain off` produced **0 dB GR**. Don't compress/gate with Neutron in the pipeline; use [[vst-compress]] /
   [[multiband-compress]] / [[fabfilter-pro-mb]].
3. **Unmask is a NO-OP single-instance** — it needs a *companion* Neutron instance's sidechain to carve against,
   which a single offline insert can't provide. Use the pure-DSP [[unmask-stems]] instead.
4. **Visual Mixer is METERING — no audio processing.** It's a GUI gain/pan/width surface for cross-track balancing;
   nothing to render. Balance with [[mix-balance]].
5. **Every param is an enum** (numeric-valued AND string). The float `parameters` dict of `[L] apply-vst-chain` can
   set **numeric** enums (gains, thresholds, drive, attack/sustain) on an already-active band, but **cannot** set
   **string/bool** enums (shapes, modes, targets, contour, enable) — those need the **[[vst-preset]]** harness
   (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
6. **The AI "Track Assistant" / Learn is GUI-only** — it won't run headless; you drive the manual DSP.
7. **Meters own tone** (Gemini hears ~16 kbps mono): judge any Neutron move with `[L] measure-spectrum`
   (tilt/centroid/bands), `measure-loudness` (crest/PLR), `measure-stereo`. A/B loudness-matched with
   `[L] render-ab` ([[level-match]]) so a brighten/punch isn't just "louder".

---

# Part A — measured on this rig

Probe: each `Neutron 4 <Module>.vst3` loaded via Pedalboard (stemmy-loops `vst` extra), processing an **8 s 48 kHz
stereo drum-bus clip** (baseline **crest 15.6 dB, centroid 3101 Hz**). Numbers below are that clip; state the
source when you reuse them.

## The verdict table (per module)

| Module | params | Render verdict | What measured | Use |
|---|---|---|---|---|
| **Equalizer** | 114 | **RENDERS & engages** | `eq_b3_gain_db=6` (3 kHz, on by default) → 2–6 kHz **+2.3 dB**, centroid **3101→3125 (+24 Hz)** | [[neutron-4-equalizer]] |
| **Sculptor** | 23 | **RENDERS & engages** | `sc_target='Instrument Bus'`, `sc_amount=80` → centroid **3101→4394 (+1293 Hz)**, 2–6k **+4.9**, >6k **+6.3**, low-mid **−3.3 dB** | [[neutron-4-sculptor]] |
| **Transient Shaper** | 30 | **RENDERS & engages** | all 3 bands `attack=10` → crest **15.6→17.7 (+2.1 dB)**, rms **+7.5 dB** | [[neutron-4-transient-shaper]] |
| **Exciter** | 40 | **RENDERS & engages** | all 3 bands `drive=14` → centroid **3101→3856 (+755 Hz)**, >6k **+1.0 dB**, crest **−3.5 dB** | [[neutron-4-exciter]] |
| **Compressor** | 63 | **INERT** — dynamics don't engage | thr −45 / ratio 10 / auto-gain off → **0 dB GR** | [[vst-compress]] / [[multiband-compress]] / [[fabfilter-pro-mb]] |
| **Gate** | — | **INERT** — gating doesn't engage headless | no GR | [[vst-compress]] / [[fabfilter-pro-mb]] |
| **Unmask** | 23 | **NO-OP single-instance** — needs a companion instance's sidechain | nothing to carve against | [[unmask-stems]] (pure DSP) |
| **Visual Mixer** | — | **Metering only — no audio** | — | [[mix-balance]] |

**Conclusion:** treat Neutron 4 as **four working processors + a metering surface**. The Equalizer / Sculptor /
Transient Shaper / Exciter are real, measurable inserts; the Compressor / Gate are the **"loads ≠ renders"** trap
(`docs/vst/README.md`) — they instantiate and accept params but their *dynamics* never engage offline; Unmask is
architecturally a two-instance feature; Visual Mixer is a meter.

## The shared module surface (every Neutron module)

Each module carries the same **utility header** plus a `global_bypass`:

| Param | Values *(default)* | Note |
|---|---|---|
| `global_bypass` | False · True *(False)* | per-module bypass |
| `global_input_gain` / `global_output_gain` | −60 … +10 dB *(0)* | gain-stage / make-up (numeric) |
| `pan` | −1 … +1 *(0)* | pan |
| `width` | −100 … +100 *(0)* | **real M/S width** (numeric) |
| `sum_to_mono` | False · True *(False)* | mono-fold (bool → harness) |
| `swap_channels` / `invert_phase` | bool *(False)* | utility (bool → harness) |
| `delay_l` / `delay_r` | 0 … 100 ms *(0)* | per-channel delay (numeric) |

So **any** Neutron module also doubles as a **width / mono / delay / gain** utility — handy even on a module whose
main DSP you're not using (though for the inert/no-op modules there's no reason to reach for them).

## 1. Equalizer (RENDERS — `Neutron 4 Equalizer.vst3`, 114 params)

A **12-band** EQ; each band has `eq_bN_frequency_hz` (20–20k), `eq_bN_gain_db` (−30…+15), `eq_bN_q` (0.1…40),
`eq_bN_threshold_db`, `eq_bN_shape` (string: Proportional Q · Bell · Band Shelf · Analog/Baxandall/Vintage Low &
High Shelf · Flat/Resonant Lowpass/Highpass), `eq_bN_enable` (bool), `eq_bN_dyn_mode` ('Down'/'Up'), and
`eq_bN_is_static` (bool: True = static EQ, False = **dynamic EQ**).

- **Bands 1–4 are ENABLED by default** (b1 Analog Low Shelf @100, b2 Proportional Q @500, b3 Proportional Q @3000,
  b4 Analog High Shelf @11k) — a `gain_db` change on b1–b4 is a real move with **no enable**, settable via the
  float dict. Bands 5–12 are off (enable is a bool → harness).
- **Dynamic EQ** = `is_static=False` + `threshold_db` + `dyn_mode` (string/bool → **harness**), 12-band per-band,
  with the shared M/S `width`. The pure-DSP twin is [[dynamic-eq]].
- **Measured:** `eq_b3_gain_db=6.0` (3 kHz, default-on) → 2–6 kHz **+2.3 dB**, centroid **3101→3125 (+24 Hz)**,
  crest +0.2 — a clean presence bump from the float dict alone.
- Workflow → [[neutron-4-equalizer]]. RENDER & engage; the surgical/spectral alternative is [[fabfilter-pro-q-4]].

## 2. Sculptor (RENDERS — `Neutron 4 Sculptor.vst3`, 23 params)

A **target-driven spectral leveler**: `sc_target` (STRING enum, default **'None'**) picks an instrument *profile*
(Instrument Bus · Bass · Deep Bass · Sub-bass · Acoustic Guitar · Electric Piano · Piano · Synth Lead/Pad · Toms ·
Dialogue · Vocals · Add Fullness · Add Punch · Add Polish · None) and reshapes the source toward it. `sc_amount`
(0–100, default 50), `sc_tone` (−50…+50), `sc_speed` (0–100), `sc_action_region_low/high_freq_hz`, `sc_global_mix`.

- **⚠ `sc_target` defaults 'None' → the module is a NO-OP until you pick a target** (string enum → **harness
  only**, the float dict can't set it). Bake the target in the preset, then tweak `sc_amount`/`sc_tone` via the
  float dict.
- **Measured:** `sc_target='Instrument Bus'`, `sc_amount=80` → centroid **3101→4394 (+1293 Hz, big brighten)**,
  2–6 kHz **+4.9 dB**, >6 kHz **+6.3 dB**, low-mid **−3.3 dB**. A target-based spectral leveler (Soothe-adjacent
  but profile-driven, not a flat de-harsher).
- Workflow → [[neutron-4-sculptor]]. For a flat, target-less dynamic resonance suppressor prefer [[de-harsh]].

## 3. Transient Shaper (RENDERS — `Neutron 4 Transient Shaper.vst3`, 30 params)

A **3-band** transient designer: `ts_bN_attack` (−15…+15), `ts_bN_sustain` (−15…+15), `ts_bN_contour`
('Sharp'/'Normal'/'Smooth'), `ts_bN_bypass`; globals `ts_global_mode` ('Precise'/'Balanced'/'Loose'),
`ts_global_mix`.

- **`attack`/`sustain` are numeric** (float-dict reachable, 3 bands active by default); **`contour`/`mode`/`bypass`
  are string/bool → harness**.
- **Measured:** all 3 bands `attack=10` → crest **15.6→17.7 (+2.1 dB, more punch)**, **but rms +7.5 dB** (attack
  boost raises level) → **always A/B loudness-matched**; the punch is the **crest delta**, not the level.
- Workflow → [[neutron-4-transient-shaper]]. The pure-DSP twin is [[drum-punch]]; the other plugin is
  [[softube-transient-shaper]].

## 4. Exciter (RENDERS — `Neutron 4 Exciter.vst3`, 40 params)

A **3-band** harmonic exciter: `exc_bN_drive` (0–15, default **0**), `exc_bN_x`/`exc_bN_y` (the harmonic-blend XY,
0–1), `exc_bN_blend` (0–100), `exc_bN_bypass`; `exc_post_filter_freq`/`exc_post_filter_gain`,
`exc_global_filter_mode` ('Full'/'Defined'/'Clear').

- **⚠ `drive` defaults 0 → a NO-OP until you drive a band; a single high band alone barely moves it — drive
  MULTIPLE bands.** `drive`/`x`/`y`/`blend` are numeric (float-dict); `global_filter_mode` is string → harness.
- **Measured:** all 3 bands `drive=14` → centroid **3101→3856 (+755 Hz)**, >6 kHz **+1.0 dB**, crest **−3.5 dB**
  (added harmonics fill between transients).
- Workflow → [[neutron-4-exciter]]. The pure-DSP twin is [[excite]] (with a built-in 5–7 kHz harshness guard).

## 5. Compressor (INERT headless — `Neutron 4 Compressor.vst3`, 63 params)

Loads and accepts every param, but the **dynamics never engage offline**: measured `threshold −45 / ratio 10 /
auto-gain off` produced **0 dB GR**. This is the "loads ≠ renders" trap for *the dynamics specifically*. **Do not
compress with Neutron in the pipeline** — use [[vst-compress]] (a real headless comp), [[multiband-compress]]
(pure-DSP band-split), or [[fabfilter-pro-mb]] (multiband dynamics that DO render).

## 6. Gate (INERT headless)

Same story as the Compressor — the gating dynamics don't engage offline. For gating reach for [[vst-compress]]
(a headless gate/expander) or [[fabfilter-pro-mb]] (downward expansion per band); the pure-DSP cleanup path is
`[L] clean-loop` (gate/HPF/declick).

## 7. Unmask (NO-OP single-instance — `Neutron 4 Unmask.vst3`, 23 params)

Unmask is architecturally a **two-instance** feature: it carves the track it's on against a **companion** Neutron
instance's sidechain (the masking source). A single offline insert has no companion to receive a sidechain from, so
**it's effectively a no-op headless**. (You can see this in the params: `unmask_amount`, `unmask_sensitivity`,
`unmask_attack_ms`, `unmask_release_ms`, an action region — all keyed to a sidechain that isn't wired up offline.)
**Use the pure-DSP [[unmask-stems]]** — it scores cross-stem masking and applies complementary cuts to the losing
stem, then re-scores, no companion instance required.

## 8. Visual Mixer (metering — no audio processing)

The Visual Mixer is Neutron's cross-track **balancing surface** — a GUI where you drag track "dots" to set
level/pan/width across instances. It **processes no audio of its own to render**; it's a metering/control view.
**Balance levels with [[mix-balance]]** (measured-LUFS gain-staging) instead.

---

# Part B — how to drive the four working modules

## The enum-harness rule (the one gotcha that bites everywhere)

Every Neutron param is reported as an `ENUM` by Pedalboard, in two flavours:

- **Numeric-valued enums** — gains, frequencies, Q, thresholds, drive, attack/sustain, blend, amount, the utility
  header. The float `parameters` dict of `[L] apply-vst-chain` **can** set these (snapped to the nearest step), but
  only **on an already-active band/target**.
- **String/bool enums** — `eq_bN_shape`/`_enable`/`_dyn_mode`/`_is_static`, `sc_target`, `ts_bN_contour`/
  `ts_global_mode`/`ts_bN_bypass`, `exc_global_filter_mode`/`exc_bN_bypass`, and `sum_to_mono`/`invert_phase`. The
  float dict **cannot** set these → use the **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`, which
  `setattr`s every param) or a dumped `.state`.

So: a **static tone move on EQ bands 1–4** or a **drive/attack push** can go through the float dict; **anything that
picks a shape, target, mode, contour, or enables a band** needs the harness. The Sculptor `sc_target` and the
Exciter `drive=0` defaults are the two **no-op-until-you-act** footguns — a bare load does nothing.

## Pipeline integration

These four are normal **inserts** in the headless pipeline:

1. **Measure** the source: `[L] measure-spectrum` (tilt/centroid/bands) + `[L] measure-loudness` (crest/PLR)
   (+ `measure-stereo` for a width move). The "before."
2. **Apply** — numeric-only via `[L] apply-vst-chain` (`{plugin_path, parameters:{…}}`, `dump_state=true` to
   capture a `.state`); anything with a string/bool enum via the [[vst-preset]] harness →
   `projects/<track>/mix/<stem>_neutron-<module>.wav` (+ `.state`).
3. **Prove it** — re-measure; confirm the intended centroid/tilt/crest moved and **detail changed** (a 0.00 delta =
   the no-op default, or an inert module). A/B loudness-matched (`[L] render-ab` / [[level-match]]).
4. Continue the normal pipeline ([[mix-check]] → [[master-track]], etc.). These are inserts, **not** mastering.

## Pitfalls & gotchas

- **#1: the Compressor & Gate are passthrough-for-dynamics headless** — never "compress" or "gate" a render with
  Neutron; you'll ship undynamiced audio. Use [[vst-compress]] / [[multiband-compress]] / [[fabfilter-pro-mb]].
- **#2: Sculptor `sc_target='None'` and Exciter `drive=0` are no-ops** — a bare load or a float-only apply does
  nothing. Set a target (harness) / drive multiple bands first.
- **A single high Exciter band barely moves it** — drive multiple bands.
- **Transient Shaper attack raises level** — re-measure crest, not just loudness; always loudness-match the A/B.
- **Sculptor reshapes the whole balance** — a strong `amount` can brighten hard (centroid +1.3 kHz here); start at
  the default 50 and confine with the action region.
- **Unmask needs a companion instance** — a single offline insert is a no-op; use [[unmask-stems]].
- **The float dict can't enable a band / pick a shape / set a mode** — that's the harness ([[vst-preset]]) or a
  `.state`.
- **The AI Track Assistant / Learn is GUI-only** — it won't run headless; drive the manual DSP.
- **Meters own tone** (Gemini hears ~16 kbps mono) — read the spectrum/crest, not vibes.

## 9. When to use a Neutron module vs the alternatives

| Want | Use |
|---|---|
| iZotope 12-band static/dynamic EQ, headless | **[[neutron-4-equalizer]]** (surgical/spectral alt: [[fabfilter-pro-q-4]]) |
| Target-based spectral reshape/level, headless | **[[neutron-4-sculptor]]** (flat de-harsh: [[de-harsh]]) |
| iZotope 3-band transient design, headless | **[[neutron-4-transient-shaper]]** (pure DSP: [[drum-punch]]; other plugin: [[softube-transient-shaper]]) |
| iZotope 3-band harmonic exciter, headless | **[[neutron-4-exciter]]** (pure DSP: [[excite]]) |
| Compression / gating (Neutron's are inert) | [[vst-compress]] · [[multiband-compress]] · [[fabfilter-pro-mb]] |
| Cross-stem unmasking (Neutron's needs 2 instances) | [[unmask-stems]] (pure DSP) |
| Cross-track level/pan balance (Visual Mixer = meter) | [[mix-balance]] |

---

## Sources

iZotope Neutron 4 product/module overview + Neutron 4 documentation (izotope.com — Equalizer / Compressor / Gate /
Exciter / Transient Shaper / Sculptor / Unmask / Visual Mixer module descriptions; the AI Track Assistant / Learn
being GUI-only). Plus **our own Pedalboard load + render measurements** on each `Neutron 4 <Module>.vst3` (Part A) —
the four-render / two-inert / two-no-op finding and the drum-bus numbers. The enum-harness + headless doctrine
cross-referenced from [`docs/vst/README.md`](README.md), [`docs/vst/fabfilter-pro-q-4.md`](fabfilter-pro-q-4.md),
and the [[vst-preset]] / [[vst-verify]] skills.
