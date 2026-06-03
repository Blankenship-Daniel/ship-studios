---
description: Drum stems folder → warm/tight bus → loops, end to end (process · balance · EQ · warm sum · loops).
argument-hint: <stems-folder> [slug]
---

Invoke the **drum-stems-warm-loops** skill on `$ARGUMENTS`.

`$1` is a folder of drum stems (kick/snare/overheads/room/+optional FX returns); optional `$2` = project
slug (else slugify the folder name). Runs the full pipeline: convert→baseline → phase-align (gated) →
per-stem process + corrective EQ → measured warm balance → **warm/tight drum bus** (`scripts/mix/warm_bus.py`,
Studer A800 30 IPS) → FX-return A/B (Gemini, meter-cross-checked) → **loops** (raw + mastered ×3 formats via
`scripts/loops/build_loops.py`). Two confirm-points: **BPM** (detect → ask) and the **FX-return** keep/drop.
Warmth = tape + tilt (never a bright boost); tight lows = HPF + low multiband + 30 IPS. Needs
`uv sync --extra vst --extra mixing` (sibling) + `--extra drum-prep` (here) + `GEMINI_API_KEY`. Pass ABSOLUTE
paths to the MCP/Gemini tools. Output is a **mix bus** (peak −1) → hand to [[master-track]] for loudness.
Defer to the skill; report per-stage before→after, the warm signature vs approved, BPM, and loop counts/formats.
