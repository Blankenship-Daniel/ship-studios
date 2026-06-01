---
description: Add delay/echo to a stem or send with your own plugin (EP-34/Brigade/Timeless).
argument-hint: <audio.wav> [time/feel, e.g. "1/8 tape"]
---

Invoke the **vst-delay** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints time/feel. The skill reads BPM from `projects/<track>/track.md` (never guesses) to compute synced times, picks a headless-safe delay (`UAD EP-34 Tape Echo`, `Delay BRIGADE`, `FabFilter Timeless 3` — see [`docs/vst/README.md`](../../docs/vst/README.md)), renders a wet/parallel pass via `[L] apply-vst-chain {…, dump_state:true}`. Needs `uv sync --extra vst`. Defer to the skill; report time (note value + ms) + feedback + `.state` path.
