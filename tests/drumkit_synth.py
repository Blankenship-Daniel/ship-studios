"""Synthetic-audio helpers for the drum_prep tests.

No audio is committed (the repo .gitignore drops all wav/aif); tests synthesize
signals with known properties into ``tmp_path`` instead.
"""
from __future__ import annotations

import numpy as np


def colored_noise(sr: int, n: int, tilt_db_per_oct: float, seed: int = 0) -> np.ndarray:
    """White noise reshaped to a known spectral tilt (dB/octave, ref 1 kHz)."""
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / sr)
    f[0] = f[1]
    spec *= 10 ** (tilt_db_per_oct * np.log2(f / 1000.0) / 20.0)
    y = np.fft.irfft(spec, n)
    return 0.4 * y / (np.max(np.abs(y)) + 1e-12)


def noise(sr: int, n: int, amp: float = 0.3, seed: int = 0) -> np.ndarray:
    return amp * np.random.default_rng(seed).standard_normal(n)


def write(path, data: np.ndarray, sr: int) -> None:
    """Write 24-bit audio, choosing AIFF for .aif/.aiff (soundfile can't infer it)."""
    import soundfile as sf  # lazy: only tests that synthesize audio need it

    p = str(path)
    if p.lower().endswith((".aif", ".aiff")):
        sf.write(p, data, sr, subtype="PCM_24", format="AIFF")
    else:
        sf.write(p, data, sr, subtype="PCM_24")
