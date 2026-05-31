---
name: gemini-speech-generation
description: Use when the user asks about Gemini text-to-speech / generating spoken audio — "gemini tts", "text to speech", "generate a voiceover / narration", "synthesize speech", "gemini tts voices / multi-speaker", "what voice or language for gemini speech", "make Gemini talk". Reference for Gemini TTS — a pre-rendered, one-shot speech file (NOT real-time conversation; that's the Live API, [[gemini-live-audio]]). 30 voices, PCM 24 kHz, ⚠️ preview; NOT wired in this repo (stemmy-gemini is read-only). Points to docs/gemini-audio/speech-generation.md. Reference + wire-up note, not a tool.
---

# Gemini speech generation / TTS — reference (text → speech)

Goal: explain Gemini's text-to-speech capability and how it *would* be added. **Not wired into
`stemmy-gemini`** — that server is read-only (audio understanding). This skill is reference +
a wire-up note.

**Full reference:** [`docs/gemini-audio/speech-generation.md`](../../../docs/gemini-audio/speech-generation.md)

## What it covers

- **Models** (all ⚠️ preview): `gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts`,
  `gemini-3.1-flash-tts-preview`.
- **30 prebuilt voices** (case-sensitive names like `Kore`, `Puck`, `Zephyr`), **≤2 speakers**,
  **90+ languages** (auto-detect).
- **Style control** via natural-language prompts + inline audio tags (`[whispers]`,
  `[excited]`, `[dramatic pause]`).
- **Output**: raw **PCM 24 kHz / 16-bit / mono** — **no native WAV/MP3**, wrap client-side;
  inaudible **SynthID** watermark; 32k-token session.

## Key facts (quote these)

- Output is raw PCM — you must add a WAV header before saving (see
  [sdk-patterns.md](../../../docs/gemini-audio/sdk-patterns.md) §5).
- No voice cloning / reference-audio style transfer; no function calling; no caching.
- ⚠️ Preview — IDs/prices/tags can change; no exhaustive published audio-tag list.

## Wire-up note (if asked to build it)

A `synthesize-speech` tool would add `stemmy_gemini_mcp/tools/synthesize_speech.py`, call
`_call.call_gemini` with `response_modalities=["AUDIO"]` + `speech_config`, and **write a WAV**.
That **breaks the server's read-only invariant** — a deliberate scope change needing the
security model updated + an output-path allowlist, not a drop-in.

## Pitfalls

- **Don't claim the repo can do TTS today** — it can't; this is reference.
- **PCM ≠ WAV** — never hand raw TTS bytes to a player without a container.

## Related

- `[[gemini-audio]]` (index) · `[[gemini-music-generation]]` (the other audio-out area) · `[[gemini-live-audio]]`
- [sdk-patterns.md](../../../docs/gemini-audio/sdk-patterns.md) · [models-and-pricing.md](../../../docs/gemini-audio/models-and-pricing.md)
