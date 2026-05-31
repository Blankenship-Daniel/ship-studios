---
name: song-mix
description: Use when the user wants to mix a full multi-instrument SONG (not just drums) from stems to a stereo bus — "mix these stems", "balance the song", "sum the bass/gtr/vox/drums to a stereo mix". Balances every named stem by measured loudness toward a target with optional per-stem gain/pan/mute, summed to a stereo bus. The role-agnostic cousin of [[drum-mix]]; tone-shaping and mastering stay separate. Local drum-prep CLI, not the stemmy MCP servers.
---

# Mix a multi-instrument song from stems to a stereo bus

Goal: fold a folder of named instrument stems (bass, guitars, keys, vox, drum
bus…) into one stereo bus — every stem balanced by *measured* loudness toward a
common target, then nudged per stem by a gain/pan/mute spec. Equal-loudness is
the **scaffold**, not the mix: it gets every stem into the same ballpark so your
spec moves are small and meaningful. Unlike [[drum-mix]] there are **no roles** —
you name the levels. Tone and glue belong elsewhere ([[finalize-mix]] then
[[master-track]]).

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/scipy/soundfile/pyloudnorm). No keys/network.
- A folder of instrument stems, **same sample rate**. Mono and stereo stems both
  fine. No role detection happens — filenames are just labels for the spec.
- Optional `spec.json`: `{"<filename>": {"gain_db": x, "pan": -1..1, "mute": true}}`.
  Keys are exact filenames as they appear in SRC.

## Recipe (ordered)

1. **First pass, equal-loudness** — `drum-prep stem-mix "<SRC>"`. Every stem is
   measured (integrated LUFS) and gained to `--target-lufs` (default -18). Mono
   stems are equal-power panned (centred); stereo stems are kept stereo (pan then
   = balance toward a side). One global anti-clip trim to a -1 dBFS ceiling. Read
   the per-stem table — this tells you which stems naturally sit hot/quiet.
2. **Write a spec to taste** — author `spec.json` with relative `gain_db` offsets
   (vs the equal-loudness target), `pan` (-1 L … +1 R), and `mute` for stems you
   want out. Re-run with `--spec spec.json`. Iterate: small offsets, re-read the
   table.
3. **Audition window** (optional) — `--t0 <sec> --dur <sec>` writes a short
   excerpt of the bus next to the full file for fast A/B without opening the whole
   bounce.
   Full surface: `drum-prep stem-mix <SRC> [--out-dir DIR]
   [--target-lufs -18] [--spec spec.json] [--t0 0] [--dur 0]`.

## Outputs

- `<SRC>/mix/` (default; override with `--out-dir`) — `song-mix.wav`, a 24-bit
  stereo bus. With `--dur > 0`, also `song-mix-excerpt.wav`. One **global**
  anti-clip trim is applied to the whole bus so relative stem balance survives.

## Reporting to the user

Give the per-stem table: **filename, measured LUFS, spec offset (dB), applied
gain (dB), placement (center / pan % / stereo / stereo bal %)**, with muted stems
flagged. Then the **global trim (dB)**, the final bus **peak (dBFS)** and
**integrated LUFS**, and the duration. Restate the `--target-lufs` used so the
user can re-run, and point them at the spec for the next pass.

## Pitfalls

- **Equal-loudness is a scaffold, not a finished mix.** A -18 LUFS bass and -18
  LUFS vocal are *measured*-equal, not *perceived*-balanced — use `--spec` to
  taste; the first pass is only a starting line.
- **This does NOT EQ, compress, or master.** No tone-shaping, no glue, no
  limiting. Tonal carving and bus comp are [[finalize-mix]]; loudness/ceiling and
  platform delivery are [[master-track]].
- **No instrument-role detection.** Stems are balanced as named files, not as
  "bass" or "vocal" — there's no perspective/panning intelligence like [[drum-mix]].
  You own the spec.
- **Sample-rate mismatch** isn't resampled — bring every stem to one rate first
  (e.g. via [[stem-split]] output) or the sum will be wrong.
- **Spec keys are exact filenames.** A typo silently leaves that stem at the
  equal-loudness default; check the table to confirm your offsets landed.

## Related

- [[drum-mix]] — the role-aware cousin for a multi-mic drum kit (balance by
  anchor, perspective panning, plate return)
- [[finalize-mix]] — EQ / compression / glue on the summed bus (the next step)
- [[master-track]] — loudness, ceiling, and platform-ready master of the bus
- [[mix-check]] — MCP perceptual/measurement diagnosis of the finished mix
- [[stem-split]] — produce the per-instrument stems that feed this mix
