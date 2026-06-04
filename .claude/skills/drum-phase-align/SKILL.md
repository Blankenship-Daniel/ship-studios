---
name: drum-phase-align
description: Use when the user wants multi-mic drums time/phase-aligned — "phase-align the drum mics", "align my drums to the overheads", "fix drum phase", "the kick/snare mics are smearing", "get the close mics tight with the overheads". Aligns every close mic to the overheads (envelope-coarse → waveform refine, partner-pair topology, polarity auto-detect) via the local drum-prep CLI. Not the MCP servers.
argument-hint: <stems dir>
---

# Phase-align a multi-mic drum kit to the overheads

Goal: make all the drum mics phase-coherent so they sum without comb-filtering —
each close mic time-aligned (and polarity-corrected) to the overheads, which stay
fixed as the kit's timing/image anchor. The only way to make *all* mics mutually
coherent is to hold one signal fixed and snap the rest to it; the overheads are
that anchor because they already contain the kit's natural relative timing.

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/scipy/soundfile). No keys/network.
- A folder of drum-mic stems, same sample rate, with overheads present (stereo,
  or an L/R pair that gets merged automatically). Roles auto-detect from
  filenames; pin with a `kit.json` if needed.

## Recipe (ordered)

1. **Confirm roles** — `drum-prep detect "<stems dir>"`. Verify partner wiring
   (snare-bottom → snare-top, kick-beater → kick-in) and the overhead reference.
   A non-standard mic *name* (e.g. "Crotch Mic") detects as role **unknown** —
   identify it by **signal, not name** (a sub mic measures LF-dominant ~70 Hz =
   `kick_sub`), pin it in a `kit.json`, and pass `--manifest <kit.json>` to both
   `detect` and `phase-align`.
2. **Align** — `drum-prep phase-align "<stems dir>"`. Topology, derived from
   roles:
   - snare-top / hi-hat / toms / ride / crash → overheads (broadband)
   - kick mics → overheads via a low-pass correlation (`--kick-lowpass`, default
     180 Hz) so they lock the fundamental, not cymbal bleed
   - snare-bottom → snare-top, kick-beater → kick-in, then composed onto the OH
     timeline (polarity multiplies, delay adds)
   - room → polarity-checked only, **timing kept** (ambience preserved)
   - overheads → copied through unchanged
   Tuning: `--max-lag` (search window, default 600 samples), `--excerpt-s` (the
   loudest window used to estimate, default 40 s), `--out-dir`.

## Outputs

- `<dir>/phase-aligned/` — every stem aligned, length-preserved, 24-bit AIFF.
  The overhead is copied through; an L/R pair becomes `overheads-merged.aif`.

## Reporting to the user

Give the per-stem table: polarity (flip or +), applied delay (samples / ms / ≈
mic distance), and the pre→post correlation vs the reference. Lead with the
**partner-pair validation** correlations (snare-top↔bottom, kick-in↔beater) —
they must be positive (in phase) after alignment. Flag any polarity flips and any
mic whose delay is physically implausible.

## Pitfalls

- **Resonant snares can half-period-slip** under naive correlation — this flow
  avoids it (envelope-coarse delay, then waveform refine in a tight window). Don't
  "fix" a delay by hand without re-checking the partner-pair correlation.
- **Don't time-align the room** — its pre-delay is the ambience; only its polarity
  is checked.
- **Spaced overhead pairs**: merging keeps the L/R image (no inter-channel
  alignment) — correct for a spaced pair. `phase-align` has no `--align`; to
  phase-lock a *coincident* L/R pair, first run `drum-prep overheads <dir>
  --align` (writes `overheads-merged.aif`), then `phase-align`.

## Related

- [[drum-reference-match]] — the usual next step (tonal match the aligned kit)
- [[drum-prep]] — run align + match + audition end to end
- [[mix-check]] — MCP perceptual/measurement diagnosis of a finished mix
