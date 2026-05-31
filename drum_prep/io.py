"""Audio I/O for drum_prep — thin wrappers over soundfile.

Stems are read/written as 24-bit AIFF (matching the source DAW stems); auditions
are 24-bit WAV (matching ship-studios' render-ab convention). Everything is
float64 in memory.
"""
from __future__ import annotations

import os

import numpy as np
import soundfile as sf

AUDIO_EXTS = (".wav", ".aif", ".aiff", ".flac")


def list_audio(directory: str) -> list[str]:
    """Sorted audio basenames in ``directory`` (non-recursive, skips dotfiles)."""
    return sorted(
        f for f in os.listdir(directory)
        if not f.startswith(".") and os.path.splitext(f)[1].lower() in AUDIO_EXTS
        and os.path.isfile(os.path.join(directory, f))
    )


def read(path: str, *, mono_sum: bool = False) -> tuple[np.ndarray, int]:
    """Read as float64; (N, ch) when ``mono_sum`` is False, else mono (N,)."""
    x, sr = sf.read(path, always_2d=True, dtype="float64")
    return (x.mean(axis=1), sr) if mono_sum else (x, sr)


def read_mono(path: str) -> tuple[np.ndarray, int]:
    return read(path, mono_sum=True)


def info(path: str) -> tuple[int, int, int]:
    """(channels, samplerate, frames) without loading the audio."""
    i = sf.info(path)
    return i.channels, i.samplerate, i.frames


def to_stereo(x: np.ndarray) -> np.ndarray:
    """Coerce to (N, 2): mono -> centred (both channels); keep first two of >2."""
    a = np.asarray(x, dtype=float)
    if a.ndim == 1:
        return np.column_stack([a, a])
    if a.shape[1] == 1:
        return np.repeat(a, 2, axis=1)
    return a if a.shape[1] == 2 else a[:, :2]


def collapse_if_mono(x: np.ndarray) -> np.ndarray:
    """(N, 1) -> (N,) so mono files write as a single channel."""
    a = np.asarray(x)
    return a[:, 0] if a.ndim == 2 and a.shape[1] == 1 else a


def write_aiff24(path: str, data: np.ndarray, sr: int) -> None:
    sf.write(path, collapse_if_mono(data), sr, subtype="PCM_24", format="AIFF")


def write_wav24(path: str, data: np.ndarray, sr: int) -> None:
    sf.write(path, collapse_if_mono(data), sr, subtype="PCM_24")


def subtype_of(path: str) -> str:
    """libsndfile subtype of an existing file (e.g. 'FLOAT', 'PCM_24', 'PCM_16')."""
    return sf.info(path).subtype


def write_wav(path: str, data: np.ndarray, sr: int, subtype: str = "FLOAT") -> None:
    """Write a little-endian WAV at an explicit subtype (default 32-bit float).

    Used by the format-preserving flows (stereo-merge, normalize) to keep the
    source bit/format rather than forcing the 24-bit AIFF the alignment/match
    flows write.
    """
    sf.write(path, collapse_if_mono(data), sr, subtype=subtype)
