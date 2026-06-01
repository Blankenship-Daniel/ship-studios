---
description: Run a stem/bus through a real console channel-strip plugin (SSL/Neve/API), measured.
argument-hint: <stem.wav> [console/character]
---

Invoke the **vst-channel-strip** skill on `$ARGUMENTS`.

`$1` is the stem/bus WAV; the rest hints the desired console/character. The skill measures (loudness/spectrum/microdynamics), picks a headless-safe strip (`British Channel`, `bx_console …`, `SSL Native Channel Strip 2`, `UAD API/Neve` — see [`docs/vst/README.md`](../../docs/vst/README.md)), applies it via `[L] apply-vst-chain {…, dump_state:true}`, and re-measures (watch crest). Needs `uv sync --extra vst`. Defer to the skill; report the moves + before/after + `.state` path.
