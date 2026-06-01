---
name: multiband-compress
description: Use when different frequency bands need different dynamics control — "compress the lows and highs separately", "the kick is uneven but the cymbals are fine", "control the boomy bass without squashing the top", "even out the low end only", "multiband compress this", "the bass jumps around in the mix". Splits into LR4 bands and compresses each independently, proven by per-band gain reduction + crest. Pure DSP, no API key. Stemmy MCP.
---

# Multiband compression — per-band dynamics, measured

Goal: control dynamics independently per frequency band — tame a boomy/uneven
low end without squashing the cymbals, glue the mids, or rein in a jumpy bass —
using `[L] multiband-compress` (LR4 crossovers, an independent stereo-linked
downward compressor per band, bands sum back flat). Prove it with per-band GR
and crest: density rose where you wanted it, not everywhere.

The overlap traps: this is per-band **level** control. It is NOT `shape-bands`
(per-band *transient* design → punch; `[[drum-punch]]`), NOT `compress-loop`
(a single broadband compressor; `[[finalize-mix]]`'s glue step), and NOT
`apply-eq` (static tone). Reach for it specifically when one band's dynamics
misbehave while another band's are fine.

## Prerequisites

- `stemmy-loops` up. `[L] multiband-compress` / `measure-*` are pure DSP, no key.
- Input is **one stereo WAV** (mix, bus, or stem) — not loop-only despite the
  schema wording.
- Decide the crossovers and which band(s) actually need control before you
  reach for 3 aggressive bands.

## Recipe (ordered — measure before/after)

1. **Baseline** — `[L] measure-loudness {path}` (crest / PLR) + `[L]
   measure-spectrum {path}`. Identify which band is uneven (e.g. low end jumps,
   mids honk on peaks).
2. **Multiband compress** — `[L] multiband-compress {path, out_path,
   crossovers_hz: [120, 2000], threshold_db: [...], ratio: [...], attack_ms,
   release_ms, makeup_db}`. All per-band arrays are length N+1 (N crossovers →
   N+1 bands). Compress only the misbehaving band(s); leave the others near
   `ratio 1.0`. Start gentle (ratio ≈ 2–3, a few dB GR).
3. **Confirm** — read back per-band max/avg GR, then re-run `[L]
   measure-loudness` + `[L] measure-spectrum`. The target band should be more
   even (its dynamics tightened) without the overall crest collapsing.

## Outputs

- Multiband-compressed file → `projects/<track>/mix/`.

## Reporting to the user

Lead with **per-band gain reduction** (avg/max) and the **crest before → after**.
State the crossovers and which bands you actually compressed (and which you left
alone). Confirm you tightened the problem band without over-squashing the whole
file.

## Pitfalls

- **Don't compress every band.** Leave well-behaved bands at `ratio 1.0` — over
  every band kills life and flattens the mix.
- **Watch total crest.** If overall crest collapses you over-did it; back off
  ratios / makeup.
- **Array lengths must be N+1.** N crossovers → N+1 bands; each per-band array
  (threshold/ratio/attack/release/makeup) must match.
- **Punch ≠ density.** If the goal is attack/snap, that's `[[drum-punch]]`
  (transient design), not multiband compression.

## Related

- [[drum-punch]] — per-band transient design (punch), the sibling lever
- [[finalize-mix]] — single-band bus glue compression
- [[vst-compress]] — the plugin form (incl. multiband plugins)
- [[mix-check]] — diagnose which band's dynamics are the problem
