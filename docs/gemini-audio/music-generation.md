# Gemini music generation — Lyria (text in → music out)

**Status:** reference + wire-up note (NOT wired in this repo) · **Date:** 2026-05-31 · **Last verified:** 2026-05-31 against [docs/music-generation](https://ai.google.dev/gemini-api/docs/music-generation) · all models **⚠️ preview / experimental**.

Google's **Lyria** family generates music from text (and image) prompts via the Gemini API.
Distinct from understanding (it *makes* audio) and from TTS (music, not speech). **Not wired
into `stemmy-gemini`.** Relevant to the *create* end of the lifecycle. Skill:
`[[gemini-music-generation]]`.

---

## Models & outputs (verified)

| Model | Generates | Output |
|---|---|---|
| `lyria-3-clip-preview` | short clips / loops / previews — **30 s** | **MP3, 44.1 kHz stereo** |
| `lyria-3-pro-preview` | full-length songs (intro/verse/chorus/bridge), length controllable via prompt | **MP3** default, optional **WAV** (`response_format: {"audio": {"mime_type": "audio/wav"}}`), 44.1 kHz stereo |
| **Lyria RealTime** | continuous, streaming instrumental | streaming PCM (research: 48 kHz) ⚠️ |

- Both Lyria 3 models can include optional/custom **lyrics** and section tags
  (`[Verse]`, `[Chorus]`, …).
- Lyria 3 is called via standard **`generateContent`** (non-streaming) and is compatible with
  the Interactions API for state.
- All generated audio carries an inaudible **SynthID** watermark.
- Access: **Gemini API** (Python/JS/Go/Java/C#/REST). Some Lyria surfaces are also on Vertex AI
  (enterprise).

## Lyria RealTime (experimental) ⚠️

A separate streaming offering for interactive, never-stopping **instrumental** generation
(no vocals), steered live by weighted prompts plus controls the research pass reported as **BPM,
density, brightness, musical scale**, with ~2 s control latency over a WebSocket. Specs are not
firmly pinned on the public overview — **verify before relying** ([deepmind.google/models/lyria](https://deepmind.google/models/lyria/lyria-realtime/)).

## SDK pattern (sketch — Lyria 3)

```python
from google import genai
client = genai.Client()
resp = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents="2-minute lo-fi hip-hop instrumental: warm piano, soft drums, ambient pads. "
             "[Intro] [Verse] [Chorus] [Verse] [Chorus] [Outro]",
)
# audio bytes in resp (MP3 by default); request WAV via response_format. See sdk-patterns.md.
```

## Wire-up note

A `generate-music` tool would mirror the TTS wire-up: a module under
`stemmy_gemini_mcp/tools/` reusing `_call.call_gemini`, **writing the returned audio** to a
caller path — which again **breaks the read-only invariant** and needs a security-model change +
output-path allowlist. Lyria RealTime (streaming) has the same out-of-band problem as the Live
API ([live-api.md](live-api.md)). Generated stems/loops could feed `[[loops-to-deliverables]]`
or `[[slice-oneshots]]`, but generation itself is a new server capability, not a drop-in.

## Related

- `[[gemini-music-generation]]` · [README.md](README.md) · [sdk-patterns.md](sdk-patterns.md) · [models-and-pricing.md](models-and-pricing.md)
