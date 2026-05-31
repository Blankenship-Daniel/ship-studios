---
description: Assemble one-shots + loops into a sellable, tagged, multi-format sample pack with metadata/blurbs.
argument-hint: <source.wav> <bpm>
---

Invoke the **sample-pack** skill on `$ARGUMENTS`.

`$1` is the source (drum stem, full mix, or an already-finished loop set), `$2` the BPM (required by `find-loops`; `extract-oneshots` needs none). Primarily **stemmy-loops**: `extract-oneshots` for the hits + `find-loops` (or the full [[loops-to-deliverables]] clean→seam→master chain) for the loops → `tag-deliverable` (use `root_note`, not `root`) → `export-deliverables` (the `distribution_44k_16` / `production_48k_24` / `master_96k_24` presets) → organize a pack tree with a README; optional `describe-loops` / `caption-loops` blurbs. Verify tags survived export ([[delivery-qc]]) — `export-deliverables tag=true` silently drops them. Defer to the skill; report the pack tree, per-category counts, and tag coverage. Distinct from [[slice-oneshots]] (no packaging) and [[sampler-kit]] (tuned kit).
