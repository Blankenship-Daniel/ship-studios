---
name: bleed-gate
description: "Use when a close mic carries too much of another instrument — 'too much hi-hat in the overheads / snare mic', 'reduce the bleed/spill', 'gate the snare mic', 'cancel the hi-hat out of the overheads', 'the close mic has too much spill'. Reduces mic bleed two ways: gate a close mic between its hits, or least-squares cancel a correlated source out of a target. Do this BEFORE balancing — turning a mic up turns its bleed up too. Local DSP."
---

# bleed-gate — reduce mic bleed before mixing

Goal: cut the spill of one instrument into another mic, so you can raise that mic in the balance
without dragging the bleed up with it. Two techniques, both via `scripts/mix/debleed.py`.

## Prerequisites

- `scripts/mix/debleed.py` run with the stemmy-loops venv (soundfile + numpy). For **cancel**, the bleed
  reference must be **time-aligned** to the target (run `[[drum-phase-align]]` first).

## Recipe

1. **Diagnose** — which mic carries the bleed and how much? Correlate the target mic with the offending
   source, or `[L] measure-spectrum`. (e.g. overhead↔hi-hat correlation, snare-top↔hi-hat.)
2. **Pick the technique:**
   - **Gate** a close mic that should only sound on its own hits (snare-top full of hat spill):
     ```bash
     ../stemmy-loops-mcp/.venv/bin/python scripts/mix/debleed.py gate "<snare top.wav>" "<out.wav>" -14 50
     ```
     Attenuates between hits (floor −14 dB), keeping every hit. It reports the % closed.
   - **Cancel** a correlated source you have isolated (null the hi-hat from the overheads — keeps the
     cymbals, which aren't in the hat mic):
     ```bash
     ../stemmy-loops-mcp/.venv/bin/python scripts/mix/debleed.py cancel "<overhead.wav>" "<hi hat.wav>" "<out.wav>" 0.55
     ```
     Least-squares subtracts the scaled, aligned reference per channel; it reports target↔ref correlation
     before → after. Keep `amount` < ~0.7 to stay natural (a hard null can sound thin/phasey).
3. **Verify** — correlation/spectrum dropped in the bleed region without wrecking the wanted content.
4. **Then balance** — feed the de-bled stems to `[[mix-balance]]`.

## Outputs

- Cleaned stem(s) in `projects/<track>/mix/` (or a working dir), ready for `[[mix-balance]]`.

## Reporting to the user

- Which mic + technique, the % gated or the correlation drop (e.g. overhead↔hat 0.65 → 0.30), and the trade-off.

## Pitfalls

- **Cancel needs a time-aligned, isolated reference** — phase-align first; otherwise it won't cancel (or combs).
- **Don't over-do it** — full null (`amount` ~1) thins/phases the target; gate floor too low chokes the mic. Moderate wins.
- **Bleed shares frequency space** (hat ≈ cymbals/snare-crack) — perfect separation is impossible; reduce, don't expect removal.
- Often the simplest fix is **just lower the carrier** (e.g. the overhead) in `[[mix-balance]]` — try balance first.

## Related

- `[[mix-balance]]` — do this before balancing · `[[drum-phase-align]]` — align stems first (required for cancel)
- `[[drum-mix]]` / `[[unmask-stems]]` — kit mix / frequency-collision sibling
