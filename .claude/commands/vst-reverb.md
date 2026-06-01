---
description: Add reverb/space to a stem or send with your own plugin (Valhalla/Pro-R), mono-checked.
argument-hint: <audio.wav> [space: plate/room/hall]
---

Invoke the **vst-reverb** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the space. The skill measures loudness + stereo (mono-sum loss), picks a headless-safe reverb (`ValhallaPlate`, `FabFilter Pro-R 2`, `SSL Native FlexVerb` — see [`docs/vst/README.md`](../../docs/vst/README.md)), renders a wet/parallel pass via `[L] apply-vst-chain {…, dump_state:true}`, and re-checks mono compatibility. Needs `uv sync --extra vst`. Defer to the skill; report decay + correlation/mono-sum deltas + `.state` path, and note if it's a send to blend.
