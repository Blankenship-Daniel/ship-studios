---
description: Add tape/harmonic color to a stem/bus with your own plugin, added-HF measured.
argument-hint: <audio.wav> [flavor: tape/console/drive]
---

Invoke the **vst-saturate** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the flavor (tape/console/multiband drive). The skill measures spectrum + distortion, picks a headless-safe saturator (`Tape Machine 80`, `FabFilter Saturn 2`, `Airwindows Consolidated` — see [`docs/vst/README.md`](../../docs/vst/README.md)), applies it via `[L] apply-vst-chain {…, dump_state:true}` (keep drive subtle), and re-measures at matched level. Needs `uv sync --extra vst`. Pure-DSP alternative: `[L] saturate-loop`. Defer to the skill; report added-HF/harmonics + level + `.state` path.
