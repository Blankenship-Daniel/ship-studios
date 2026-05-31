---
description: Chop a loop/break into per-hit one-shot WAVs for a sampler, QC, and optionally tag (lightweight, no sales packaging).
argument-hint: <loop-or-break.wav>
---

Invoke the **slice-oneshots** skill on `$ARGUMENTS`.

`$1` is the loop/break to chop. The skill tunes `extract-oneshots` slice params (min-separation / pre-pad / post-pad) for the material, writes `hit_NN.wav`, QCs on per-hit peak + `check-clipping` (NOT `inspect-loop` — vacuous on one-shots), and optionally tags. For a sellable multiformat pack use [[sample-pack]]; to tune the hits to the key use [[sampler-kit]]. Defer to the skill; report kept/dropped counts and the output dir.
