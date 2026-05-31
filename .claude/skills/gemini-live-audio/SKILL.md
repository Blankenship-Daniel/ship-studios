---
name: gemini-live-audio
description: Use when the user asks about Gemini real-time / streaming / conversational audio — "gemini live api", "realtime voice", "streaming audio in/out", "voice conversation", "barge-in / interrupt the model", "live audio monitoring", "native audio dialog". Reference for the Live API — real-time, bidirectional, streaming voice conversation (NOT one-shot TTS file generation; that's [[gemini-speech-generation]]). 16 kHz PCM in / 24 kHz PCM out, WebSocket, ⚠️ preview; NOT wired in this repo (doesn't fit the stdio request/response MCP shape). Points to docs/gemini-audio/live-api.md. Reference + wire-up note, not a tool.
---

# Gemini Live API — reference (real-time audio in ↔ out)

Goal: explain Gemini's real-time bidirectional voice capability and why it's out-of-band for
this MCP. **Not wired into `stemmy-gemini`.** Reference + wire-up note.

**Full reference:** [`docs/gemini-audio/live-api.md`](../../../docs/gemini-audio/live-api.md)

## What it covers

- **Stateful WebSocket**: model listens and speaks in real time.
- **Audio I/O**: input raw **16-bit PCM, 16 kHz, mono**; output raw **16-bit PCM, 24 kHz**.
- **Capabilities**: Voice Activity Detection + **barge-in**, affective dialog (⚠️ 2.5-native;
  verify on 3.1), proactive audio / async tool calls (model-dependent).
- **Models** (⚠️ preview): `gemini-2.5-flash-native-audio-preview-12-2025`,
  `gemini-3.1-flash-live-preview`.
- **Session limits** ⚠️: commonly ~15 min audio-only / ~2 min audio+video, ~10 min socket with
  resumption, ~128k context — version-specific, confirm in the live guide.

## Key facts (quote these)

- It's a **persistent duplex stream**, fundamentally unlike a request→response MCP tool.
- It still hears **mono** — not a stereo/critique-quality upgrade, a real-time UX feature.
- Pricing ≈ $0.005/min in, $0.018/min out
  ([models-and-pricing.md](../../../docs/gemini-audio/models-and-pricing.md)).

## Wire-up note (if asked to build it)

Realistic integration is a **separate long-running process/service** (live monitoring / spoken
review), **not** a `stemmy-gemini` stdio tool. Per the roadmap this is a future UX feature, not
a critique-quality win.

## Pitfalls

- **Don't promise live audio from the MCP today** — out of scope/shape.
- **Confirm session/limit numbers** in the live guide before building — they're ⚠️ and move.

## Related

- `[[gemini-audio]]` (index) · `[[gemini-speech-generation]]` · `[[gemini-music-generation]]`
- [sdk-patterns.md](../../../docs/gemini-audio/sdk-patterns.md) §6 · [`docs/mix-master-capability-roadmap.md`](../../../docs/mix-master-capability-roadmap.md)
