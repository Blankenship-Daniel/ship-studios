---
description: Slice a drum stem or full mix into cleaned, mastered, tagged loop deliverables.
argument-hint: <stem-or-mix.wav> <bpm>
---

Invoke the **loops-to-deliverables** skill on `$ARGUMENTS`.

`$1` is the source WAV and `$2` the BPM (a full mix → the skill sets `separate=true` on find-loops). The skill extracts loops (find-loops / analyze-loops), then per loop runs clean-loop → optimize-seam → render-mastered → tag-deliverable → export-deliverables; describe-loops is optional for audible groove notes. Defer to the skill for flags and output paths.
