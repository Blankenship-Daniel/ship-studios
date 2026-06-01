---
description: Master a mix with your own plugin chain (EQ→comp→limiter) + streaming compliance.
argument-hint: <mix.wav> [--platform spotify] [target LUFS]
---

Invoke the **vst-master** skill on `$ARGUMENTS`.

`$1` is a near-final stereo mix; the rest sets platform/target. The skill measures baseline (LUFS/TP/PLR/LRA, clipping), optionally reads `[G] mastering-feedback`, builds ONE measured `[L] apply-vst-chain` EQ→comp→limiter (`FabFilter Pro-Q 4` → `Pro-C 2`/`SSL Native Bus Compressor 2` → `Pro-L 2`/`Brickwall Limiter` — see [`docs/vst/README.md`](../../docs/vst/README.md); limiter sets the ceiling) → `projects/<track>/masters/`, then verifies with `[L] check-clipping` + `[G] check-streaming-targets`. Needs `uv sync --extra vst` (+ `GEMINI_API_KEY`). This is the opt-in/non-deterministic sibling of `/master` (pure-DSP). Defer to the skill; report LUFS/TP + compliance + `.state` paths, then hand to `/delivery-qc`.
