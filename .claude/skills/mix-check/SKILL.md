---
name: mix-check
description: Use when the user wants a mix diagnosed before mastering — "what's wrong with this mix", "is this mix balanced", "check my mix", "find the problems", "too harsh / muddy / boomy / honky", "any phase issues", "why does this sound off". Fuses Gemini perceptual listening with loops + gemini DSP measurement into one prioritized report and concrete corrective EQ / compression moves. Does NOT master — hands off to [[master-track]].
---

# Diagnose a mix (perceptual + measurement, then fix)

Goal: find what's wrong with a mix and emit concrete corrective moves,
reconciling what a model *hears* against what DSP *measures*. The value is
the fusion: Gemini catches audible problems ("snare flammy at 1:12",
"sibilant vocal") that no single number flags; the DSP grounds those reads
in objective LUFS / spectrum / correlation so you don't chase a phantom.

Tools span both servers. Perceptual + targeted-DSP detection lives on
**stemmy-gemini**; broad measurement and the corrective render tools live on
**stemmy-loops**. Note that several DSP measurement tools exist on *both*
servers (`measure-loudness`, `measure-spectrum`); this skill uses the
loops copies for the broad measures and the gemini copies for the targeted
resonance/sibilance/phase pulls, matching the blueprint.

## Prerequisites

- Both `stemmy-loops` and `stemmy-gemini` registered and running.
- `stemmy-gemini` perceptual tools (`detect-mix-issues`, `analyze-mix-
  balance`) need `GEMINI_API_KEY`. The targeted DSP tools (`find-
  resonances`, `find-sibilance`, `analyze-phase-mono`) are pure DSP — **no**
  key required.
- `stemmy-loops:measure-loudness` needs the `mixing` extra; `measure-
  spectrum` / `measure-stereo` / `apply-eq` / `compress-loop` are core DSP.

## Recipe (ordered)

1. **Listen for problems** — `stemmy-gemini:detect-mix-issues {path,
   severity_threshold}`. Clipping, sibilance, masking, pumping, phase, with
   severity + timestamps. This sets the suspect list.
2. **Perceptual balance** — `stemmy-gemini:analyze-mix-balance {path}`.
   Band-by-band tonal / stereo / depth critique with suggestions.
3. **Objective loudness** — `stemmy-loops:measure-loudness {path}`. Ground
   the perceptual read with LUFS / true-peak / crest / PLR numbers.
4. **Objective spectrum** — `stemmy-loops:measure-spectrum {path}`. Third-
   octave / tilt / 5-band ratios to confirm or refute the perceptual tonal
   call (e.g. "muddy" → is there actually a 200–400 Hz bump?).
5. **Objective stereo** — `stemmy-loops:measure-stereo {path}`. Correlation /
   width / mono-sum loss to validate any stereo/phase concern from step 1–2.
6. **Pin resonances** — `stemmy-gemini:find-resonances {path}`. Narrow-Q
   peaks with suggested notch dB — these become precise `apply-eq` bells.
7. **Pin sibilance** — `stemmy-gemini:find-sibilance {path}`. Sibilance
   transients + de-esser settings (center Hz, Q, threshold, GR).
8. **Confirm mono safety** — `stemmy-gemini:analyze-phase-mono {path}`. Per-
   band correlation + polarity-flip flag before committing EQ moves.
9. **Reconcile** — merge perceptual findings (1–2) with measurements (3–5)
   and targeted pulls (6–8) into a single prioritized issue list. Drop any
   perceptual claim the DSP contradicts; promote any DSP anomaly the
   listener also flagged.
10. **Apply corrective EQ** — `stemmy-loops:apply-eq {path, out_path, bands,
    tilt_db_per_octave}`. Bells from `find-resonances` notches, shelves/tilt
    from the balance read. Write to `projects/<track>/mix/`.
11. **Apply compression where dynamics call for it** —
    `stemmy-loops:compress-loop {path, out_path, threshold_db, ratio, ...}`
    only where the dynamics analysis (crest/PLR + pumping flag) justifies it.
    Parallel (`mix`) blend keeps transients when the goal is glue, not
    squash.

## Outputs

- Corrected mix → `projects/<track>/mix/` (one file after EQ, or chained
  EQ → compression).
- The prioritized issue list is the headline deliverable; the corrected WAV
  is the optional follow-through if the user wants it applied, not just
  diagnosed.

## Reporting to the user

Lead with the prioritized issue list: each issue, its severity, whether it
was *heard* / *measured* / *both*, and the exact corrective move (band +
freq + gain + Q, or comp threshold/ratio). Quote the de-esser settings from
`find-sibilance` verbatim. End with: this is a mix fix, not a master —
route to [[master-track]] once the mix is clean.

## Pitfalls

- **Don't master here.** No `render-mastered`, no loudness-normalize. That's
  [[master-track]]. Mixing and mastering stay separate stages.
- **Believe the measurement over the vibe when they conflict.** "Too bright"
  with a flat/dark `measure-spectrum` tilt usually means a narrow resonance
  (step 6), not a broad shelf — notch, don't tilt.
- **De-ess with the emitted settings.** `find-sibilance` returns concrete
  center Hz / Q / threshold / GR; feed those, don't guess.
- **One move at a time on the chain.** EQ then re-measure conceptually before
  piling compression on top, so the report stays attributable.

## Related

- [[master-track]] — the downstream stage once the mix passes
- [[reference-match]] — when the goal is "sound like <ref>", not "fix problems"
- [[understand-audio]] — perceptual deep-dive on a specific timestamp/region
- [[gemini-audio-understanding]] — what Gemini can/can't hear (it sums to mono; take stereo/phase from `measure-stereo` / `analyze-phase-mono`, not Gemini)
