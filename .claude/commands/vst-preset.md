---
description: Save a VST chain as a reusable preset, or apply a saved preset to a file (gain-stage + enum params).
argument-hint: save <name> | apply <preset.json> <in.wav> [out.wav]
---

Invoke the **vst-preset** skill on `$ARGUMENTS`.

Apply: `apply_vst_preset.py presets/vst/<name>.json <in> <out>` (handles the input gain-stage + enum/bool params + M/S narrow that `apply-vst-chain` can't), then re-measure vs the preset's `target_signature`. Save: capture the dialed chain (gain, params incl. enums, width, trim) → `presets/vst/<name>.json` + `dump_state` blobs. Plugins must render (`/vst-verify`); use `uaudio_*` paths. Example shipped: `vintage-1960s`. See [`presets/vst/README.md`](../../presets/vst/README.md). Defer to the skill; report the preset path / before→after vs target.
