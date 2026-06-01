#!/usr/bin/env bash
# scan-channels.sh <dir> — read-only per-channel triage of a folder of WAV/AIFF.
#
# Prints peak(dB), RMS(dB), DC offset, channel count, duration, and a FLAG:
#   DEAD = peak < -60 dB  -> armed-but-unused interface input (candidate to drop)
#   HOT  = peak >= -0.1 dB -> likely clipped at the converter (verify w/ check-clipping)
#   LOW  = -60..-25 dB     -> bleed / distant / quiet mic (KEEP — may be live in another song)
#   live = normal program level
#
# Notes learned the hard way:
#  - sox `stat` field "Mean amplitude" is the signed DC offset; "Midline amplitude" is NOT.
#  - A channel that reads DEAD in one song can be LOW/live in another take — always
#    cross-check across takes before deleting (see multitrack-triage SKILL, step 6).
set -uo pipefail
for tool in sox soxi; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: '$tool' not on PATH — install sox; otherwise every file reads as DEAD/0ch" >&2; exit 1; }
done
dir="${1:?usage: scan-channels.sh <dir>}"
printf "%-36s %8s %8s %11s %3s %8s  %s\n" FILE peak_dB rms_dB DC ch dur_s FLAG
shopt -s nullglob
for f in "$dir"/*.wav "$dir"/*.aif "$dir"/*.aiff; do
  [ -e "$f" ] || continue
  s=$(sox "$f" -n stat 2>&1) || { printf "%-36s  (unreadable)\n" "$(basename "$f")"; continue; }
  pk=$(awk -F: '/Maximum amplitude/{print $2}'  <<<"$s" | xargs)
  rms=$(awk -F: '/RMS +amplitude/{print $2}'    <<<"$s" | xargs)
  dc=$(awk -F: '/Mean +amplitude/{print $2}'    <<<"$s" | xargs)
  ch=$(soxi -c "$f" 2>/dev/null); dur=$(soxi -D "$f" 2>/dev/null)
  pkdb=$(awk -v p="$pk"  'BEGIN{if(p+0>0)printf "%.1f",20*log(p)/log(10);else print "-inf"}')
  rmsdb=$(awk -v r="$rms" 'BEGIN{if(r+0>0)printf "%.1f",20*log(r)/log(10);else print "-inf"}')
  flag=$(awk -v d="$pkdb" 'BEGIN{
    if(d=="-inf"||d+0< -60){print "DEAD"} else if(d+0>=-0.1){print "HOT"}
    else if(d+0< -25){print "LOW"} else {print "live"}}')
  printf "%-36s %8s %8s %11s %3s %8.1f  %s\n" "$(basename "$f")" "$pkdb" "$rmsdb" "$dc" "$ch" "${dur:-0}" "$flag"
done
