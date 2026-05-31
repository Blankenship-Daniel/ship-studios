# Gemini audio — models & pricing

**Status:** reference · **Date:** 2026-05-31 · **Last verified:** 2026-05-31 against [docs/models](https://ai.google.dev/gemini-api/docs/models) and [docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) · **Scope:** which models do audio, context, and audio token prices.

⚠️ Prices and model IDs change often and several entries are **preview**. Every figure is from
the May 2026 pricing/models pages; re-fetch before committing a budget. Prices are USD per 1M
tokens, paid standard tier.

---

## Audio token rate (the foundation)

Audio is metered at **32 tokens/second**, fixed across models, independent of bitrate/channels.

```
audio_cost_usd = duration_seconds × 32 ÷ 1_000_000 × input_price_per_M
```

| Duration | Tokens | @ $1.00/M (2.5 Flash audio-in) |
|---|---|---|
| 1 min | 1,920 | $0.0019 |
| 10 min | 19,200 | $0.019 |
| 1 hour | 115,200 | $0.115 |

---

## Audio-INPUT (understanding) models

All return **text** (not audio). Context window for the current Pro/Flash lines is **1M tokens**.

| Model | Audio in | Status | Text in (≤200k) | Audio in | Output |
|---|---|---|---|---|---|
| `gemini-3.1-pro-preview` *(repo default)* | ✅ | ⚠️ preview | $2.00 (>200k: $4.00) | not separately listed → billed at the input-token rate | $12.00 (>200k: $18.00) |
| `gemini-2.5-pro` | ✅ | GA | $1.25 (>200k: $2.50) | not separately listed | $10.00 (>200k: $15.00) |
| `gemini-2.5-flash` | ✅ | GA | $0.30 | **$1.00** | $2.50 |
| `gemini-2.5-flash-lite` | ✅ | GA | $0.10 | **$0.30** | $0.40 |

Notes:
- Pro models don't break audio out as a separate line — audio input is billed at the model's
  standard input-token price (×32 tokens/sec).
- ⚠️ The research pass surfaced a "gemini-3.5-flash" entry that could **not** be confirmed on
  the live models page; it is intentionally omitted. Verify any sub-3.1 / post-3.1 names live.

**Picking a model:** compound critique (tonal + dynamics + feel) → `gemini-3.1-pro-preview`
(repo default) or `gemini-2.5-pro` (GA, best diarization); cheap/fast classification →
`gemini-2.5-flash` / `-flash-lite`. See [audio-understanding.md](audio-understanding.md).

---

## Audio-OUTPUT (TTS) models

Output is raw PCM 24 kHz 16-bit mono. All **preview**. ([speech-generation.md](speech-generation.md))

| Model | Status | Text in | Audio out |
|---|---|---|---|
| `gemini-2.5-flash-preview-tts` | ⚠️ preview | $0.50 | **$10.00** |
| `gemini-2.5-pro-preview-tts` | ⚠️ preview | $1.00 | **$20.00** |
| `gemini-3.1-flash-tts-preview` | ⚠️ new preview | $1.00 | **$20.00** |

---

## Live / native-audio models

Bidirectional audio (16 kHz in / 24 kHz out). All **preview**. ([live-api.md](live-api.md))

| Model | Status | Audio in | Audio out |
|---|---|---|---|
| `gemini-3.1-flash-live-preview` | ⚠️ new preview | $3.00 (≈$0.005/min) | $12.00 (≈$0.018/min) |
| `gemini-2.5-flash-native-audio-preview-12-2025` | ⚠️ preview | $3.00 | $12.00 |

---

## Music generation (Lyria) models

Billed differently (per-generation/clip, not always per audio-token). ([music-generation.md](music-generation.md))

| Model | Status | Output |
|---|---|---|
| `lyria-3-clip-preview` | ⚠️ preview | 30 s MP3, 44.1 kHz stereo |
| `lyria-3-pro-preview` | ⚠️ preview | full-length MP3 (opt. WAV), 44.1 kHz stereo |
| Lyria RealTime | ⚠️ experimental | streaming PCM (research: 48 kHz) |

---

## Context caching

Caching a long audio file once and reusing it across a multi-tool run cuts repeat input cost.
The pricing page currently lists ~**50%** off cached-content retrieval; the repo roadmap cites
up to **90%** implicit on the 2.5+ generation (minimum ~32,768 tokens ≈ 17 min of audio).
⚠️ Treat the exact discount as version-dependent — see [docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)
and [docs/caching](https://ai.google.dev/gemini-api/docs/caching).

---

## Deprecations

- ⚠️ **`gemini-2.0` Flash** (audio-capable) is **deprecated** and sunsetting in 2026 — migrate
  to 2.5 or 3.x. Beyond the deprecation, 2.0 has a known MM:SS-range transcription bug. See
  [docs/deprecations](https://ai.google.dev/gemini-api/docs/deprecations).

---

## Related

- [README.md](README.md) · [audio-understanding.md](audio-understanding.md) · [caveats-and-limits.md](caveats-and-limits.md) · [sdk-patterns.md](sdk-patterns.md)
- Repo model default + override: `STEMMY_MCP_MODEL` (`_genai.py::default_model`).
