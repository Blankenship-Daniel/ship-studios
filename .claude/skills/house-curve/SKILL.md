---
name: house-curve
description: Use when a whole EP/album needs ONE shared tonal target, or you want a reusable reference profile — "build a house curve from these references", "make all my tracks share the same tonal balance", "give the EP one consistent sound", "match every mix to this set of references", "create a target curve for the album", "save a tonal target I can reuse". Power-averages references into a versioned profile, then matches each mix to it. Pure DSP, no API key. Stemmy MCP.
argument-hint: <references...> -- <mixes-or-album-dir>
---

# House curve — one shared tonal target across a release

Goal: capture a **single** tonal target from a set of reference tracks and steer
every mix in an EP/album toward it, so the release is tonally consistent
instead of each track matching a different reference. `[L] build-target-profile`
power-averages the references' third-octave spectra (linear power, not dB-mean)
plus their loudness/dynamics/width into a versioned JSON; `[L] match-to-profile`
reports each mix's per-band delta vs that profile; `[L] match-eq` (or `apply-eq`)
renders the correction.

The overlap trap: `[[reference-match]]` matches **one** mix to **one** reference.
This is the **multi-track** version — build the target once, reuse it across the
set. It's the front-half companion to `[[batch-master]]` (which makes the set
*loudness*-consistent); house-curve makes it *tonally* consistent.

## Prerequisites

- `stemmy-loops` up. `build-target-profile` / `match-to-profile` / `match-eq` /
  `apply-eq` / `measure-*` are pure DSP, no key (`match-eq` needs `mixing`).
- One or more reference WAVs that represent the target sound, and the set of
  mixes to align (typically `projects/<album>/*/mix/`).

## Recipe (ordered — measure before/after)

1. **Build the profile** — `[L] build-target-profile {paths: [ref1, ref2, ...],
   out_json}` → one versioned house-curve JSON. Use a few references that agree
   on the sound; outliers smear the average.
2. **Per mix — measure the gap** — `[L] match-to-profile {path: mix,
   profile_json}` → per-band delta (input − target) + a suggested cut/boost per
   band. This is the "before" curve.
3. **Per mix — close it** — `[L] match-eq {source_path: mix, ... }` driven by
   the profile delta (tune `match_strength ≈ 0.5`, `phase` min/linear), or
   `apply-eq` for a few surgical bells if you'd rather stay light. Don't force
   the curve flat — partial correction keeps each track musical.
4. **Confirm convergence** — re-run `[L] match-to-profile` on each corrected mix;
   the per-band deltas should shrink toward zero and, crucially, the **spread
   across tracks** should tighten (that's the consistency win).
5. **Hand off** — send the tonally-aligned set to `[[batch-master]]` for one
   shared loudness target.

## Outputs

- The house-curve JSON (durable; keep it in `projects/<album>/`).
- Tonally-aligned mixes → each track's `mix/`.

## Reporting to the user

Lead with the **per-track before → after deltas vs the profile** and the
**cross-track spread** (how much more consistent the set is now). Note the
profile path so it's reusable, and point at `[[batch-master]]` for loudness.

## Pitfalls

- **Curated references only.** Averaging wildly different refs makes a muddy
  target. Pick refs that share the sound you want.
- **Don't over-correct.** `match_strength 1.0` can make every track identical
  and lifeless; ~0.5 keeps character while pulling toward the target.
- **Tonal ≠ loudness.** This aligns tone; loudness consistency is
  `[[batch-master]]` / `analyze-album-normalization`.
- **Profile is peak/shape-referenced.** It compares spectral *shape*, not
  absolute level — don't read the deltas as loudness.

## Related

- [[reference-match]] — single mix ↔ single reference (the per-track version)
- [[batch-master]] — the loudness-consistency companion for the same set
- [[release-package]] — assemble the consistent set for distribution
- [[level-match]] — gain-only match for honest A/B while you tune
