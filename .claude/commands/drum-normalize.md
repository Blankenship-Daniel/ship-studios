---
description: Gain-stage a multi-mic drum kit with a balance-preserving GLOBAL gain (local DSP).
argument-hint: <stems dir> [target dBFS]
---

Invoke the **drum-normalize** skill on `$ARGUMENTS`.

`$1` is the folder of drum-mic stems; an optional second arg sets `--target-dbfs` (default `-1.0`). The skill drives the local `drum-prep normalize` CLI (NOT the stemmy MCP servers). Domain rule it enforces: on a multi-mic kit the **relative** mic levels ARE the balance, so `--mode global` (default) finds the loudest peak across the entire set and applies that **one** gain to every stem and both channels — inter-mic balance and stereo image untouched; `--mode per-file` is warned against (it changes the kit's sound). Source format is preserved → `<dir>/normalized/`. `--include PATH` folds a sibling fx return into the same global gain. Requires `uv sync --extra drum-prep`. Defer to the skill; report the applied gain and the new peak.
