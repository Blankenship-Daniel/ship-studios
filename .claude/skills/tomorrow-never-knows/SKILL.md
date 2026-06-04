---
name: tomorrow-never-knows
description: "Use when the user wants The Beatles 'Tomorrow Never Knows' / Ringo / Geoff Emerick 1966 drum sound from a FOLDER of multi-mic drum stems — 'Tomorrow Never Knows drums', 'that Beatles/Revolver drum sound', 'Ringo TNK', 'heavily compressed pumping drums', 'lo-fi 60s mono drums', 'Emerick close-mic drum sound', 'crushed tom-forward drums'. The composite end-to-end recipe (#2 in the famous-drum-sound series): phase-align → per-stem process (DARK) → tom-FORWARD balance → Fairchild-pump + Studer-15IPS-dark-tape + mono-narrow bus → loops. The OPPOSITE axis from [[fool-in-the-rain]]: CRUSH/pump (not glue), DARK/lo-fi (not warm-open), MONO/narrow (not wide-room). This is the TONE, not Ringo's tom GROOVE, and it wants TOM mics. Local DSP + the stemmy MCP servers; needs the `vst` extra (Fairchild/Studer/LA-3A/Vibe) + optional GEMINI_API_KEY (perceptual A/B)."
argument-hint: <stems-folder> [slug] [bpm]
---

# tomorrow-never-knows — The Beatles "Tomorrow Never Knows" drum sound (end to end)

One ordered pipeline that takes a **folder of multi-mic drum stems** and produces the **heavily-compressed,
dark/lo-fi, mono, tom-forward "Tomorrow Never Knows" tone** as (a) a finished drum **bus** and (b) drum
**loops**. The OPPOSITE axis from the Bonham [[fool-in-the-rain]] recipe — mirror that skill's anatomy.
Chain-validated 2026-06-03 on the Ship Studios kit.

**User steps → stages:** process stems (Stage 2) · volume-adjust TOM-FORWARD (Stage 3) · EQ (Stage 2 dark
corrective + Stage 4 dark tilt) · use the VST plugins + sum (Stage 4: Fairchild → Studer 15 IPS → mono-narrow)
· loops (Stage 5).

## What this is — and is NOT

- It chases the **TONE/feel**: heavy compression with audible **PUMP/breathing** (crest down, ambience
  swells), **DARK/lo-fi/saturated** (rolled-off top, no air), **MONO/narrow** image, **tom-forward** balance,
  deep **damped** kick. **Not** Ringo's hypnotic tom GROOVE — that's in the source performance.
- It **wants TOM mics** (rack/floor) for the tom-forward balance. No toms → you still get the TNK *tone*
  (crush/dark/mono) but kick+snare lead instead of toms (the documented fallback).
- **Honest proxies:** the authentic **Studer J37** (Arturia Tape J-37) is **passthrough headless** ([[tape-j-37]])
  → **Studer A800** stands in; the exact 1966 compressor is debated (Fairchild 660 / Altec) → **Fairchild 660**
  is the era/Abbey-Road choice. The repo Fairchild **colors more than it crushes** ([[fairchild-660]] — holds
  crest), so the Fairchild-only pump is gentler than the over-limited original → add the **`--la3a`** opto
  stage ([[la-3a]], genuine crest reduction) and/or **`--vibe`** ([[vibe-analog-machines]], lo-fi grit) for the
  heavy crush. The tuning workflow A/Bs them.

## Inputs & setup

- **`$1` = stems folder**; **`$2` = slug** (else slugify); **`$3` = BPM** (for Stage-5 loops).
- Prereqs: `uv sync --extra drum-prep`; in `../stemmy-loops-mcp`: `uv sync --extra vst --extra mixing`. UADx
  `uaudio_fairchild_660.vst3` + `uaudio_studer_a800.vst3` (+ `uaudio_la3a.vst3` / `uaudio_verve.vst3` for the
  optional stages) installed/authorized (`uaudio_*` builds render headless). `GEMINI_API_KEY` only for the
  optional Stage-4b A/B.
- **Run scripts with the stemmy-loops vst venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python`. `drum-prep` via
  `uv run --no-sync drum-prep`. ABSOLUTE paths for find-loops / Gemini tools; in a worktree, `projects/`/`artifacts/`
  live in the canonical checkout.

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` ([[format-fix]]; `afconvert -d LEI24 -f WAVE`).
- Baseline-measure each + **energy-scan to find the active region** (drum-stem exports often have a long
  quiet intro/outro — measure the wrong window and you'll amplify the noise floor). Keep the third-octave spectra.

## Stage 1 — phase-align close mics → overheads (gated)

- `uv run --no-sync drum-prep detect <stems-dir>` (FX/reverb returns auto-detect as `fx`, excluded; OH = stereo
  anchor; room = polarity-only) → `phase-align` → `phase-aligned/`. Stereo-image gate as in [[drum-phase-align]]
  (toms/kick/snare mono-collapse if dual-mono; OH/room stay stereo).

## Stage 2 — process the stems (DARK, gentle)

Author `presets/mix/<slug>-stem-process.plans.json` from `presets/mix/tomorrow-never-knows-stem-process.plans.json`
(adapt freqs/roles to your kit). TNK rules: **DARK + gentle, NO air anywhere.** Damped kick (keep the sub,
de-ring ~350, no click); **resonant-but-controlled toms** (tame ring, keep fundamental + a touch of stick);
thuddy snare (keep body, dynamic de-harsh the bright edge, no crack); dark overheads (cymbals back). Keep low-mid
weight (no low-mid scoop in the API EQ). declick OFF. Run `process_stems.py … <kit>/processed-tnk`.

## Stage 3 — TOM-FORWARD balance (+ sum)

Measured-LUFS balance with **toms + kick + snare FORWARD** and **overheads/room pulled back** (TNK is close &
dark; the heavy bus comp brings the ambience UP as the pump — so the room is *pump fuel*, not the star). Targets
in `presets/mix/tomorrow-never-knows.json` (`balance_targets_lufs`); a **no-toms fallback** is documented there
(kick+snare lead). `balance_stems.py … → bus_tnk_pre.wav`. A balance problem is not an EQ problem ([[mix-balance]]).

## Stage 4 — TNK bus (Fairchild pump → Studer 15 IPS dark tape → dark EQ → mono narrow)

`$VENV scripts/mix/tomorrow_never_knows_bus.py <pre-bus> bus_tnk.wav` — defaults reproduce the approved signature
(`presets/mix/tomorrow-never-knows.json`):

- **A. HPF 35** → **B. Fairchild 660** (mono, driven HARD: input −6, thresh 8, time_const 2, headroom 8, sc_filt
  Off = full-range pump) → **C. Studer A800 15 IPS NAB** (repro_hf 1.5 = dark, fat lows) → **D. dark EQ** (low-shelf
  +1.5@100, bell +2@200 thump, high-shelf **−4@8k** = no air) → **E. adjust-stereo width 0.35** (mono-narrow) → −1 dBFS.
- **Optional crush:** `--la3a` (opto LIMIT, HF-emphasis 0 — genuine crest reduction, the real TNK crush) and/or
  `--vibe` (VINTAGIZE lo-fi grit). **Knobs:** `--fc-input/--fc-thresh/--fc-headroom/--fc-tc` (pump amount),
  `--repro-hf` (dark — raise if muddy), `--dark` (high-shelf cut), `--width` (mono amount). Expect: centroid DOWN
  hard, crest DOWN (pump), correlation UP toward ~0.99 (mono). **On an already-dark source it can over-darken
  (~centroid 1500) — ease `--repro-hf` up and `--dark` toward −2.**

### Stage 4b — lock the settings (tuning workflow)

Run `.claude/workflows/tomorrow-never-knows.js` (`/workflows`) — renders variants (Fairchild drive · +LA-3A ·
+Vibe · narrow amount · dark amount) and runs a **Gemini judge panel** scoring each on the TNK brief (pump/breathing,
dark, lo-fi/grit, mono/narrow, low-mid weight). **Gemini hears ~16 kbps mono** — trust the meters for crest/centroid/
correlation, ears for the *feel* of the pump and grit ([[gemini-audio-understanding]]). Winner's meters → the
preset's `approved_signature`.

## Stage 5 — create loops (raw + mastered)

As [[loops-to-deliverables]] / [[fool-in-the-rain]] Stage 5 on `bus_tnk.wav`: structure-trim → **confirm BPM** →
`find-loops` (bars [1,2,4,8]) → seam → raw (tagged) + mastered (gentle, crest-preserving, ×3 formats, tagged) →
verify-tags ([[delivery-qc]]). Tagging gotchas handled in `scripts/loops/build_loops.py`.

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/phase-aligned/ · stems/processed-tnk/
  mix/   bus_tnk_pre.wav · bus_tnk.wav (FINAL, peak −1) · fitr_shootout-style variants
  loops/ · deliverables/ · track.md
presets/mix/<slug>-stem-process.plans.json
artifacts/<slug>-loops/
```

## Report to the user

Per-stage before→after; the TNK signature vs approved (centroid DOWN, crest DOWN = pump, correlation UP = mono);
the tom-forward balance table (or the no-toms note); confirmed BPM; loop counts + all_tagged. MIX bus (peak −1)
→ hand to [[master-track]].

## Pitfalls

- **Needs toms** for the tom-forward balance; no toms → tone-only (kick+snare lead).
- **Tone, not groove.** Don't expect the hypnotic feel without the performance.
- **Over-dark risk** on already-dark kits (centroid ~1500) — ease `--repro-hf`/`--dark`.
- **Don't widen** — mono/narrow is the defining TNK image.
- **Find the active window** before measuring/balancing — the source may have a long quiet intro.
- The Fairchild-only pump is **gentle** (it colors, holds crest) — use `--la3a` for the heavy 1966 crush.

## Related
[[fool-in-the-rain]] · [[fairchild-660]] · [[la-3a]] · [[studer-a800]] · [[vibe-analog-machines]] · [[tape-j-37]] · [[drum-prep]] · [[stem-process]] · [[mix-balance]] · [[loops-to-deliverables]] · [[delivery-qc]] · [[gemini-audio-understanding]] · [[master-track]]
