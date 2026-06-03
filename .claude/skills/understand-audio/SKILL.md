---
name: understand-audio
description: Use when the user wants to understand a reference track or stem perceptually — "what's in this audio", "transcribe this", "what happens at 1:30", "find every kick / drop / crash", "is this house or techno", "compare these references", "pull the song structure as JSON". Pure Gemini audio understanding via stemmy-gemini — no rendering, never modifies the audio. The recon step before [[mix-check]] / [[master-track]] / [[reference-match]].
argument-hint: <audio.wav> [question or goal]
---

# Understand audio perceptually (Gemini)

Goal: answer questions *about* a piece of audio — transcription, what
happens in a region, where specific events occur, what genre/tags fit, how
candidates differ, or a structured pull of song structure. This is the
listen-and-describe stage; it reads audio and returns understanding, it
never writes a new WAV.

Every tool here is on **stemmy-gemini** (`stemmy-gemini:*`). This skill picks
the right one (or few) for the ask rather than running a fixed chain — the
"recipe" is a routing table.

## Prerequisites

- `stemmy-gemini` registered and running.
- All perceptual tools below need `GEMINI_API_KEY` (and `google-genai`,
  which is a hard dependency of the gemini server — `uv sync`, no extra).
- For long inputs (>1 hour / >100 MB) the file goes through Gemini's File
  API automatically inside `summarize-long-audio`; other tools assume an
  ordinary-length clip.

## Route by the ask

| User wants | Tool (`stemmy-gemini:`) | Key params |
|---|---|---|
| Speech / lyrics with timestamps | `transcribe-audio` | `path`, `diarize`, `language` |
| "What happens between X and Y" | `describe-audio-region` | `path`, `start_s`, `end_s`, `prompt` |
| "Find every <event>" (kick, drop, crash, vocal entry) | `extract-audio-events` | `path`, `event_description` |
| "Is this <genre/tag>?" / zero-shot tagging | `classify-audio` | `path`, `labels`, `multi_label` |
| Compare 2–10 candidates / references | `compare-audio-files` | `paths`, `prompt`, `schema` |
| Structured pull (song structure, chapters, instrument inventory, sentiment) | `audio-to-json` | `path`, `prompt`, `schema` |
| Long-form summary (>1 h / >100 MB; routes via Gemini's File API) | `summarize-long-audio` | `path`, `prompt` |

For most asks one tool suffices. Chain only when the ask is genuinely
compound, e.g. "transcribe it and tell me where the chorus hits" →
`transcribe-audio` then `extract-audio-events {event_description: "chorus
section start"}`.

## Recipe (typical single-tool calls)

1. **Transcription** — `stemmy-gemini:transcribe-audio {path, diarize}`.
   MM:SS timestamps per segment; `diarize: true` when the user cares who
   speaks.
2. **Region Q&A** — `stemmy-gemini:describe-audio-region {path, start_s,
   end_s, prompt}`. Convert any "at 1:30" to seconds (`start_s: 90`) and
   scope the prompt tightly to that window.
3. **Event detection** — `stemmy-gemini:extract-audio-events {path,
   event_description}`. Describe the event in plain language; returns
   timestamped instances for arrangement understanding.
4. **Zero-shot tagging** — `stemmy-gemini:classify-audio {path, labels,
   multi_label}`. Supply the candidate label list; `multi_label: true` when
   several can apply at once.
5. **Multi-file comparison** — `stemmy-gemini:compare-audio-files {paths,
   prompt, schema}`. 2–10 files; pass a `schema` when you want the
   discriminating features back as structured JSON.
6. **Deep structured extraction** — `stemmy-gemini:audio-to-json {path,
   prompt, schema}`. For song structure, chapter lists, instrument
   inventories — define the JSON Schema and let the model fill it.

## Outputs

Findings only — text/JSON summaries. **Never** write a processed WAV from
this skill. If the user wants the audio changed based on what you found,
route to the appropriate processing skill.

## Reporting to the user

Summarize the answer directly, with timestamps where the tool returned them.
For comparisons, lead with the single most discriminating feature. For
structured pulls, show the JSON and a one-line gloss. If the finding implies
a next action ("the low end is muddy" / "this is a techno reference"), name
the skill to run next.

## Pitfalls

- **Timestamps in / out.** `describe-audio-region` takes seconds
  (`start_s` / `end_s`), but `transcribe-audio` and `extract-audio-events`
  *return* MM:SS — convert when feeding one into the other.
- **`classify-audio` needs labels.** It's zero-shot against *your* list, not
  open-vocabulary; supply realistic candidate tags.
- **Read-only.** No tool here renders audio. Don't promise an output WAV.
- **This is recon, not measurement.** For objective LUFS/spectrum numbers use
  the DSP tools in [[mix-check]] / [[master-track]]; this skill is the
  perceptual half.

## Related

- [[mix-check]] — once recon surfaces a problem, diagnose + fix it
- [[reference-match]] — after comparing references, match the mix to the winner
- [[loops-to-deliverables]] — after finding the loopable / drop sections, slice them
- [[master-track]] — after choosing a target from a reference, master to it
- [[gemini-audio-understanding]] — reference for what these Gemini tools can do + their limits (Gemini hears mono — judge stereo/phase with the DSP meters)
