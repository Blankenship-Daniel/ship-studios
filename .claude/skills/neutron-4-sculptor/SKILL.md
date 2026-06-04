---
name: neutron-4-sculptor
description: "Use when running the Neutron 4 Sculptor for target-based spectral shaping / resonance leveling on a stem or bus — 'Neutron Sculptor', 'iZotope spectral shaper', 'reshape this toward an instrument profile', 'Soothe-style but target-based', 'level the resonances toward a bus tone'. The measured, plugin-specific deep-dive of [[vst-eq]] (resonance twin [[de-harsh]]). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: brighten|instrument-bus|tame-resonance|target-profile]
---

# neutron-4-sculptor — drive the Neutron 4 Sculptor (measured)

The plugin-specific, measured workflow for the **iZotope Neutron 4 Sculptor**
(`/Library/Audio/Plug-Ins/VST3/Neutron 4 Sculptor.vst3`) — a **target-driven spectral leveler**: it reshapes a
source's spectrum toward a chosen instrument *profile* (`sc_target`), dynamically and per-band, with `sc_amount`
(intensity), `sc_tone` (tilt the result), `sc_speed`, and an action region. Soothe-adjacent (the resonance-taming
twin [[de-harsh]]) but **target-based** — it moves the whole tonal balance toward a model, not just ducks peaks.
The spectral member of [[vst-eq]]. Full field guide — the per-module render verdicts, the enum-harness rule,
sources — [`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md). This skill is the workflow.

## The governing facts (read first — measured on this rig)

1. **Renders headless here** — the `Neutron 4 Sculptor.vst3` build loads + processes in the offline Pedalboard
   host (NI/iLok-account-authorized on this Mac). **Re-verify elsewhere** with [[vst-verify]] — loads ≠ renders.
2. **⚠ `sc_target` defaults to `'None'` → the module is a NO-OP until you pick a target.** `sc_target` is a
   **string enum** (options incl. 'Instrument Bus', 'Bass', 'Deep Bass', 'Sub-bass', 'Acoustic Guitar',
   'Electric Piano', 'Piano', 'Synth Lead', 'Synth Pad', 'Toms', 'Dialogue', 'Vocals', 'Add Fullness',
   'Add Punch', 'Add Polish', 'None') → the float dict **can't set it** → **[[vst-preset]] harness only**.
3. **Every param is an enum** (numeric AND string). Once a target is picked, `apply-vst-chain`'s float
   `parameters` dict CAN set the **numeric** enums (`sc_amount` 0..100, `sc_tone` −50..+50, `sc_speed` 0..100,
   `sc_action_region_low_freq_hz` / `sc_action_region_high_freq_hz`, `sc_global_mix`) — but the **target itself**
   (string) needs the harness.
4. **It's a target-driven spectral leveler, not a flat de-harsher.** ★ MEASURED (drum bus):
   `sc_target='Instrument Bus'`, `sc_amount=80` → centroid **3101→4394 (+1293 Hz, big brighten)**, 2–6 kHz
   **+4.9 dB**, >6 kHz **+6.3 dB**, low-mid **−3.3 dB** — it reshapes toward the profile (here, brighter +
   leaner low-mid). Pick the target deliberately; raising `sc_amount` deepens the reshape.
5. **Shared utility header** on every Neutron module: `global_input_gain`/`global_output_gain` (−60..+10 dB),
   `pan`, `width` (−100..+100, **real M/S width**), `sum_to_mono`, `invert_phase`, `delay_l`/`delay_r` — so the
   Sculptor doubles as a width / mono / delay utility.
6. **The AI "Track Assistant" / Learn is GUI-only** — it won't run headless; you pick the target + amount manually.
7. **Meters own tone** (Gemini hears ~16 kbps mono) — read `[L] measure-spectrum` centroid / tilt / band-ratios,
   not vibes (it can move centroid >1 kHz — confirm it's the move you wanted, not a runaway brighten).

## Prerequisites

- `[L] apply-vst-chain` / `[L] list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]
  find-resonances` (optional, **pure DSP — no key**) to see what's ringing before you reshape.
- **`/Library/Audio/Plug-Ins/VST3/Neutron 4 Sculptor.vst3`** — confirm with `[L] list-vst-plugins
  {name_contains:"Neutron 4 Sculptor"}` and take the **VST3** path.
- **Pre-screen with [[vst-verify]]** (`presets/vst/probe_plugin.py "Neutron 4 Sculptor"`, expect `RENDERS ✓`) —
  and note a bare load is a **no-op** (`sc_target='None'`), so verify with a real target set.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness`
   (+ `[L] measure-stereo` for a width move). The "before" column.
2. **Pick the target** matching the source/intent (drum bus → 'Instrument Bus' / 'Add Punch' / 'Add Polish';
   bass → 'Bass'/'Deep Bass'; etc.) and an `sc_amount` (start ~50, the default; 80 is a strong reshape). Optionally
   set `sc_tone` to tilt the result, and an action region to confine it.
3. **Apply via the harness** (the target is a string) — `…/stemmy-loops-mcp/.venv/bin/python
   presets/vst/apply_vst_preset.py presets/vst/neutron4-sculptor-*.json <in>
   projects/<track>/mix/<stem>_neutron-sculptor.wav`. Once a target is baked, tweak `sc_amount`/`sc_tone` via
   `[L] apply-vst-chain` and `dump_state=true` for a stable re-render.
4. **Prove it** — re-`measure-spectrum`/`measure-loudness`: confirm centroid/tilt/bands moved **toward** the
   profile and **detail changed** (a 0.00 delta = the no-op default target). A/B loudness-matched (`[L] render-ab`
   / [[level-match]]).
5. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch over-brightening / thinness; cross-check any mono
   "dark/bright" flag against the stereo spectrum ([[gemini-audio-understanding]]). It's an insert, not a master —
   hand off to [[master-track]].

## Move table

| Goal | Neutron 4 Sculptor move | Reach |
|---|---|---|
| **Brighten / shape a drum bus** ★ | `sc_target='Instrument Bus'`, `sc_amount=80` | target → harness |
| **Add presence/polish** | `sc_target='Add Polish'` / `'Add Punch'`, `amount` to taste | target → harness |
| **Fatten / fill** | `sc_target='Add Fullness'` | target → harness |
| **Shape a bass/sub** | `sc_target='Bass'/'Deep Bass'/'Sub-bass'` | target → harness |
| **Confine the reshape** | `sc_action_region_low_freq_hz` / `_high_freq_hz` around the problem band | numeric |
| **Tilt the result darker/brighter** | `sc_tone` − (darker) / + (brighter) | numeric |
| **Tame ringing (Soothe-style)** | a target + modest `amount` + a tight action region (twin [[de-harsh]]) | target → harness |
| **Parallel / width** | `sc_global_mix` down · `width` (real M/S) | numeric |

★ shipped example, on an 8 s 48 kHz stereo **drum-bus** clip (baseline crest 15.6 dB, centroid 3101 Hz):
`sc_target='Instrument Bus'`, `sc_amount=80` → centroid **3101→4394 (+1293 Hz)**, 2–6 kHz **+4.9 dB**, >6 kHz
**+6.3 dB**, low-mid **−3.3 dB** — a strong target-driven brighten + lean-low-mid reshape. `sc_target` is a string
enum → harness; `sc_amount`/`sc_tone`/`sc_speed`/region are numeric (float-dict reachable once a target is set).

## Outputs

- `projects/<track>/mix/<stem>_neutron-sculptor.wav` (+ the `.state` blob if dumped, and the reusable
  `presets/vst/neutron4-sculptor-*.json`).

## Reporting to the user

State the target + amount + tone + action region, the before→after **centroid / tilt / band deltas**, that it ran
headless via the `Neutron 4 Sculptor.vst3` build, and the `.state`/preset path. Flag that it's a **target-driven
spectral leveler** (it can move centroid >1 kHz) and A/B loudness-matched.

## Pitfalls

- **#1: `sc_target='None'` = a NO-OP** — a bare load or a float-only `apply-vst-chain` (which can't set the string
  target) does nothing. Pick a target via the [[vst-preset]] harness first, or you'll ship a passthrough.
- **It reshapes the whole balance, not just peaks** — a strong `amount` can brighten hard (centroid +1.3 kHz in
  our test). Start at the default 50, confine with the action region, and verify the centroid move is intended.
- **The Compressor/Gate dynamics don't engage headless** (a separate measured caveat) — for compression reach for
  [[vst-compress]] / [[multiband-compress]] / [[fabfilter-pro-mb]], not a Neutron dynamics module.
- For a flat, target-less dynamic resonance suppressor prefer the pure-DSP [[de-harsh]] (it ducks peaks above the
  envelope without reshaping toward a model).
- A spectral insert is not mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md) — the Neutron 4 family field guide ·
  [[izotope]] — the iZotope index
- [[vst-eq]] — the generic EQ skill this specializes · [[de-harsh]] — the pure-DSP resonance/harshness suppressor
  (no target, no plugin) · [[fabfilter-pro-q-4]] — Spectral Dynamics is the Pro-Q analogue
- Sibling Neutron modules: [[neutron-4-equalizer]] · [[neutron-4-transient-shaper]] · [[neutron-4-exciter]]
- [[vst-preset]] — apply the string-target chain (required) · [[vst-verify]] — prove the build renders (with a
  real target) · [[vst-chain]] — the backbone · [[vst]] — index/doctrine · `[G] find-resonances` — see the
  ringing first (pure DSP, no key)
- [[mix-check]] (find the problems first) · [[master-track]] (loudness) · [[gemini-audio-understanding]] — why
  meters (not Gemini mono) own the spectrum read
