#!/usr/bin/env bash
# aiff2wav.sh <src-dir-or-file> <dst-dir>
#
# drum-prep writes its phase-aligned stems as 24-bit AIFF but with a `.wav`
# extension. ffmpeg's extension/container sniffing then misreads them as
# little-endian PCM and produces "Invalid PCM packet" garbage. sox auto-detects
# the real (AIFF/big-endian) format, so route through sox to get TRUE 32-bit
# float WAV that downstream ffmpeg mixing can read.
#
# Run this on `<kit>/cleaned/phase-aligned/` before building any ffmpeg audition.
set -uo pipefail
src="${1:?usage: aiff2wav.sh <src-dir-or-file> <dst-dir>}"; dst="${2:?dst dir}"
mkdir -p "$dst"
conv(){ sox "$1" -e float -b 32 "$dst/$(basename "${1%.*}").wav" && echo "  $(basename "$1") -> $(basename "${1%.*}").wav"; }
if [ -d "$src" ]; then
  shopt -s nullglob
  for f in "$src"/*.wav "$src"/*.aif "$src"/*.aiff; do [ -e "$f" ] && conv "$f"; done
else
  conv "$src"
fi
