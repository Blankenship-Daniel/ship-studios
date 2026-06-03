"""Flow -1 — consolidate L/R spaced pairs into stereo files (subtype-preserving).

Generalizes :mod:`drum_prep.overheads` (which only did the overhead role and
wrote 24-bit AIFF) to *any* ``<name> - left`` / ``<name> - right`` pair —
overhead, room, a stereo snare-plate return, etc. The merge is a straight
L->left / R->right interleave (no time-alignment) so a spaced pair keeps its
natural inter-channel image; pass ``align=True`` only for a coincident pair you
want phase-locked. The source bit-depth/subtype is preserved (Float32 stays
Float32); the output container follows the output extension (the merged file is
written under ``<stem><ext>`` where ``ext`` is the left file's extension).

The value here is the **review** baked into every merge: inter-channel
correlation, best-lag delay, polarity, mono-sum loss, and a reverb-vs-mic flag —
the same read that caught a "snare plate" being a reverb return, not a mic.
"""
from __future__ import annotations

import os
import re

import numpy as np
from scipy.signal import correlate

from drum_prep import dsp, io

_SIDE_RE = re.compile(r"[\s_\-]+(left|right|l|r)$", re.IGNORECASE)


def _db(v: float) -> float:
    return 20.0 * np.log10(v) if v > 0 else float("-inf")


def _split_side(filename: str) -> tuple[str, str | None]:
    """('overhead', 'L') from 'overhead - left.wav'; (base, None) if no side token."""
    base = os.path.splitext(filename)[0]
    m = _SIDE_RE.search(base)
    if not m:
        return base, None
    stem = base[: m.start()].rstrip(" _-")
    return stem, ("L" if m.group(1).lower() in ("left", "l") else "R")


def find_pairs(directory: str) -> list[tuple[str, str, str]]:
    """Sorted ``(stem, left_file, right_file)`` for every complete L/R pair.

    Raises ``ValueError`` when two files collapse to the same ``(stem, side)``
    (e.g. ``oh - l.wav`` and ``oh - left.wav``) — silently keeping only one and
    dropping the other would build the merge from the wrong file with no warning.
    """
    sides: dict[str, dict[str, str]] = {}
    for f in io.list_audio(directory):
        stem, side = _split_side(f)
        if side is not None:
            existing = sides.setdefault(stem, {}).get(side)
            if existing is not None:
                raise ValueError(
                    f"ambiguous {side} side for stem {stem!r}: {existing!r} and {f!r} "
                    "— rename one so each side resolves to a single file"
                )
            sides[stem][side] = f
    return [(stem, d["L"], d["R"]) for stem, d in sorted(sides.items())
            if "L" in d and "R" in d]


def _best_lag(a: np.ndarray, b: np.ndarray, sr: int, max_ms: float = 50.0) -> tuple[int, float]:
    """Inter-channel delay (samples) + normalized corr at that lag, on a mid excerpt."""
    n = len(a)
    seg = min(n, sr * 20)
    s = (n - seg) // 2
    aa = a[s:s + seg].astype(np.float64)
    aa -= aa.mean()
    bb = b[s:s + seg].astype(np.float64)
    bb -= bb.mean()
    na, nb = np.linalg.norm(aa), np.linalg.norm(bb)
    if na == 0 or nb == 0:
        return 0, 0.0
    xc = correlate(aa, bb, mode="full", method="fft") / (na * nb)
    c = len(xc) // 2
    # Clamp the lag window to the available correlation half-width; otherwise a
    # short excerpt makes c-ml negative and the slice wraps -> a garbage lag.
    ml = min(int(sr * max_ms / 1000.0), c)
    win = xc[c - ml:c + ml + 1]
    k = int(np.argmax(np.abs(win)))
    return k - ml, float(win[k])


def review_pair(left: np.ndarray, right: np.ndarray, sr: int) -> dict:
    """Read-only image analysis of an L/R pair (no audio written)."""
    n = min(len(left), len(right))
    L, R = left[:n], right[:n]

    def st(x: np.ndarray) -> dict:
        pk = float(np.max(np.abs(x))) if x.size else 0.0
        rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if x.size else 0.0
        return {"peak_dbfs": round(_db(pk), 2), "rms_dbfs": round(_db(rms), 2),
                "over_1.0": int(np.sum(np.abs(x) > 1.0))}

    sL, sR = st(L), st(R)
    Ld = L.astype(np.float64) - L.mean()
    Rd = R.astype(np.float64) - R.mean()
    den = np.linalg.norm(Ld) * np.linalg.norm(Rd)
    corr0 = float(np.dot(Ld, Rd) / den) if den else 0.0
    lag, corr_lag = _best_lag(L, R, sr)
    mono = 0.5 * (Ld + Rd)
    side = 0.5 * (Ld - Rd)
    mono_rms = _db(float(np.sqrt(np.mean(mono ** 2))))
    side_rms = _db(float(np.sqrt(np.mean(side ** 2))))
    louder = max(sL["rms_dbfs"], sR["rms_dbfs"])
    mono_loss = louder - mono_rms
    width = side_rms - mono_rms
    lag_ms = lag / sr * 1000.0
    likely_reverb = (corr_lag < 0.0 or abs(corr0) < 0.2) and abs(lag_ms) > 5.0
    return {
        "left": sL, "right": sR, "frames": int(n),
        "corr_lag0": round(corr0, 3), "best_corr": round(corr_lag, 3),
        "best_lag_samples": int(lag), "best_lag_ms": round(lag_ms, 2),
        "polarity": "inverted" if corr_lag < 0 else "normal",
        "mono_sum_loss_db": round(mono_loss, 2),
        "mono_safe": bool(mono_loss < 3.0),
        "side_minus_mid_db": round(width, 1),
        "image": "mono/near-coincident" if width < -12 else "spaced/wide",
        "likely_reverb_return": bool(likely_reverb),
    }


def merge_pair(left_path: str, right_path: str, out_path: str,
               align: bool = False, max_lag: int = 600) -> dict:
    """Interleave L/R -> stereo at the source subtype (container = out extension);
    returns the review + verify."""
    L, srL = io.read(left_path, mono_sum=True)
    R, srR = io.read(right_path, mono_sum=True)
    if srL != srR:
        raise ValueError(f"sample-rate mismatch: {srL} vs {srR}")
    sr = srL
    n = min(len(L), len(R))
    L, R = L[:n], R[:n]
    rep = review_pair(L, R, sr)
    if align:  # opt-in: phase-lock R to L (collapses a spaced image)
        d, pol, _, _ = dsp.align_to(R, L, max_lag, sr)
        R = dsp.fractional_delay(R, d) * pol
    # The merged file carries ONE subtype; if L/R disagree the right channel is
    # coerced to the left's format. That's rare for a true pair but must not be
    # silent — surface it so a PCM_24/FLOAT mismatch is visible, not lossy-by-stealth.
    subtype = io.subtype_of(left_path)
    right_subtype = io.subtype_of(right_path)
    subtype_mismatch = subtype != right_subtype
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    io.write_wav(out_path, np.column_stack([L, R]), sr, subtype=subtype)
    chk, _ = io.read(out_path)
    verified = chk.shape[1] == 2 and chk.shape[0] == n
    return {"out": out_path, "sr": sr, "subtype": subtype, "frames": int(n),
            "subtype_mismatch": subtype_mismatch,
            "right_subtype": right_subtype if subtype_mismatch else None,
            "aligned": align, "verified": bool(verified), "review": rep}


def merge_dir(src_dir: str, out_dir: str | None = None, align: bool = False) -> dict:
    """Merge every complete L/R pair found in ``src_dir`` into stereo files."""
    pairs = find_pairs(src_dir)
    if not pairs:
        raise ValueError(f"no '<name> - left/right' pairs found in {src_dir!r}")
    out_dir = out_dir or os.path.join(src_dir, "stereo")
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for stem, lf, rf in pairs:
        ext = os.path.splitext(lf)[1]
        res = merge_pair(os.path.join(src_dir, lf), os.path.join(src_dir, rf),
                         os.path.join(out_dir, f"{stem}{ext}"), align=align)
        res["stem"] = stem
        results.append(res)
    return {"flow": "stereo-merge", "src_dir": src_dir, "out_dir": out_dir,
            "pairs": len(results), "merged": results}
