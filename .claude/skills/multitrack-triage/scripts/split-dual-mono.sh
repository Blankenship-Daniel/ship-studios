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
diff=$(ffmpeg -hide_banner -nostats -i "$f" -af "pan=mono|c0=c0-c1,astats=metadata=1" -f null - 2>&1 \
        | awk -F: '/RMS level dB/{print $2; exit}' | xargs)
sox "$f" "$o1" remix 1
sox "$f" "$o2" remix 2
echo "split: $(basename "$f") -> $(basename "$o1") + $(basename "$o2")  (L-R diff RMS=${diff}dB; -inf=identical dual-mono)"
if [ "$del" = 1 ]; then rm -f "$f" && echo "  removed interleaved original"; fi
exit 0
