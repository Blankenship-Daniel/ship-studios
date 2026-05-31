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

from drum_prep import dsp, io
from drum_prep.kit import Kit, anchored_to_oh, ambience_stems, partner_pairs
from drum_prep.overheads import resolve_overhead

SOUND_CMS = 34300.0  # speed of sound, cm/s — for the distance sanity column


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
    os.makedirs(out_dir, exist_ok=True)

    oh_arr, sr, oh_name = resolve_overhead(kit)
    ref_m = dsp.mono(oh_arr)
    sl = dsp.pick_excerpt(ref_m, sr, excerpt_s)
    ref_seg = ref_m[sl]
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
        d, pol, pre, post = dsp.align_to(sig[sl], ref_seg, max_lag, sr, band=band)
        if s.polarity_lock is not None:
            pol = float(s.polarity_lock)
        anchor_delay[s.name] = (d, pol)
        note = "-> OH" + (f" (LP{int(band)})" if band else "")
        plan.append((s, sig, d, pol, pre, post, note))

    # --- partner pairs: align to partner, then compose onto the OH timeline ---
    for partner, anchor in partner_pairs(kit):
        psig = io.read_mono(kit.path(partner))[0]
        asig = io.read_mono(kit.path(anchor))[0]
        d_pa, pol_pa, pre, post = dsp.align_to(psig[sl], asig[sl], max_lag, sr)
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
            _, rpeak = dsp.estimate(dsp.mono(rx)[sl], ref_seg, max_lag)
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
