---
description: Fix audio format/rate/bit-depth issues — the AIFF-as-.wav trap and conversions (local shell, no MCP).
argument-hint: <file or dir> [target format/rate/bit-depth]
---

Invoke the **format-fix** skill on `$ARGUMENTS`.

`$1` is the file or directory to fix; any remaining args name the target format/rate/bit-depth. The skill is a **local shell utility** — sox / afconvert / ffmpeg / afinfo, **no MCP servers, no keys**. It first identifies the REAL container (never trusts the extension), then converts with the right tool. The trap it exists for: drum-prep writes 24-bit **AIFF** carrying a `.wav` extension, so anything in `phase-aligned/`/`ref-matched/`/`auditions/` is suspect — read/convert with sox or afconvert (or `multitrack-triage/scripts/aiff2wav.sh`), never raw ffmpeg (which emits `Invalid PCM packet`/garbage). `soundfile` reads those files fine, so the drum-prep flows themselves are unaffected — this only bites external ffmpeg steps. Defer to the skill; report the detected format → conversion done.
