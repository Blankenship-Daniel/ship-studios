---
description: Render loudness-matched A/B auditions of a prepped drum kit (local DSP).
argument-hint: <stems dir> <reference.wav>
---

Invoke the **drum-audition** skill on `$ARGUMENTS`.

`$1` is the folder (with `phase-aligned/` and `ref-matched/` sets), `$2` the reference used for the match. The skill drives the local `drum-prep audition` CLI: it builds coherent stereo kit sums and writes two loudness-matched (BS.1770) A/B WAVs into `<dir>/auditions/` — `AB_before-vs-after.wav` and `AB_reference-vs-after.wav`. Requires `uv sync --extra drum-prep`. Report the matched LUFS per A/B and point at the before-vs-after file.
