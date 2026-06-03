---
name: drum-tune
description: Use when the user wants to tune a drum sample to the song — "tune the kick to the key", "what note is this kick", "pitch this tom", "these samples clash with the bass". Measures a drum's fundamental (Hz/note/cents) and, optionally, retunes a SAMPLE by resampling. Local drum-prep CLI, not the stemmy MCP servers.
argument-hint: <sample.wav> [target key/note]
---

# Tune a drum sample to the song

Goal: find a drum hit's pitched fundamental (Hz / note / cents) and, when asked,
retune that **sample** toward a target so it sits with the song's key/root instead
of clashing with the bass. Retuning is done by **resampling**, which shifts pitch
**and duration together** — so this is a one-shot/sample tool, not a performance
tool.

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/scipy/soundfile). No keys/network.
- A single drum **sample** WAV — one hit (kick, tom, or other pitched drum), not a
  full performance/loop.
- The song's key/root if you intend to retune (so you know the target note).

## Recipe (ordered)

1. **Measure** — `drum-prep tune "<sample.wav>"` (no `--out`). Returns the
   fundamental as `hz`, a note name (e.g. `B1`), and `cents` off that note. This is
   read-only; use it to answer "what note is this kick" and to decide a target.
2. **Pick a target** (only if retuning) — choose exactly one of:
   - `--target-hz <Hz>` — an explicit frequency.
   - `--target-midi <n>` — a MIDI note number (e.g. the song's root in the sub
     octave).
   - `--semitones <s>` — a relative shift in semitones (± fractional ok).
3. **Retune** — `drum-prep tune "<sample.wav>" --out "<out.wav>" <one target flag>`.
   Resamples toward the target. Pitched **up** ⇒ shorter file; **down** ⇒ longer.

## Outputs

- Measure-only: no files — just the printed `hz` / note / `cents`.
- With `--out`: one resampled sample WAV at the given path.

## Reporting to the user

- Measure: state `hz`, the note name, and `cents` off (e.g. "≈ 61.7 Hz, B1, +12
  cents — sharp of B1").
- Retune: report `from_hz`/`from_note` → `to_hz`/`to_note`, the resample `ratio`,
  and frames in → out (shorter = pitched up). Name the target note relative to the
  song key so the user can confirm it locks to the root.

## Pitfalls

- **Never retune a full drum TRACK or loop** — resampling changes its tempo. This
  is for single samples only; pitch-preserving time-stretch is out of scope.
- **For a kit**: retune the kick/tom **samples**, then re-trigger them in the
  arrangement — don't resample the recorded performance.
- **Tune to the song**, not in isolation — pick the target from the song's
  key/root (usually the sub-octave) so the kick reinforces the bass instead of
  beating against it.
- **Exactly one** of `--target-hz` / `--target-midi` / `--semitones` per retune.
- A weak/short transient-only hit may give an unstable fundamental — trust the
  reading more on a kick/tom with audible sustain.

## Related

- [[sub-design]] — design/shape the sub once the kick is tuned to the root
- [[drum-prep]] — phase-align + reference-match + audition a full multi-mic kit
