---
name: unmask-stems
description: Use when stems are fighting in the same frequency range — "the kick and bass are masking", "vocal gets buried by the guitars", "carve space between my stems", "fix the frequency clashes", "unmask the mix", "make room for the lead". Scores cross-stem masking, applies complementary EQ cuts to the LOSING stem of each collision, then re-scores to prove the overlap shrank. The corrective-only sibling of [[stem-master]] — no summing, no mastering. Pure DSP, no API key.
argument-hint: <stems-dir-or-map>
---

# Unmask stems — resolve frequency collisions between stems

Goal: take a set of named stems that are masking each other and carve them
apart with surgical, *complementary* EQ. The unique value is closing a loop
nothing else in the ecosystem closes: `analyze-stem-masking` uniquely returns
the **center Hz + cut dB + Q + which stem to cut** for each collision, but no
skill or pipeline feeds that prescription into `apply-eq`. This does.

This is **corrective only** — it returns carved stems, it does not sum or
master them. For the full per-stem correct → sum → hand-to-master workflow,
use [[stem-master]]; this is the lighter standalone carve.

## Prerequisites

- Both `stemmy-loops` and `stemmy-gemini` registered and up.
- `[G] analyze-stem-masking` and `[G] measure-spectrum` are **pure DSP** —
  no `GEMINI_API_KEY`. `[L] apply-eq` / `[L] detect-masking` are core DSP,
  no key.
- Input is a **map of named stems** (`{kick: ..., bass: ..., vox: ...}`),
  not a stereo bounce. Resolve the stem paths up front.
- Optional audible A/B only: `drum-prep stem-mix` is the **local** drum-prep
  CLI (`uv sync --extra drum-prep`), not an MCP tool — no MCP tool sums an
  arbitrary stem set.

## Recipe (ordered)

1. **Score collisions** — `[G] analyze-stem-masking {stems}`. Returns ranked
   conflicts: dominant stem, stem-to-cut, center Hz, cut dB, suggested Q.
   This is the prescription the whole skill acts on.
2. **(Optional) cross-check** — `[L] detect-masking` on the suspect
   stem/loop pairs. It scores per-band *overlap only* (no cut prescription),
   so use it to confirm the worst collisions, not to decide the move.
3. **Cut the loser** — `[L] apply-eq` on each stem-to-cut, one call per stem,
   with a bell at the prescribed center Hz / cut dB / Q. **Boost nothing** —
   masking is resolved by cutting the loser, not boosting the winner.
4. **Prove it** — re-run `[G] analyze-stem-masking` + `[L] measure-spectrum`
   on the corrected stems. Confirm the overlap dropped *and* the cut didn't
   hollow out the stem (spectrum sanity).
5. **(Optional) audition** — `drum-prep stem-mix <dir>` to sum before/after
   for an ear check. Local DSP; skip if you only need the carved stems.

## Outputs

- Carved stems → `projects/<track>/stems/unmasked/`.
- Headline deliverable is the **before → after overlap table**; the corrected
  stems are the follow-through.

## Reporting to the user

One row per collision: the stem pair, the colliding frequency, **which stem
was cut**, the dB + Q, and the before → after overlap score. Confirm no stem
was gutted. If you summed an A/B, give its path.

## Pitfalls

- **No MCP tool sums a stem set.** Don't reach for `render-ab` to A/B a
  "summed mix" — the proof is the re-scored masking + spectrum, or a local
  `drum-prep stem-mix` audition.
- **`apply-eq` is single-file.** One call per losing stem, never a batch.
- **`detect-masking` only scores overlap** — the cut prescription (Hz/dB/Q)
  comes from `analyze-stem-masking`.
- **Cut, don't boost.** Carve the loser; piling gain on the winner just
  re-creates the collision louder.

## Related

- [[stem-master]] — the full per-stem correct → sum → master workflow this feeds
- [[mix-check]] — single-bounce diagnosis when you don't have stems
- [[song-mix]] — balance the carved stems to a bus
- [[drum-reference-match]] — tonal-match a kit rather than carve collisions
