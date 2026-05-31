---
description: Separate a mixdown into stems via Demucs (extract the drum stem) — stemmy MCP.
argument-hint: <mix.wav> <bpm>
---

Invoke the **stem-split** skill on `$ARGUMENTS`.

`$1` is the stereo mixdown to separate, `$2` the BPM (**required** — read it from `projects/<track>/track.md`; never guess). The skill runs `[L] extract-drums {path, bpm}` (Demucs) on **stemmy-loops** and returns the isolated drum stem, written to `projects/<track>/stems/` (durable) or `artifacts/<run>/` (scratch); an optional `[L] measure-spectrum` confirms the stem is LF/transient-dominant without melodic bleed. Needs the **`separate`** extra (`uv sync … --extra separate`) — heavy, pure DSP, fetches the Demucs model weights on first run, no API key. Defer to the skill; report the stem path and the verification read.
