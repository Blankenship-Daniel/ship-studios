---
description: QC a finished deliverable (loudness/true-peak/clipping/streaming + tag/format survival) before shipping.
argument-hint: <deliverable file or dir> [platforms]
---

Invoke the **delivery-qc** skill on `$ARGUMENTS`.

`$1` is the deliverable to gate — a single master WAV, a `projects/<track>/deliverables/` directory, or a `loops/` set; any remaining args name the destination platform(s) to check compliance against. The skill fuses the objective checks — `[G] check-streaming-targets` / `check-delivery-spec` (pure DSP, no key) and `[L] check-clipping` / `inspect-loop` — with the one thing no meter covers: tag/format survival via the local `drum-prep verify-tags` (`uv sync --extra drum-prep`). Lead with the real failure it catches: `export-deliverables tag=true` silently drops the RIFF INFO chunk while returning success. Defer to the skill; lead the report with the ship / don't-ship verdict and the tag-coverage result.
