---
description: Compress a stem/bus with your own comp plugin (1176/LA-2A/bus comp), crest/PLR measured.
argument-hint: <audio.wav> [comp/intent]
---

Invoke the **vst-compress** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the compressor/character (FET/opto/VCA/bus). The skill measures microdynamics (crest/PLR), picks a headless-safe comp (`Black 76`, `Comp FET-76`, `FabFilter Pro-C 2`, `SSL Native Bus Compressor 2`, `UAD Tube-Tech CL 1B` — see [`docs/vst/README.md`](../../docs/vst/README.md)), applies it via `[L] apply-vst-chain {…, dump_state:true}`, and re-measures (judge by crest, not level). Needs `uv sync --extra vst`. Defer to the skill; report crest/PLR + LUFS deltas + `.state` path.
