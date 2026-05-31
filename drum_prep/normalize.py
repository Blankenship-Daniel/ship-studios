"""Flow 0.5 — gain-stage a multi-mic kit (balance-preserving by default).

The non-obvious rule this encodes: on a multi-mic kit the *relative* mic levels
ARE the kit balance, so normalizing each file independently destroys it.
``mode="global"`` applies ONE gain (derived from the loudest peak across the
whole set) to every stem and to both channels of the stereo files — relative
balance and stereo image untouched. ``mode="per_file"`` is offered but warned
against (it changes the kit balance). Source bit/format is preserved.

Verified non-destructive: writes to ``<src>/normalized/`` (never edits inputs).
"""
from __future__ import annotations

import os

import numpy as np

from drum_prep import io


def _db(v: float) -> float:
    return 20.0 * np.log10(v) if v > 0 else float("-inf")


def _peak(path: str) -> float:
    x, _ = io.read(path)
    return float(np.max(np.abs(x))) if x.size else 0.0


def normalize_kit(src_dir: str, out_dir: str | None = None, target_dbfs: float = -1.0,
                  mode: str = "global", extra: tuple[str, ...] = ()) -> dict:
    """Normalize every audio file in ``src_dir`` (+ optional ``extra`` paths).

    ``mode='global'`` (default): one uniform gain so the loudest peak across the
    whole set hits ``target_dbfs`` — preserves inter-mic balance + stereo image.
    ``mode='per_file'``: each file independently to ``target_dbfs`` — maximizes
    each stem but CHANGES the kit balance.
    """
    if mode not in ("global", "per_file"):
        raise ValueError("mode must be 'global' or 'per_file'")
    out_dir = out_dir or os.path.join(src_dir, "normalized")
    os.makedirs(out_dir, exist_ok=True)
    files = [(os.path.join(src_dir, f), f) for f in io.list_audio(src_dir)]
    files += [(p, os.path.basename(p)) for p in extra]
    if not files:
        raise ValueError(f"no audio files in {src_dir!r}")

    target_lin = 10.0 ** (target_dbfs / 20.0)
    peaks = {src: _peak(src) for src, _ in files}
    overall = max(peaks.values()) or 1.0
    ggain = target_lin / overall  # global gain (used when mode == 'global')

    rows, deltas = [], []
    for src, rel in files:
        x, sr = io.read(src)
        pk = peaks[src]
        gain = ggain if mode == "global" else (target_lin / pk if pk > 0 else 1.0)
        y = x * gain
        dst = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        io.write_wav(dst, y, sr, subtype=io.subtype_of(src))
        deltas.append(_db(gain))
        rows.append({"file": rel, "in_peak_dbfs": round(_db(pk), 2),
                     "out_peak_dbfs": round(_db(pk * gain), 2),
                     "gain_db": round(_db(gain), 3), "channels": int(x.shape[1])})

    spread = (max(deltas) - min(deltas)) if deltas else 0.0
    return {
        "flow": "normalize", "src_dir": src_dir, "out_dir": out_dir, "mode": mode,
        "target_dbfs": target_dbfs, "set_peak_dbfs": round(_db(overall), 3),
        "global_gain_db": round(_db(ggain), 3) if mode == "global" else None,
        "gain_spread_db": round(spread, 4),
        "balance_preserved": bool(mode == "global" and spread < 0.01),
        "files": rows,
    }
