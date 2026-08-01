"""Audio I/O for drum_prep — thin wrappers over soundfile.

The alignment/match flows read/write 24-bit AIFF via :func:`write_aiff24`
(matching the source DAW stems); auditions/mixes use 24-bit WAV via
:func:`write_wav24` (matching ship-studios' render-ab convention).
:func:`write_wav` is the generic *bit-depth/subtype-preserving* writer (default
subtype FLOAT) used by the normalize/stereo-merge flows that carry the source
SUBTYPE through; the output CONTAINER follows the destination extension (derived
to an explicit ``format=`` so a 3-letter ``.aif`` name — which soundfile can't
infer — still writes a real AIFF, and a ``.wav`` name a real WAV, regardless of
the source container). Everything is float64 in memory.
"""
from __future__ import annotations

import os

import numpy as np
import soundfile as sf

AUDIO_EXTS = (".wav", ".aif", ".aiff", ".flac")

#: Output extension -> libsndfile container. soundfile infers the container from
#: the extension, but the 3-letter ``.aif`` is NOT recognised (only ``.aiff`` is)
#: -> it raises a raw TypeError mid-batch. Derive ``format=`` explicitly so a
#: ``.aif`` name still writes a real AIFF; an unknown ext falls back to inference.
_EXT_FORMAT = {".wav": "WAV", ".aif": "AIFF", ".aiff": "AIFF", ".flac": "FLAC"}


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


def common_samplerate(paths: list[str]) -> int:
    """Shared sample rate of ``paths``; raise ``ValueError`` if they disagree.

    The summing/mixing flows read every input at one rate and add them in the
    time domain — a stray off-SR file would sum *time-misaligned* into silent
    corruption. Validate the whole set up front instead. Reads headers only.
    """
    if not paths:
        raise ValueError("no inputs to check sample rate")
    srs = {p: info(p)[1] for p in paths}
    if len(set(srs.values())) > 1:
        detail = ", ".join(f"{os.path.basename(p)}={s}" for p, s in srs.items())
        raise ValueError(f"sample-rate mismatch across inputs (resample first): {detail}")
    return next(iter(srs.values()))


def summarize_inputs(paths: list[str]) -> tuple[int, list[int]]:
    """``(shared_samplerate, [frames_per_path])`` from a SINGLE header pass.

    The summing flows need both the common SR (they add in the time domain — a
    stray off-SR file would sum *time-misaligned*) and each file's frame count
    (to find the common length). Doing it here reads each header once instead of
    calling :func:`common_samplerate` and then a separate ``info`` loop. Raises
    ``ValueError`` on a sample-rate mismatch, same as :func:`common_samplerate`.
    """
    if not paths:
        raise ValueError("no inputs to summarize")
    meta = {p: info(p) for p in paths}  # one info() per path
    srs = {p: m[1] for p, m in meta.items()}
    if len(set(srs.values())) > 1:
        detail = ", ".join(f"{os.path.basename(p)}={s}" for p, s in srs.items())
        raise ValueError(f"sample-rate mismatch across inputs (resample first): {detail}")
    sr = next(iter(srs.values()))
    return sr, [meta[p][2] for p in paths]


def truncation_note(frames: list[int]) -> str | None:
    """Note when summing over the common length will drop trailing audio.

    Returns ``None`` for a trivial (<= 1 frame) difference so 1-sample rounding
    between otherwise-identical stems doesn't raise a false alarm.
    """
    if not frames:
        return None
    n, longest = min(frames), max(frames)
    if longest - n <= 1:
        return None
    return f"stems truncated to the shortest ({n} frames); longest was {longest}"


def refuse_in_place(flow: str, out_dir: str, **sources: str) -> None:
    """Raise if ``out_dir`` resolves to one of ``sources``.

    The write flows are documented as non-destructive — they render a fresh set
    into a subdirectory. Nothing stopped ``--out-dir`` from naming the SOURCE
    directory, though, which silently replaced the originals: a raw WAV/PCM_16
    ``snare top.wav`` came back as AIFF/PCM_24 under the same name, with the
    untouched multitrack gone and no prompt. Compared by ``realpath`` so a
    symlink or a trailing slash cannot slip past. Also guards re-processing an
    already-processed set (matching a kit into the directory it was read from
    compounds the EQ on every run).
    """
    out = os.path.realpath(out_dir)
    for label, src in sources.items():
        if src and os.path.realpath(src) == out:
            raise ValueError(
                f"{flow}: --out-dir resolves to the same directory as {label} "
                f"({out}) — this flow writes a fresh set and would overwrite the "
                f"input in place. Point --out-dir at a new directory."
            )


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
    """Write at an explicit libsndfile subtype (default 32-bit float).

    Used by the bit-depth/subtype-preserving flows (stereo-merge, normalize) to
    keep the source SUBTYPE (bit depth) rather than forcing the 24-bit AIFF the
    alignment/match flows write. The output CONTAINER is derived from the
    destination extension (so a ``.wav`` name yields a real WAV even when the
    source was a mislabeled AIFF) — passed explicitly via ``format=`` because
    soundfile can't infer the 3-letter ``.aif`` container and would otherwise
    crash with a raw TypeError mid-batch. An unknown extension falls back to
    soundfile's own inference.
    """
    fmt = _EXT_FORMAT.get(os.path.splitext(path)[1].lower())
    if fmt is None:
        sf.write(path, collapse_if_mono(data), sr, subtype=subtype)
    else:
        sf.write(path, collapse_if_mono(data), sr, subtype=subtype, format=fmt)
