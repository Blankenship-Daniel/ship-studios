---
name: oxide-tape
description: "Use when running the UAD/UADx Oxide Tape Recorder for fast, simple analog tape warmth, glue, or lo-fi color on a stem/bus/mix/master/loop — 'Oxide Tape Recorder', 'UAD Oxide', 'quick tape warmth', 'simple tape glue', 'lo-fi tape', or the stripped-down UA tape machine (one Input drive + IPS/EQ/NR switches) vs the full Ampex/Studer surface. The plugin-specific deep-dive of [[vst-saturate]]; the lighter cousin of [[ampex-atr-102]] / [[studer-a800]]. Stemmy MCP, the `vst` extra."
argument-hint: <wav-or-bus> [goal: warm|master|lofi|clean]
---

# oxide-tape — drive the UAD/UADx Oxide Tape Recorder (measured)

The plugin-specific, measured workflow for the **UAD/UADx Oxide Tape Recorder**
(`/Library/Audio/Plug-Ins/VST3/uaudio_oxide_tape.vst3`) — UA's affordable, low-CPU, **stripped-down** tape
machine: one **Input** drive knob, one **Output** make-up, **7.5 / 15 IPS**, **NAB / CCIR** EQ, a **Noise
Reduction** switch, an **Input / Repro** path. Full field guide (real param surface, levers, harmonic theory,
recipes, our isolation numbers) lives in [`docs/vst/oxide-tape.md`](../../../docs/vst/oxide-tape.md). This skill
is the workflow; pull the doc for the *why* and the tables.

> **It's the simple UA tape, not the full Ampex/Studer.** Same engine team (and AES expert Jay McKnight), but
> with **no** tape type / bias / width / transformer / wow-flutter / 30 IPS / per-channel control. If you need
> those levers, use [[ampex-atr-102]] (mastering deck) or [[studer-a800]] (multitrack). Oxide's selling point is
> *speed* — pick warm/colored, turn up Input, done.

## The governing facts (read first)

1. **The whole plugin is ONE color knob — `input_level` (the Input drive).** It trades crest for harmonics:
   measured `+0 → +24` dropped **crest 14.3 → 11.1** (tape compression = the glue) while THD rose **0.16% →
   38%**. Read Input as **saturation + compression + level**. There's **no Auto-Gain** → pull `output_level`
   down to gain-match (or let the harness peak-trim) and **A/B loudness-matched**.
2. **Near-NEUTRAL at low drive, and it BRIGHTENS as you push it** — the opposite of the default-darkening
   Ampex/A800. Centroid *rose* 2990 → 3800 over `+0 → +24` as the odd-harmonic stack lit up. Driven Oxide gets
   **brighter + grittier**, not warmer. Past ~+16 on a full mix it spits — back off.
3. **Tape = ODD/3rd harmonics** (Repro path); the **electronics-only Input path = a faint EVEN/2nd and NO
   compression** (the "machine on, transport stopped" sheen). Harshness is a *driven* phenomenon; the cure is
   **less Input**, not EQ.
4. **NAB vs CCIR is the strongest tone lever and it's a BRIGHTNESS switch:** CCIR pushed centroid **3027 → 3475
   (+448)**. NAB = warmer/fuller top, CCIR = brighter/leaner.
5. **15 IPS = warm/full lows; 7.5 IPS = "more colored / frequency-shift," leaner low + more upper energy** (this
   *inverts* the textbook "slow = bigger bass bump" — on this model 15 carries the weight). No 30 IPS.
6. **NR (default ON) is a noise-floor switch, NOT a tone control** — tonally identical on a hot bus (measured
   bit-identical). Leave it on unless you *want* the modeled hiss/hum for vibe.
7. **Meters own this** (Gemini hears mono): verify with `[L] measure-loudness` (crest), `[L] measure-spectrum`
   (centroid/tilt/bands), `[L] measure-distortion` (THD = the drive), `[L] check-clipping`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- Renders **headless via Pedalboard** (UADx native, no iLok dongle — authorized on this rig; `bypass` == dry
  bit-for-bit). Load **`uaudio_oxide_tape.vst3`** — the **`UAD Oxide Tape.component`** twin passes audio through
  unprocessed offline (load the `uaudio_*.vst3` build, not the `.component` twin). Verify on any new machine ([[vst-verify]]).
- **Harness for the switches.** `input_level` / `output_level` are **numeric** (drivable from `apply-vst-chain`'s
  float dict), but `path_select` / `ips` / `emphasis_eq` / `noise_reduct` are **string/bool enums** the float
  dict silently ignores → use the **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`). Exact enum
  strings: `path_select` `"Input"`/`"Repro"`; `ips` `"7.5 IPS"`/`"15 IPS"`; `emphasis_eq` `"NAB"`/`"CCIR"`;
  `noise_reduct` `true`/`false`.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt). The "before" column.
2. **Pick the starting point** by goal (doc Part B §4):
   - **Quick warm drum/instrument bus:** Repro · **15 IPS** · **NAB** · NR on · Input **+6…+10**
     (`oxide-warm-drum-glue.json`).
   - **Transparent 2-bus / master polish:** Repro · 15 IPS · NAB · NR on · Input gentle **+3…+5**, before the
     limiter (`oxide-master-glue.json`).
   - **Lo-fi / driven color:** Repro · **7.5 IPS** · NAB (or CCIR brighter) · NR off · Input hot **+12…+18**
     (`oxide-lofi-color.json`).
   - **Clean electronics sheen (no tape):** Path = **Input** · modest drive — faint 2nd-harmonic, no compression.
3. **Drive by crest, not by a number.** Raise `input_level` until you see only **~1–2 dB crest reduction** for
   glue; **stop before the top spits** (rising 3rd/5th). To brighten/darken, switch **CCIR/NAB** or **7.5/15
   IPS** — don't overdrive Input to chase tone (it just adds grit). Trim `output_level` down to gain-match.
4. **Apply** via [[vst-preset]] (`apply_vst_preset.py <preset.json> <in.wav> <out.wav>` with the `vst` venv) so
   the switches are honored. Output → `projects/<track>/mix/`. (For drive-only tweaks on the defaults you *can*
   use `[L] apply-vst-chain` with just `input_level`/`output_level`.)
5. **Verify** — re-measure. Glue = **crest down only ~1–2 dB** (not collapsed); warm = NAB/15 IPS (more 20–200
   energy); brighter = CCIR/7.5 (centroid up); drive = THD up. `check-clipping` (Input raises true-peak). A/B
   with `[L] render-ab` loudness-matched so "better" isn't just "louder."
6. It's a **stem/bus/master color insert**, not a limiter — hand the result to [[finalize-mix]] / [[master-track]].

## Outputs

- Processed WAV in `projects/<track>/mix/` (or `masters/` for a 2-bus pass) + the reusable preset JSON.
- Ready-made presets in `presets/vst/`: `oxide-{warm-drum-glue, lofi-color, master-glue}.json` — each
  measure-validated. `scripts/mix/oxide_sweep.py` reproduces the isolation numbers.

## Reporting to the user

State Path / IPS / EQ / NR / Input, the before→after **crest + centroid/tilt** (and THD if driven hard), that it
ran **headless**, and whether the move was warm (15/NAB) vs colored/bright (7.5 or CCIR) vs lo-fi (driven). A/B
loudness-matched.

## Pitfalls

- **Input both saturates AND raises level** (no Auto-Gain) — gain-match with Output / render-ab.
- **Driven = brighter, not darker** — chasing warmth by overdriving just adds odd-harmonic grit. Use NAB/15 IPS
  or less drive for warmth; reserve high Input for lo-fi color.
- **NR is not a tone control** — it only removes the modeled hiss/hum floor. Don't expect it to change tone.
- **No 30 IPS / tape type / bias / width / transformer** — reach for [[ampex-atr-102]] / [[studer-a800]] if you
  need them.
- **Switches need the harness** — `apply-vst-chain`'s float dict silently keeps the default Repro/15/NAB/NR-on
  for every string/bool param; only `input_level`/`output_level` are reachable directly.
- **Two builds** — `uaudio_oxide_tape.vst3` renders; the `UAD Oxide Tape.component` twin passes through.
- **Tape can't do surgery** — a sibilance hotspot / harsh resonance wants [[de-ess]] / [[de-harsh]] /
  [[dynamic-eq]]; a balance problem wants [[mix-balance]] first. Oxide is glue + tilt + harmonic color only.

## Related

- [`docs/vst/oxide-tape.md`](../../../docs/vst/oxide-tape.md) — the full measured field guide (levers, theory, recipes, sources)
- [[vst-saturate]] — the generic tape/harmonic-color skill this specializes · [[vst-preset]] — apply enum chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — backbone recipe · [[vst-shootout]] — render IPS/EQ/Input variants & judge
- [[ampex-atr-102]] (smooth 2-bus mastering tape) · [[studer-a800]] (punchy multitrack tape) · [[softube-tape]] (Softube's own 3-machine deck) — the fuller UAD siblings; Oxide is the fast/light one
- [[vibe-analog-machines]] — the lo-fi/character cousin · [[warm-drum-bus]] — the warm drum-bus pref this serves · [[finalize-mix]] / [[master-track]] — the stages a tape insert lives in
- [[gemini-audio-understanding]] — why meters (not Gemini) own loudness/peak/stereo for tape moves · [[vst]] / [[vst-verify]] — the UADx/headless caveats
