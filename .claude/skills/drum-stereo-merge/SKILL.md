---
name: drum-stereo-merge
description: Use when the user has separate L/R mono files for drum mics and wants stereo tracks — "merge the overhead left/right", "make stereo tracks from these L/R pairs", "combine the room mics into stereo". Consolidates every "<name> - left/right" pair into one format-preserving stereo file and reviews each (inter-channel correlation, polarity, mono-compatibility, reverb-vs-mic). Local drum-prep CLI, not the stemmy MCP servers.
argument-hint: <stems dir>
---

# Merge L/R mono drum mics into stereo tracks

Goal: turn split mono captures (`<name> - left`, `<name> - right`) into proper
two-channel stereo files — interleaving L→left / R→right — while *preserving* the
source bit depth/format. A spaced mic pair (overheads, rooms) carries its image in
the natural L/R level+time differences, so the merge stays time-faithful by
default; alignment is the exception, not the rule.

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/scipy/soundfile). No keys/network.
- A folder where mic pairs are split as `<name> - left` / `<name> - right` (also
  `_l`/`_r` and `" l"`/`" r"` suffixes), same sample rate per pair.

## Recipe (ordered)

1. **Merge** — `drum-prep stereo-merge "<src dir>"`. Finds every `<name> -
   left`/`<name> - right` pair and interleaves L→left, R→right into one stereo
   file per pair. **No time-alignment by default**: a spaced pair keeps its
   natural stereo image. Source bit depth/format is preserved — Float32 stays
   Float32 — unlike the older `overheads` command (overheads-only, writes 24-bit
   AIFF). Flags: `--out-dir DIR` (default `<src>/stereo/`), `--align` to
   phase-lock — **only** for a coincident pair.
2. **Review each pair** — read the per-pair report the command returns and decide
   keep / drop / move (see Reporting).

## Outputs

- `<src>/stereo/` (or `--out-dir`) — one format-preserving stereo file per merged
  pair. The original L/R component files are left in place.

## Reporting to the user

Per pair, give the image review and the reverb-vs-mic flag:

- Per-channel peak / RMS, correlation at lag 0, best-lag delay (ms), and polarity
  (normal / inverted).
- Mono-compatibility: `mono_sum_loss_db` + `mono_safe`.
- Width: side-minus-mid level + the resulting image read.
- `likely_reverb_return` — a decorrelated pair with an offset is probably a reverb
  return, not a mic; flag it so it isn't treated as a kit channel.

## Pitfalls

- **Non-destructive** — the L/R component files stay put. Remove them (or move
  them out) after merging, or `detect` will see both the components and the merged
  stereo and double them up.
- **An fx/plate stereo merge isn't a mic** — move it out of the kit folder. The FX
  role only auto-*excludes* it from alignment; it doesn't keep it out of the kit
  sum. See [[drum-prep]].
- **`--align` is for coincident pairs only** — a spaced pair (overheads, rooms)
  must keep its natural L/R time/level image; aligning it collapses the width.

## Related

- [[drum-prep]] — detect → phase-align → reference-match → audition end to end
- [[drum-phase-align]] — the usual next step (align the merged mics to the OH)
- [[multitrack-triage]] — upstream cleanup that splits/labels raw interface dumps
