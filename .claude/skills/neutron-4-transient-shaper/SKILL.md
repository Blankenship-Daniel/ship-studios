---
name: neutron-4-transient-shaper
description: "Use when running the Neutron 4 Transient Shaper for punch/attack or tail control on a drum loop or drum bus — 'Neutron transient shaper', 'iZotope add punch', 'more attack on the kick/snare', 'tighten the drum tails', '3-band transient design'. The measured, plugin-specific deep-dive of [[drum-punch]] (twin [[softube-transient-shaper]]). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: punch|attack|tighten-tail|per-band]
---

# neutron-4-transient-shaper — drive the Neutron 4 Transient Shaper (measured)

The plugin-specific, measured workflow for the **iZotope Neutron 4 Transient Shaper**
(`/Library/Audio/Plug-Ins/VST3/Neutron 4 Transient Shaper.vst3`) — a **3-band** transient designer (per-band
`attack` −15..+15, `sustain` −15..+15, `contour` Sharp/Normal/Smooth) with a global detection `mode`
(Precise/Balanced/Loose). The iZotope member of [[drum-punch]] alongside [[softube-transient-shaper]]. Full field
guide — the per-module render verdicts, the enum-harness rule, sources —
[`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md). This skill is the workflow.

## The governing facts (read first — measured on this rig)

1. **Renders headless here** — the `Neutron 4 Transient Shaper.vst3` build loads + processes in the offline
   Pedalboard host (NI/iLok-account-authorized on this Mac). **Re-verify elsewhere** with [[vst-verify]] — loads ≠
   renders.
2. **`attack` boost ADDS punch but also adds ~+7 dB of level — and CLIPS if you don't compensate.** ★ MEASURED
   (drum bus): `ts_b1_attack=ts_b2_attack=ts_b3_attack=10.0` raised rms **+7.5 dB** and slammed the peak to
   **0 dBFS / +0.4 dBTP (clipped)**. Add `global_output_gain≈−7` to cancel the level; THEN — loudness-matched
   (LUFS −18.3→−17.9, true-peak a clean **−0.6 dBTP**) — crest rises **15.6→17.7 (+2.1 dB, more punch)**. The
   punch is the **crest delta**, not the level — always loudness-match the A/B and check true-peak.
3. **Every param is an enum** (numeric AND string). `apply-vst-chain`'s float `parameters` dict CAN set the
   **numeric** enums (`ts_bN_attack`, `ts_bN_sustain`, `ts_global_mix`) — but it **CANNOT** set the **string/bool**
   enums (`ts_bN_contour` Sharp/Normal/Smooth, `ts_global_mode` Precise/Balanced/Loose, `ts_bN_bypass`). Those need
   the **[[vst-preset]]** harness (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
4. **3 bands, all active by default** (`ts_bN_bypass=False`), so an `attack`/`sustain` move on any band is a real
   move with no enable. `attack`/`sustain` default 0 (no-op); drive them.
5. **Shared utility header** on every Neutron module: `global_input_gain`/`global_output_gain` (−60..+10 dB),
   `pan`, `width` (−100..+100, **real M/S width**), `sum_to_mono`, `invert_phase`, `delay_l`/`delay_r` — so the
   Transient Shaper doubles as a width / mono / delay utility.
6. **The AI "Track Assistant" / Learn is GUI-only** — it won't run headless; you drive the manual 3 bands.
7. **Meters own it** (Gemini hears ~16 kbps mono) — read `[L] measure-loudness` crest/PLR + `[L]
   measure-microdynamics` per-band punch, not vibes.

## Prerequisites

- `[L] apply-vst-chain` / `[L] list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **`/Library/Audio/Plug-Ins/VST3/Neutron 4 Transient Shaper.vst3`** — confirm with `[L] list-vst-plugins
  {name_contains:"Neutron 4 Transient Shaper"}` and take the **VST3** path.
- **Pre-screen with [[vst-verify]]** (`presets/vst/probe_plugin.py "Neutron 4 Transient Shaper"`, expect
  `RENDERS ✓`) — re-verify on any new machine.
- Balance the bus first ([[mix-balance]]); this is a punch/shaping stage, **not** a master — hand off to
  [[master-track]].

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest / PLR / true-peak) + `[L] measure-microdynamics` (per-band
   block-crest + punch) + `[L] measure-spectrum`. The "before."
2. **Pick the move** from the table. Decide per band: `attack` (+ = punch, − = soften), `sustain` (+ = bigger
   tail/room, − = tighter/drier), and the global `mode` (Precise = tightest detection, Loose = smoother).
3. **Apply** — numeric `attack`/`sustain`/`mix` via `[L] apply-vst-chain` (`dump_state=true` to capture `.state`);
   anything with a `contour`/`mode`/`bypass` via `…/stemmy-loops-mcp/.venv/bin/python
   presets/vst/apply_vst_preset.py presets/vst/neutron4-ts-*.json <in>
   projects/<track>/mix/<stem>_neutron-transient.wav`.
4. **Prove it** — re-`measure-loudness` / `measure-microdynamics`: expect **crest UP** for an attack boost (with
   rms also up → loudness-match), tail control on the sustain bands. **A/B loudness-matched** (`[L] render-ab` /
   [[level-match]]) so "punchier" isn't "louder."
5. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch over-shaping (clicky/unnatural); reconcile any
   mono "dynamics" flag against the stereo meters ([[gemini-audio-understanding]]).

## Move table

| Goal | Neutron 4 TS move | Reach |
|---|---|---|
| **Whole-kit punch** ★ | `ts_b1_attack=ts_b2_attack=ts_b3_attack=10` + `global_output_gain≈−7` (cancel the added level / avoid clipping) | numeric |
| **Kick attack only** | `ts_b1_attack` + (low band) | numeric |
| **Snare crack / presence** | `ts_b2_attack` + (mid band) | numeric |
| **Tighten the tails (drier)** | `ts_bN_sustain` − on the offending band | numeric |
| **Bigger room / longer tail** | `ts_bN_sustain` + | numeric |
| **Sharper vs smoother edge** | `ts_bN_contour` 'Sharp' (clicky) ↔ 'Smooth' (rounded) | harness |
| **Detection feel** | `ts_global_mode` 'Precise' (tight) ↔ 'Loose' (smooth) | harness |
| **Parallel blend** | `ts_global_mix` down for parallel transient design | numeric |

★ shipped example, on an 8 s 48 kHz stereo **drum-bus** clip (baseline crest 15.6 dB, −18.3 LUFS): all three bands'
attack `=10.0` raises rms **+7.5 dB** and clips (peak 0 dBFS / +0.4 dBTP) — so pair it with `global_output_gain=−7`
to cancel the level. Loudness-matched (−18.3→−17.9 LUFS), the result is crest **15.6→17.7 (+2.1 dB punch)** with a
clean **−0.6 dBTP**. The punch is the crest delta, not the level. `attack`/`sustain` are numeric (float-dict
reachable); `contour`/`mode` are string enums → harness.

## Outputs

- `projects/<track>/mix/<stem>_neutron-transient.wav` (+ the `.state` blob if dumped, and a reusable
  `presets/vst/neutron4-ts-*.json` for a contour/mode move).

## Reporting to the user

State the per-band moves (attack/sustain, contour, global mode), the before→after **crest / per-band punch /
PLR**, that it ran headless via the `Neutron 4 Transient Shaper.vst3` build, and the `.state`/preset path.
A/B loudness-matched so "punchier" isn't "louder."

## Pitfalls

- **Attack boost raises level ~+7 dB and CLIPS** — measured, attack +10 across 3 bands hit **0 dBFS / +0.4 dBTP**.
  Compensate with `global_output_gain≈−7` (or lower the attack), then re-measure crest **and true-peak** and
  loudness-match the A/B — the crest gain (+2.1) only materializes clean once level-matched.
- **The float dict can't set `contour`/`mode`/`bypass`** — for those use the [[vst-preset]] harness (or `.state`).
- **`attack`/`sustain` default 0 = no-op** — you must drive at least one band.
- **The Compressor/Gate dynamics don't engage headless** (a separate measured caveat) — for compression reach for
  [[vst-compress]] / [[multiband-compress]] / [[fabfilter-pro-mb]], not a Neutron dynamics module.
- A transient stage is an insert, not mastering — hand off to [[master-track]] for true-peak / loudness.

## Related

- [`docs/vst/izotope-neutron.md`](../../../docs/vst/izotope-neutron.md) — the Neutron 4 family field guide ·
  [[izotope]] — the iZotope index
- [[drum-punch]] — the pure-DSP transient-design twin (no plugin, deterministic) · [[softube-transient-shaper]] —
  the other plugin transient shaper
- Sibling Neutron modules: [[neutron-4-equalizer]] · [[neutron-4-sculptor]] · [[neutron-4-exciter]]
- [[vst-preset]] — apply contour/mode chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — the
  backbone · [[vst]] — index/doctrine
- [[mix-check]] (find the problems first) · [[master-track]] (loudness) · [[gemini-audio-understanding]] — why
  meters (not Gemini mono) own crest/punch
