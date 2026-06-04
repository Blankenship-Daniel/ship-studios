---
name: neutron-4-equalizer
description: "Use when running the Neutron 4 Equalizer for static or dynamic EQ on a stem/bus/loop — 'Neutron EQ', 'iZotope dynamic EQ', 'tame the mud only when it builds', 'presence bump', '12-band EQ with M/S width'. The measured, plugin-specific deep-dive of [[vst-eq]] (dynamic-EQ twin [[dynamic-eq]]). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: presence|tilt|notch|dynamic|shelf|mid-side]
---

# neutron-4-equalizer — drive the Neutron 4 Equalizer (measured)

The plugin-specific, measured workflow for the **iZotope Neutron 4 Equalizer**
(`/Library/Audio/Plug-Ins/VST3/Neutron 4 Equalizer.vst3`) — a **12-band** EQ where every band can run
**static or dynamic** (`Down`/`Up`), with a dozen shapes (Proportional Q, Bell, Band Shelf, Analog/Baxandall/
Vintage shelves, Flat/Resonant pass) and a real M/S `width` utility. The transparent/flexible member of
[[vst-eq]] alongside [[fabfilter-pro-q-4]]; its dynamic side is the plugin twin of pure-DSP [[dynamic-eq]]. Full
field guide — the per-module render verdicts, the enum-harness rule, sources —
[`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md). This skill is the workflow.

## The governing facts (read first — measured on this rig)

1. **Renders headless here** — the `Neutron 4 Equalizer.vst3` build loads + processes in the offline Pedalboard
   host (NI/iLok-account-authorized on this Mac). **Re-verify elsewhere** with [[vst-verify]] — loads ≠ renders.
2. **Bands 1–4 are ENABLED by default**, so a `gain_db` change on b1–b4 is a real move with **no enable needed**:
   b1 `Analog Low Shelf @100 Hz`, b2 `Proportional Q @500 Hz`, b3 `Proportional Q @3000 Hz`, b4 `Analog High
   Shelf @11 kHz`. Bands 5–12 are disabled (`eq_bN_enable=False`) — enabling them is a **bool** → harness.
3. **Every param is an enum** (numeric-valued AND string). `apply-vst-chain`'s float `parameters` dict CAN set the
   **numeric** enums (`eq_bN_frequency_hz`, `eq_bN_gain_db` −30..+15, `eq_bN_q` 0.1..40, `eq_bN_threshold_db`) on
   an **already-active band** — but it **CANNOT** set the **string/bool** enums (`eq_bN_shape`, `eq_bN_enable`,
   `eq_bN_dyn_mode` 'Down'/'Up', `eq_bN_is_static`). Those need the **[[vst-preset]]** harness
   (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
4. **Dynamic EQ** = set `eq_bN_is_static=False` + `eq_bN_threshold_db` + `eq_bN_dyn_mode` (cut above / boost
   below) — all string/bool → **harness only**. 12-band, per-band, with the shared M/S `width`. (Pure-DSP twin:
   [[dynamic-eq]].)
5. **Shared utility header** on every Neutron module: `global_input_gain`/`global_output_gain` (−60..+10 dB),
   `pan`, `width` (−100..+100, **real M/S width**), `sum_to_mono`, `invert_phase`, `delay_l`/`delay_r` — so the
   Equalizer doubles as a width / mono / delay utility.
6. **The AI "Track Assistant" / Learn is GUI-only** — it won't run headless; you drive the manual 12 bands.
7. **Meters own tone** (Gemini hears ~16 kbps mono) — read `[L] measure-spectrum` centroid / tilt / band-ratios,
   not vibes.

## Prerequisites

- `[L] apply-vst-chain` / `[L] list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]
  find-resonances` (optional, **pure DSP — no key**) to target a surgical Bell.
- **`/Library/Audio/Plug-Ins/VST3/Neutron 4 Equalizer.vst3`** — confirm with `[L] list-vst-plugins
  {name_contains:"Neutron 4 Equalizer"}` and take the **VST3** path.
- **Pre-screen with [[vst-verify]]** (`presets/vst/probe_plugin.py "Neutron 4 Equalizer"`, expect `RENDERS ✓`) —
  re-verify on any new machine.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness`
   (+ `[L] measure-stereo` for an M/S/width move). The "before" column.
2. **Pick the move** from the table. For a **static tone** move on b1–b4 (enabled by default), the float dict is
   enough. For a **new band, a non-default shape, or a dynamic band**, you need the [[vst-preset]] harness.
3. **Apply** — numeric-only on b1–b4 via `[L] apply-vst-chain` (`{plugin_path, parameters:{eq_b3_gain_db:6.0,…}}`,
   `dump_state=true` to capture `.state`); anything with a shape/enable/dyn-mode/static flag via
   `…/stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py presets/vst/neutron4-eq-*.json <in>
   projects/<track>/mix/<stem>_neutron-eq.wav`.
4. **Prove it** — re-`measure-spectrum`/`measure-loudness`: confirm the intended band/tilt moved and **detail
   changed** (a 0.00 spectrum delta = passthrough). A dynamic band shows the cut on peaks while steady level is
   preserved. A/B loudness-matched (`[L] render-ab` / [[level-match]]).
5. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch over-EQ; cross-check any mono "dark/boxy" flag
   against the stereo spectrum ([[gemini-audio-understanding]]). It's a per-track/bus insert, not a master — hand
   off to [[master-track]].

## Move table

| Goal | Neutron 4 EQ move | Reach |
|---|---|---|
| **Presence bump** ★ | `eq_b3_gain_db=+6` (3 kHz, enabled by default, Proportional Q) — float dict, no enable | numeric |
| **Tilt / warmth** | b1 `Analog Low Shelf` gain ± / b4 `Analog High Shelf` gain ± (both default-on) | numeric |
| **Surgical notch** | enable a free band, `shape='Bell'`, narrow `q`, `gain_db` −3…−6 (deeper for a ring) | harness |
| **Dynamic mud/boom** | `is_static=False`, `dyn_mode='Down'`, `threshold_db` so it cuts only on loud hits (twin [[dynamic-eq]]) | harness |
| **Dynamic fill** | `is_static=False`, `dyn_mode='Up'`, threshold so it boosts only when the band dips | harness |
| **Resonant pass** | a free band `shape='Resonant Lowpass'/'Resonant Highpass'` for a filter-sweep edge | harness |
| **M/S width / mono** | `width` (−100..+100, real M/S) · `sum_to_mono` · `global_output_gain` make-up | numeric |

★ shipped example, on an 8 s 48 kHz stereo **drum-bus** clip (baseline crest 15.6 dB, centroid 3101 Hz):
`eq_b3_gain_db=6.0` (3 kHz, enabled by default) → the **2–6 kHz band rose +2.3 dB**, centroid **3101→3125
(+24 Hz)**, crest +0.2 — a clean, real presence bump set entirely from the float dict (no enable, no harness).

## Outputs

- `projects/<track>/mix/<stem>_neutron-eq.wav` (+ the `.state` blob if dumped, and the reusable
  `presets/vst/neutron4-eq-*.json` for a harness move).

## Reporting to the user

State the moves (bands: shape/freq/gain/Q, which are dynamic + dyn-mode), the before→after **tilt / centroid /
target-band deltas**, that it ran headless via the `Neutron 4 Equalizer.vst3` build, and the `.state`/preset path.
A/B loudness-matched so taste isn't a level illusion.

## Pitfalls

- **The float dict can't shape / enable / make-dynamic a band** — it only moves an already-active band's numeric
  values. For a new band, a shape change, or a dynamic band use the [[vst-preset]] harness (or a `.state`).
- **Bands 5–12 are off by default** — a `gain_db` on a disabled band is a no-op; enable it (bool → harness) first.
- **A dynamic band needs every dynamic param set explicitly** (`is_static`, `dyn_mode`, `threshold_db`) — an unset
  one inherits the restored state's value.
- **The Compressor/Gate dynamics don't engage headless** (a separate measured caveat) — for compression reach for
  [[vst-compress]] / [[multiband-compress]] / [[fabfilter-pro-mb]], not a Neutron dynamics module.
- A tonal EQ is an insert, not mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md) — the Neutron 4 family field guide ·
  [[izotope]] — the iZotope index
- [[vst-eq]] — the generic EQ skill this specializes · [[fabfilter-pro-q-4]] — the surgical/spectral EQ alternative
- Sibling Neutron modules: [[neutron-4-transient-shaper]] · [[neutron-4-sculptor]] · [[neutron-4-exciter]]
- Pure-DSP twins (no plugin): [[dynamic-eq]] (apply-dynamic-eq) · `[L] apply-eq` / [[de-harsh]]
- [[vst-preset]] — apply enum/dynamic chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — the
  backbone · [[vst]] — index/doctrine · `[G] find-resonances` — target a notch (pure DSP, no key)
- [[mix-check]] (find the problems first) · [[master-track]] (loudness) · [[gemini-audio-understanding]] — why
  meters (not Gemini mono) own the spectrum read
