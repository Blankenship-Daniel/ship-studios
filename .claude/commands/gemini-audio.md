---
description: Gemini audio capability reference — index to docs/gemini-audio/ (what Gemini can do with audio, which model, what it costs, its limits).
argument-hint: [topic, e.g. "token cost" | "tts voices" | "does it hear stereo"]
---

Invoke the **gemini-audio** skill on `$ARGUMENTS`.

`$ARGUMENTS` is the question about Gemini's audio capabilities. The skill is a documentation
index: it routes to the matching per-area skill ([[gemini-audio-understanding]],
[[gemini-speech-generation]], [[gemini-live-audio]], [[gemini-music-generation]]) and the docs
under `docs/gemini-audio/`, and answers model/price/limit lookups with cited figures. It is
read-only — it points at docs, it does not process audio.
