"""Sidechain-keyed gate: gate a bleed-contaminated ambient mic (room / overheads)
from the envelope of CLEAN key mics (kick + snare + crotch), not its own envelope.

Why: a self-keyed gate (scripts/mix/debleed.py gate) keys off the target's OWN
signal — which here contains LOUD spoken-word bleed, so the speech holds the gate
open (bleed passes) and clamps erratically (pumping). Keying from the clean
close-mic drum transients makes the gate open only on kit hits; speech is never in
the key, so it is ducked to the floor in every gap regardless of how loud it is.

Opens instantly on a key transient, releases slowly (cymbal/room decay window),
floors between hits. Run with the stemmy-loops venv (soundfile + numpy + scipy).

Usage:
    python keyed_gate.py <target.wav> <out.wav> <floor_db> <thresh_pct> <release_ms> <key1.wav> [key2.wav ...]
"""
import sys

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d


def main() -> int:
    target, outp = sys.argv[1], sys.argv[2]
    floor_db, thresh_pct, release_ms = (float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]))
    keys = sys.argv[6:]
    if not keys:
        print("need at least one key file"); return 2

    a, sr = sf.read(target, dtype="float32")
    n = len(a)

    # Build the key envelope from the SUM of clean close mics (drum timing only).
    keysum = np.zeros(n, dtype=np.float32)
    for k in keys:
        x, kr = sf.read(k, dtype="float32")
        if kr != sr:
            print(f"key {k} sr {kr} != target {sr}"); return 2
        xm = x if x.ndim == 1 else x.mean(1)
        xm = xm[:n] if len(xm) >= n else np.pad(xm, (0, n - len(xm)))
        keysum += xm

    env = uniform_filter1d(np.abs(keysum), size=max(1, int(0.005 * sr)))  # 5 ms key env
    thr = float(np.percentile(env, 75) * (thresh_pct / 100.0))
    floor = 10 ** (floor_db / 20.0)
    g = np.where(env > thr, 1.0, floor).astype(np.float32)

    # Click-free: instant open (key transient masks the edge), slow release to floor.
    rg = np.exp(-1.0 / (release_ms / 1000.0 * sr))
    p = 1.0
    sm = np.empty_like(g)
    for i, v in enumerate(g):
        p = v if v > p else rg * p + (1 - rg) * v
        sm[i] = p

    y = a * (sm if a.ndim == 1 else sm[:, None])
    sf.write(outp, y, sr, subtype="PCM_24")
    open_pct = float(np.mean(g >= 1.0)) * 100.0
    print(f"keyed-gate -> {outp}  open {open_pct:.0f}%  (floor {floor_db:+.0f} dB, "
          f"release {release_ms:.0f} ms, {len(keys)} key mics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
