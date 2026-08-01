"""End-to-end drum-prep: resolve kit -> phase-align -> reference-match -> audition.

The overhead merge is handled inside phase-align (in memory, written into the
aligned set), so the chain has three reported stages. Each stage's output dir
feeds the next.
"""
from __future__ import annotations

import os

from drum_prep.audition import render_auditions
from drum_prep.kit import resolve_kit
from drum_prep.phase_align import phase_align
from drum_prep.reference_match import apply_match


def run_chain(src_dir: str, ref_path: str, manifest_path: str | None = None,
              out_root: str | None = None, strict: bool = True,
              max_lag: int = 600, excerpt_s: float = 40.0, kick_lowpass: float = 180.0,
              strength: float = 0.75, t0: float = 44.0, dur: float = 12.0,
              gap: float = 0.6, boost_cap: float = 6.0, cut_cap: float = -8.0,
              owner_thresh: float = 0.20, low_zero: float = 30.0,
              ceil_dbfs: float = -1.0) -> dict:
    # exclude the reference from kit detection if it happens to live in src_dir
    exclude = {os.path.basename(ref_path)} if ref_path else set()
    kit = resolve_kit(src_dir, manifest_path, strict, exclude=exclude)
    kit.reference = ref_path or kit.reference
    base = out_root or src_dir
    aligned = os.path.join(base, "phase-aligned")
    matched = os.path.join(base, "ref-matched")
    auds = os.path.join(base, "auditions")

    stages = [
        phase_align(kit, out_dir=aligned, max_lag=max_lag, excerpt_s=excerpt_s,
                    kick_lowpass=kick_lowpass),
        apply_match(kit, kit.reference, aligned_dir=aligned, out_dir=matched,
                    strength=strength, boost_cap=boost_cap, cut_cap=cut_cap,
                    owner_thresh=owner_thresh, low_zero=low_zero, ceil_dbfs=ceil_dbfs),
        render_auditions(kit, kit.reference, aligned_dir=aligned, matched_dir=matched,
                         out_dir=auds, t0=t0, dur=dur, gap=gap),
    ]
    return {"flow": "chain", "input": src_dir, "reference": kit.reference, "stages": stages}
