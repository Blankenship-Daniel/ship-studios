---
description: Bring a file to a target/reference loudness with one peak-safe linear gain (no limiting) — for honest A/B.
argument-hint: <file.wav> [--reference <ref.wav> | --lufs <-14>]
---

Invoke the **level-match** skill on `$ARGUMENTS`.

`$1` is the file to normalize; provide exactly one of a reference file or a target LUFS. The skill runs `[L] match-loudness` (single peak-safe linear gain, not a limiter) and reports in/out LUFS, true peak, applied gain, and whether `peak_capped` fired. Defer to the skill. If `peak_capped` fired the file couldn't reach the target by gain alone — that needs [[master-track]], not this.
