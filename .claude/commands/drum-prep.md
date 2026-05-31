---
description: Prep a folder of multi-mic drum stems — phase-align, reference-match, and audition (local DSP).
argument-hint: <stems dir> <reference.wav>
---

Invoke the **drum-prep** skill on `$ARGUMENTS`.

`$1` is the folder of individual drum-mic stems, `$2` the reference to match the kit's tone to. The skill drives the local `drum-prep` CLI (NOT the stemmy MCP servers): `detect` roles → `chain` (phase-align to the overheads → per-stem reference-match EQ → loudness-matched A/B auditions), writing into `phase-aligned/`, `ref-matched/`, `auditions/`. Requires `uv sync --extra drum-prep`. Defer to the skill for flags; report the per-stem delays/flips, the tonal residual before→after, and the audition paths.
