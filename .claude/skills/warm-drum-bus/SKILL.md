---
name: warm-drum-bus
description: "Use when the user wants a WARM drum bus with a tight/controlled bottom end — 'warm drum bus', 'make the drums warm', 'my drum sound', 'warm and tight drums', 'controlled low end on the kit', 'tape-warm drum glue', 'warm up the drum bus'. The user's PREFERRED drum-bus recipe: measured warm balance → tilt EQ + low-band multiband control → Studer A800 30 IPS tape. Warmth from tape/tilt (NOT bright EQ); tight lows from HPF + low multiband + 30 IPS. Local DSP + the `vst` extra (Studer)."
argument-hint: <drum-bus.wav | stems-dir>
---

# warm-drum-bus — the user's warm, tight/controlled drum bus

Goal: turn a multi-mic drum kit (or a summed drum bus) into a **warm bus with a tight, controlled
bottom end** — the user's approved signature drum sound. The recipe is saved at
[`presets/mix/warm-tight-drum-bus.json`](../../../presets/mix/warm-tight-drum-bus.json); this skill drives it.

**The two governing principles (don't violate):**
- **Warmth = tape + tonal tilt, NEVER a bright EQ boost.** A high-shelf cut + low-mid lift + Studer tape
  darken musically; boosting the top to "add presence" reads as harsh to this user (see [[studer-a800]] /
  [[api-vision-channel-strip]]).
- **Tight/controlled bottom = HPF + low-band multiband + 30 IPS tape.** Use **30 IPS** (head bump up at
  ~100 Hz, no sub-bloom), NOT 15 IPS (its bigger ~60 Hz bump blooms the lows). The multiband evens the
  low band so the kick doesn't pump the bus.

**Local DSP + VST** — runs the stemmy-loops tools + the Studer A800 (`uaudio_studer_a800.vst3`) through the
stemmy-loops **`vst` venv** (`../stemmy-loops-mcp/.venv`). Not the MCP servers directly.

## Prerequisites

- `uv sync --extra vst` in `../stemmy-loops-mcp` (Pedalboard + the DSP tools); the UADx Studer build installed/authorized.
- A drum bus to warm, **or** a multi-mic kit to balance first. Best results from a **phase-aligned**,
  optionally **per-stem-processed** kit ([[stem-process]]). Resolve paths up front.
- Scripts: `scripts/mix/balance_stems.py`, `scripts/mix/warm_bus.py`. Recipe: `presets/mix/warm-tight-drum-bus.json`.

## Recipe (ordered)

1. **Warm balance** (if starting from stems) — `scripts/mix/balance_stems.py` with the preset's per-role
   targets: bright stems **down** (snare-bottom −32, hi-hat −28, kick-beater −26), body/room **up**
   (kick-in −16, snare-top −18, overhead −22, room −26); measured LUFS, one global −6 dBFS headroom trim.
   → `bus_warm_pre.wav`. (Already have a bus? skip to 2.)
2. **Warm/tight chain** — `scripts/mix/warm_bus.py <bus_warm_pre.wav> <bus_warm.wav>`. It applies, in order:
   HPF 35 + warm tilt (low-shelf +1.5 @ 180, bell −1.5 @ 2.5 k, high-shelf −4 @ 6 k, zero-phase) → multiband
   compressing the **<110 Hz** band (3:1, the controlled bottom) → **Studer A800 30 IPS / 456 / repro_hf_eq 2**
   tape (warmth + glue). Output peak −1 dBFS (mix bus, not mastered).
3. **Verify** — the script prints before→after. Confirm the **warm/tight signature**: centroid DOWN, tilt
   more negative (~−2.4 to −2.7), correlation UP (~0.96–0.97 = tight mono-solid lows), crest controlled
   (~21–23 = glued, not spiky). Write to `projects/<track>/mix/`.

## Outputs

- `projects/<track>/mix/bus_warm.wav` — the warm, tight drum bus (a **mix bus**, peak −1, NOT mastered).
- Hand to [[master-track]] for loudness/limiting/delivery.

## Reporting to the user

Give before→after centroid / tilt / crest / correlation, and state plainly it's warmed by tape+tilt (not
EQ brightening) with a 30 IPS / multiband-controlled bottom. A/B loudness-matched with `render-ab` so the
warmth isn't a loudness illusion.

## Pitfalls

- **Calibrate on a REPRESENTATIVE window, or verify full-length.** A chain tuned on a short bright excerpt
  over-darkens the whole track (we saw centroid 3990 on the opening 60 s → 2880 over the full 10.5 min,
  because the intro was brighter than the average). Measure the full render; if a brighter/darker source
  pushes it off, ease the high-shelf (−4 → −2 @ 6 k) and tape `repro_hf_eq` (2 → 3), or push them for more warmth.
- **Never warm with a bright EQ boost** — it's the opposite of the goal and reads harsh to this user.
- **Don't use 15 IPS for "more warmth"** — its low-end head bump blooms the bottom; 30 IPS keeps lows tight.
  More warmth → ease the HF / drive the tape a touch, not a lower IPS.
- **It's a MIX bus, not a master** — peak −1, no limiting. Loudness is [[master-track]]'s job.
- **Watch the crest** — if it collapses below ~20, back off the multiband ratio / tape drive (it's getting
  over-glued, losing life).

## Related

- [[stem-process]] — the per-stem corrective + color stage that feeds this (best source for the bus)
- [[studer-a800]] — the tape engine here (why 30 IPS = tight + warm) · [[mix-balance]] — the measured balance method
- [[drum-mix]] — the role-aware kit sum · [[finalize-mix]] — the generic bus-glue stage · [[master-track]] — loudness after this
- `warm-bus-shootout` (workflow) — A/B/C several tuning variants (e.g. default vs `--hs-gain -2 --repro-hf 3`) through a warmth/tightness/life judge panel
- Recipe + preference: `presets/mix/warm-tight-drum-bus.json`
