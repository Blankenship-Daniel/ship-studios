# Gemini speech generation / TTS (text in → speech out)

**Status:** reference + wire-up note (NOT wired in this repo) · **Date:** 2026-05-31 · **Last verified:** 2026-05-31 against [docs/speech-generation](https://ai.google.dev/gemini-api/docs/speech-generation) · all models **⚠️ preview**.

Gemini's TTS models turn text into controllable, natural speech — 30 voices, multi-speaker,
and natural-language style direction. **`stemmy-gemini` does not expose this** (it's a
read-only, audio-understanding server). Documented here for completeness and as a wire-up
target. Skill: `[[gemini-speech-generation]]`.

---

## What it does

- **Single- or multi-speaker** narration (**≤2 speakers** per generation).
- **30 prebuilt voices** (astronomical names): Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus,
  Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib,
  Rasalgethi, Laomedeia, Achernar, Alnilam, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi,
  Vindemiatrix, Sadachbia, Sadaltager, Sulafat. (Voice names are **case-sensitive** — `Kore`,
  not `kore`.)
- **90+ languages** with automatic detection.
- **Style control** via natural-language prompts + inline **audio tags** like `[whispers]`,
  `[excited]`, `[dramatic pause]`. Advanced prompting layers Audio Profile, Scene, Director's
  Notes, and Sample Context.

## Models

| Model | Notes |
|---|---|
| `gemini-2.5-flash-preview-tts` | fast/cheap; real-time-ish |
| `gemini-2.5-pro-preview-tts` | studio quality, long-form narration |
| `gemini-3.1-flash-tts-preview` | newest preview |

Prices in [models-and-pricing.md](models-and-pricing.md).

## Output format (important)

- **Raw PCM, 24 kHz, 16-bit, mono.** There is **no native WAV/MP3** — you must wrap the PCM in
  a container client-side (e.g. write a WAV header, or pipe through ffmpeg/soundfile).
- Carries an inaudible **SynthID** watermark.
- Session **context window 32k tokens**; quality can drift past ~3–5 min, so segment long copy.

## SDK pattern (sketch)

```python
from google import genai
from google.genai import types

client = genai.Client()
resp = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents="Say cheerfully: Welcome to the session! [excited]",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
            )
        ),
    ),
)
pcm = resp.candidates[0].content.parts[0].inline_data.data  # raw 24kHz/16-bit/mono
# wrap pcm in a WAV container before saving (see sdk-patterns.md)
```

Full code incl. WAV wrapping: [sdk-patterns.md](sdk-patterns.md).

## Limitations / gotchas

- **No voice cloning / style transfer from a reference audio** — text-in only.
- **No function calling**; **no prompt caching** for TTS.
- ⚠️ Preview: IDs/prices/limits can change.
- ⚠️ No exhaustive published audio-tag list; test the tags you rely on.

## Wire-up note (how it would slot into `stemmy-gemini`)

A `synthesize-speech` tool would: add `stemmy_gemini_mcp/tools/synthesize_speech.py`, reuse
`_call.call_gemini` with `response_modalities=["AUDIO"]` + `speech_config`, **write a WAV** to a
caller-supplied path, and register in `tools/__init__.py`. **Caveat:** this **writes audio**,
breaking the server's read-only invariant (see stemmy-gemini's SECURITY.md) — it's a deliberate
scope change, not a drop-in, and would need the security model updated and an output-path
allowlist. For musical context, voiceovers/stems could feed the create stage, but rendering of
*music* is Lyria's job ([music-generation.md](music-generation.md)), not TTS.

## Related

- `[[gemini-speech-generation]]` · [README.md](README.md) · [sdk-patterns.md](sdk-patterns.md) · [models-and-pricing.md](models-and-pricing.md)
