#!/usr/bin/env bash
# split-dual-mono.sh <file> [--delete-original]
#
# Split an interleaved 2-channel WAV that is really two INDEPENDENT mono sources
# packed as L/R (common when two interface inputs — e.g. a DI pair or a stereo
# room — get written to one file like "..._1_2.wav"). Produces two mono files and
# reports the L-R difference so you can tell a true stereo image (large diff) from
# dual-mono (-inf = identical).
#
# Naming: "<stem>_1_2.wav" -> "<stem>_1.wav" + "<stem>_2.wav"
#         otherwise         -> "<stem>_chL.wav" + "<stem>_chR.wav"
set -uo pipefail
for tool in sox soxi ffmpeg; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: '$tool' not on PATH — install sox/ffmpeg; otherwise the split silently fails" >&2; exit 1; }
done
f=""; del=0
for a in "$@"; do
  case "$a" in
    --delete-original) del=1 ;;
    -*) echo "unknown flag: $a" >&2; exit 2 ;;
    *) [ -z "$f" ] && f="$a" ;;
  esac
done
[ -n "$f" ] || { echo "usage: split-dual-mono.sh <file> [--delete-original]" >&2; exit 1; }
ch=$(soxi -c "$f" 2>/dev/null || echo 0)
[ "$ch" = "2" ] || { echo "skip (not 2-ch): $(basename "$f")"; exit 0; }
dir=$(dirname "$f"); stem="$(basename "${f%.*}")"
if [[ "$stem" == *_1_2 ]]; then o1="$dir/${stem%_1_2}_1.wav"; o2="$dir/${stem%_1_2}_2.wav"
else o1="$dir/${stem}_chL.wav"; o2="$dir/${stem}_chR.wav"; fi
# Refuse to clobber existing files (re-run, or a derived name colliding with a real channel).
for o in "$o1" "$o2"; do
  [ -e "$o" ] && { echo "ERROR: would overwrite existing $(basename "$o") — remove it first or rename" >&2; exit 1; }
done
diff=$(ffmpeg -hide_banner -nostats -i "$f" -af "pan=mono|c0=c0-c1,astats=metadata=1" -f null - 2>&1 \
        | awk -F: '/RMS level dB/{print $2; exit}' | xargs)
[ -n "$diff" ] || diff="?(extract failed)"   # don't print a bare "RMS=dB"
# Only declare success (and only ever delete the original) if BOTH splits ran AND
# both outputs are non-empty — a failed sox under `set -uo pipefail` (no -e) must not
# fall through to the rm and destroy the sole copy of the channel.
if sox "$f" "$o1" remix 1 && sox "$f" "$o2" remix 2 && [ -s "$o1" ] && [ -s "$o2" ]; then
  echo "split: $(basename "$f") -> $(basename "$o1") + $(basename "$o2")  (L-R diff RMS=${diff}dB; -inf=identical dual-mono)"
  if [ "$del" = 1 ]; then rm -f "$f" && echo "  removed interleaved original"; fi
else
  echo "ERROR: split failed for $(basename "$f") — keeping original" >&2
  rm -f "$o1" "$o2"
  exit 1
fi
exit 0
