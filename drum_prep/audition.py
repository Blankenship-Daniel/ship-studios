"""Flow 3 — loudness-matched stereo A/B auditions (ITU-R BS.1770 via pyloudnorm).

  A  before-vs-after : [ kit BEFORE | gap | kit AFTER ]  (after matched to
     before's LUFS) -- hear ONLY what the reference-match EQ did.
  B  reference-vs-after : [ reference | gap | kit AFTER ] (after matched to the
     reference's LUFS) -- character check vs the target.

Kit sums are coherent stereo: mono close mics -> centre, stereo OH/room kept
L/R. Within each pair, after matching one to the other's integrated LUFS, a
single common anti-clip trim keeps the loudness match exact. Writes 24-bit WAV.
"""
from __future__ import annotations

import os

import numpy as np
import pyloudnorm as pyln

from drum_prep import dsp, io
from drum_prep.kit import Kit

# ITU-R BS.1770 integrates over 400 ms blocks; shorter audio yields -inf LUFS and
# would silently skip the loudness match. Require at least one block + margin.
_MIN_MATCH_S = 0.5


def _kit_sum(directory: str) -> tuple[np.ndarray, int]:
    names = io.list_audio(directory)
    if not names:
        raise ValueError(f"no stems found in {directory!r}")
    sr = io.common_samplerate([os.path.join(directory, nm) for nm in names])
    arrs = []
    for name in names:
        x, _ = io.read(os.path.join(directory, name))
        arrs.append(io.to_stereo(x))
    n = min(len(a) for a in arrs)
    acc = np.zeros((n, 2))
    for a in arrs:
        acc += a[:n]
    return acc, sr


def _prep_pair(left: np.ndarray, right: np.ndarray, sr: int, ceil: float):
    """Match ``right`` to ``left``'s integrated LUFS, then one common anti-clip trim.

    Callers must pass excerpts of at least ``_MIN_MATCH_S`` (see
    :func:`render_auditions`); a genuinely silent half still measures -inf, in
    which case the match is skipped and the reported LUFS will show -inf.
    """
    meter = pyln.Meter(sr)
    l_left = meter.integrated_loudness(left)
    l_right = meter.integrated_loudness(right)
    if np.isfinite(l_left) and np.isfinite(l_right):  # silent signal -> -inf; skip (no NaN)
        right = right * 10 ** ((l_left - l_right) / 20.0)
    pk = max(float(np.abs(left).max()), float(np.abs(right).max()))
    if pk > ceil:
        f = ceil / pk
        left, right = left * f, right * f
    return left, right, l_left, l_right


def _assemble(a: np.ndarray, b: np.ndarray, sr: int, gap: float, path: str) -> float:
    silence = np.zeros((int(gap * sr), 2))
    y = np.concatenate([a, silence, b])
    io.write_wav24(path, y, sr)
    return y.shape[0] / sr


def render_auditions(kit: Kit, ref_path: str | None = None, aligned_dir: str | None = None,
                     matched_dir: str | None = None, out_dir: str | None = None,
                     t0: float = 44.0, dur: float = 12.0, gap: float = 0.6,
                     ceil: float = 0.95, emit_halves: bool = True) -> dict:
    aligned_dir = aligned_dir or os.path.join(kit.src_dir, "phase-aligned")
    matched_dir = matched_dir or os.path.join(kit.src_dir, "ref-matched")
    out_dir = out_dir or os.path.join(kit.src_dir, "auditions")
    os.makedirs(out_dir, exist_ok=True)
    ref_path = ref_path or kit.reference
    if not ref_path:
        raise ValueError("no reference given (pass ref_path or set it in kit.json)")

    before, sr = _kit_sum(aligned_dir)
    after, sr2 = _kit_sum(matched_dir)
    if sr != sr2:
        raise ValueError(f"aligned/matched sample-rate mismatch: {sr} vs {sr2}")
    refx, rsr = io.read(ref_path)
    ref = io.to_stereo(refx)
    if rsr != sr:
        raise ValueError(f"reference sr {rsr} differs from stems sr {sr} — resample first")

    # kit excerpt (clamp the window to available length)
    nframes = min(len(before), len(after))
    a, b = int(t0 * sr), int((t0 + dur) * sr)
    if b > nframes:
        b = nframes
        a = max(0, nframes - int(dur * sr))
    before_x, after_x = before[a:b], after[a:b]
    # reference: loudest dur-second window (handles loop or full track)
    ref_x = ref[dsp.pick_excerpt(dsp.mono(ref), rsr, dur)]

    # Guard the loudness-match contract: too-short excerpts measure -inf LUFS and
    # would emit an UNMATCHED A/B while claiming to be matched. Fail clearly.
    min_frames = int(_MIN_MATCH_S * sr)
    for label, seg in (("kit", before_x), ("reference", ref_x)):
        if len(seg) < min_frames:
            raise ValueError(
                f"{label} excerpt is {len(seg) / sr:.2f}s — too short for "
                f"ITU-R BS.1770 loudness matching (need >= {_MIN_MATCH_S}s); "
                "increase --dur or use longer source audio")

    auditions = []
    bA, aA, lb, la = _prep_pair(before_x, after_x, sr, ceil)
    path_a = os.path.join(out_dir, "AB_before-vs-after.wav")
    dur_a = _assemble(bA, aA, sr, gap, path_a)
    auditions.append({"name": "before-vs-after", "path": path_a, "seconds": round(dur_a, 1),
                      "lufs_before": round(lb, 2), "lufs_after": round(la, 2),
                      "gain_db_on_after": round(lb - la, 2)})

    rB, aB, lr, lak = _prep_pair(ref_x, after_x, sr, ceil)
    path_b = os.path.join(out_dir, "AB_reference-vs-after.wav")
    dur_b = _assemble(rB, aB, sr, gap, path_b)
    auditions.append({"name": "reference-vs-after", "path": path_b, "seconds": round(dur_b, 1),
                      "lufs_reference": round(lr, 2), "lufs_after": round(lak, 2),
                      "gain_db_on_after": round(lr - lak, 2)})

    # standalone loudness-matched halves -> feed directly to stemmy-gemini
    # compare-to-reference (mix_path=after, reference_path=reference). Saves the
    # manual slice of the concatenated A/B.
    halves = None
    if emit_halves:
        ref_h = os.path.join(out_dir, "cmp_reference.wav")
        aft_h = os.path.join(out_dir, "cmp_after.wav")
        io.write_wav24(ref_h, rB, sr)
        io.write_wav24(aft_h, aB, sr)
        halves = {"reference": ref_h, "after": aft_h, "lufs": round(lr, 2),
                  "note": "loudness-matched; feed to compare-to-reference "
                          "(mix_path=after, reference_path=reference)"}

    return {"flow": "audition", "reference": ref_path, "out_dir": out_dir,
            "kit_excerpt_s": [round(a / sr, 1), round(b / sr, 1)], "auditions": auditions,
            "gemini_halves": halves}
