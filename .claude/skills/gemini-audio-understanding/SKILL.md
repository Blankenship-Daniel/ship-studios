---
name: gemini-audio-understanding
description: Use when the user asks how Gemini analyzes audio as INPUT or about its limits — "how does gemini transcribe / analyze audio", "gemini speaker diarization", "audio token cost / 32 tokens per second", "gemini audio file-size or duration limit", "what audio formats does gemini accept", "does gemini hear stereo / phase", "get structured JSON from audio", "which gemini model for audio analysis". Reference for the audio-IN side — the only Gemini audio area this repo wires up (the stemmy-gemini perceptual tools). Points to docs/gemini-audio/audio-understanding.md. Reference, not a pipeline.
argument-hint: [topic, e.g. "diarization" | "file size limit" | "token cost"]
---

# Gemini audio understanding — reference (audio in → text/JSON)

Goal: explain what Gemini can do with audio *input* and its limits, and route to the deep doc.
This is the **only** Gemini audio area the repo implements — every `stemmy-gemini` perceptual
tool is a `generate_content` call with an audio part. To actually *run* these tools, use the
pipeline skill `[[understand-audio]]`; this skill is the capability/limits reference.

**Full reference:** [`docs/gemini-audio/audio-understanding.md`](../../../docs/gemini-audio/audio-understanding.md)

## What it covers

- **Tasks** → repo tool: transcription/diarization (`transcribe-audio`), region Q&A
  (`describe-audio-region`), comparison (`compare-audio-files`), zero-shot classification
  (`classify-audio`), event detection (`extract-audio-events`), long-audio summarization
  (`summarize-long-audio`), structured extraction (`audio-to-json`), and perceptual mix/master
  critique (`analyze-mix-balance`, `detect-mix-issues`, `compare-to-reference`,
  `mastering-feedback`).
- **Input mechanics**: inline vs Files API (repo routes at 80 MB; 2 GB/file, ~48 h retention);
  formats WAV/MP3/AIFF/AAC/OGG/FLAC (+ m4a/opus/webm in-repo).
- **Cost/limits**: 32 tokens/sec, 9.5 h/request, `count_tokens` pre-flight.
- **Timestamps & structured output**: ask for MM:SS explicitly; the `audioTimestamp` flag is
  ⚠️ broken — use a schema `segments` array + DSP cross-check; bounds are advisory (clamp).

## Key facts (quote these)

- Gemini hears **mono, ~16 kbps** → **cannot** judge stereo width, true-peak, or absolute
  loudness. Measure those with `[L] measure-stereo` / `[G] analyze-phase-mono` /
  `[L] measure-loudness`. (See [caveats-and-limits.md](../../../docs/gemini-audio/caveats-and-limits.md).)
- Timestamps are **~seconds** accurate, not frame-accurate.
- Diarization: `gemini-2.5-pro` native (best); avoid deprecated `gemini-2.0` (range bug).
- Repo default model `gemini-3.1-pro-preview` (audio-in, text-out; ⚠️ preview).

## Pitfalls

- **This is the reference, `[[understand-audio]]` is the doer.** Don't reinvent the routing
  here — hand off to run a tool.
- **Don't ask Gemini for stereo/loudness numbers** — it's mono-deaf; that's a meter's job.

## Related

- `[[understand-audio]]` (the pipeline) · `[[gemini-audio]]` (index) · `[[mix-check]]` · `[[master-track]]`
- [models-and-pricing.md](../../../docs/gemini-audio/models-and-pricing.md) · [sdk-patterns.md](../../../docs/gemini-audio/sdk-patterns.md) · [caveats-and-limits.md](../../../docs/gemini-audio/caveats-and-limits.md)
