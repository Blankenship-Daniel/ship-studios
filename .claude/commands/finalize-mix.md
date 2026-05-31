---
description: Glue a mix bus with gentle compression/saturation/stereo BEFORE mastering — no limiting.
argument-hint: <mix.wav>
---

Invoke the **finalize-mix** skill on `$ARGUMENTS`.

`$1` is a near-final **stereo mix bus** (not stems, not loops). The skill is the stage between mixing and [[master-track]]: it measures, then applies gentle bus glue/density — `compress-loop` (light bus comp), `saturate-loop`, `adjust-stereo` — WITHOUT limiting (loudness + the limiter stay [[master-track]]'s job). `measure-loudness` and the render tools need the `mixing` extra; the rest are core DSP, no key. If the mix isn't clean yet (tonal/phase/balance), run [[mix-check]] first. Defer to the skill; report before/after and hand off to `/master`.
