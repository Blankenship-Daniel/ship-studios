---
name: format-fix
description: "Use when audio files have the wrong/confusing format or won't load — 'this wav won't open in ffmpeg', 'convert these AIFFs to wav', 'resample to 48k', 'fix the 24-bit AIFF with a .wav name', 'Invalid PCM packet error'. Fixes the AIFF-as-.wav trap and does format/rate/bit-depth conversion with the right tools. Local shell, no MCP servers."
argument-hint: <file or dir> [target format/rate/bit-depth]
---

# Fix audio file format / rate / bit-depth (the AIFF-as-.wav trap and friends)

**The trap, first.** drum-prep writes its rendered stems as **24-bit AIFF carrying
a `.wav` extension**. `ffmpeg`/`ffprobe` sniff the *container*, not the byte order,
so they read those files as little-endian PCM and emit garbage —
`Invalid PCM packet`, static, or wrong-length output. **Anything in
`phase-aligned/`, `ref-matched/`, or `auditions/` from drum-prep is suspect.**

**The fix:** read/convert with **sox** or **afconvert** (which honor the real
AIFF/big-endian container), NEVER raw ffmpeg. Or convert up front with
`.claude/skills/multitrack-triage/scripts/aiff2wav.sh <src-dir-or-file> <dst-dir>`
(routes through sox → true 32-bit float WAV that downstream ffmpeg can read).
Note: **`soundfile` (`sf.info`/`sf.read`) reads the AIFF-as-.wav fine** — so the
drum-prep flows themselves are unaffected; this only bites *external* ffmpeg steps.

This is a local shell utility. **No MCP servers, no API keys** — pure
sox/afconvert/ffmpeg/afinfo.

## Prerequisites

- `sox`, `ffmpeg`/`ffprobe`, and (macOS) `afconvert`/`afinfo` on PATH.
- The converter helper: `.claude/skills/multitrack-triage/scripts/aiff2wav.sh`
  (`chmod +x` once). Reuse it rather than re-deriving the sox incantation.
- Optional cross-check: `python -c "import soundfile"` for `sf.info`.

## Recipe (ordered)

1. **Identify the REAL format — never trust the extension.** Probe the container,
   byte order, sample rate, bit depth, channels. Use any of:
   - `afinfo file.wav` (macOS — reports `AIFF` vs `WAVE`, big/little-endian).
   - `sox --i file.wav` (auto-detects the true container; "Sample Encoding" +
     "File Size/Comment" reveal AIFF-vs-WAV).
   - `python -c "import soundfile as sf; print(sf.info('file.wav'))"` (format,
     subtype, samplerate, channels — reads the AIFF-as-.wav correctly).
   - `ffprobe -hide_banner file.wav` **only as a sanity check** — if it disagrees
     with sox/afinfo or throws `Invalid PCM packet`, sox/afinfo are right and
     you've found an AIFF-in-.wav.
2. **Convert with a tool that honors the real container** (sox or afconvert), then
   pick by job:
   - **AIFF-in-.wav → true WAV** (the common drum-prep case): batch a whole dir
     with `scripts/aiff2wav.sh <src-dir> <dst-dir>`, or a single file:
     `sox in.wav -e float -b 32 out.wav` · or `afconvert -d LEI24 -f WAVE in.wav out.wav`.
   - **AIFF ↔ WAV** explicitly: `sox in.aiff out.wav` · `afconvert -f WAVE -d LEI24 in.aiff out.wav`
     (and `-f AIFF -d BEI24` for the reverse).
   - **Resample** (e.g. → 48 k): `sox in.wav -r 48000 out.wav` (sox has the better
     resampler) · or `ffmpeg -i in.wav -ar 48000 out.wav` (only if `in.wav` is a
     genuine WAV — re-probe per step 1 first).
   - **Change bit depth** (e.g. 24→16 with dither): `sox in.wav -b 16 out.wav -G`
     (`-G` guards against clipping; sox auto-dithers on depth reduction) · or
     `afconvert -d LEI16 -f WAVE in.wav out.wav`.
   - **Combined** (AIFF-in-.wav → 48 k / 24-bit true WAV in one shot):
     `sox in.wav -e signed-integer -b 24 -r 48000 out.wav`.
3. **Verify the OUTPUT's real format** — re-run step 1 on the result. Confirm
   container = WAVE/RIFF (or your target), and that sample rate / bit depth /
   channel count match what you asked for. For the AIFF-fix path, the win is
   `ffprobe out.wav` now reading cleanly (no `Invalid PCM packet`).

## Outputs

No fixed tree — conversions land where the user points (a `<dir>/converted/` or
`/tmp/...` is fine; keep it out of any source/DAW folder). The aiff2wav helper
writes one `.wav` per input into the given `<dst-dir>`.

## Reporting to the user

Per file, one line: **detected real format → target format, the command used.**
E.g. `kick_in.wav: AIFF/24-bit BE (mislabeled .wav) → WAVE/32f 48k via sox`.
Lead with the diagnosis (what it *actually* was vs the extension), then the
conversion, then the verified output format. Flag any file whose extension lied.

## Pitfalls

- **Never trust the extension or `ffprobe` alone** — sox/afinfo/soundfile read the
  true container; ffmpeg sniffs by extension and misreads AIFF-in-.wav.
- **drum-prep output is AIFF-in-`.wav`** (`phase-aligned/`, `ref-matched/`,
  `auditions/`) — convert with `aiff2wav.sh` (or sox/afconvert) before *any*
  ffmpeg step; raw ffmpeg gives `Invalid PCM packet`.
- **soundfile reads it fine** — the drum-prep DSP flows are unaffected; this fix is
  only for ffmpeg / external tooling that chokes on the byte order.
- **ffmpeg multi-input trims need `atrim` in the filtergraph.** Input-side `-ss/-t`
  only applies to the *first* `-i`; for any multi-input mix/concat, trim with
  `atrim=START:END,asetpts=PTS-STARTPTS` inside the graph.
- **`adeclip` can overshoot past 0 dBFS** — always renormalize after (sox `-G` or a
  follow-up gain) so the "fixed" file doesn't clip worse than the original.
- **Reducing bit depth needs dither** — sox dithers automatically on depth
  reduction; if you route through ffmpeg use `-af aresample=...:dither_method=triangular`.

## Related

- [[multitrack-triage]] — owns `aiff2wav.sh`/`declip.sh`/`scan-channels.sh`; the
  upstream cleaning stage where format confusion first shows up.
- [[drum-prep]] — produces the AIFF-in-`.wav` stems this skill un-traps.
- [[loops-to-deliverables]] — the proper format-matrix export (`export-deliverables`
  presets + dither) for finished deliverables, rather than ad-hoc conversion.
