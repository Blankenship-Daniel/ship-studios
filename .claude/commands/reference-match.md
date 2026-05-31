---
description: Match a mix to a reference track and render a loudness-matched A/B audition.
argument-hint: <mix.wav> <reference.wav>
---

Invoke the **reference-match** skill on `$ARGUMENTS`.

`$1` is the mix to correct, `$2` the reference to match. The skill derives numeric (match-reference-numeric, compare-tonality) and perceptual (compare-to-reference) deltas, reconciles them into an apply-eq move set, then renders a single `[reference | gap | matched]` A/B WAV via render-ab. Report residual deltas after the move.
