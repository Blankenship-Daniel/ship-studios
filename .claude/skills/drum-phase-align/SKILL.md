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
     180 Hz) so they lock the fundamental, not cymbal bleed. A **non-standard
     low-frequency mic** (a "crotch mic" between the knees, a sub-kick pickup)
     won't auto-detect — pin it in `kit.json` as `kick_sub` so it routes through
     this same low-pass topology instead of a broadband lock it can't support.
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


- **A mixed-sample-rate kit now RAISES — convert upstream first.** Every stem is
  written back out at the *overhead's* rate, so an off-rate stem used to be
  silently reinterpreted: a 44.1k room mic in a 48k kit came out pitched **+8.8%**
  with an empty `warnings` list, and because every later stage then saw a uniform
  set it passed *their* sample-rate checks too — the corruption was laundered
  through the whole chain. The flow now header-checks every stem it touches and
  fails before writing anything. Resample the odd stem, then re-run.
- **A delay outside `--max-lag` is DETECTED, not applied — read the warning.** The
  railed answer is *not* pinned at the rail: a true 880-sample offset searched at
  `--max-lag 600` returned **-541 with the polarity flipped**, so the mic would
  have partially *cancelled* the overheads. When `post_corr` is low the flow now
  re-searches wider and, if the true peak lies outside your window, **skips** that
  mic and names the `--max-lag` to re-run with. A skipped mic is unaligned, not
  aligned — re-run with the suggested value rather than shipping it. (This is the
  fixed inter-converter offset in the Field notes.)
- **`--out-dir` may not be the source dir.** It's refused now: this flow writes a
  fresh 24-bit AIFF set, so pointing it at the stems folder replaced the raw
  WAV/PCM_16 multitrack in place, under the same names, with no prompt.
- **Align on FULL-BAND signals — phase-align BEFORE corrective EQ.** The delays
  are physical mic distances; estimate them from the unprocessed stems. In
  particular, if the overheads have already been **high-passed** (a common
  corrective move), there's no low end left for the kick (LP180) to correlate
  against → a bogus lock (seen: a 971-sample / 20 ms "delay", post_corr 0.05).
  If you've already EQ'd, derive the delays from the **full-band originals** (a
  temp dir + `kit.json`) and apply them to the processed stems: a pure time-shift
  **commutes** with zero-phase EQ and gating (all LTI), so aligning the processed
  stems is identical (in the interior) to aligning first. The clean order is
  **align → then EQ/HPF/gate the aligned output**.
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
