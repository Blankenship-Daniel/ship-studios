---
name: drum-audition
description: Use when the user wants to hear the drum-prep result fairly — "A/B my drums before and after", "render a loudness-matched audition", "let me hear the EQ change", "compare my kit to the reference". Builds coherent stereo kit sums and renders loudness-matched (ITU-R BS.1770) A/B WAVs: before-vs-after EQ, and reference-vs-after. Local drum-prep CLI, not the MCP servers.
argument-hint: <stems dir> <reference.wav>
---

# Loudness-matched A/B auditions of a drum kit

Goal: let the user judge the prep honestly, with loudness removed as a bias. Two
stereo A/Bs — before-vs-after the reference-match EQ (hear only the tone change),
and reference-vs-after (character check vs the target).

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.
Unlike the MCP `render-ab` (mono, single file), this builds a coherent **stereo**
kit sum from the stems so you hear the overhead/room image and the air the EQ
touched.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/soundfile/pyloudnorm). No keys/network.
- A **phase-aligned** set (`<dir>/phase-aligned/`) and a **reference-matched** set
  (`<dir>/ref-matched/`) — i.e. run [[drum-phase-align]] then
  [[drum-reference-match]] first.
- The reference file used for the match.

## Recipe (ordered)

1. **Render** — `drum-prep audition "<dir>" --reference "<ref>"`. Builds coherent
   stereo sums of the aligned ("before") and matched ("after") stems, takes the
   same excerpt of each, and writes two loudness-matched A/Bs:
   - `AB_before-vs-after.wav` — after matched to before's LUFS (hear the EQ only)
   - `AB_reference-vs-after.wav` — after matched to the reference's LUFS
   Knobs: `--t0` / `--dur` (excerpt start/length, default 44 s / 12 s), `--gap`
   (default 0.6 s), `--aligned-dir` / `--matched-dir` / `--out-dir`.
   It also writes standalone loudness-matched halves (surfaced as `gemini_halves`):
   `<out-dir>/cmp_reference.wav` and `cmp_after.wav` (on by default; `--no-emit-halves`
   to skip).
2. **(Optional) Perceptual A/B** — feed the halves straight to the stemmy-gemini
   `compare-to-reference` tool (`mix_path=cmp_after.wav`,
   `reference_path=cmp_reference.wav`) for an ears-on read — no manual slicing of the
   concatenated AB file. See [[reference-match]] for the MCP analogue.

## Outputs

- `<dir>/auditions/AB_before-vs-after.wav` and `AB_reference-vs-after.wav`
  (24-bit WAV, `[ A | gap | B ]`).
- `<dir>/auditions/cmp_reference.wav` and `cmp_after.wav` — standalone
  loudness-matched halves (`gemini_halves`), ready to hand to `compare-to-reference`.

## Reporting to the user

Give the two file paths and, per A/B, the integrated LUFS each half was matched to
and the gain applied to "after". Point them at `AB_before-vs-after.wav` as the key
listen. Note that the reference comparison is tonal/character only (different
performance).

## Pitfalls

- **Loudness matching needs duration** — BS.1770 integrated loudness is unstable
  on excerpts under a few seconds; keep `--dur` ≥ ~8 s (default 12). If the
  reference is shorter than the window it's clamped automatically.
- **This equalizes loudness, it doesn't master.** It's an audition, not a render
  ([[master-track]] is downstream).
- The kit sum is a flat unity sum (close-mic-heavy) — fine for an A/B of the EQ,
  not your final mix balance.

## Related

- [[drum-reference-match]] — produces the "after" set this auditions
- [[drum-prep]] — the full chain (align → match → audition)
- [[reference-match]] — MCP perceptual A/B; feed it the `cmp_*` halves via `compare-to-reference`
- [[master-track]] — when the prepped kit is bounced and ready to master
