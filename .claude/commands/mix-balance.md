---
description: Mix stem volumes by MEASURED loudness (LUFS) to deliberate per-role targets — before any EQ.
argument-hint: <stems dir or files> [intent, e.g. "kick/snare forward, OH under"]
---

Invoke the **mix-balance** skill on `$ARGUMENTS`.

The skill sets levels by measured integrated LUFS (not eyeballed dB, not RMS, not peak-normalizing the sum) via `scripts/mix/balance_stems.py`: measure each stem → deliberate per-role targets (kick/snare forward, **overhead under them** so the hat/cymbals don't dominate, room subtle) → sum with headroom → re-measure → only THEN hand to tone (`[[finalize-mix]]`/`[[vst-chain]]`). De-spill forward close mics first with `[[bleed-gate]]`. For a full multi-mic kit prefer `[[drum-mix]]`; for a song `[[song-mix]]`. Needs the `mixing` venv. Defer to the skill; report the balance table. **A balance problem is not an EQ problem.**
