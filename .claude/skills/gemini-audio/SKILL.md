---
name: gemini-audio
description: Use when the user asks what Gemini can do with audio, which Gemini model/format/limit/price fits an audio task, or where the Gemini audio docs live — "what can Gemini do with audio", "which gemini model for audio", "gemini audio token cost", "gemini audio file-size / duration limit", "does gemini do TTS / music / realtime audio", "gemini audio capabilities / docs / limits". The index to the Gemini-audio reference suite (docs/gemini-audio/); routes to the per-area skills. Reference, not a pipeline — it points at docs, it does not process audio.
argument-hint: [topic, e.g. "token cost" | "tts voices" | "does it hear stereo"]
---

# Gemini audio — capability reference (index)

Goal: answer "what can Gemini do with audio, and what should I use / watch out for" by
routing to the right reference doc under [`docs/gemini-audio/`](../../../docs/gemini-audio/README.md).
This is a **documentation index**, not a processing pipeline — it never calls a tool or
touches audio. For *doing* perceptual analysis use `[[understand-audio]]` / `[[mix-check]]`.

## The four capability areas (+ model/SDK/limit lookups) → where to look

| The user is asking about… | Skill | Doc |
|---|---|---|
| Analyzing audio **input** (transcribe, classify, critique, token cost, limits, "does it hear stereo") | `[[gemini-audio-understanding]]` | [audio-understanding.md](../../../docs/gemini-audio/audio-understanding.md) |
| **Text-to-speech** (voices, narration, voiceover) | `[[gemini-speech-generation]]` | [speech-generation.md](../../../docs/gemini-audio/speech-generation.md) |
| **Real-time** voice / Live API / streaming | `[[gemini-live-audio]]` | [live-api.md](../../../docs/gemini-audio/live-api.md) |
| **Music generation** (Lyria) | `[[gemini-music-generation]]` | [music-generation.md](../../../docs/gemini-audio/music-generation.md) |
| Which **model / price / context** | — | [models-and-pricing.md](../../../docs/gemini-audio/models-and-pricing.md) |
| **SDK** / how to call it / build a new tool | — | [sdk-patterns.md](../../../docs/gemini-audio/sdk-patterns.md) |
| **Limits / gotchas** (read before trusting a read) | — | [caveats-and-limits.md](../../../docs/gemini-audio/caveats-and-limits.md) |

## At a glance

- **In this repo**: only **audio understanding** is wired (the `stemmy-gemini` perceptual
  tools). TTS, Live, and Lyria are documented as reference + wire-up notes — `stemmy-gemini`
  is read-only and stdio-shaped.
- **The one caveat that governs everything**: Gemini downsamples to ~16 kbps and **sums to
  mono** before hearing — so it **cannot judge stereo, true-peak, or absolute loudness**. Use
  meters for those (`[L] measure-stereo` / `[G] analyze-phase-mono` / `[L] measure-loudness`);
  use Gemini for harshness / pumping / masking / "feel." See
  [caveats-and-limits.md](../../../docs/gemini-audio/caveats-and-limits.md) and
  the `gemini-mastering-feedback-cross-check` memory note.
- **Numbers you reach for**: audio = **32 tokens/sec**, up to **9.5 h**/request; inline routes
  to Files API at **80 MB**; formats WAV/MP3/AIFF/AAC/OGG/FLAC; repo default model
  `gemini-3.1-pro-preview` (⚠️ preview).

## How to use this skill

Identify which area the question is about, hand off to the matching per-area skill, and quote
the relevant doc. If it's a model/price/SDK/limit lookup, read the
corresponding doc directly and answer with the cited figure (flag ⚠️ preview/unverified items).

## Pitfalls

- **Don't process audio here.** This skill points at docs; to actually analyze a file use
  `[[understand-audio]]`, to critique a mix use `[[mix-check]]`.
- **Re-check moving numbers.** Models/prices/preview status change — every doc cites its
  source page and a "last verified" date; verify before betting a build on a number.

## Related

- `[[gemini-audio-understanding]]` · `[[gemini-speech-generation]]` · `[[gemini-live-audio]]` · `[[gemini-music-generation]]`
- `[[understand-audio]]` (uses the understanding tools) · `[[mix-check]]` · `[[master-track]]`
- Proposal for *future* DSP capabilities: [`docs/mix-master-capability-roadmap.md`](../../../docs/mix-master-capability-roadmap.md)
