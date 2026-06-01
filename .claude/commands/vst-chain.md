---
description: Apply an arbitrary chain of your headless-safe VST3/AU effect plugins to a WAV, measured.
argument-hint: <audio.wav> [plugins/intent]
---

Invoke the **vst-chain** skill on `$ARGUMENTS`.

`$1` is the input WAV (stem/bus/loop); the rest is the desired plugins or intent. The skill runs the canonical VST recipe: measure baseline (`[L] measure-loudness`/`measure-spectrum`) → confirm headless-safe plugin paths via `[L] list-vst-plugins` (only titles in [`docs/vst/README.md`](../../docs/vst/README.md)) → `[L] apply-vst-chain {…, dump_state:true}` → re-measure and verify `changed:true` (flag demo-mode silence) → write to `projects/<track>/mix/`. Needs `uv sync --extra vst`. Defer to the skill; report before/after deltas + the dumped `.state` path.
