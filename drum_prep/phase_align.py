"""Flow 1 — phase-align every close mic to the overheads (fixed reference).

Topology is derived from the kit roles, not hard-coded names:
  * broadband close mics (snare-top, hats, toms, ride/crash) -> OH
  * kick mics -> OH using a low-pass correlation (lock the fundamental, not
    cymbal bleed)
  * partner pairs (snare-bottom -> snare-top, kick-beater -> kick-in) align to
    their partner, then compose onto the OH timeline
  * room/ambience -> polarity-checked only, timing kept
  * overheads -> untouched reference, copied through

Method per mic: envelope-coarse delay -> waveform polarity + sub-sample refine
(no half-period slips) -> length-preserving fractional delay. Non-destructive;
writes a fresh 24-bit AIFF set into ``<src>/phase-aligned/``.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass

import numpy as np

from drum_prep import dsp, io
from drum_prep.kit import (
    Kit,
    ambience_stems,
    anchored_to_oh,
    overhead_lr,
    overhead_reference,
    partner_pairs,
)
from drum_prep.overheads import resolve_overhead

SOUND_CMS = 34300.0  # speed of sound, cm/s — for the distance sanity column
_MIN_OVERLAP = 64    # samples — below this an FFT correlation is meaningless

#: post_corr below this triggers a wider re-search to check for a railed max_lag.
#: Above it the peak is already convincing, so the (2x cost) probe is skipped —
#: which is the common case, so a healthy kit pays nothing.
_RAIL_PROBE_BELOW = 0.75
#: ...and the wider result must beat the narrow one by this much to be believed,
#: so a legitimately low-correlation mic (hi-hat vs overheads) isn't misread as
#: railed and skipped.
_RAIL_MARGIN = 0.10


def _excerpt_overlap(sig: np.ndarray, sl: slice) -> tuple[slice, bool]:
    """Slice of ``sig`` overlapping the OH excerpt window ``sl``.

    The excerpt slice is derived from the (full-length) overheads; a close mic
    shorter than ``sl.start`` would give ``sig[sl]`` an EMPTY array, and the bare
    ``np.fft.rfft([])`` downstream raises a cryptic 'Invalid number of FFT data
    points (0)'. Clamp the window to the stem's actual length so we align over
    the real overlap instead. Returns ``(local_slice, ok)`` where ``ok`` is False
    when the overlap is too short to align meaningfully (caller skips + notes).
    """
    stop = min(sl.stop, len(sig))
    if sl.start >= len(sig) or stop - sl.start < _MIN_OVERLAP:
        return slice(0, 0), False
    return slice(sl.start, stop), True


def _touched_paths(kit: Kit) -> list[str]:
    """Every stem path :func:`phase_align` reads and writes back out.

    Deliberately built from the same role helpers the flow itself iterates, so a
    stem can never be aligned without having been sample-rate checked. Stems
    excluded from alignment (FX returns) are not touched and not checked.
    """
    stems = list(anchored_to_oh(kit)) + list(ambience_stems(kit))
    for partner, anchor in partner_pairs(kit):
        stems += [partner, anchor]
    oh = overhead_reference(kit)
    if oh is not None:
        stems.append(oh)
    else:
        stems += [s for s in overhead_lr(kit) if s is not None]
    # dict.fromkeys: de-dupe (an anchor is also in anchored_to_oh) but keep order,
    # so the mismatch message lists stems in a stable, reproducible order.
    return list(dict.fromkeys(kit.path(s) for s in stems))


@dataclass
class AlignResult:
    name: str
    role: str
    delay_samples: float
    polarity: int
    pre_corr: float
    post_corr: float
    note: str


def phase_align(kit: Kit, out_dir: str | None = None, max_lag: int = 600,
                excerpt_s: float = 40.0, kick_lowpass: float = 180.0) -> dict:
    out_dir = out_dir or os.path.join(kit.src_dir, "phase-aligned")
    io.refuse_in_place("phase-align", out_dir, the_stem_dir=kit.src_dir)

    # Every stem is written back out at the OVERHEAD's rate, so the whole set must
    # already share one rate. Without this a 44.1k room mic in a 48k kit is rewritten
    # as 48k — pitched +8.8%, `warnings: []` — and because every downstream stage then
    # sees a uniform set, it passes THEIR io.common_samplerate checks and the
    # corruption is laundered through the rest of the chain. Header-only, and checked
    # BEFORE makedirs so a mismatch leaves no empty output dir behind. Resampling is
    # out of scope here (it would change the timing this flow exists to measure) —
    # raise and let the operator convert upstream.
    io.common_samplerate(_touched_paths(kit))

    os.makedirs(out_dir, exist_ok=True)
    oh_arr, sr, oh_name = resolve_overhead(kit)
    ref_m = dsp.mono(oh_arr)
    sl = dsp.pick_excerpt(ref_m, sr, excerpt_s)
    io.write_aiff24(os.path.join(out_dir, oh_name), oh_arr, sr)  # OH passthrough

    results = [AlignResult(oh_name, "overhead", 0.0, 1, 1.0, 1.0, "reference (fixed)")]
    aligned_segs: dict = {}
    anchor_delay: dict[str, tuple[float, float]] = {}
    plan: list[tuple] = []  # (stem, full_sig, delay, polarity, pre, post, note)

    # --- mics anchored directly to the overheads ---
    for s in anchored_to_oh(kit):
        sig = io.read_mono(kit.path(s))[0]
        is_kick = s.role.value.startswith("kick")
        band = s.lowpass_hz if s.lowpass_hz is not None else (kick_lowpass if is_kick else None)
        sub, ok = _excerpt_overlap(sig, sl)
        if not ok:  # stem shorter than the excerpt window — skip, keep timing, note it
            anchor_delay[s.name] = (0.0, 1.0)
            warn = f"{s.name}: shorter than the OH excerpt window — alignment skipped"
            kit.warnings.append(warn)
            plan.append((s, sig, 0.0, 1.0, 0.0, 0.0, "-> OH (skipped: too short)"))
            continue
        d, pol, pre, post = dsp.align_to(sig[sub], ref_m[sub], max_lag, sr, band=band)
        if post < _RAIL_PROBE_BELOW:
            wider = dsp.align_probe_wider(sig[sub], ref_m[sub], max_lag, sr, band=band)
            if wider is not None and wider[3] > post + _RAIL_MARGIN:
                # The true delay is OUTSIDE +/- max_lag, so `d` is a sidelobe — and a
                # sidelobe brings a bogus polarity with it, which would make this mic
                # partially CANCEL the overheads. Keep the stem untouched and say so;
                # applying a shift we have just proven wrong is the actual defect.
                # Not auto-widening: max_lag is the operator's stated search range,
                # and silently exceeding it would hide a genuine mic-distance error.
                warn = (f"{s.name}: true delay ≈ {wider[0]:.0f} samples lies outside "
                        f"--max-lag {max_lag} (corr {post:.3f} -> {wider[3]:.3f} when "
                        f"searched wider) — alignment SKIPPED; re-run with "
                        f"--max-lag {int(abs(wider[0]) * 1.5)} or larger")
                kit.warnings.append(warn)
                anchor_delay[s.name] = (0.0, 1.0)
                plan.append((s, sig, 0.0, 1.0, pre, post, "-> OH (skipped: lag > max_lag)"))
                continue
        if s.polarity_lock is not None:
            pol = float(s.polarity_lock)
        anchor_delay[s.name] = (d, pol)
        note = "-> OH" + (f" (LP{int(band)})" if band else "")
        plan.append((s, sig, d, pol, pre, post, note))

    # --- partner pairs: align to partner, then compose onto the OH timeline ---
    for partner, anchor in partner_pairs(kit):
        psig = io.read_mono(kit.path(partner))[0]
        asig = io.read_mono(kit.path(anchor))[0]
        # clamp the excerpt to BOTH signals' lengths (either may be short)
        stop = min(sl.stop, len(psig), len(asig))
        ok = sl.start < min(len(psig), len(asig)) and stop - sl.start >= _MIN_OVERLAP
        if not ok:  # too little overlap to align the pair — keep timing, note it
            warn = f"{partner.name}: too short to align to {anchor.name} — alignment skipped"
            kit.warnings.append(warn)
            d_anchor, pol_anchor = anchor_delay.get(anchor.name, (0.0, 1.0))
            pol_total = (float(partner.polarity_lock) if partner.polarity_lock is not None
                         else pol_anchor)
            plan.append((partner, psig, d_anchor, pol_total, 0.0, 0.0,
                         f"-> {anchor.name} (skipped: too short)"))
            continue
        sub = slice(sl.start, stop)
        d_pa, pol_pa, pre, post = dsp.align_to(psig[sub], asig[sub], max_lag, sr)
        d_anchor, pol_anchor = anchor_delay.get(anchor.name, (0.0, 1.0))
        d_total = d_pa + d_anchor
        pol_total = (float(partner.polarity_lock) if partner.polarity_lock is not None
                     else pol_pa * pol_anchor)
        plan.append((partner, psig, d_total, pol_total, pre, post, f"-> {anchor.name}"))

    # --- apply, write, record ---
    for s, sig, d, pol, pre, post, note in plan:
        out = dsp.fractional_delay(sig, d) * pol
        io.write_aiff24(os.path.join(out_dir, s.name), out, sr)
        aligned_segs[s.name] = out[sl]
        results.append(AlignResult(s.name, s.role.value, round(float(d), 3), int(pol),
                                   round(pre, 4), round(post, 4), note))

    # --- room/ambience: polarity-check only, timing kept ---
    for s in ambience_stems(kit):
        rx, _ = io.read(kit.path(s))
        if s.polarity_lock is not None:
            rpol = float(s.polarity_lock)
        else:
            rmono = dsp.mono(rx)
            sub, ok = _excerpt_overlap(rmono, sl)
            if not ok:  # too short to read polarity — keep as-is (+1), note it
                rpol = 1.0
                kit.warnings.append(f"{s.name}: shorter than the OH excerpt window — "
                                    "polarity check skipped (kept +1)")
            else:
                _, rpeak = dsp.estimate(rmono[sub], ref_m[sub], max_lag)
                rpol = -1.0 if rpeak < 0 else 1.0
        io.write_aiff24(os.path.join(out_dir, s.name), rx * rpol, sr)
        results.append(AlignResult(s.name, s.role.value, 0.0, int(rpol), 0.0, 0.0,
                                   "ambience (timing kept)"))

    # --- validation: partner pairs must now be in phase (positive corr) ---
    validation = {}
    for partner, anchor in partner_pairs(kit):
        if partner.name in aligned_segs and anchor.name in aligned_segs:
            key = f"{anchor.name} vs {partner.name}"
            validation[key] = round(dsp.normcorr(aligned_segs[anchor.name],
                                                 aligned_segs[partner.name]), 4)

    return {
        "flow": "phase-align",
        "input": kit.src_dir,
        "reference": oh_name,
        "sr": sr,
        "excerpt_s": [round(sl.start / sr, 1), round(sl.stop / sr, 1)],
        "out_dir": out_dir,
        "results": [asdict(r) for r in results],
        "validation": validation,
        "warnings": kit.warnings,
    }
