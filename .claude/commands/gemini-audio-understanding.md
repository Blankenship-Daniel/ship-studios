---
description: Reference for Gemini audio understanding (audio in → text/JSON) — tasks, formats, limits, token cost, timestamps, the mono-downmix caveat.
argument-hint: [topic, e.g. "diarization" | "file size limit" | "token cost"]
---

Invoke the **gemini-audio-understanding** skill on `$ARGUMENTS`.

`$ARGUMENTS` is the question about Gemini's audio-input capabilities. The skill explains the
understanding area (the only one this repo wires up, via the stemmy-gemini perceptual tools) and
points to `docs/gemini-audio/audio-understanding.md`. To actually analyze a file, use
[[understand-audio]] instead.
