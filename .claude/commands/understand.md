---
description: Gemini perceptual analysis (transcribe / region / events / classify / compare) of a track or stem.
argument-hint: <audio.wav> [question or goal]
---

Invoke the **understand-audio** skill on `$ARGUMENTS`.

`$1` is the audio to analyze; any remaining args are the question or goal. The skill picks the matching Gemini tool(s) — transcribe-audio, describe-audio-region, extract-audio-events, classify-audio, compare-audio-files, summarize-long-audio (for >1h / >100MB sources), or audio-to-json — and summarizes findings. It is read-only: never modify the audio.
