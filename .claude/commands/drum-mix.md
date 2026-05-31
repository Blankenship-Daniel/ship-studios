---
description: Mix a prepped multi-mic drum kit to a stereo bus — balance by loudness, pan by perspective, fold in the FX return (local DSP).
argument-hint: <stems dir> [feel] [perspective]
---

Invoke the **drum-mix** skill on `$ARGUMENTS`.

`$1` is the prepped kit folder (it reads `<dir>/ref-matched/` if present, else the dir); any remaining args set the two taste-forks — `--feel roomy|punchy|natural|dry` (how loud the room/overheads sit) and `--perspective drummer|audience` (whose left/right). The skill drives the local `drum-prep mix` CLI (NOT the stemmy MCP servers): balance = per-**role** integrated-loudness offsets vs the overhead anchor, pan by perspective, a spaced room pair channel-balanced, an optional `--plate` stereo FX return folded in; `--flat` does a unity bounce. No bus compression or limiting — that's [[master-track]]'s job. Requires `uv sync --extra drum-prep`. Defer to the skill; surface both forks before running and report the per-role balance + pan map.
