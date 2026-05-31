---
description: Reference for the Gemini Live API (real-time 16kHz-in / 24kHz-out audio, VAD, barge-in) — preview; not wired in this repo.
argument-hint: [topic, e.g. "audio format" | "session limits" | "models"]
---

Invoke the **gemini-live-audio** skill on `$ARGUMENTS`.

`$ARGUMENTS` is the question about Gemini's real-time audio. The skill explains the Live API
I/O, capabilities, and models, and points to `docs/gemini-audio/live-api.md`. Note: the Live API
is NOT wired into stemmy-gemini (a WebSocket stream doesn't fit the stdio MCP shape) — the skill
includes the out-of-band wire-up note.
