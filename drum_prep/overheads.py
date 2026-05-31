"""Flow 0 — resolve the stereo overhead reference.

If the kit already has a pre-merged stereo overhead, that file *is* the
reference. If it has a separate L/R pair, stack them into one stereo file. By
default the L/R image is preserved (no time-alignment) — a spaced overhead pair
*should* keep its inter-channel timing; pass ``align=True`` only for a
coincident pair you want phase-locked.
"""
from __future__ import annotations

import os

import numpy as np

from drum_prep import dsp, io
from drum_prep.kit import Kit, KitError, overhead_lr, overhead_reference


def resolve_overhead(kit: Kit, align: bool = False, max_lag: int = 200
                     ) -> tuple[np.ndarray, int, str]:
    """Return ``(stereo (N,2), sr, out_name)`` for the overhead reference.

    Merges an L/R pair in memory when needed; never writes to disk.
    """
    oh = overhead_reference(kit)
    if oh is not None:
        x, sr = io.read(kit.path(oh))
        return io.to_stereo(x), sr, oh.name

    left, right = overhead_lr(kit)
    if left is None or right is None:
        raise KitError("no overheads to resolve (need role 'overhead', or both "
                       "'overhead_l' and 'overhead_r')")
    lft, sr = io.read_mono(kit.path(left))
    rgt, sr2 = io.read_mono(kit.path(right))
    if sr != sr2:
        raise KitError(f"overhead L/R sample-rate mismatch: {sr} vs {sr2}")
    n = min(len(lft), len(rgt))
    lft, rgt = lft[:n], rgt[:n]
    if align:  # opt-in: phase-lock R to L (collapses a spaced-pair image)
        d, pol, _, _ = dsp.align_to(rgt, lft, max_lag, sr)
        rgt = dsp.fractional_delay(rgt, d) * pol
    return np.column_stack([lft, rgt]), sr, "overheads-merged.aif"


def merge_overheads(kit: Kit, out_path: str | None = None, align: bool = False) -> dict:
    """Standalone flow: write the merged stereo overhead (no-op if already stereo)."""
    oh = overhead_reference(kit)
    if oh is not None:
        return {"flow": "overheads", "merged": False, "reference": kit.path(oh),
                "note": "already a stereo overhead — nothing to merge"}
    arr, sr, name = resolve_overhead(kit, align=align)
    out = out_path or os.path.join(kit.src_dir, name)
    io.write_aiff24(out, arr, sr)
    return {"flow": "overheads", "merged": True, "output": out, "sr": sr,
            "aligned": align, "frames": int(arr.shape[0])}
