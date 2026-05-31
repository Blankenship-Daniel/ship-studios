"""Mix arbitrary named stems to a stereo bus — the role-agnostic song-mix cousin
of :mod:`drum_prep.mix`.

No drum roles: a folder of named instrument stems, each balanced by measured
integrated loudness toward a target, with optional per-stem gain/pan/mute
overrides, summed to a stereo bus with one global anti-clip trim. Tone-shaping
and mastering stay separate — this is the balance+pan+sum stage for a whole song.
An equal-loudness start is only a scaffold; pass a ``spec`` to taste.
"""
from __future__ import annotations

import os

import numpy as np

from drum_prep import dsp, io


def _db(v: float) -> float:
    return 20.0 * np.log10(v) if v > 0 else float("-inf")


def _pan(mono: np.ndarray, theta: float) -> np.ndarray:
    a = (theta + 1.0) * np.pi / 4.0
    return np.column_stack([mono * np.cos(a), mono * np.sin(a)])


def mix_stems(src_dir: str, out_dir: str | None = None, target_lufs: float = -18.0,
              spec: dict | None = None, ceil_dbfs: float = -1.0,
              out_name: str = "song-mix.wav", t0: float = 0.0, dur: float = 0.0) -> dict:
    """Balance every stem in ``src_dir`` to ``target_lufs`` (+ per-stem overrides)
    and sum to a stereo bus. ``spec``: {filename: {gain_db, pan, mute}}."""
    import pyloudnorm as pyln

    spec = spec or {}
    out_dir = out_dir or os.path.join(src_dir, "mix")
    os.makedirs(out_dir, exist_ok=True)
    names = io.list_audio(src_dir)
    if not names:
        raise ValueError(f"no stems found in {src_dir!r}")
    sr = io.info(os.path.join(src_dir, names[0]))[1]
    meter = pyln.Meter(sr)
    n = min(io.info(os.path.join(src_dir, nm))[2] for nm in names)

    mix = np.zeros((n, 2))
    rows = []
    for nm in names:
        s = spec.get(nm, {})
        if s.get("mute"):
            rows.append({"stem": nm, "muted": True})
            continue
        x, _ = io.read(os.path.join(src_dir, nm))
        meas = io.to_stereo(x) if x.shape[1] == 2 else dsp.mono(x)
        lufs = meter.integrated_loudness(meas)
        off = float(s.get("gain_db", 0.0))
        gain = 10 ** ((target_lufs + off - lufs) / 20.0) if np.isfinite(lufs) else 10 ** (off / 20.0)
        pan = float(s.get("pan", 0.0))
        if x.shape[1] == 2:
            ch = io.to_stereo(x)[:n] * gain
            if pan:  # balance a stereo stem toward a side
                ch = ch * np.array([1.0 - max(0.0, pan), 1.0 - max(0.0, -pan)])
            contrib, place = ch, ("stereo" if pan == 0 else f"stereo bal {int(pan * 100)}%")
        else:
            contrib = _pan(x[:n, 0], pan) * gain
            place = "center" if pan == 0 else f"pan {int(pan * 100)}%"
        mix[:len(contrib)] += contrib[:n]
        rows.append({"stem": nm, "lufs": round(float(lufs), 1), "offset_db": off,
                     "gain_db": round(_db(gain), 2), "place": place})

    raw = float(np.max(np.abs(mix)))
    ceil = 10 ** (ceil_dbfs / 20.0)
    trim = ceil / raw if raw > ceil else 1.0
    mix *= trim

    out = os.path.join(out_dir, out_name)
    io.write_wav24(out, mix, sr)
    excerpt = None
    if dur and dur > 0:
        a, b = int(t0 * sr), int((t0 + dur) * sr)
        if b <= n:
            excerpt = os.path.join(out_dir, out_name.replace(".wav", "-excerpt.wav"))
            io.write_wav24(excerpt, mix[a:b], sr)

    return {"flow": "stem-mix", "src_dir": src_dir, "out": out, "excerpt": excerpt,
            "target_lufs": target_lufs, "global_trim_db": round(_db(trim), 2),
            "peak_dbfs": round(_db(float(np.max(np.abs(mix)))), 2),
            "lufs": round(float(meter.integrated_loudness(mix)), 1),
            "channels": 2, "duration_s": round(n / sr, 2), "stems": rows}
