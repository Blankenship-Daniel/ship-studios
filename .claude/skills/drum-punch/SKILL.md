---
name: drum-punch
description: Use when a drum loop or drum bus needs more punch/attack — "make the drums punchier", "give the kick more attack", "the snare has no snap", "tighten the low end and add slam", "more transient on the drums", "the drums sound flat/soft". Measure-driven multiband transient design via shape-bands (per-band LR4 transient + gain), proven before/after with crest/PLR so louder-transient isn't just louder. Works on ONE stereo drum file (loop or bus) — a multi-mic kit goes through [[drum-prep]] first.
argument-hint: <drum-loop-or-bus.wav>
---

# Drum punch — multiband transient design, measured before/after

Goal: make a drum loop or summed drum bus hit harder by accentuating attack
and tightening the lows with `shape-bands` (per-band LR4 transient design +
gain) — and *prove* it, because "punchier" and "louder" are easy to confuse.
The discipline is the point: measure crest/PLR before, shape, then re-measure
to show transients rose without clipping, and A/B loudness-matched.

`shape-bands` is a powerful tool with no existing skill coverage. Note the
overlap traps: `master-track`'s `transient_shape` is a single broadband knob
inside the mastering render; `finalize-mix` / `mix-check` "punch" is
parallel/NY compression; `drum-mix --feel punchy` is just ambience balance.
None of those is per-band transient design — this is.

## Prerequisites

- `stemmy-loops` registered and up. Every tool here is `[L]`, pure DSP, no
  API key — they run on the base install; the loudness/crest reads
  (`measure-loudness`, `inspect-loop`, `render-ab`) need the `mixing` extra
  (pyloudnorm). (There is no `core` extra.)
- Input is **one stereo drum file** — a loop or a summed drum bus. For a
  multi-mic kit (overheads + close mics), prep and bounce it first with
  [[drum-prep]] / [[drum-mix]]; `shape-bands` is not kit-aware.
- BPM (from `projects/<track>/track.md`) only matters if you want a tidy A/B.

## Recipe (ordered — measure before/after)

1. **Baseline** — `[L] measure-loudness` (crest / PLR — the punch proxies)
   + `[L] measure-spectrum` (low / attack balance) + `[L] check-clipping`.
   This is the "before" column; punch = a *rise* in crest at matched loudness.
2. **Multiband transient design** — `[L] shape-bands {crossovers_hz: [120,
   2500], bands: [{transient, gain_db}, ...]}`. Crossovers are a **separate
   ascending list**; N crossovers → N+1 bands, so `bands` length must equal
   `len(crossovers_hz) + 1` (default crossovers `[120, 2000]` → 3 bands). Push
   positive `transient` (range −1..+1) on the low band (kick attack) and the
   high-mid band (snare snap); keep the lows tight. One coherent move set,
   then measure.
3. **Re-measure** — `[L] inspect-loop` (or `measure-loudness` again) +
   `[L] check-clipping`. Confirm crest/PLR **rose** (more transient) and the
   attack boost did **not** push true-peak into clipping.
4. **Loudness-matched A/B** — `[L] render-ab {processed, reference: <original>,
   out_path, gap_seconds}` → one A/B WAV so the change is judged at matched
   level, not just louder. (`out_path` is required; `gap_seconds` defaults to
   0.5. `render-ab` collapses to mono — fine for a punch
   check; for a stereo kit audition use [[drum-audition]].)

## Outputs

- Punched drum file → `projects/<track>/mix/` (or `loops/` if it's a loop).
- The loudness-matched A/B WAV alongside it.

## Reporting to the user

Lead with the **crest/PLR delta** (the punch metric, before → after). List
the per-band `transient` / `gain_db` applied and the crossovers. Confirm
clipping stayed clean. Give the A/B path and state plainly: it got punchier,
not just louder.

## Pitfalls

- **Single file only.** `shape-bands` isn't kit-aware — a multi-mic kit must
  go through [[drum-prep]] → [[drum-mix]] to a bus first.
- **Prove punch with crest/PLR**, not loudness — re-measure; don't trust the
  ear at unmatched level.
- **Watch true-peak** — positive transient raises peaks; always
  `check-clipping` after.
- **`render-ab` is mono.** For a stereo before/after of a kit, use
  [[drum-audition]].

## Related

- [[drum-prep]] — prep a multi-mic kit before you can punch the bus
- [[drum-mix]] — bounce a prepped kit to the stereo bus this operates on
- [[drum-audition]] — stereo, loudness-matched A/B of a kit
- [[finalize-mix]] — bus glue/compression (different lever than transients)
- [[mix-check]] — diagnose first if the drums have tonal/phase problems
