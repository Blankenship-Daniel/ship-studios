---
name: drum-reference-match
description: Use when the user wants a multi-mic drum kit's tone matched to a reference, per stem — "make my drums sound like this reference", "match the kit tone to this loop", "EQ each drum stem to the reference", "get that vintage drum sound on my kit". Measures the coherent kit sum, builds one corrective curve toward the reference, and distributes it per-stem (cuts to all, boosts to band owners) with zero-phase EQ. Local drum-prep CLI, not the MCP servers.
---

# Reference-match a drum kit's tonal balance, per stem

Goal: shape a multi-mic kit so its **summed** tone matches a reference, by EQ'ing
each stem in the band it owns — without disturbing the phase alignment. You can't
match each stem to a full-mix reference's whole spectrum (a kick stem shouldn't
chase the reference's hi-hats); instead match the *kit sum* and distribute the
correction by band ownership.

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.
This is the multi-mic, per-stem cousin of the MCP [[reference-match]] skill, which
matches a single finished stereo *mix*.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/scipy/soundfile). No keys/network.
- A **phase-aligned** stem set (run [[drum-phase-align]] first; the flow reads
  `<dir>/phase-aligned/` by default).
- A reference file (loop or track), kept outside the stems folder.

## Recipe (ordered)

1. **Read the gap (optional, read-only)** — `drum-prep analyze "<dir>"
   --reference "<ref>"`. Reports the reference vs kit 6-band tonal delta, tilt,
   and which stem owns each band. Nothing is written.
2. **Apply the match** — `drum-prep reference-match "<dir>" --reference "<ref>"`.
   - Measures the kit as the **coherent time-domain sum** of the aligned stems
     (what they sum to in a DAW — a power-sum would undercount the correlated
     kick lows and over-boost them).
   - Builds one corrective 1/3-octave curve = `strength × (reference − kit)`,
     smoothed and capped.
   - **Cuts → every stem** (uniform = exact bus darkening, harmless where silent);
     **boosts → only the band's owner(s)** (so the kick's lows get fattened without
     amplifying bleed/rumble elsewhere), nothing below ~30 Hz.
   - **Zero-phase EQ** (real, symmetric gain) → the phase alignment is untouched.
   - One **global** headroom trim keeps inter-stem balance and prevents clipping.
   Knobs: `--strength` (default 0.75; lower = subtler, 1.0 = full), `--boost-cap`,
   `--cut-cap`, `--owner-thresh`, `--low-zero`, `--ceil-dbfs`, `--out-dir`.

## Outputs

- `<dir>/ref-matched/` — the aligned stems, per-stem EQ'd, 24-bit AIFF, peak ≤ −1 dBFS.

## Reporting to the user

Give the per-stem EQ moves (6-band) and the headline **residual before→after**
(reference − kit) per band plus the kit tilt move toward the reference's. State
the global trim applied. Flag any band intentionally left short (e.g. capped air,
un-chased sub-30 Hz) and why. Note this is a partial match at the chosen strength.

**Fold in the `notes` array** from the `apply_match` result — it diagnoses
stubborn residuals so you can tell the user *why* a band wouldn't close and what
to do next:

- **A LOW band (sub 20–60 / low 60–120) still ≥ 2.5 dB short** = an
  **extension/sustain gap, not a level gap.** The close mics lack genuine
  fundamental, so more EQ won't help (you'd just boost what isn't there).
  Recommend a **sub-harmonic generator or saturation at the MIX stage** to
  synthesize the missing low end.
- **A non-low band still short** = a level gap EQ *can* close: raise
  `--strength` (or, if the owner boost is capped, raise `--boost-cap`) and re-run.

## Pitfalls

- **Match strength is a taste call.** Fully matching a steep-rolloff vintage loop
  darkens hard; 0.5–0.75 is usually the sweet spot. Audition before committing.
- **Run phase-align first.** Matching un-aligned stems bakes comb-filtering into
  the curve.
- **The kit sum is a flat unity sum**, close-mic-heavy — it's a tonal proxy, not
  your final balance. The per-stem EQ is balance-independent tone shaping.
- **A residual that won't close on the sub is sustain, not level — don't chase it
  with EQ.** If a low band stays ≥ 2.5 dB short (see the `notes` array), the close
  mics simply don't contain that fundamental; cranking `--strength`/`--boost-cap`
  just amplifies noise. Synthesize it later with a sub-harmonic generator or
  saturation at the mix stage.

## Related

- [[drum-audition]] — render a loudness-matched before/after to judge the match
- [[drum-phase-align]] — run first
- [[drum-prep]] — the full chain
- [[reference-match]] — MCP analogue for a finished stereo mix
