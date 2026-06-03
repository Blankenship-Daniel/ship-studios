---
name: softube-tape
description: "Use when running the Softube Tape plugin for analog tape color, warmth, glue, or lo-fi on a stem/drum-bus/mix-bus/loop — 'Softube Tape', 'add tape', 'tape glue/warmth on the drums', 'tape on the 2-bus', 'parallel tape on the kick/bass', 'lo-fi tape character', 'Type A/B/C tape', or the three-machine deck with the RC-1 Remote Control (AMOUNT/TYPE/TAPE SPEED). The measured, plugin-specific deep-dive of [[vst-saturate]] — grounded in the real 15-param surface + isolation numbers in docs/vst/softube-tape.md. NOT the Ampex ([[ampex-atr-102]]) or Studer ([[studer-a800]]). Stemmy MCP, the `vst` extra."
argument-hint: <wav-or-bus> [goal: warm|tight|mix-glue|parallel|lofi]
---

# softube-tape — drive the Softube Tape plugin (measured)

The plugin-specific, measured workflow for **Softube Tape** (`/Library/Audio/Plug-Ins/VST3/Tape.vst3`) — the
three-machine tape emulation with the deck + **RC-1 Remote Control** panel. Full field guide (real param
surface, the levers, harmonic theory, recipes, decision table, our isolation numbers) lives in
[`docs/vst/softube-tape.md`](../../../docs/vst/softube-tape.md). This skill is the workflow; pull the doc for
the *why* and the tables.

> **It's Softube's own "Tape," not an Ampex/UAD.** The faceplate's "MANUFACTURED IN SWEDEN" is Softube's
> branding, not the modeled machine. For the actual Ampex use [[ampex-atr-102]]; for the Studer A800 use
> [[studer-a800]]. (An earlier inventory note claiming this plugin "isn't installed / doesn't exist" was
> wrong — it **is** installed and renders headless; see the doc.)

## The governing facts (read first)

1. **Amount is GAIN-COMPENSATED → it moves *crest*, not tone.** Measured: sweeping Amount 2→10 shifted
   centroid only ~2218→2245 Hz, but crest fell −0.2 (a2) → −0.9 (a8) → **−4.9 dB (a10, crushes)**. Read Amount
   as **saturation + tape compression**. The official drive guide is "until the GUI THD meter ≈ 1–1.4 %" —
   **headless that meter is unreadable**, so cap Amount by **crest drop + render-ab**, not by a knob value.
2. **The bare default is hot.** A no-params load = Amount **7.8** / Type **C** / **WET** / **+6 in** /
   Crosstalk **50** (crest −0.9). Always set Amount + dry_wet explicitly for subtle use.
3. **Types differ mostly in low-end weight (on drums):** A = most transparent (≈ dry), **B = darkest/fattest**
   (most LF), C = middle + a touch of top. **Faster IPS = brighter + tighter lows; 15 IPS = fattest** (head
   bump on the kick); 30 IPS = tight/bright; slow = lo-fi/noise.
4. **High Freq Trim is the tone lever** (measured ±~560 Hz centroid: CUT 1705 / FLAT 2219 / BOOST 2785) — use
   it, not Amount, to brighten/darken.
5. **Crosstalk NARROWS/glues, never widens** (corr 0.98→0.995, mono-sum loss 0.63→0.30 at 100) and is **inert
   on mono**. Use 40–50 % for center weight + better mono-sum, not for width.
6. **Meters own this** (Gemini hears mono): verify with `[L] measure-loudness` (crest), `[L] measure-spectrum`
   (centroid/tilt), `[L] measure-stereo` (crosstalk), `[L] check-clipping` (Input pushes true-peak).

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- The plugin renders **headless via Pedalboard** (Softube/iLok-PACE — authorized on this rig). iLok is a
  render-farm landmine ([[vst]]): **verify load+render on any new machine** ([[vst-verify]]).
- **Harness is mandatory.** 13 of 15 params are **string enums** (`color_type`, `tape_speed`, `dry_wet`,
  `speed_stability`, `high_freq_trim`, `crosstalk`, `input_db`, `output_db`) — `apply-vst-chain`'s float-only
  dict **cannot** set them. Use the **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`); it
  `setattr`s every param (exact-string-then-snap). Enum strings are exact: `"A"/"B"/"C"`, `"15 IPS"`,
  `"WET"/"DRY"/"50.0"`, `"FLAT"/"CUT"/"BOOST"`, `"OFF"/"50.0"`, `"STABLE"/"WOBBLY"`. Keep `playback="RUN"`.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt) [+ `measure-stereo`
   if you'll use Crosstalk]. The "before" column.
2. **Pick the starting point** by goal (doc §7 decision table):
   - **Warm/fat drum bus:** Type **B** · **15 IPS** · Amount 5–6 · Crosstalk 40–50 · HF FLAT
     (`softube-tape-drum-glue-warm.json`).
   - **Tight/modern drum bus:** Type **A** · **30 IPS** · Amount 4–5 · Crosstalk OFF (`softube-tape-drum-tight.json`).
   - **Transparent mix/master glue:** Type **A** · **30 IPS** · Amount 2–3 · Crosstalk 40–50 (`softube-tape-mix-bus-glue.json`).
   - **Parallel thick (drums/bass):** Type **C** (B for bass) · 15 IPS · Amount **8** · **dry_wet 50 %**
     (`softube-tape-parallel-thick.json`).
   - **Lo-fi character:** Type **C** · 3¾/1⅞ IPS · Amount 8–10 · Speed Stability into wobble · **Noise on** ·
     HF CUT (`softube-tape-lofi.json`).
3. **Drive by crest, not by knob.** Raise `color_amount` until you see only **~1–2 dB crest reduction** for
   glue; **stop before the top spits** (rising 3rd harmonic). Shape tone with **High Freq Trim** (BOOST air /
   CUT warm), not by overdriving Amount. Don't double-compress after tape.
4. **Apply** via [[vst-preset]] (`apply_vst_preset.py <preset.json> <in.wav> <out.wav>` with the `vst` venv) so
   the enums + parallel blend are honored. Output → `projects/<track>/mix/`.
5. **Verify** — re-measure. Glue = **crest down only ~1–2 dB** (not collapsed) + a small **centroid/tilt move**
   (DOWN for warm Type B / 15 IPS; UP for 30 IPS / BOOST). Crosstalk = **correlation up + mono-sum loss down**
   (not width up). `check-clipping` (Input raises true-peak). A/B with `[L] render-ab` loudness-matched so
   "better" isn't just "louder" (Input isn't gain-compensated; Amount is).
6. It's a **stem/bus insert**, not a master — hand the result to [[finalize-mix]] / [[master-track]].

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset JSON (`.state` if dumped).
- Ready-made presets in `presets/vst/`: `softube-tape-{drum-glue-warm, drum-tight, mix-bus-glue,
  parallel-thick, lofi}.json` — each measure-validated (see the doc).

## Reporting to the user

State the Type / IPS / Amount / DRY-WET / HF-Trim / Crosstalk, the before→after **crest + centroid/tilt**
(and correlation if Crosstalk was used), that it ran **headless**, and whether the move was warm (Type B /
15 IPS, centroid down) vs tight (30 IPS, up). A/B loudness-matched.

## Pitfalls

- **Don't trust the bare default** (Amount 7.8 / WET / Crosstalk 50 = already obvious). Set values explicitly.
- **Amount past ~8 stops gluing and starts crushing/distorting** (a10 = −4.9 dB crest). Glue lives ≤6–7.
- **Input ≠ gain-compensated** — it adds saturation *and* level; gain-match with Output / render-ab. Calibration
  is rumored ~−13 dBFS = 0 VU (unverified) → gain-stage conservatively, watch true-peak.
- **Crosstalk needs stereo and narrows** — useless on a mono loop, and at 100 it's near-mono. Not a widener.
- **Tape can't do surgery** — a true sibilance hotspot / harsh resonance wants [[de-ess]] / [[de-harsh]] /
  [[dynamic-eq]]; tape is glue + tilt + compression only. A balance problem wants [[mix-balance]] first.
- **Speed Stability is pitch/level modulation** spectra barely capture — judge wow/flutter by ear.

## Related

- [`docs/vst/softube-tape.md`](../../../docs/vst/softube-tape.md) — the full measured field guide (levers, theory, decision table, sources)
- [[vst-saturate]] — the generic tape/harmonic-color skill this specializes · [[vst-preset]] — apply enum/parallel chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — backbone recipe · [[vst-shootout]] — render Type/IPS/Amount variants & judge
- [[studer-a800]] (punchy multitrack tape) · [[ampex-atr-102]] (smooth 2-bus master tape) — the UAD siblings; Softube Tape is subtler + far more CPU-efficient, with fewer formulas
- [[softube-transient-shaper]] — the other Softube unit · [[warm-drum-bus]] — the warm+tight drum-bus pref this serves · [[finalize-mix]] / [[master-track]] — the stages a tape insert lives in
- [[gemini-audio-understanding]] — why meters (not Gemini) own loudness/peak/stereo for tape moves · [[vst]] — the iLok/headless caveats
