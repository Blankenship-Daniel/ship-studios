# Gemini audio — models & pricing

**Status:** reference · **Date:** 2026-05-31 · **Last verified:** 2026-06-03 against [docs/models](https://ai.google.dev/gemini-api/docs/models) and [docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) · **Scope:** which models do audio, context, and audio token prices.

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
| `gemini-3.5-flash` | ✅ | GA (2026-05-19) | not separately listed | not separately listed → billed at the input-token rate | — |
| `gemini-2.5-pro` | ✅ | GA | $1.25 (>200k: $2.50) | not separately listed | $10.00 (>200k: $15.00) |
| `gemini-2.5-flash` | ✅ | GA | $0.30 | **$1.00** | $2.50 |
| `gemini-2.5-flash-lite` | ✅ | GA | $0.10 | **$0.30** | $0.40 |

Notes:
- Pro models don't break audio out as a separate line — audio input is billed at the model's
  standard input-token price (×32 tokens/sec).
- `gemini-3.5-flash` is now **GA (announced 2026-05-19)**, audio-capable, with a 1M-token input
  / 64K-token output window. (An earlier research pass couldn't confirm it on the live models
  page; it has since shipped.) Re-fetch its exact per-token prices before committing a budget —
  they weren't broken out as a separate audio line on the pricing page at last check.

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
As of 2026-06, **implicit and explicit caching give the same ~75% discount** on cached input
tokens (the older "~50% / up-to-90%" split is stale). The explicit-cache **minimum** is
~**4,096 tokens** on `gemini-3.x` (≈ 2:08 of audio at 32 tok/s) and ~**1,024–2,048 tokens** on
`gemini-2.5` — so the earlier "~32,768 tokens ≈ 17 min" floor no longer holds. A typical
3–4 min mix is ~**5,760–7,680 audio tokens** (32 tok/s), which **clears** the 3.x minimum, so a
multi-tool critique run over one mix is worth caching.
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
