---
description: Dial the UAD API Vision Channel Strip for tight/punchy/forward drums — measured.
argument-hint: <audio.wav> [goal: punchy-bus/glue/de-harsh]
---

Invoke the **api-vision-channel-strip** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (tight/punchy bus / gentle glue / de-harsh). The skill gain-stages
the 212 input for color (not clipping), tightens with the 215 HPF (~40 Hz bus), punches with the 225 comp
(**measure crest across Fast/Medium/Slow — Medium often beats Slow here**, 3–6 dB GR, New=tight / Old=glue),
and adds 550 low-thump + de-box while **keeping the top flat** (boosting 2–5 kHz re-creates harshness;
proportional-Q sharpens big boosts; 5 kHz sits in both HMF+HF — never stack). Applies via the [[vst-preset]]
harness (`uaudio_api_vision_channel_strip.vst3`, enum params honored, `dump_state`) and **measures
crest/centroid/correlation before & after** (crest up = punch, not just louder). Decision table + the full
param surface: [`docs/vst/api-vision-channel-strip.md`](../../docs/vst/api-vision-channel-strip.md). Needs
`uv sync --extra vst`.

Key facts: the strip is **near-passthrough until driven** (color is opt-in, 2nd-order harmonic); **no THRUST
on the 225L** (use 215 sidechain + HPF); default flow is **comp→EQ** (PREDYN to flip). Ready preset:
`presets/vst/tight-70s-api.json`. Pure-DSP alternative: `[L] compress-loop` + `[L] apply-eq`. Defer to the
skill; report modules used, before→after crest/centroid/corr, and the preset/`.state` path.
