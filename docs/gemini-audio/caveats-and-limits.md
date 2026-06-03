# Gemini audio — caveats, limits & known gaps

**Status:** reference (read before trusting any Gemini audio read) · **Date:** 2026-05-31 · **Last verified:** 2026-06-03 · **Scope:** all four audio areas.

The capability docs say what Gemini *can* do. This one says where it **silently misleads** or
where the public facts are thin. Most matter directly to mix/master critique. Items flagged
⚠️ are unverified or known-broken.

---

## Decision-critical (these change what you trust Gemini for)

### 1. Gemini hears MONO, ~16 kbps — not your stereo file
Gemini downsamples to ~16 kbps and **sums multichannel to mono** before inference
([docs/audio](https://ai.google.dev/gemini-api/docs/audio)). It therefore **cannot judge**:
stereo width / image, panning, L–R differences, phase/correlation, true-peak, or absolute
loudness.

> **Rule:** meters are ground truth; Gemini is for what meters can't see (harshness, pumping,
> sibilance *feel*, masking, depth, "brittle"). Never let Gemini drive a loudness / peak /
> stereo **amount**. Measure stereo & phase with `[L] measure-stereo` / `[G] analyze-phase-mono`,
> loudness/true-peak with `[L] measure-loudness` — always cross-check a Gemini mastering read against the dBTP/LUFS meters.

### 2. Timestamps are navigation-grade and the flag is broken
- Accuracy ≈ a few **seconds**, not frame-accurate. Fine for "boomy around 01:23"; useless for
  edit-point automation.
- ⚠️ The `audioTimestamp` flag **drifts / is effectively broken** on the public endpoint
  ([python-aiplatform#5056](https://github.com/googleapis/python-aiplatform/issues/5056)).
  Get timestamps via a schema `segments` array and **cross-check the DSP onset detector**.

### 3. Emotion / "feel" reads are inference, not measurement
Emotion and subjective-quality classifications are plausible heuristics — they miss subtlety,
sarcasm, and context. Treat "sounds stressed / warm / harsh" as a **first pass to confirm with
a meter or a second listen**, not a verdict.

### 4. Diarization is model-dependent
- `gemini-2.5-pro`: native, production-grade for ~2–3 speakers.
- `gemini-2.5-flash`: works, degrades with heavy crosstalk / 3+ speakers.
- ⚠️ **`gemini-2.0`**: known bug — MM:SS-MM:SS range requests return random segments; closed
  not-planned. Avoid; it's deprecated anyway.

### 5. Preview instability
The repo default `gemini-3.1-pro-preview`, all TTS models, all Live models, and all Lyria
models are **preview** — IDs, prices, limits, and availability can change without notice. Pin
the model, and don't build an SLA on a preview model. (`gemini-2.5-flash`/`-pro` are GA.)

### 6. ⚠️ Possible Gemini-3 audio/ASR regression
A 2026-06-02 report flags that the **whole Gemini 3 series may have regressed on audio/ASR**
versus the 2.5 line. Unconfirmed, but it means a model bump is **not** a safe drop-in: the
repo default and `gemini-3.5-flash` could read *worse* on real material than `gemini-2.5-pro`.
**Don't auto-upgrade the critique model.** The model-currency decision is **ear-gated** — A/B
candidate models on your own audio (`scripts/gemini_model_ab.py`) before changing
`STEMMY_MCP_MODEL`, and keep `gemini-2.5-pro` as the conservative audio fallback.

---

## Hard limits (verified)

| Limit | Value | Source |
|---|---|---|
| Audio token rate | 32 tokens/sec (≈1,920/min) | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| Max audio / request | 9.5 h combined | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| Inline request cap | ~20 MB cited / ≈100 MB hard; repo routes to Files API at 80 MB | [docs/audio](https://ai.google.dev/gemini-api/docs/audio), `_upload.py` |
| Files API | 2 GB/file, ~48 h retention | [docs/files](https://ai.google.dev/gemini-api/docs/files) |
| Documented formats | WAV, MP3, AIFF, AAC, OGG, FLAC | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| TTS output | raw PCM, 24 kHz, 16-bit mono (no native WAV/MP3 — wrap client-side) | [docs/speech-generation](https://ai.google.dev/gemini-api/docs/speech-generation) |
| TTS speakers / context | ≤2 speakers; 32k-token session | [docs/speech-generation](https://ai.google.dev/gemini-api/docs/speech-generation) |
| Live audio I/O | in 16 kHz PCM mono / out 24 kHz PCM, 16-bit LE | [docs/live](https://ai.google.dev/gemini-api/docs/live) |
| All generated audio | carries an inaudible **SynthID** watermark | [docs/music-generation](https://ai.google.dev/gemini-api/docs/music-generation) |

---

## Known gaps in the public docs (⚠️ verify before relying)

From the research completeness pass — facts implementers hit that Google doesn't pin down:

- **Error codes / rate limits.** Behavior on exceeding 9.5 h, requests-per-second caps, and
  Files API quota-exceeded (the per-project total and whether it's a hard error vs rollover)
  are not clearly documented. Handle defensively.
- **Structured-output validation failures.** Numeric bounds are advisory; the model can emit
  out-of-range or omit non-required fields — **clamp/validate server-side** (the repo does).
- **Prompt caching for audio.** Caching exists; as of 2026-06 **implicit and explicit caching
  give the same ~75% discount** on cached input tokens (the older "~50% / up-to-90%" split is
  stale — [docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)). The explicit-cache
  minimum is ~**4,096 tokens** on `gemini-3.x` (≈ 2:08 of audio at 32 tok/s) and ~**1,024–2,048**
  on `gemini-2.5` — *not* the old ~32,768-token floor — so a typical 3–4 min mix (~5,760–7,680
  audio tokens) **clears it**, and caching one file across a multi-tool run is worthwhile. Treat
  exact figures as ⚠️ version-dependent and re-check. See
  [models-and-pricing.md](models-and-pricing.md#context-caching).
- **Mono-downmix algorithm** (simple L+R/2? envelope?) is unspecified — so "sounds thin" from
  Gemini could be a downmix artifact. Cross-check with a meter.
- **TTS audio-tag taxonomy.** Many inline tags exist (`[whispers]`, `[excited]`, …) but there's
  no exhaustive published list or defined unsupported-tag behavior. Test the tags you need.
- **Live API session/WebSocket specifics.** Session caps (commonly cited ~15 min audio-only /
  ~2 min audio+video, ~10 min socket life with resumption) and context-compression behavior
  are version-specific and thinly documented — ⚠️ confirm in the live guide.
- **Lyria RealTime** is experimental; control-latency and exact stream format (research cites
  PCM 48 kHz, ~2 s control latency) are not firmly pinned — ⚠️.
- **Post-cutoff model IDs.** Verify any newer name against the live
  [models](https://ai.google.dev/gemini-api/docs/models) page. `gemini-3.5-flash` is now GA
  (2026-05-19, audio-capable). This reference centers on `gemini-3.1-pro-preview` (repo default)
  and the GA 2.5 line, with `gemini-3.5-flash` as a GA flash alternative — but the whole Gemini 3
  series carries an ⚠️ audio-regression caveat (see #6 below); pick by ear, not by version number.

---

## Related

- [README.md](README.md) · [audio-understanding.md](audio-understanding.md) · [models-and-pricing.md](models-and-pricing.md)
- [`../mix-master-capability-roadmap.md`](../mix-master-capability-roadmap.md) — "The one finding that shapes everything" expands on caveat #1.
- `[[gemini-audio]]` · `[[mix-check]]` · `[[master-track]]`
