---
name: de-ess
description: Use when sibilance ("ess"/"sh"/"t") is harsh on a vocal, lead, or bright bus — "de-ess the vocal", "the esses are spitty/harsh", "tame the sibilance", "too much 's' on the lead", "the hi-hat/cymbals are spitting". Finds the sibilant band with find-sibilance, then ducks ONLY that band with the native split-band de-ess (no plugin), proven by the 4–9 kHz band-energy delta. Pure DSP for the render; find-sibilance is Gemini. Stemmy MCP.
argument-hint: <vocal-or-bus.wav>
---

# De-ess — measured split-band sibilance control

Goal: tame harsh sibilance on a stereo file (vocal, lead, or a spitty bright
bus) by ducking **only** the sibilant band when it trips — not the whole top
end. The discipline: let `[G] find-sibilance` *locate* the band and propose the
settings, drive `[L] de-ess` with exactly those numbers, then prove the 4–9 kHz
band energy dropped while the rest of the spectrum stayed intact.

`[L] de-ess` is the **native, deterministic, no-key** de-esser. It's distinct
from `[[vst-de-ess]]` (your own plugin, non-deterministic) — reach for this
unless the user specifically wants a plugin. It is also not a high-shelf cut
(`apply-eq`): a shelf is always-on and dulls every word; this ducks the band
*only when sibilance trips* the detector.

## Prerequisites

- `stemmy-loops` up. `[L] de-ess` / `measure-spectrum` are pure DSP, no key.
- `[G] find-sibilance` needs `GEMINI_API_KEY` (it listens). If no key, skip it
  and dial `de-ess` by hand from `measure-spectrum` (sibilance usually lives
  5–9 kHz; start `center_hz 6500`, `q 2`).
- Input is **one stereo WAV** — a vocal/lead stem or a bus. Despite the schema
  wording, `de-ess` is not loop-only; it works on any stereo file.

## Recipe (ordered — measure before/after)

1. **Baseline** — `[L] measure-spectrum {path}`. Note the 4–9 kHz region; this
   is the "before" column the de-ess delta is judged against.
2. **Locate the band** — `[G] find-sibilance {path}` → returns `center_hz`,
   `q`, `threshold_dbfs`, `reduction_db` (and timestamps/severity). These feed
   the renderer 1:1.
3. **Duck the band** — `[L] de-ess {path, out_path, center_hz, q,
   threshold_dbfs, reduction_db, mode: "split"}`. `split` (default) ducks only
   the sibilant band and recombines; use `wide` only if you want the whole
   signal to duck when the band trips (rare). `reduction_db` is a GR **ceiling**,
   not makeup — start at the `find-sibilance` value (typically 4–8 dB).
4. **Confirm** — read back the reported 4–9 kHz band-energy delta + peak GR,
   then re-run `[L] measure-spectrum` and `[L] measure-loudness`. The sibilant
   band should drop; overall loudness/tilt should barely move (you tamed esses,
   not the whole top).

## Outputs

- De-essed file → `projects/<track>/mix/`.

## Reporting to the user

Lead with the **4–9 kHz band-energy delta** and the **peak GR applied** (the
proof you ducked sibilance, not the whole top). State the band that was treated
(`center_hz`/`q`) and the threshold, and confirm overall loudness/tilt held.

## Pitfalls

- **Don't over-duck.** Too much `reduction_db` lisps the vocal. If consonants
  go soft, lower `reduction_db` or raise `threshold_dbfs`.
- **`split`, not `wide`, by default.** `wide` pumps the whole signal on every
  "s" — only use it deliberately.
- **A balance/tone problem isn't sibilance.** If the whole top is harsh (not
  just esses), that's `[[de-harsh]]` (resonance suppression) or an EQ tilt, not
  de-essing.
- **Hi-hat "spit" may be a balance issue.** A too-loud overhead carrying the hat
  reads as sibilant — check levels with `[[mix-balance]]` first.

## Related

- [[mix-check]] — diagnoses sibilance (find-sibilance) as part of the full read
- [[de-harsh]] — broadband harshness/ringing (not just the sibilant band)
- [[vst-de-ess]] — the plugin form, when you want your own de-esser
- [[stem-master]] — de-ess offending stems before summing
