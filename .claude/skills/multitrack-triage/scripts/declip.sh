#!/usr/bin/env bash
# declip.sh <in> <out> [hpf_hz=30]
#
# Reconstruct clipped samples (ffmpeg `adeclip`), high-pass sub-rumble, then
# renormalize to -1 dBFS. adeclip interpolates ABOVE the old clip ceiling, so it
# overshoots past 0 dBFS — the renormalize brings it back. Output is 32-bit float.
#
# Reality check: digital clipping is only APPROXIMATELY recoverable. On heavily
# clipped material (tens of thousands of clipped samples) this smooths the
# flat-tops but cannot invent the lost peaks — re-tracking is the only true fix.
# Use only on channels that scan-channels.sh flags HOT and check-clipping confirms.
set -uo pipefail
in="${1:?usage: declip.sh <in> <out> [hpf_hz]}"; out="${2:?out path}"; hpf="${3:-30}"
tmp="$(dirname "$out")/.declip_tmp_$$.wav"
trap 'rm -f "$tmp"' EXIT          # clean the temp even if ffmpeg/sox fail or we're interrupted
ffmpeg -hide_banner -loglevel error -y -i "$in" -af "adeclip,highpass=f=${hpf}:poles=2" -c:a pcm_f32le "$tmp"
sox "$tmp" -e float -b 32 "$out" gain -n -1
pk=$(sox "$out" -n stat 2>&1 | awk -F: '/Maximum amplitude/{print $2}' | xargs)
echo "declipped: $(basename "$in") -> $(basename "$out")  (HPF ${hpf}Hz, normalized -1dBFS, peak=$pk)"
