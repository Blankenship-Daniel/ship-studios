---
description: Make a drum loop/bus punchier with measured multiband transient design (proven via crest/PLR, A/B'd).
argument-hint: <drum-loop-or-bus.wav>
---

Invoke the **drum-punch** skill on `$ARGUMENTS`.

`$1` is a single stereo drum file (a loop or summed drum bus — not a multi-mic kit; that's [[drum-prep]]). The skill measures crest/PLR + spectrum + clipping, drives `shape-bands` (per-band LR4 transient + gain) to add attack and tighten lows, re-measures to prove transients rose without clipping, and renders a loudness-matched `render-ab`. Defer to the skill; lead the report with the crest/PLR delta.
