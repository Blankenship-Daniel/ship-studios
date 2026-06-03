---
name: dynamic-eq
description: Use when a frequency problem is LEVEL-DEPENDENT, not constant — "carve the mud only when the kick hits", "tame 3 kHz only on loud phrases", "the low-mids build up only on the chorus", "de-boom the bass only on the loud notes", "fill the sub only when it dips". Threshold-gated per-band EQ that fires by the band's own level (cut above / boost below). Pure DSP, no API key. Stemmy MCP.
argument-hint: <mix-or-stem.wav>
---

# Dynamic EQ — threshold-gated, level-dependent per-band carving

Goal: fix a frequency problem that only shows up at certain levels, without
cutting when it isn't there. `[L] apply-dynamic-eq` runs a fixed bandpass per
band and changes that band's gain only when its own level crosses a threshold —
`cut` ducks the band when it rises **above** threshold (de-mud only when the
kick hits), `boost` fills the band when it falls **below** threshold (hold up a
sub that dips). Difference-signal method, so it's dynamic without zipper noise.

The overlap traps: a **static** tonal problem (always too much 200 Hz) is plain
`apply-eq` ([[mix-check]]); a **ringing/harsh** resonance is `[[de-harsh]]`;
**sibilance** is `[[de-ess]]`; **broadband density** is `[[multiband-compress]]`.
This is specifically *level-dependent* EQ.

## Prerequisites

- `stemmy-loops` up. `[L] apply-dynamic-eq` / `measure-*` are pure DSP, no key.
- Input is **one stereo WAV** (mix, bus, or stem) — not loop-only despite the
  schema wording.
- Know the *trigger*: which band, and whether the problem appears when that band
  gets **loud** (use `cut`) or when it **dips** (use `boost`).

> **Caveat (per CLAUDE.md):** `apply-dynamic-eq` is time-varying DSP that is
> currently **unit-tested only** — ear-check on real material before a release.

## Recipe (ordered — measure before/after)

1. **Baseline** — `[L] measure-spectrum {path}` + `[L] measure-loudness {path}`.
   Identify the offending band and confirm the problem is level-linked (compare
   loud vs quiet sections, or use `[G] critique-region` on a loud window).
2. **Dynamic carve** — `[L] apply-dynamic-eq {path, out_path, bands: [{freq_hz,
   q, threshold_dbfs, ratio, range_db, attack_ms, release_ms, mode}]}`.
   `range_db` clamps the max gain change; `cut` for build-ups, `boost` to fill
   dips. Start one band, modest `range_db` (≈6), `threshold_dbfs` near the
   level where the problem appears.
3. **Confirm** — read back per-band max applied gain change, then re-run
   `[L] measure-spectrum` + `[L] measure-loudness`. The static tonal balance
   should be largely unchanged at quiet passages and only move where the trigger
   fires.

## Outputs

- Dynamic-EQ'd file → `projects/<track>/mix/`.

## Reporting to the user

Lead with the **per-band max applied gain change** and *when* it fired (the
level-dependent point). State the band(s), mode (cut/boost), threshold, and
range. Confirm the steady-state tone barely moved — that's the whole reason to
use dynamic over static EQ.

## Pitfalls

- **Don't reach for this for static problems.** If the band is always wrong, a
  plain `apply-eq` cut ([[mix-check]]) is simpler and cleaner.
- **Set the threshold to the trigger.** Too low and it acts like a static cut;
  too high and it never fires.
- **One band at a time.** Stack carefully — multiple aggressive bands interact.
- **Unit-tested only — ear-check.** A/B loudness-matched with `[[level-match]]`.

## Related

- [[unmask-stems]] — static complementary cuts between stems
- [[de-harsh]] — ring/harshness suppression (not threshold-gated by band level)
- [[de-ess]] — the sibilant band specifically
- [[mix-check]] — diagnose first; it flags when a problem is level-dependent
