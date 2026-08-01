"""Reinforce a kick's low end with a synthesized sub layer — the *extension* EQ
cannot add (close kick mics often lack genuine fundamental).

A sine at the kick's fundamental, amplitude-following the kick envelope so it
tracks every hit, blended under the kick at a target level. This is the
downstream answer to a reference-match sub residual that "won't close": that gap
is sustain/extension, not level — generate it, don't EQ for it.

The synthesized sub is mono and added identically to every channel (a fully
correlated, dead-centre layer) — standard for kick reinforcement, and at sub
frequencies stereo width is inaudible anyway.
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
    notes: list[str] = []
    if sub_hz is None:
        # Search and clamp over the SAME range. They used to disagree (search
        # [30,120], clamp [30,80]), so a 100 Hz kick was silently given an 80 Hz
        # sub — a detuned layer that beats against the fundamental instead of
        # reinforcing it. Report the clamp instead of hiding it.
        detected = estimate_fundamental(k, sr, lo=30.0, hi=80.0)
        wide = estimate_fundamental(k, sr, lo=30.0, hi=120.0)
        if abs(wide - detected) > 1.0:
            notes.append(
                f"kick fundamental measures ~{wide:.0f} Hz, above the {80.0:.0f} Hz "
                f"sub range — using {detected:.0f} Hz; pass --sub-hz explicitly if you "
                f"want the sub on the true fundamental")
        sub_hz = float(detected)

    env = dsp.envelope(k, sr, fc=env_fc)
    # The FFT brick-wall low-pass of |k| can ring slightly negative; clamp so the
    # amplitude follower never flips the sub sine's polarity in low-level regions.
    env = np.maximum(env, 0.0)
    env = env / (env.max() + 1e-12)
    t = np.arange(len(k)) / sr
    # Choose the sub's PHASE to correlate with the kick's own low band rather than
    # starting free-running at 0. At the default the sub sits on the kick's own
    # fundamental, so an arbitrary relative phase can put them near anti-phase and
    # the "reinforcement" SUBTRACTS low end. Pick the phase maximising correlation
    # with the kick's sub-band content — the same empirical-sign idea align_to uses.
    k_low = dsp.lowpass(k, max(sub_hz * 1.5, 60.0), sr)
    ref = k_low * env
    c = float(np.dot(ref, np.cos(2 * np.pi * sub_hz * t)))
    s = float(np.dot(ref, np.sin(2 * np.pi * sub_hz * t)))
    phase = np.arctan2(c, s) if (c or s) else 0.0
    sub = env * np.sin(2 * np.pi * sub_hz * t + phase)

    krms = np.sqrt(np.mean(k ** 2))
    srms = np.sqrt(np.mean(sub ** 2)) + 1e-12
    g = (krms * 10 ** (amount_db / 20.0)) / srms
    sub = sub * g

    low_before = _db(np.sqrt(np.mean(dsp.lowpass(k, 60.0, sr) ** 2)))
    out = x.astype(np.float64).copy()
    for ch in range(out.shape[1]):
        out[:, ch] += sub
    low_after = _db(np.sqrt(np.mean(dsp.lowpass(dsp.mono(out), 60.0, sr) ** 2)))
    # The whole point is MORE low end. If the blend removed some, say so loudly
    # rather than shipping a kick with its bottom partially cancelled.
    if low_after <= low_before + 0.1:
        notes.append(
            f"sub blend did not add low end ({low_before:.1f} -> {low_after:.1f} dB "
            f"under 60 Hz) — the sub is cancelling the kick; try a different --sub-hz")

    ceil = 10 ** (ceil_dbfs / 20.0)
    pk = float(np.max(np.abs(out)))
    trim = ceil / pk if pk > ceil else 1.0
    out *= trim

    io.write_wav(out_path, out, sr, subtype=io.subtype_of(kick_path))
    return {"flow": "sub-design", "out": out_path, "sub_hz": round(sub_hz, 2),
            "amount_db": amount_db, "sub_gain_db": round(_db(g), 2),
            "anti_clip_trim_db": round(_db(trim), 2),
            "low_60_before_db": round(low_before, 2), "low_60_after_db": round(low_after, 2),
            "low_60_gain_db": round(low_after - low_before, 2),
            "notes": notes or None}
