---
description: Diagnose a mix (perceptual + measurement) and emit concrete, prioritized EQ/compression moves.
argument-hint: <mix.wav>
---

Invoke the **mix-check** skill on `$ARGUMENTS`.

`$1` is the mix WAV to diagnose. The skill fuses Gemini perceptual listening (detect-mix-issues, analyze-mix-balance, find-resonances, find-sibilance, analyze-phase-mono) with DSP measurement (measure-loudness, measure-spectrum, measure-stereo) into one prioritized issue list, then proposes and optionally applies apply-eq / compress-loop moves. Do not master here — hand off to `/master`.
