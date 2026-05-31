# Gemini Live API — real-time audio (audio in ↔ audio out)

**Status:** reference + wire-up note (NOT wired in this repo) · **Date:** 2026-05-31 · **Last verified:** 2026-05-31 against [docs/live](https://ai.google.dev/gemini-api/docs/live) · all models **⚠️ preview**.

The Live API is a **stateful WebSocket** for low-latency, bidirectional voice — the model
listens and speaks in real time, with interruption (barge-in) and emotional adaptation. **Not
wired into `stemmy-gemini`**, and structurally awkward for an MCP server (see wire-up note).
Skill: `[[gemini-live-audio]]`.

---

## Audio I/O (verified)

| Direction | Format |
|---|---|
| **Input** | raw **16-bit PCM, 16 kHz**, little-endian, mono |
| **Output** | raw **16-bit PCM, 24 kHz**, little-endian |

Audio streams as base64 chunks over the WebSocket.

## Capabilities

- **Voice Activity Detection + barge-in** — the user can interrupt the model mid-response.
- **Affective dialog** — adapts response style/tone to the user's expression. ⚠️ Reported as a
  2.5-native-audio feature; the newer 3.1 live model may not support it — verify in the
  [live guide](https://ai.google.dev/gemini-api/docs/live).
- **Proactive audio** / async function calling — model-dependent.

## Models

| Model | Notes |
|---|---|
| `gemini-2.5-flash-native-audio-preview-12-2025` | native audio I/O |
| `gemini-3.1-flash-live-preview` | newest preview live model |

Prices in [models-and-pricing.md](models-and-pricing.md) (≈$0.005/min in, $0.018/min out).

## Session limits ⚠️

The overview page doesn't pin these; the live guide / research indicate **~15 min audio-only**,
**~2 min audio+video** (hard), ~10 min WebSocket lifetime with resumption, and a context window
around 128k tokens with optional context-window compression to extend. **Treat as version-
specific and confirm in the [live guide](https://ai.google.dev/gemini-api/docs/live) before
building.**

## SDK pattern (sketch)

```python
from google import genai
client = genai.Client()
config = {"response_modalities": ["AUDIO"]}
async with client.aio.live.connect(
    model="gemini-2.5-flash-native-audio-preview-12-2025", config=config
) as session:
    await session.send_realtime_input(audio={"data": pcm16k, "mime_type": "audio/pcm;rate=16000"})
    async for msg in session.receive():
        if msg.data:  # 24kHz PCM out
            play(msg.data)
```

## Wire-up note (why it's out-of-band for this MCP)

MCP tools are **request → response**; the Live API is a **persistent duplex stream**. It does
not fit a stdio tool call. A realistic integration would be a **separate long-running process /
service** (not a `stemmy-gemini` tool) for a "live monitoring / spoken review" UX. Per the
roadmap this is a future UX feature, **not a critique-quality win** (and it still hears mono —
[caveats-and-limits.md](caveats-and-limits.md)).

## Related

- `[[gemini-live-audio]]` · [README.md](README.md) · [sdk-patterns.md](sdk-patterns.md) · [`../mix-master-capability-roadmap.md`](../mix-master-capability-roadmap.md)
