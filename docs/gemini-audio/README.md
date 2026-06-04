# Gemini audio capabilities — reference index

**Status:** reference (what the Gemini API can do today) · **Date:** 2026-05-31 · **Last verified:** 2026-05-31 against the official [Gemini API docs](https://ai.google.dev/gemini-api/docs) · **Scope:** every Gemini *audio* capability, with the subset `ship-studios` actually wires up called out.

This folder is the single source of truth for **what Gemini models can do with audio** —
not a proposal (that's [`../mix-master-capability-roadmap.md`](../mix-master-capability-roadmap.md)),
but a grounded reference an agent can pull on demand. It is wired into the skill surface as
the **`gemini-audio`** suite (`[[gemini-audio]]`, `[[gemini-audio-understanding]]`,
`[[gemini-speech-generation]]`, `[[gemini-live-audio]]`, `[[gemini-music-generation]]`) — ask
about Gemini audio and the matching skill routes you here.

> **Verification caveat.** Today is 2026-05-31; the model lineup moves fast and several
> facts below are **preview** features. Every hard number cites its source page. Re-fetch the
> cited page before betting a build on a number, and treat anything flagged ⚠️ as
> verify-before-use. Where this reference and a model's own docs disagree, the live docs win.

---

## The four audio capability areas

Gemini audio splits into one **input** area and three **output** areas:

| # | Area | Direction | What it is | In this repo? | Doc |
|---|---|---|---|---|---|
| 1 | **Audio understanding** | audio **in** → text/JSON out | Transcribe, describe, classify, Q&A, event-detect, summarize, structured-extract | ✅ **Yes** — the audio-in `stemmy-gemini` tools (see "How this maps to the repo today") | [audio-understanding.md](audio-understanding.md) |
| 2 | **Speech generation (TTS)** | text **in** → speech **out** | Controllable narration, 30 voices, multi-speaker | ❌ Not wired (read-only server) | [speech-generation.md](speech-generation.md) |
| 3 | **Live API (real-time audio)** | audio **in** ↔ audio **out** | Low-latency bidirectional voice, VAD, barge-in | ❌ Not wired (stdio req/resp shape) | [live-api.md](live-api.md) |
| 4 | **Music generation (Lyria)** | text **in** → music **out** | Instrumental/song generation, real-time steering | ❌ Not wired | [music-generation.md](music-generation.md) |

Supporting references:

- [models-and-pricing.md](models-and-pricing.md) — which model does what, context windows, **audio token pricing**, deprecations.
- [sdk-patterns.md](sdk-patterns.md) — `google-genai` Python patterns for every area, anchored to this repo's own `stemmy-gemini-mcp` code.
- [caveats-and-limits.md](caveats-and-limits.md) — the decision-critical limits + known gaps (read this before trusting any Gemini audio read).

---

## The one finding that shapes everything

> Gemini **downsamples audio to ~16 kbps and mixes multichannel down to MONO** before the
> model ever "hears" it ([docs/audio](https://ai.google.dev/gemini-api/docs/audio)).

So Gemini **cannot hear true stereo width, true-peak, or absolute loudness.** Use it for what
meters can't see — harshness, pumping, sibilance *feel*, masking, depth, "too brittle" — and
keep **meters as ground truth** for any loudness/peak/stereo *amount*
(`[L] measure-stereo` / `[G] analyze-phase-mono` for stereo & phase). This matches the
repo's standing policy of cross-checking any Gemini mastering read against the meters, and the
roadmap's headline finding. Full treatment in [caveats-and-limits.md](caveats-and-limits.md).

---

## Audio at a glance (the numbers you reach for most)

| Fact | Value | Source |
|---|---|---|
| Audio token rate | **32 tokens / second** (≈1,920 tokens/min) — fixed across models | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| Max audio per request | **9.5 hours** combined | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| Inline (base64) request cap | ~**20 MB** commonly cited; hard request payload ≈100 MB. `stemmy-gemini` routes to the Files API at **80 MB** | [docs/audio](https://ai.google.dev/gemini-api/docs/audio), `_upload.py` |
| Files API | per-file **2 GB**, ~**48 h** retention | [docs/files](https://ai.google.dev/gemini-api/docs/files) |
| Google-documented formats | WAV, MP3, AIFF, AAC, OGG (Vorbis), FLAC | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| Repo default model | `gemini-3.1-pro-preview` (audio-in, **text-out**) | `_genai.py::default_model` |
| Audio cost formula | `seconds × 32 ÷ 1e6 × price_per_M` | see [models-and-pricing.md](models-and-pricing.md) |

---

## How this maps to the repo today

`stemmy-gemini-mcp` is an **audio-understanding** server built on Gemini perceptual tools, all
audio-in → text/JSON, plus a parallel pure-DSP measurement suite. They split two ways:

- **Audio-understanding** (the `understand-audio` pipeline) — `transcribe-audio`,
  `describe-audio-region`, `extract-audio-events`, `classify-audio`, `compare-audio-files`,
  `audio-to-json`, and `summarize-long-audio`.
- **Perceptual mix/master critique** (the mix-check / master-track / reference-match pipelines)
  — `analyze-mix-balance`, `detect-mix-issues`, `compare-to-reference`, `mastering-feedback`,
  `critique-region`, `master-assistant`, and `recommend-mastering-chain`.

Two of these — `summarize-long-audio` and `recommend-mastering-chain` — are **documented
reference tools, not yet wired into a pipeline** (no canonical pipeline calls them today); the
rest are wired into the pipelines named above.

The server is **read-only** — it uploads audio and returns text/JSON, never writes audio (see
the stemmy-gemini-mcp repo's `SECURITY.md`). That's why areas 2–4 (which *emit* audio) are
documented here as **reference + wire-up notes**, not as live tools:

- **Speech/TTS & Music/Lyria** would write audio files — a new capability that breaks the
  read-only invariant; [speech-generation.md](speech-generation.md) / [music-generation.md](music-generation.md)
  sketch where such a tool would slot in (`stemmy_gemini_mcp/tools/`, reusing `_call.call_gemini`).
- **Live API** needs a persistent WebSocket, which doesn't fit the stdio request/response MCP
  shape; [live-api.md](live-api.md) flags it as out-of-band.

For *building* any of these, the new-tool recipe and SDK patterns live in
[sdk-patterns.md](sdk-patterns.md). For the proposed *future* DSP capabilities (de-esser,
matched-EQ, dynamic EQ…), see [`../mix-master-capability-roadmap.md`](../mix-master-capability-roadmap.md).

---

## Discovering this on demand

- **Skills** (agent routing): the `gemini-audio` umbrella skill answers "what can Gemini do
  with audio / which model / how much does it cost", and the four per-area skills go deep. Each
  skill links back to its doc here.
- **CLAUDE.md** points here from the stemmy-gemini description and the Understand / Perceptual
  tables.
- Convention: these reference skills link to their doc file (a deliberate extension of the
  usual skill→skill wikilink convention — see CLAUDE.md › Conventions).
