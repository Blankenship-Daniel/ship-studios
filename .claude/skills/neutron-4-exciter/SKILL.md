---
name: neutron-4-exciter
description: "Use when running the Neutron 4 Exciter for harmonic air/presence/warmth on a stem or bus — 'Neutron exciter', 'iZotope add air/sparkle', 'harmonic excitement', 'add presence without a static shelf', '3-band exciter with harmonic blend'. The measured, plugin-specific deep-dive of [[excite]]. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: air|presence|warmth|harmonic-blend]
---

# neutron-4-exciter — drive the Neutron 4 Exciter (measured)

The plugin-specific, measured workflow for the **iZotope Neutron 4 Exciter**
(`/Library/Audio/Plug-Ins/VST3/Neutron 4 Exciter.vst3`) — a **3-band** harmonic exciter (per-band `drive` 0..15,
an `x`/`y` harmonic-blend XY 0..1, `blend` 0..100), a post-filter, and a global `filter_mode`
(Full/Defined/Clear). The iZotope member of [[excite]] — it *generates* air/presence/warmth as harmonics from the
material instead of a static EQ shelf. Full field guide — the per-module render verdicts, the enum-harness rule,
sources — [`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md). This skill is the workflow.

## The governing facts (read first — measured on this rig)

1. **Renders headless here** — the `Neutron 4 Exciter.vst3` build loads + processes in the offline Pedalboard host
   (NI/iLok-account-authorized on this Mac). **Re-verify elsewhere** with [[vst-verify]] — loads ≠ renders.
2. **⚠ `drive` defaults to 0 → a NO-OP until you drive a band; a single high band alone barely moves it — drive
   MULTIPLE bands.** ★ MEASURED (drum bus): `exc_b1_drive=exc_b2_drive=exc_b3_drive=14.0` → centroid **3101→3856
   (+755 Hz)**, >6 kHz **+1.0 dB**, crest **−3.5 dB** (the added harmonics fill between transients).
3. **Every param is an enum** (numeric AND string). `apply-vst-chain`'s float `parameters` dict CAN set the
   **numeric** enums (`exc_bN_drive` 0..15, `exc_bN_x`, `exc_bN_y` 0..1, `exc_bN_blend` 0..100,
   `exc_post_filter_freq`, `exc_post_filter_gain`) — but it **CANNOT** set the **string/bool** enums
   (`exc_global_filter_mode` Full/Defined/Clear, `exc_bN_bypass`). Those need the **[[vst-preset]]** harness
   (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
4. **3 bands, all active by default** (`exc_bN_bypass=False`), so a `drive` move on any band is a real move with no
   enable — but `drive` defaults 0, so you must drive it. The `x`/`y` XY chooses the harmonic blend (which
   exciter character).
5. **Shared utility header** on every Neutron module: `global_input_gain`/`global_output_gain` (−60..+10 dB),
   `pan`, `width` (−100..+100, **real M/S width**), `sum_to_mono`, `invert_phase`, `delay_l`/`delay_r` — so the
   Exciter doubles as a width / mono / delay utility.
6. **The AI "Track Assistant" / Learn is GUI-only** — it won't run headless; you drive the 3 bands manually.
7. **Meters own tone** (Gemini hears ~16 kbps mono) — read `[L] measure-spectrum` centroid / >6 kHz band +
   `[L] measure-loudness` crest, not vibes (excitement raises HF AND drops crest — expect both).

## Prerequisites

- `[L] apply-vst-chain` / `[L] list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **`/Library/Audio/Plug-Ins/VST3/Neutron 4 Exciter.vst3`** — confirm with `[L] list-vst-plugins
  {name_contains:"Neutron 4 Exciter"}` and take the **VST3** path.
- **Pre-screen with [[vst-verify]]** (`presets/vst/probe_plugin.py "Neutron 4 Exciter"`, expect `RENDERS ✓`) — and
  note a bare load is a **no-op** (`drive=0`), so verify with a real drive set across multiple bands.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness`
   (crest / PLR). The "before" column.
2. **Pick the move** from the table. Drive **multiple bands** (a single band barely moves it). Choose the harmonic
   character with the `x`/`y` XY, and `blend` per band for parallel-style dry/wet.
3. **Apply** — numeric `drive`/`x`/`y`/`blend`/post-filter via `[L] apply-vst-chain` (`dump_state=true` to capture
   `.state`); a `filter_mode`/`bypass` change via `…/stemmy-loops-mcp/.venv/bin/python
   presets/vst/apply_vst_preset.py presets/vst/neutron4-exciter-*.json <in>
   projects/<track>/mix/<stem>_neutron-exciter.wav`.
4. **Prove it** — re-`measure-spectrum`/`measure-loudness`: expect **centroid + >6 kHz UP** and **crest DOWN**
   (harmonics fill between transients) and **detail changed** (a 0.00 delta = the no-op `drive=0` default). A/B
   loudness-matched (`[L] render-ab` / [[level-match]]).
5. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch harshness / fizz from over-driving; cross-check any
   mono "dull/bright" flag against the stereo spectrum ([[gemini-audio-understanding]]). It's an insert, not a
   master — hand off to [[master-track]].

## Move table

| Goal | Neutron 4 Exciter move | Reach |
|---|---|---|
| **Broadband air/presence/warmth** ★ | `exc_b1_drive=exc_b2_drive=exc_b3_drive=14` (all 3 bands) | numeric |
| **Top-end air only** | drive the **high** band + a second band (a single band barely moves it) | numeric |
| **Harmonic character** | the `exc_bN_x`/`exc_bN_y` XY per band (which harmonic blend) | numeric |
| **Parallel excitement** | `exc_bN_blend` down for dry/wet per band | numeric |
| **Shape the excited top** | `exc_post_filter_freq` / `exc_post_filter_gain` (post-filter) | numeric |
| **Filter character** | `exc_global_filter_mode` 'Full' / 'Defined' / 'Clear' | harness |
| **Width / mono** | `width` (real M/S) · `sum_to_mono` | numeric |

★ shipped example, on an 8 s 48 kHz stereo **drum-bus** clip (baseline crest 15.6 dB, centroid 3101 Hz): all three
bands' drive `=14.0` → centroid **3101→3856 (+755 Hz)**, >6 kHz **+1.0 dB**, crest **−3.5 dB** (added harmonics
fill between transients). `drive`/`x`/`y`/`blend` are numeric (float-dict reachable); `global_filter_mode` is a
string enum → harness.

## Outputs

- `projects/<track>/mix/<stem>_neutron-exciter.wav` (+ the `.state` blob if dumped, and a reusable
  `presets/vst/neutron4-exciter-*.json` for a filter-mode move).

## Reporting to the user

State the per-band drive + XY blend + filter mode, the before→after **centroid / >6 kHz / crest**, that it ran
headless via the `Neutron 4 Exciter.vst3` build, and the `.state`/preset path. Note that excitement **raises HF
and lowers crest** (harmonics between transients) — A/B loudness-matched so "brighter" isn't "louder."

## Pitfalls

- **#1: `drive=0` = a NO-OP, and one band alone barely moves it** — drive multiple bands. A bare load or
  undriven render is a passthrough.
- **The float dict can't set `filter_mode`/`bypass`** — for those use the [[vst-preset]] harness (or `.state`).
- **Over-driving fizzes** — excitement that adds 5–7 kHz harshness needs a backed-off drive (the pure-DSP
  [[excite]] has a built-in 5–7 kHz harshness guard if you want that safety net).
- **The Compressor/Gate dynamics don't engage headless** (a separate measured caveat) — for compression reach for
  [[vst-compress]] / [[multiband-compress]] / [[fabfilter-pro-mb]], not a Neutron dynamics module.
- An exciter insert is not mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md) — the Neutron 4 family field guide ·
  [[izotope]] — the iZotope index
- [[excite]] — the pure-DSP harmonic exciter twin (no plugin, with a 5–7 kHz harshness guard)
- Sibling Neutron modules: [[neutron-4-equalizer]] · [[neutron-4-transient-shaper]] · [[neutron-4-sculptor]]
- [[vst-preset]] — apply the filter-mode chain · [[vst-verify]] — prove the build renders (with a real drive) ·
  [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- [[mix-check]] (find the problems first) · [[master-track]] (loudness) · [[gemini-audio-understanding]] — why
  meters (not Gemini mono) own the spectrum read
