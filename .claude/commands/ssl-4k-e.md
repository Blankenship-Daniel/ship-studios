---
description: Dial the SSL 4K E channel strip (SL 4000 E) for clean, weighty drums/bus — measured.
argument-hint: <audio.wav> [goal: drum-bus/glue/kick/snare/air]
---

Invoke the **ssl-4k-e** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (drum-bus weight+punch / bus glue / kick / snare / air). The SSL
4K E is SSL's **SL 4000 E** console channel — the **clean/weighty/controlled** British counterpart to API
forwardness ([[api-vision-channel-strip]]/[[kit-bb-a5]]) and Neve/tape warmth ([[studer-a800]]/[[kit-bb-n105]]).

Key facts (measured): **EQ COLOUR is the signature lever** — **'02 Brown'** brightest/airy, **'242 Black'**
fattest lows ("legendary low-end weight"), **'132 Orange'** (passive) most forward 2.5–5 kHz (kick/snare);
pick the colour, then dial. **The comp's FAST button is the punch lever and it's the OPPOSITE of the API
strip** — FAST **out** (slow) = crest UP (punch), FAST **in** (~1 ms grabby VCA) = denser/tamer; measure
crest. Transparent at unity (color is opt-in: colour + comp + the MIC preamp drive). The E EQ is
**constant-Q** — big top boosts go bright, not snappy; get attack from the comp.

**Headless gotcha:** `apply-vst-chain`'s float dict sets the float params but **NOT** the string enums
(`compressor_ratio`, `eq_colour`, `lf_type`/`hf_type`, the `Out`/`In` routing toggles, `fader_level_db`,
`pan`) — it reports them set but the value silently doesn't take. Use the [[vst-preset]] harness
(`presets/vst/apply_vst_preset.py`, `SSL 4K E.vst3`, exact strings, HPF snapped). Ready presets:
`presets/vst/ssl-4k-e-drum-bus.json` (Black weight+punch) / `ssl-4k-e-glue.json` (Brown glue). Needs
`uv sync --extra vst`; iLok/PACE (verified-headless here — re-verify elsewhere with `probe_plugin.py`).

**Measure before & after** crest / centroid / correlation (crest up = punch, not just louder); A/B
loudness-matched with `[L] render-ab`. It's the **4K E**, not Channel Strip 2 — confirm the path. Full
param surface + decision table: [`docs/vst/ssl-4k-e.md`](../../docs/vst/ssl-4k-e.md). Defer to the skill;
report colour + moves, before→after crest/centroid/corr, and the preset/`.state` path.
