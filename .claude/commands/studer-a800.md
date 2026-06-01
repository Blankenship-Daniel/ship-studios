---
description: Drive the UAD Studer A800 tape machine (warmth/glue, de-harsh) — measured.
argument-hint: <audio.wav> [goal: warm/glue/tame-harshness/punch]
---

Invoke the **studer-a800** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (warm / mix-bus glue / tame-harshness / tight-punch). The skill
gain-stages to the A800's −12 dBFS reference, picks a starting point from the decision table in
[`docs/vst/studer-a800.md`](../../docs/vst/studer-a800.md) (default REPRO·456·15 IPS·NAB·Cal +6·Auto Cal ON),
drives `input_level` only to ~1–3 dB of transient reduction, applies it via the [[vst-preset]] harness
(`uaudio_studer_a800.vst3`, enum params honored, `dump_state`), and **measures spectrum/crest before & after**
(centroid + tilt DOWN = warming, not a 2–5 kHz rise). Needs `uv sync --extra vst`.

Key facts: **tape darkens — harshness is upstream**, isolate & measure; tape harmonics are **odd/3rd-order**,
so over-driving adds edge (cure = less Input); for de-harshing, the direct levers (measured) are `repro_hf_eq`
down, less Input, 30 IPS, over-`bias`. Pure-DSP alternative: `[L] saturate-loop`. Defer to the skill; report
the chain, before→after centroid/tilt/crest, and the `.state`/preset path.
