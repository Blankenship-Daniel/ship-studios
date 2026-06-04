# Gemini audio understanding (audio in → text / JSON)

**Status:** reference · **Date:** 2026-05-31 · **Last verified:** 2026-05-31 · **Source:** [docs/audio](https://ai.google.dev/gemini-api/docs/audio), [docs/files](https://ai.google.dev/gemini-api/docs/files) · **Repo:** this is the area `stemmy-gemini` fully implements.

Gemini accepts audio as a first-class input modality and reasons over it the way it reasons
over text or images. You send audio (inline or via the Files API) plus a prompt; you get back
text or schema-constrained JSON. This is the **only** Gemini audio area `ship-studios` wires
up — every perceptual tool on `stemmy-gemini` is a thin wrapper over a `generate_content` call
with an audio `Part`. Skill: `[[gemini-audio-understanding]]`; pipeline skill: `[[understand-audio]]`.

---

## What it can do (tasks) → which repo tool implements it

| Task | What Gemini does | `stemmy-gemini` tool |
|---|---|---|
| **Transcription** | Speech → text, with MM:SS timestamps; optional speaker diarization | `transcribe-audio` |
| **Region Q&A** | Answer about a `[start_s, end_s]` window | `describe-audio-region` |
| **Multi-file comparison** | Discriminate 2–10 files in one request | `compare-audio-files`, `compare-to-reference` |
| **Zero-shot classification** | Tag against *your* label list (not open-vocab) | `classify-audio` |
| **Event detection** | Timestamped instances of a described event (kicks, drops, crashes) | `extract-audio-events` |
| **Long-audio summarization** | Summarize >1 h / >100 MB sources via Files API | `summarize-long-audio` |
| **Structured extraction** | Fill an arbitrary JSON schema from audio | `audio-to-json` |

The six rows above are the **understand-audio** pipeline (`[[understand-audio]]`). The
mix/master critique tools that *also* run on this same audio-in machinery — `analyze-mix-balance`,
`detect-mix-issues`, `compare-to-reference`, `mastering-feedback`, `recommend-mastering-chain` —
are **not** part of the understand pipeline; they belong to the **mix-check**, **master-track**,
and **reference-match** pipelines (`[[mix-check]]` / `[[master-track]]` / `[[reference-match]]`).
They're listed under "Related Gemini tools beyond audio understanding" at the bottom of this page.

> *Stereo/width is a perceptual guess only — Gemini hears mono. See caveats.*

**Non-speech understanding is real.** Gemini describes music, ambience, and SFX, not just
speech — which is exactly what the mix/master critique tools lean on (harshness, pumping,
masking). Don't confine it to transcription.

---

## Getting audio in

Two transports, picked by size:

### Inline (base64 `Part.from_bytes`)
- One round-trip, no expiring artifact. Cheapest for small clips.
- Practical cap: **~20 MB** is the commonly-cited inline limit; the hard request payload is
  ≈100 MB including prompt + schema. `stemmy-gemini` conservatively routes to the Files API at
  **80 MB** (`_upload.py::INLINE_LIMIT_BYTES`) to leave headroom.
- SDK: `types.Part.from_bytes(data=..., mime_type='audio/wav')`.

### Files API (`client.files.upload` → `Part.from_uri`)
- Use for large or repeatedly-referenced audio. **Upload once, reference many times** (e.g.
  iterating critique prompts on the same mix).
- Limits: **2 GB** per file, ~**48 h** retention ([docs/files](https://ai.google.dev/gemini-api/docs/files)).
- `stemmy-gemini` caches uploads by content sha256 (in-process + a 48h sidecar) so the same
  file isn't re-uploaded across tool calls (`_upload.py`).
- SDK: `f = client.files.upload(file='mix.wav'); contents=[f, "prompt"]`.

See [sdk-patterns.md](sdk-patterns.md) for full code.

### Formats
Google documents six: **WAV, MP3, AIFF, AAC, OGG (Vorbis), FLAC**
([docs/audio](https://ai.google.dev/gemini-api/docs/audio)). `stemmy-gemini` additionally
accepts `m4a` (audio/mp4), `opus`, and `webm` by MIME type (`_upload.py::_MIME_TYPES`); if a
format misbehaves, re-encode to WAV (see `[[format-fix]]`).

### What Gemini does to your audio (automatic, lossy)
- **Downsamples to ~16 kbps** and **mixes to mono** before the model hears it.
- High-res sources (96 kHz stereo FLAC) gain nothing — fidelity is normalized for content,
  not audiophile playback. **Consequence:** Gemini is blind to stereo image, true-peak, and
  absolute loudness. Measure those with DSP. (Full detail: [caveats-and-limits.md](caveats-and-limits.md).)

---

## Cost & limits

- **32 tokens/second**, fixed across models — so cost scales only with duration, not bitrate
  or channels. 1 min ≈ 1,920 tokens; 1 h ≈ 115,200 tokens. Formula:
  `seconds × 32 ÷ 1e6 × price_per_M_tokens` ([models-and-pricing.md](models-and-pricing.md)).
- **9.5 hours** max combined audio per request. Longer jobs must be **chunked**; for album/podcast
  work, 3–15 min chunks critiqued independently keep each call cheap and within context.
- Pre-flight a token budget with `client.models.count_tokens(...)` before a big call.

---

## Timestamps & structured output

- **Timestamps are not automatic** — ask for them explicitly ("provide MM:SS timestamps for
  each issue"). Gemini otherwise returns prose without positions.
- **Accuracy is navigation-grade (~seconds), not frame-accurate.** Good for "boomy kick around
  01:23"; for sub-second sync use forced alignment, not Gemini.
- ⚠️ The dedicated `audioTimestamp` request flag is **effectively broken / drifts** on the
  public endpoint ([python-aiplatform#5056](https://github.com/googleapis/python-aiplatform/issues/5056)).
  **Get timestamps via a schema `segments` array** and cross-check against the DSP onset
  detector — which is exactly what `stemmy-gemini`'s `transcribe-audio` /
  `extract-audio-events` do.
- **Structured JSON**: pass `response_mime_type="application/json"` + a `response_schema`.
  Supports `enum`, `nullable`, `minItems/maxItems`, numeric `minimum/maximum`, and (Nov 2025)
  `additionalProperties` — but **numeric bounds are advisory, not enforced**, so clamp
  server-side (`stemmy-gemini` validates schema depth ≤10 / ≤1000 keys and clamps).
  ([docs/structured-output](https://ai.google.dev/gemini-api/docs/structured-output))

---

## Models for understanding

Any current Gemini multimodal model accepts audio input and returns **text** (none of the
understanding-capable models return audio — that's TTS/Live). Practical picks:

- `gemini-3.1-pro-preview` — the repo default; best for compound critique (tonal + dynamics +
  feel). Audio-in, text-out. ⚠️ preview.
- `gemini-2.5-pro` — strong, GA; **best native speaker diarization** for multi-speaker work.
- `gemini-2.5-flash` / `-flash-lite` — cheaper, fast; good for quick classification / "is this
  clipped?" Diarization degrades with heavy crosstalk.
- ⚠️ **Avoid `gemini-2.0`** for production — deprecated (sunsetting 2026), and has a known
  MM:SS-range transcription bug.

See [models-and-pricing.md](models-and-pricing.md) for the full table and prices, and
[caveats-and-limits.md](caveats-and-limits.md) for diarization/emotion caveats.

---

## Related Gemini tools beyond audio understanding

These run on the same audio-in machinery but are **perceptual critique**, not understanding —
they live in other pipelines, so don't reach for them from the understand step:

| Tool | Pipeline / skill |
|---|---|
| `analyze-mix-balance` | mix-check (`[[mix-check]]`) |
| `detect-mix-issues` | mix-check (`[[mix-check]]`) |
| `compare-to-reference` | reference-match (`[[reference-match]]`) |
| `mastering-feedback` | master-track (`[[master-track]]`) |
| `recommend-mastering-chain` | master-track (`[[master-track]]`) |

All five should respect the mono-downsample caveat (Gemini can't judge stereo/true-peak/loudness).

---

## Related

- `[[understand-audio]]` — the pipeline skill that *uses* these tools (routing table for the ask).
- `[[mix-check]]` / `[[master-track]]` / `[[reference-match]]` — the perceptual-critique pipelines built on this area; all should respect the mono-downsample caveat.
- [caveats-and-limits.md](caveats-and-limits.md) · [sdk-patterns.md](sdk-patterns.md) · [models-and-pricing.md](models-and-pricing.md)
