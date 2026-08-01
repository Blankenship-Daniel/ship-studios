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


def _refine_peak(f: np.ndarray, p: np.ndarray, i: int) -> float:
    """Sub-bin peak frequency by a parabolic fit through bins ``i-1, i, i+1``.

    The raw ``argmax`` bin is only accurate to +/- half a bin, and at this job's
    resolution that is a musical error, not a rounding one: a 0.3 s kick gives
    df = 3.33 Hz, so a true 54 Hz fundamental reads 53.33 Hz (-22 cents) and a
    55 Hz one reads 56.67 Hz (+52 cents). Since :func:`retune` derives its
    resample ratio from this number — and then re-measures the result the same
    way, so the report looks self-consistent — the error lands silently in the
    output sample. Fitting in the LOG domain is the right model: a windowed
    spectral peak is approximately Gaussian in magnitude, hence parabolic in log
    magnitude. Deliberately local to this module: ``dsp.psd``'s resolution is
    shared with the reference-match EQ and must not change.
    """
    if i <= 0 or i >= len(p) - 1:
        return float(f[i])
    tiny = 1e-30  # welch can return exact zeros; log(0) would poison the fit
    y0, y1, y2 = (float(np.log(p[j] + tiny)) for j in (i - 1, i, i + 1))
    den = y0 - 2 * y1 + y2
    if abs(den) < 1e-12:  # flat/degenerate — no better estimate than the bin
        return float(f[i])
    # clip to the bin: a parabola through noisy neighbours can extrapolate wildly,
    # and the true peak cannot be more than half a bin from the argmax bin.
    delta = float(np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5))
    return float(f[i] + delta * (f[i + 1] - f[i]))


def measure_fundamental(path: str, lo: float = 30.0, hi: float = 400.0) -> dict:
    x, sr = io.read(path)
    f, p = dsp.psd(dsp.mono(x), sr)
    idx = np.flatnonzero((f >= lo) & (f <= hi))
    hz = _refine_peak(f, p, int(idx[np.argmax(p[idx])])) if idx.size else 0.0
    return {"hz": round(hz, 2), **hz_to_note(hz)}


def retune(path: str, out_path: str, target_hz: float | None = None,
           target_midi: int | None = None, semitones: float | None = None) -> dict:
    """Retune by resampling. Give exactly one of target_hz / target_midi / semitones."""
    provided = sum(v is not None for v in (target_hz, target_midi, semitones))
    if provided > 1:
        raise ValueError("give only one of target_hz, target_midi, semitones")
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
    # An extreme ratio collapses to up == down == 1 (a silent no-op) once the
    # denominator is capped — reject it rather than return the input unchanged.
    if up == down == 1 and abs(np.log2(ratio)) > 0.01:
        raise ValueError(f"requested pitch ratio {ratio:.3f} is outside the resampling range")
    out = resample_poly(x, up, down, axis=0)  # x is always 2-D (N, ch) -> (new_n, ch)
    new_n = out.shape[0]
    io.write_wav(out_path, out, sr, subtype=io.subtype_of(path))

    after = measure_fundamental(out_path)
    return {"flow": "tune", "out": out_path, "from_hz": src, "from_note": cur["note"],
            "ratio": round(ratio, 4), "to_hz": after["hz"], "to_note": after["note"],
            "frames_in": int(n), "frames_out": int(new_n)}
