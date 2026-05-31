---
description: Chop a break into one-shots, tune the pitched hits to the song key, QC, tag, and export a multiformat kit.
argument-hint: <break.wav> [key/root]
---

Invoke the **sampler-kit** skill on `$ARGUMENTS`.

`$1` is the break to chop; pass the song key/root if it isn't in `track.md`. The skill runs `extract-oneshots`, has you designate which slices are pitched (no auto kick/snare classifier — Gemini classify is confounded by bleed), measures fundamentals with `tune-kick`, retunes the pitched hits via `drum-prep tune`, QCs on peak/clipping, then `tag-deliverable` → `export-deliverables` → `verify-tags`. Output is a tagged one-shot kit, not a mapped sampler patch. Defer to the skill; report per-hit retune + export paths.
