---
description: Tighten a loop's timing (quantize to grid or stretch to exact bars), then re-fix the seam and QC.
argument-hint: <loop.wav> [bpm] [bars]
---

Invoke the **groove-tighten** skill on `$ARGUMENTS`.

`$1` is the loop; pass BPM if it isn't in `track.md`/the manifest (the skill never guesses BPM), and `bars` for `length` mode. The skill runs `quantize-loop` (groove or length), then re-runs `optimize-seam` because quantizing shifts onsets and breaks the wrap point, then `inspect-loop` + a mono `render-ab`. Requires the `quantize` extra. Defer to the skill; report mode/BPM, seam result, and the A/B path.
