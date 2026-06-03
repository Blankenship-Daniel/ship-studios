---
name: groove-tighten
description: Use when a loop's timing is loose — "tighten the timing", "quantize this loop to the grid", "make it exactly 4 bars", "snap the groove", "the loop drifts / doesn't line up", "fix the timing on this loop". Quantizes onsets to the BPM grid (groove) or stretches to exact bars (length), then re-runs optimize-seam because quantizing shifts onsets and breaks the wrap point, and QCs. Wraps the otherwise-unwrapped quantize-loop. BPM is REQUIRED — read it from track.md, never guess.
argument-hint: <loop.wav> [bpm] [bars]
---

# Groove-tighten — quantize a loop, then re-fix the seam

Goal: tighten a loose loop's timing — either snap its onsets to the BPM grid
(`groove` mode) or time-stretch it to an exact bar count (`length` mode) —
without shipping a clicking loop. The load-bearing, easy-to-miss step: after
quantizing you **must** re-run `optimize-seam`, because moving onsets shifts
the loop's wrap point and the old seam no longer lines up.

This wraps `quantize-loop`, which has no other skill coverage and several
non-obvious gotchas (modes, required BPM, the `quantize` extra) — exactly the
guardrails a skill should encode.

## Prerequisites

- `stemmy-loops` registered and up. All tools here are `[L]`, pure DSP, no
  API key.
- **`quantize-loop` needs the `quantize` extra** (`uv sync --extra quantize`).
  (`midi` mode would also need `--extra classify`, but this skill's chain
  doesn't use it.)
- **BPM is REQUIRED.** Read it from `projects/<track>/track.md` or the loop
  manifest. **Never guess** — a wrong BPM quantizes to the wrong grid.
- `optimize-seam` / `inspect-loop` are core DSP.

## Recipe (ordered)

1. **Resolve BPM + mode** — read BPM from `track.md` / manifest (ask if
   absent; never guess). Choose the mode: `groove` (snap onsets to the grid)
   or `length` (stretch to an exact bar count — requires `bars`).
2. **Quantize** — `[L] quantize-loop {path, out_path, mode, bpm, [bars]}` →
   timing-corrected loop.
3. **Re-fix the seam** — `[L] optimize-seam` on the quantized loop. This is
   the non-obvious must-do: quantizing shifts onsets, so the previous wrap
   point is now wrong; skipping this ships a loop that clicks at the loop
   boundary.
4. **QC** — `[L] inspect-loop` → deliverability check (seam continuity,
   length, peak) on the result.
5. **A/B** — `[L] render-ab {processed: <tightened>, reference: <original>}`
   so the timing change is audible against the original. (Mono — fine for a
   timing A/B.)

## Outputs

- Tightened loop → `projects/<track>/loops/` (or `artifacts/<run>/` for
  scratch).
- The A/B WAV alongside it.

## Reporting to the user

State the mode used and the BPM (and `bars` if `length`), the `optimize-seam`
result, the `inspect-loop` verdict, and the A/B path. Note that the timing
moved while the loop's character was preserved.

## Pitfalls

- **BPM required, never guessed** — read `track.md` / manifest or ask.
- **Always re-seam after quantizing** — onset shifts break the wrap point;
  skipping `optimize-seam` = a clicking loop.
- **`length` mode needs `bars`** — without it the stretch target is undefined.
- **Needs the `quantize` extra installed** — flag this prerequisite if the
  tool errors.
- **`render-ab` is mono** — fine for a timing check, not a stereo audition.

## Related

- [[loops-to-deliverables]] — clean → seam → master → tag → export a loop set
- [[sample-pack]] — assemble tightened loops into a sellable pack
- [[drum-audition]] — stereo loudness-matched A/B when you need it
