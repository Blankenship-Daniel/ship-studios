---
description: Reduce mic bleed before mixing — gate a close mic, or cancel a correlated source out of a target.
argument-hint: gate <mic.wav> | cancel <target.wav> <bleedsource.wav>
---

Invoke the **bleed-gate** skill on `$ARGUMENTS`.

Two modes via `scripts/mix/debleed.py`: **gate** a close mic so only its own hits pass (kills spill in the gaps, e.g. hi-hat in the snare-top mic); **cancel** a correlated, time-aligned source out of a target by least-squares subtraction (e.g. null the hi-hat out of the overheads while keeping the cymbals). Cancel needs phase-aligned stems (`[[drum-phase-align]]`); keep amount < ~0.7 to stay natural. Do this BEFORE `[[mix-balance]]` — raising a mic raises its bleed. Often, just lowering the carrier in the balance is enough — try that first. Needs the venv. Defer to the skill; report the % gated / correlation drop.
