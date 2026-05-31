"""Reinforce a kick's low end with a synthesized sub layer — the *extension* EQ
cannot add (close kick mics often lack genuine fundamental).

A sine at the kick's fundamental, amplitude-following the kick envelope so it
tracks every hit, blended under the kick at a target level. This is the
downstream answer to a reference-match sub residual that "won't close": that gap
is sustain/extension, not level — generate it, don't EQ for it.
"""
from __future__ import annotations

import numpy as np

from drum_prep import dsp, io


def _db(v: float) -> float:
    return 20.0 * np.log10(v) if v > 0 else float("-inf")


def estimate_fundamental(mono: np.ndarray, sr: int, lo: float = 30.0, hi: float = 120.0) -> float:
    """Dominant low-band partial (Welch PSD peak in [lo, hi])."""
    f, p = dsp.psd(mono, sr)
    band = (f >= lo) & (f <= hi)
    return float(f[band][np.argmax(p[band])]) if band.any() else (lo + hi) / 2.0


def add_sub(kick_path: str, out_path: str, sub_hz: float | None = None,
            amount_db: float = -3.0, env_fc: float = 30.0, ceil_dbfs: float = -1.0) -> dict:
    """Blend an envelope-followed sine sub under the kick at ``amount_db`` vs it."""
    x, sr = io.read(kick_path)
    k = dsp.mono(x)
    if sub_hz is None:
        sub_hz = float(np.clip(estimate_fundamental(k, sr), 30.0, 80.0))

    env = dsp.envelope(k, sr, fc=env_fc)
    env = env / (env.max() + 1e-12)
    t = np.arange(len(k)) / sr
    sub = env * np.sin(2 * np.pi * sub_hz * t)

    krms = np.sqrt(np.mean(k ** 2))
    srms = np.sqrt(np.mean(sub ** 2)) + 1e-12
    g = (krms * 10 ** (amount_db / 20.0)) / srms
    sub = sub * g

    low_before = _db(np.sqrt(np.mean(dsp.lowpass(k, 60.0, sr) ** 2)))
    out = x.astype(np.float64).copy()
    for ch in range(out.shape[1]):
        out[:, ch] += sub
    low_after = _db(np.sqrt(np.mean(dsp.lowpass(dsp.mono(out), 60.0, sr) ** 2)))

    ceil = 10 ** (ceil_dbfs / 20.0)
    pk = float(np.max(np.abs(out)))
    trim = ceil / pk if pk > ceil else 1.0
    out *= trim

    io.write_wav(out_path, out, sr, subtype=io.subtype_of(kick_path))
    return {"flow": "sub-design", "out": out_path, "sub_hz": round(sub_hz, 2),
            "amount_db": amount_db, "sub_gain_db": round(_db(g), 2),
            "anti_clip_trim_db": round(_db(trim), 2),
            "low_60_before_db": round(low_before, 2), "low_60_after_db": round(low_after, 2),
            "low_60_gain_db": round(low_after - low_before, 2)}
