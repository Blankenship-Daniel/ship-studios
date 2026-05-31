---
name: stem-split
description: "Use when the user wants to separate a mixdown into stems — 'split this song into stems', 'isolate the drums from this track', 'get the drum stem out of this mix', 'separate for a remix/sample'. Runs Demucs source separation via the stemmy-loops server. Stemmy MCP, not local."
---

# Split a mixdown into stems (Demucs source separation)

Goal: take a finished stereo mixdown and pull an isolated stem back out of it
via Demucs. The stemmy surface currently exposes the **drum stem**
specifically — point a mix at `[L] extract-drums` and get the separated drum
WAV back for remix / sampling / reconstruction work.

One server is in play. Demucs separation lives on **stemmy-loops** (`[L]`).
No Gemini step is required for the split itself. Never invent a tool — every
name below is verified against CLAUDE.md.

## Prerequisites

- `.mcp.json` registers `stemmy-loops` (sibling at `../stemmy-loops-mcp`).
  Confirm the server is up.
- `[L] extract-drums` runs Demucs and needs the **`separate`** extra
  (`uv sync ... --extra separate`). It's GPU/CPU-heavy and pure DSP — no
  `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`, no network beyond fetching the
  Demucs model weights on first run.
- **BPM is required.** Read it from `projects/<track>/track.md`; never guess.
  If it's unknown, ask before running.
- Resolve up front: input mix WAV, BPM, and where the stem should land
  (`artifacts/<run>/` for scratch, or `projects/<track>/stems/` if it's
  feeding a durable per-track workspace).

## Recipe (ordered)

1. **Separate** — `[L] extract-drums {path, bpm}`. Runs Demucs and returns
   the path to the isolated drum stem. Write to `projects/<track>/stems/`
   (durable) or let it land in `artifacts/<run>/` (scratch).
2. **(Optional) verify the split** — `[L] measure-spectrum {path: <drum
   stem>}` to confirm the stem is LF/transient-dominant as expected and
   isn't dragging melodic bleed. Cheap pure-DSP sanity check, no key needed.
3. **Hand off.** The stem is now a normal mono/stereo WAV — feed it into
   whatever comes next (see Related).

**Doing loop work instead?** Don't call `extract-drums` first.
`[L] find-loops {path, bpm, separate: true}` runs the same Demucs separation
*internally* before slicing — one call, not two.

## Outputs

- Isolated drum stem WAV → `projects/<track>/stems/` (or `artifacts/<run>/`).
- The path to that stem is the user-facing artifact.

## Reporting to the user

Give the absolute path to the separated drum stem and state plainly that it's
**Demucs-separated** — expect some bleed and artifacts, it is not a clean
multitrack. If you ran step 2, report the spectrum read as a quick "looks like
drums" / "has melodic bleed" confirmation.

## Pitfalls / honest scope

- **Drum stem only.** The stemmy surface exposes the **drum** stem
  specifically. A full 4-way split (vocals / bass / other) is not wired up —
  it would require extending stemmy-loops. Don't promise stems we can't return.
- **Separation is lossy.** Use the result for remix / sampling / reconstruction,
  not as a clean multitrack. There will be bleed and separation artifacts.
- **A real multi-mic session is not separation.** If the user actually has the
  original Logic session or an interface dump, get the raw recordings via
  [[logic-extract]] / [[multitrack-triage]] — separating a mixdown is strictly
  worse than the captures that already exist.
- **BPM is a number.** `bpm: 120`, not `"120 BPM"`. It's required, not optional.
- **For loops, use `find-loops separate=true`.** Calling `extract-drums` then
  re-feeding the stem to `find-loops` double-runs Demucs for no reason.

## Related

- [[loops-to-deliverables]] — turn the separated stem into tagged, mastered loops
- [[drum-prep]] — phase-align / reference-match a *real* multi-mic kit (not a split)
- [[multitrack-triage]] — clean, song-split, role-label raw multitrack from a session
- [[understand-audio]] — perceptual recon of the mix before deciding to split it
