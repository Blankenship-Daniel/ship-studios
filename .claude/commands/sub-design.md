---
description: Synthesize an envelope-followed sine sub under a kick — low-end EXTENSION EQ can't add (local DSP).
argument-hint: <kick.wav>
---

Invoke the **sub-design** skill on `$ARGUMENTS`.

`$1` is a single kick stem (the in/beater mic or a kick sum). The skill drives the local `drum-prep sub-design` CLI (NOT the stemmy MCP servers): it detects the kick fundamental (Welch PSD, clamped 30–80 Hz; override with `--sub-hz`), generates a sine amplitude-followed by the kick's own envelope, scales it to `--amount-db` (default `-3.0`) relative to the kick RMS, sums it in, and anti-clips. This adds genuine low-end **extension/sustain** the source lacks — NOT an EQ boost — for the reference-match sub residual that won't close ([[drum-reference-match]] flags exactly this case). Requires `uv sync --extra drum-prep`. Defer to the skill; move `--amount-db` in 1–2 dB steps.
