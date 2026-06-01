---
description: Render N VST chain/preset variants on one source and adversarially judge them to a winner.
argument-hint: <audio.wav> [goal/variants, e.g. "vintage drum flavors"]
---

Invoke the **vst-shootout** skill on `$ARGUMENTS`.

`$1` is the source WAV; the rest sets the goal/variants. The skill defines 2–5 distinct chains/presets, renders them **serially** (UADx dislikes concurrent hosts) via `[[vst-chain]]`/`[[vst-preset]]`, measures each, and judges them across lenses (a Workflow adversarial judge panel for a rigorous pick; optional `[G]` ears) → winner + one refinement, optionally a loudness-matched `render-ab`. Pre-screen plugins with `[[vst-verify]]`. The VST-chain cousin of `[[variant-shootout]]`. Defer to the skill; report the comparison table + winner + rationale.
