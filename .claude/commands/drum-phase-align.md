---
description: Phase-align multi-mic drum stems to the overheads (local DSP).
argument-hint: <stems dir>
---

Invoke the **drum-phase-align** skill on `$ARGUMENTS`.

`$1` is the folder of drum-mic stems. The skill drives the local `drum-prep` CLI (`detect` then `phase-align`): every close mic is time/polarity-aligned to the overheads (broadband; kick via a low-pass correlation; snare-bottom→top and kick-beater→in as partner pairs; room polarity-only). Output lands in `<dir>/phase-aligned/`. Requires `uv sync --extra drum-prep`. Report the per-stem delay/polarity table and the partner-pair validation correlations.
