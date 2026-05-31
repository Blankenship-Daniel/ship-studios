---
description: Merge `<name> - left/right` mono drum-mic pairs into format-preserving stereo files (local DSP).
argument-hint: <stems dir>
---

Invoke the **drum-stereo-merge** skill on `$ARGUMENTS`.

`$1` is a folder where mic pairs are split as `<name> - left` / `<name> - right` (also `_l`/`_r`, `" l"`/`" r"`). The skill drives the local `drum-prep stereo-merge` CLI (NOT the stemmy MCP servers): it interleaves L→left / R→right into one stereo file per pair, source bit depth/format preserved, with **no** time-alignment by default (a spaced pair keeps its natural image; `--align` only for a coincident pair) → `<dir>/stereo/`. It then reviews each pair — inter-channel correlation, polarity, mono-compatibility, reverb-vs-mic. Requires `uv sync --extra drum-prep`. Defer to the skill; report the per-pair image review and any keep/drop/move call.
