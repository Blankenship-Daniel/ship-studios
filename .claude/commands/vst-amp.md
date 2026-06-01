---
description: Reamp a DI guitar/bass track through your own amp-sim plugin (TONEX/NAM/Amp Rooms).
argument-hint: <DI.wav> [tone: clean/crunch/high-gain, bass/guitar]
---

Invoke the **vst-amp** skill on `$ARGUMENTS`.

`$1` is a **DI / clean** guitar or bass track; the rest hints the tone. The skill measures the DI, picks a headless-safe amp sim (`TONEX`, `NeuralAmpModeler`, `UAD Softube Bass/Metal Amp Room` — see [`docs/vst/README.md`](../../docs/vst/README.md)), applies it via `[L] apply-vst-chain {…, dump_state:true}` → `projects/<track>/stems/` (NAM/TONEX captures restore via `state_path`), and re-measures. Needs `uv sync --extra vst`. Tracking/reamp only — keep it off the mix bus. Defer to the skill; report tone shift + level + `.state` path.
