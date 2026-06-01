"""Measure a drum's fundamental pitch and retune a SAMPLE by resampling.

Resampling shifts pitch AND duration together, so this targets one-shots/samples
(a kick or tom hit) — not full performances. Pitch-preserving time-stretch
(phase vocoder) is deliberately out of scope. Use it to tune a kick sample to the
song's key, or to pitch a tom set.
"""
from __future__ import annotations

import numpy as np

from drum_prep import dsp, io

_A4 = 440.0
_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def hz_to_note(hz: float) -> dict:
    if hz <= 0:
        return {"note": None, "midi": None, "cents": 0.0}
    midi = 69 + 12 * np.log2(hz / _A4)
    m = int(round(midi))
    return {"note": f"{_NAMES[m % 12]}{m // 12 - 1}", "midi": m,
            "cents": round(float((midi - m) * 100), 1)}


def note_to_hz(midi: int) -> float:
    return _A4 * 2 ** ((midi - 69) / 12)


def measure_fundamental(path: str, lo: float = 30.0, hi: float = 400.0) -> dict:
    x, sr = io.read(path)
    f, p = dsp.psd(dsp.mono(x), sr)
    band = (f >= lo) & (f <= hi)
    hz = float(f[band][np.argmax(p[band])]) if band.any() else 0.0
    return {"hz": round(hz, 2), **hz_to_note(hz)}


def retune(path: str, out_path: str, target_hz: float | None = None,
           target_midi: int | None = None, semitones: float | None = None) -> dict:
    """Retune by resampling. Give exactly one of target_hz / target_midi / semitones."""
    cur = measure_fundamental(path)
    src = cur["hz"]
    if semitones is not None:
        ratio = 2 ** (semitones / 12)
    elif target_midi is not None:
        ratio = note_to_hz(target_midi) / src if src > 0 else 1.0
    elif target_hz is not None:
        ratio = target_hz / src if src > 0 else 1.0
    else:
        raise ValueError("give target_hz, target_midi, or semitones")

    from fractions import Fraction

    from scipy.signal import resample_poly

    x, sr = io.read(path)
    n = x.shape[0]
    # Resample by ~1/ratio (higher pitch => fewer samples). resample_poly applies
    # a proper anti-aliasing FIR, unlike a bare linear interp which aliases when
    # pitching up. Approximate 1/ratio as a rational up/down.
    frac = Fraction(1.0 / ratio).limit_denominator(2000)
    up, down = (frac.numerator or 1), frac.denominator
    out = resample_poly(x, up, down, axis=0)  # x is always 2-D (N, ch) -> (new_n, ch)
    new_n = out.shape[0]
    io.write_wav(out_path, out, sr, subtype=io.subtype_of(path))

    after = measure_fundamental(out_path)
    return {"flow": "tune", "out": out_path, "from_hz": src, "from_note": cur["note"],
            "ratio": round(ratio, 4), "to_hz": after["hz"], "to_note": after["note"],
            "frames_in": int(n), "frames_out": int(new_n)}
