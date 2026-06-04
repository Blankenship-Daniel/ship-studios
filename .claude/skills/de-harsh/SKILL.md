---
name: de-harsh
description: Use when a mix/stem rings or sounds harsh/brittle/fatiguing — "tame the harshness", "it's brittle/edgy/abrasive", "Soothe this", "there's a ringing resonance", "the 3–5 kHz is fatiguing", "smooth out the top without dulling it". Soothe-STYLE dynamic resonance suppressor: ducks narrow peaks ONLY when they ring above the spectral envelope, leaving broadband tone intact. Pure DSP; find-resonances (optional) is also pure DSP (no key). Stemmy MCP.
argument-hint: <mix-or-stem.wav>
---

# De-harsh — Soothe-style dynamic resonance / harshness suppression

Goal: smooth harsh, ringing, or fatiguing material by attenuating narrow
spectral resonances **only when they spike above** a smooth median spectral
envelope — so the broadband tone survives and you don't just dull the whole
track. Optionally lean the sensitivity into the 2–10 kHz harshness region.
Prove it by reporting the mean/max attenuation actually applied and confirming
the overall spectrum/loudness held.

This is `[L] suppress-resonances` — dynamic and ring-targeted. It's distinct
from a static `apply-eq` notch (always-on, fixed depth → over-cuts when the
resonance isn't ringing) and from `[[de-ess]]` (the sibilant band only, not
broadband harshness). For *level-dependent* problems (mud only when the kick
hits) use `[[dynamic-eq]]` instead.

> **Caveat (per CLAUDE.md):** `suppress-resonances` is time-varying DSP that is
> currently **unit-tested only** — ear-check the result on real material (and
> A/B with `[[level-match]]`) before trusting it on a release.

## Prerequisites

- `stemmy-loops` up. `[L] suppress-resonances` / `measure-spectrum` are pure
  DSP, no key.
- `[G] find-resonances` (optional, to pinpoint peaks first) is **pure DSP — no
  `GEMINI_API_KEY`** (it lives on the stemmy-gemini server but makes no model call).
- Input is **one stereo WAV** (mix, bus, or stem) — works on any stereo file,
  not just loops.

## Recipe (ordered — measure before/after)

1. **Baseline** — `[L] measure-spectrum {path}` (note the 2–10 kHz region) +
   `[L] measure-loudness {path}`. Optional `[G] find-resonances {path}` to get
   exact peak frequencies — useful for setting `focus_band`.
2. **Suppress** — `[L] suppress-resonances {path, out_path, depth: 0.5,
   selectivity: 0.5, sensitivity_tilt: 0.4, max_reduction_db: 6}`. For broadband
   harshness lean `sensitivity_tilt` positive (biases 2–10 kHz). Raise
   `selectivity` to treat only sharp isolated peaks; lower it to also catch
   broader humps. Restrict with `focus_band:[lo,hi]` when the problem is
   confined (e.g. `[2000, 8000]`).
3. **Confirm** — read back the reported mean/max attenuation, then re-run
   `[L] measure-spectrum` + `[L] measure-loudness`. The harsh region should ease
   while broadband energy/tilt and loudness stay close.

## Outputs

- De-harshed file → `projects/<track>/mix/`.

## Reporting to the user

Lead with the **mean and max attenuation applied** and the spectrum delta in
the harsh region (before → after). Confirm broadband tone/loudness held — the
point is it smoothed without dulling. Note it's the unit-tested-only tool, so
the A/B is the real test.

## Pitfalls

- **Start gentle.** `depth 0.5` + `max_reduction_db 6` is plenty; pushing both
  high dulls the track and creates a lifeless top.
- **Ring-only, not level-dependent.** If the problem is "harsh only on loud
  parts" or "mud only when the kick hits", that's `[[dynamic-eq]]`.
- **Sibilance ≠ harshness.** Spitty esses are `[[de-ess]]`.
- **Ear-check it.** This tool is unit-tested only — never ship the render
  unheard; A/B loudness-matched with `[[level-match]]`.

## Related

- [[de-ess]] — the sibilant band specifically
- [[dynamic-eq]] — level-dependent (threshold-gated) carving
- [[mix-check]] — find-resonances + the full diagnostic read
- [[excite]] — the opposite move (add air) when something's dull, not harsh
- [[fabfilter-pro-q-4]] — the in-the-box (VST) soothe twin (Spectral Dynamics); Pedalboard auto-compensates its spectral band's linear-phase latency (net 0 samples in→out), so soothed stems stay sample-aligned — safe to soothe **per-stem before summing**
