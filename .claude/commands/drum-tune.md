---
description: Measure a drum sample's fundamental (Hz/note/cents) and optionally retune the SAMPLE by resampling (local DSP).
argument-hint: <sample.wav> [target key/note]
---

Invoke the **drum-tune** skill on `$ARGUMENTS`.

`$1` is a single drum **sample** (one hit — kick, tom, or other pitched drum, not a loop/performance); pass a target if you want to retune. The skill drives the local `drum-prep tune` CLI (NOT the stemmy MCP servers): measure-only (no `--out`) returns the fundamental as `hz` + note name + `cents` off; with `--out` and exactly one of `--target-hz` / `--target-midi` / `--semitones` it **resamples** toward the target (pitch and duration shift together — so samples only). Requires `uv sync --extra drum-prep`. Defer to the skill; report the measured fundamental and, if retuned, the shift + output path.
