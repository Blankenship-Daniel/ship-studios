---
description: Warm, tight/controlled drum bus (the user's preferred sound) — tape + tilt, 30 IPS.
argument-hint: <drum-bus.wav | stems-dir>
---

Invoke the **warm-drum-bus** skill on `$ARGUMENTS`.

`$1` is either a summed drum bus or a stems dir (if stems, balance first with the warm targets). Applies the
user's PREFERRED warm/tight recipe ([`presets/mix/warm-tight-drum-bus.json`](../../presets/mix/warm-tight-drum-bus.json)):
measured warm balance (bright stems down, body/room up) → `scripts/mix/warm_bus.py` (HPF 35 + warm tilt →
low-band multiband control → **Studer A800 30 IPS** tape). **Warmth = tape + tilt, never a bright EQ boost;
tight lows = HPF + low multiband + 30 IPS (not 15 IPS).** Verify the signature (centroid down, tilt ~−2.4
to −2.7, correlation ~0.96–0.97, crest ~21–23) and A/B loudness-matched. Needs `uv sync --extra vst`. It's a
**mix bus** (peak −1, not mastered) → hand to [[master-track]]. Calibrate on a representative window / verify
full-length (a bright excerpt over-darkens the whole track). Defer to the skill; report before→after + the path.
