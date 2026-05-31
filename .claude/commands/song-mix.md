---
description: Mix a full multi-instrument song from named stems to a stereo bus, balanced by measured loudness (local DSP).
argument-hint: <stems dir> [spec.json]
---

Invoke the **song-mix** skill on `$ARGUMENTS`.

`$1` is a folder of named instrument stems (bass, guitars, keys, vox, drum bus…); pass an optional `spec.json` for per-stem `gain_db` / `pan` / `mute`. The skill drives the local `drum-prep stem-mix` CLI (NOT the stemmy MCP servers): a first equal-loudness pass measures every stem and gains it to `--target-lufs` (default -18), then your spec moves nudge from there, summed to a stereo bus with one global anti-clip trim. It's the role-agnostic cousin of [[drum-mix]] (no role detection — filenames are just labels). Tone/glue + mastering stay separate ([[finalize-mix]] → [[master-track]]). Requires `uv sync --extra drum-prep`. Defer to the skill; report the per-stem balance table.
