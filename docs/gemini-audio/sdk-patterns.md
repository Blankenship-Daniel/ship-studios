# Gemini audio — `google-genai` Python SDK patterns

**Status:** reference · **Date:** 2026-05-31 · **Last verified:** 2026-05-31 · **Source:** [docs/libraries](https://ai.google.dev/gemini-api/docs/libraries) + this repo's `stemmy-gemini-mcp` code.

Copy-paste patterns for every audio area, plus the **in-repo helper layer** so new
`stemmy-gemini` tools stay consistent with the existing ones.

> **Package name gotcha:** the current SDK is **`google-genai`** (`from google import genai`,
> `client = genai.Client()`). The old **`google-generativeai`** (`import google.generativeai`)
> is legacy — don't mix them. `stemmy-gemini` pins `google-genai`.

```bash
pip install google-genai      # or, in this monorepo: uv sync
export GEMINI_API_KEY=...      # the SDK also reads GOOGLE_API_KEY
```

```python
from google import genai
from google.genai import types
client = genai.Client()        # reads the key from env
```

---

## 1. Audio understanding — inline (small files)

```python
with open("clip.wav", "rb") as f:
    data = f.read()
resp = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents=[
        types.Part.from_bytes(data=data, mime_type="audio/wav"),
        "Transcribe with MM:SS timestamps; flag any harshness.",
    ],
)
print(resp.text)
```

## 2. Audio understanding — Files API (large / reused)

```python
f = client.files.upload(file="long_mix.wav")          # 2 GB max, ~48h retention
resp = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[f, "Summarize the arrangement section by section."],
)
# reuse `f` across many prompts within 48h; delete early with client.files.delete(name=f.name)
```

## 3. Structured JSON output (the critique pattern)

```python
schema = {
  "type": "object",
  "properties": {
    "issues": {"type": "array", "items": {"type": "object", "properties": {
      "timestamp": {"type": "string"},
      "severity": {"type": "string", "enum": ["minor", "moderate", "serious"]},
      "category": {"type": "string"},
      "suggestion": {"type": "string"},
    }, "required": ["timestamp", "severity", "category"]}},
  },
  "required": ["issues"],
}
resp = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents=[f, "List audible mix issues with MM:SS timestamps."],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
    ),
)
import json; data = json.loads(resp.text)
```
⚠️ Numeric bounds in the schema are **advisory** — clamp/validate after parsing (the repo
enforces schema depth ≤10 / ≤1000 keys, no `$ref`).

## 4. Token counting (budget pre-flight)

```python
n = client.models.count_tokens(model="gemini-2.5-flash", contents=[f, "Analyze"]).total_tokens
# audio is 32 tokens/sec; after the call:
resp.usage_metadata.prompt_token_count, resp.usage_metadata.candidates_token_count
```

## 5. TTS (writes raw PCM → wrap as WAV)

```python
import wave
resp = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents="Welcome to the session! [excited]",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore"))),
    ),
)
pcm = resp.candidates[0].content.parts[0].inline_data.data    # 24kHz/16-bit/mono, no container
with wave.open("vo.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
```

## 6. Live API (async WebSocket — sketch)

```python
config = {"response_modalities": ["AUDIO"]}
async with client.aio.live.connect(
    model="gemini-2.5-flash-native-audio-preview-12-2025", config=config) as session:
    await session.send_realtime_input(
        audio={"data": pcm_16k_mono, "mime_type": "audio/pcm;rate=16000"})
    async for msg in session.receive():
        if msg.data: play(msg.data)        # 24kHz PCM out
```

## 7. Music (Lyria 3)

```python
resp = client.models.generate_content(
    model="lyria-3-pro-preview",
    contents="Upbeat 60s funk instrumental, 120 BPM. [Intro][Verse][Chorus][Outro]",
)  # MP3 bytes by default; request WAV via response_format
```

---

## In-repo helper layer (build new `stemmy-gemini` tools with these)

Don't hand-roll the SDK call in a new tool — reuse the chokepoints so timeouts, model
selection, thinking-tier policy, upload caching, and File-API cleanup all stay centralized:

| Helper | Does | Where |
|---|---|---|
| `audio_part(client, path)` | inline-vs-Files-API routing (80 MB threshold), sha256 upload cache | `_upload.py` |
| `build_multi_audio_contents(client, paths)` | interleave labels + parts for 2–10 files (bounded concurrency) | `_upload.py` |
| `cleanup_uploaded(client, names)` | best-effort File-API delete (skips cached) | `_upload.py` |
| `call_gemini(...)` | the single `generate_content` chokepoint: timeout, thinking config, error mapping | `_call.py` |
| `default_model()` / `validate_model()` | `STEMMY_MCP_MODEL` (default `gemini-3.1-pro-preview`) + allowlist | `_genai.py` |
| `thinking_config_for(tool, model)` | per-tool thinking tier (3.x `thinking_level` vs 2.5 `thinking_budget`) | `_genai.py` |

**New-tool recipe:** add `stemmy_gemini_mcp/tools/<name>.py`, build contents with
`audio_part` / `build_multi_audio_contents`, call `call_gemini`, pass a `response_schema` for
structured output, `cleanup_uploaded` after, and register in `tools/__init__.py`. (For tools
that **emit** audio — TTS/Lyria — see the read-only-invariant caveat in
[speech-generation.md](speech-generation.md) / [music-generation.md](music-generation.md).)

## Gotchas

- `google-genai` ≠ `google-generativeai`.
- TTS returns **raw PCM** — always wrap before saving.
- Voice names are **case-sensitive**.
- Files auto-expire ~48 h — re-upload or rely on the repo's hash cache.
- See [caveats-and-limits.md](caveats-and-limits.md) for mono-downmix, timestamp, and preview caveats.

## Related

- [README.md](README.md) · [audio-understanding.md](audio-understanding.md) · [models-and-pricing.md](models-and-pricing.md)
