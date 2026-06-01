---
description: De-ess a vocal/bright track with your own de-esser, band/threshold set by find-sibilance.
argument-hint: <vocal.wav>
---

Invoke the **vst-de-ess** skill on `$ARGUMENTS`.

`$1` is the vocal/bright WAV. The skill measures spectrum, runs `[G] find-sibilance` to locate the band + threshold + target GR, picks a headless-safe de-esser (`FabFilter Pro-DS`, `SSL DeEss`, `Lindell 902 De-esser` — see [`docs/vst/README.md`](../../docs/vst/README.md)), applies it via `[L] apply-vst-chain {…, dump_state:true}`, and re-measures. Needs `uv sync --extra vst` + `GEMINI_API_KEY`. Pure-DSP alternative: `[L] de-ess`. Defer to the skill; report band/threshold/GR + high-band deltas + `.state` path.
