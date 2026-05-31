---
name: gemini-music-generation
description: Use when the user asks about generating music with Gemini / Google — "generate music with gemini", "lyria", "ai music / backing track / instrumental generation", "generate an instrumental", "AI-generate a loop / jingle / stock music", "make a song from a prompt", "lyria realtime", "text to music". Reference for Lyria (Lyria 3 clip/pro + Lyria RealTime; MP3/WAV 44.1 kHz; ⚠️ preview/experimental) — NOT wired in this repo. Points to docs/gemini-audio/music-generation.md. Reference + wire-up note, not a tool.
---

# Gemini music generation (Lyria) — reference (text → music)

Goal: explain Google's Lyria music-generation models and how they'd be added. **Not wired into
`stemmy-gemini`.** Reference + wire-up note. Relevant to the *create* end of the lifecycle.

**Full reference:** [`docs/gemini-audio/music-generation.md`](../../../docs/gemini-audio/music-generation.md)

## What it covers

- **`lyria-3-clip-preview`** — 30 s clips/loops, **MP3, 44.1 kHz stereo**.
- **`lyria-3-pro-preview`** — full-length songs (length via prompt), **MP3** (opt. **WAV**),
  44.1 kHz stereo; optional/custom lyrics + section tags (`[Verse]`, `[Chorus]`).
- **Lyria RealTime** ⚠️ experimental — continuous streaming **instrumental** (no vocals),
  steered live (research: BPM/density/brightness/scale, ~2 s latency, PCM ~48 kHz).
- Lyria 3 uses standard **`generateContent`**; all output carries an inaudible **SynthID**
  watermark; accessible via the **Gemini API** (some surfaces also on Vertex AI).

## Key facts (quote these)

- Distinct from TTS (`[[gemini-speech-generation]]`): Lyria makes **music**, TTS makes speech.
- Lyria 3 = request/response; **Lyria RealTime = streaming WebSocket** (same out-of-band issue
  as `[[gemini-live-audio]]`).
- ⚠️ Preview/experimental — verify model IDs, formats, and RealTime controls live.

## Wire-up note (if asked to build it)

A `generate-music` tool would mirror the TTS wire-up (module under
`stemmy_gemini_mcp/tools/`, `_call.call_gemini`, **write the returned audio**) — which **breaks
the read-only invariant** and needs a security-model change + output-path allowlist. Generated
loops/stems could then feed `[[loops-to-deliverables]]` / `[[slice-oneshots]]`, but generation
itself is a new server capability, not a drop-in.

## Pitfalls

- **Don't claim the repo generates music today** — it doesn't; reference only.
- **Lyria ≠ TTS** — route voice requests to `[[gemini-speech-generation]]`.

## Related

- `[[gemini-audio]]` (index) · `[[gemini-speech-generation]]` · `[[gemini-live-audio]]`
- [music-generation.md](../../../docs/gemini-audio/music-generation.md) · [sdk-patterns.md](../../../docs/gemini-audio/sdk-patterns.md) · [models-and-pricing.md](../../../docs/gemini-audio/models-and-pricing.md)
