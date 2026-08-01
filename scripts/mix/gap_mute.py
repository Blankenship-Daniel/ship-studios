"""Mute the pure-speech GAPS in the desktop-drums kit (head, tail, and internal
no-drum sections) across all stems — the targeted edit that gating/Demucs can't do.

Detection keys off DRUM ONSETS, not level: in a true speech-only gap the Demucs
drums stem (drum_key.wav) has no sharp transients (leaked speech is smooth), while
drum hits are sharp. Spectral-flux peaks mark hits; a region is ACTIVE if a hit
falls within [-pre, +hold]; contiguous inactive spans longer than min_gap are muted
with cosine fades. Applied uniformly to every stem so the kit stays phase-locked.

Usage:
    python gap_mute.py report                 # dry-run: mask stats at known windows + gap list
    python gap_mute.py apply <SRC_DIR> <OUT_DIR> [room_override.wav]
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import stft
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/ isn't a package
from _core import repo_root, sibling_python    # noqa: E402

SR = 48000
ROOT = repo_root()
KEY = ROOT / "artifacts/desktop-drums-demucs/drum_key.wav"
STEMS = ["kick_in", "snare_top", "snare_bottom", "crotch_mic", "overheads", "room"]

# tunables
HOP = 512                 # ~10.7 ms frames
FLUX_THR_FRAC = 0.07      # hit if flux > frac * 99.5th-percentile flux (0.07 caught all real drums w/o over-muting; 0.12 over-muted continuous drums at 88-91s)
PRE_S = 0.08              # keep this long before a hit
HOLD_S = 0.50             # keep this long after a hit (shorter = mute decay-tail speech sooner)
MIN_GAP_S = 1.0           # only mute inactive spans longer than this
PRE_EXTEND_S = 0.30       # extend each gap's START earlier, to eat the speech-on-decay tail
FADE_S = 0.050            # cosine fade at every mute boundary
FLOOR_DB = -90.0          # mute floor


def active_mask(n: int) -> np.ndarray:
    key, sr = sf.read(str(KEY))
    key = np.asarray(key)
    key = key if key.ndim == 1 else key.mean(1)
    f, t, Z = stft(key, sr, nperseg=1024, noverlap=1024 - HOP)
    mag = np.abs(Z)
    flux = np.maximum(0.0, np.diff(mag, axis=1)).sum(0)
    flux = np.concatenate([[0.0], flux])
    thr = FLUX_THR_FRAC * np.percentile(flux, 99.5)
    hits = flux > thr
    pre, hold = int(PRE_S / (HOP / sr)), int(HOLD_S / (HOP / sr))
    act = np.zeros_like(hits)
    idx = np.flatnonzero(hits)
    for i in idx:
        act[max(0, i - pre): i + hold + 1] = True
    # frame -> sample
    fs = np.zeros(n, dtype=bool)
    for i, a in enumerate(act):
        if a:
            s = i * HOP
            fs[s: s + HOP] = True
    return fs


def gap_spans(fs: np.ndarray) -> list[tuple[float, float]]:
    spans = []
    i = 0
    n = len(fs)
    mg = int(MIN_GAP_S * SR)
    while i < n:
        if not fs[i]:
            j = i
            while j < n and not fs[j]:
                j += 1
            if j - i >= mg:
                spans.append((i / SR, j / SR))
            i = j
        else:
            i += 1
    return spans


def gain_from_mask(fs: np.ndarray) -> np.ndarray:
    """1.0 in active, FLOOR in muted gaps (>=MIN_GAP), cosine fades at edges."""
    g = np.full(len(fs), 10 ** (FLOOR_DB / 20.0), dtype=np.float32)
    for a, b in gap_spans(fs):
        pass  # gaps stay at floor
    # set everything NOT in a long gap to 1.0
    g[:] = 1.0
    fade = int(FADE_S * SR)
    pre_ext = int(PRE_EXTEND_S * SR)
    floor = 10 ** (FLOOR_DB / 20.0)
    for a, b in gap_spans(fs):
        sa, sb = max(0, int(a * SR) - pre_ext), int(b * SR)   # eat the contaminated decay tail
        g[sa:sb] = floor
        # fade out into the gap, fade in out of it
        g[max(0, sa - fade):sa] = np.linspace(1.0, floor, min(fade, sa))
        g[sb:sb + fade] = np.linspace(floor, 1.0, min(fade, len(g) - sb))
    return g


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    n = sf.info(str(KEY)).frames
    fs = active_mask(n)
    spans = gap_spans(fs)

    if mode == "report":
        def frac(a, b):
            return float(np.mean(fs[int(a * SR):int(b * SR)]))
        print(f"active frames overall: {100 * fs.mean():.0f}%   muted gaps: {len(spans)}")
        for lbl, a, b in [("head 10-40", 10, 40), ("GAP 124-131", 124, 131),
                          ("drums 131-140", 131, 140), ("drums 200-210", 200, 210),
                          ("tail 340-360", 340, 360)]:
            print(f"  {lbl:14s} active {100 * frac(a, b):5.0f}%")
        tot = sum(b - a for a, b in spans)
        print(f"muted total {tot:.1f}s of {n / SR:.1f}s")
        print("gap spans (s):")
        for a, b in spans:
            print(f"  {a:7.1f} - {b:7.1f}  ({b - a:.1f}s)")
        return 0

    if mode == "apply":
        src, out = Path(sys.argv[2]), Path(sys.argv[3])
        room_override = sys.argv[4] if len(sys.argv) > 4 else None
        out.mkdir(parents=True, exist_ok=True)
        g = gain_from_mask(fs)
        for s in STEMS:
            p = room_override if (s == "room" and room_override) else str(src / f"{s}.wav")
            x, sr = sf.read(p, always_2d=True)
            m = min(len(x), len(g))
            y = x[:m] * g[:m, None]
            y = y[:, 0] if y.shape[1] == 1 else y
            sf.write(str(out / f"{s}.wav"), y, sr, subtype="PCM_24")
        print(f"applied gap-mute ({len(spans)} gaps, {sum(b-a for a,b in spans):.1f}s) -> {out}")
        return 0

    print("mode must be report|apply")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
