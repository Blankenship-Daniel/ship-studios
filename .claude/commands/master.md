---
description: Master a near-final stereo mix to a platform-ready master and export the deliverable format matrix.
argument-hint: <mix.wav> [target platform/LUFS]
---

Invoke the **master-track** skill on `$ARGUMENTS`.

`$1` is the source WAV; any remaining args name the target platform / LUFS / ceiling. The skill runs the verified measure → mastering-feedback → render-mastered → check-streaming-targets → export-deliverables chain across the `stemmy-loops` and `stemmy-gemini` servers. Do not restate the recipe here — defer to the skill, and report before/after numbers plus release-readiness.
