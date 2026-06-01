---
description: De-ess a vocal/lead/bright bus with the native split-band de-esser, grounded by find-sibilance and proven via the 4–9 kHz delta.
argument-hint: <vocal-or-bus.wav>
---

Invoke the **de-ess** skill on `$ARGUMENTS`.

`$1` is one stereo WAV (a vocal/lead stem or a bright bus — not a multi-mic kit). The skill baselines `measure-spectrum`, locates the sibilant band with `[G] find-sibilance`, ducks only that band with `[L] de-ess` (split mode), and re-measures. Defer to the skill; lead the report with the 4–9 kHz band-energy delta and the peak gain reduction.
