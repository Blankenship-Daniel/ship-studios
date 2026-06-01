"""Flow 2 — reference-match the kit's tonal balance, per stem.

Measures the kit as the **coherent time-domain sum** of the aligned stems (what
they actually sum to in a DAW — a power-sum would undercount the correlated kick
low-end and over-boost it). Builds one corrective 1/3-octave curve toward the
reference at ``strength``, then distributes it:
  * cuts   -> every stem (uniform = exact bus darkening, harmless where silent)
  * boosts -> only the band's owner(s) (share >= ``owner_thresh``, fc >= ``low_zero``)
EQ is zero-phase (real, symmetric gain) so the prior phase alignment is intact.
A single global headroom trim preserves inter-stem balance.

``analyze`` is read-only (no writes); ``apply_match`` writes ``<src>/ref-matched/``.
"""
from __future__ import annotations

import os

import numpy as np

from drum_prep import dsp, io
from drum_prep.kit import Kit

THIRD = dsp.THIRD_OCT


def _measure(aligned_dir: str, ref_path: str, nperseg: int) -> dict:
    rx, rsr = io.read_mono(ref_path)
    fr, pr = dsp.psd(rx, rsr, nperseg)
    ref_db = dsp.band_db(fr, pr, THIRD)

    names = io.list_audio(aligned_dir)
    if not names:
        raise ValueError(f"no aligned stems found in {aligned_dir!r}")
    # All stems must share one SR (the coherent sum below is time-domain), and
    # that SR must match the reference — validate the whole set, not just the
    # last file read.
    sr = io.common_samplerate([os.path.join(aligned_dir, nm) for nm in names])
    if sr != rsr:
        raise ValueError(f"reference sr {rsr} differs from stems sr {sr} — resample first")
    raw: list[tuple[str, np.ndarray]] = []
    powr: list[np.ndarray] = []
    cur = None
    for name in names:
        x, _ = io.read(os.path.join(aligned_dir, name))
        m = dsp.mono(x)
        f, p = dsp.psd(m, sr, nperseg)
        powr.append(dsp.band_power(f, p, THIRD))
        raw.append((name, x))
        if cur is None:
            cur = m.copy()
        else:
            n = min(len(cur), len(m))
            cur = cur[:n] + m[:n]
    assert cur is not None
    fc, pc = dsp.psd(cur, sr, nperseg)
    cur_db = dsp.band_db(fc, pc, THIRD)
    M = np.array(powr)
    share = M / (M.sum(axis=0, keepdims=True) + 1e-20)
    return {"ref_db": ref_db, "cur_db": cur_db, "names": names, "raw": raw,
            "share": share, "sr": sr, "nperseg": nperseg}


def analyze(kit: Kit, ref_path: str | None = None, aligned_dir: str | None = None,
            nperseg: int = 16384) -> dict:
    """Read-only tonal report: reference vs kit shape + per-stem band ownership."""
    aligned_dir = aligned_dir or os.path.join(kit.src_dir, "phase-aligned")
    ref_path = ref_path or kit.reference
    if not ref_path:
        raise ValueError("no reference given (pass ref_path or set it in kit.json)")
    m = _measure(aligned_dir, ref_path, nperseg)
    delta = dsp.shape(m["ref_db"], THIRD) - dsp.shape(m["cur_db"], THIRD)
    # dominant stem per macro band (informational)
    share = m["share"]
    ownership = {}
    for gname, (lo, hi) in dsp.GROUPS.items():
        bidx = np.where((THIRD >= lo) & (THIRD < hi))[0]
        if len(bidx):
            si = int(share[:, bidx].mean(axis=1).argmax())
            ownership[gname] = m["names"][si]
    return {
        "flow": "analyze", "reference": ref_path, "aligned_dir": aligned_dir,
        "ref_tilt": round(dsp.tilt(m["ref_db"], THIRD), 3),
        "kit_tilt": round(dsp.tilt(m["cur_db"], THIRD), 3),
        "delta_6band": {k: round(v, 2) for k, v in dsp.group_avg(delta, THIRD).items()},
        "band_owner": ownership, "stems": m["names"],
    }


def apply_match(kit: Kit, ref_path: str | None = None, aligned_dir: str | None = None,
                out_dir: str | None = None, strength: float = 0.75,
                boost_cap: float = 6.0, cut_cap: float = -8.0,
                owner_thresh: float = 0.20, low_zero: float = 30.0,
                nperseg: int = 16384, ceil_dbfs: float = -1.0) -> dict:
    aligned_dir = aligned_dir or os.path.join(kit.src_dir, "phase-aligned")
    out_dir = out_dir or os.path.join(kit.src_dir, "ref-matched")
    os.makedirs(out_dir, exist_ok=True)
    ref_path = ref_path or kit.reference
    if not ref_path:
        raise ValueError("no reference given (pass ref_path or set it in kit.json)")

    m = _measure(aligned_dir, ref_path, nperseg)
    sr, names, raw, share = m["sr"], m["names"], m["raw"], m["share"]

    # corrective curve: smoothed, strength-scaled, capped
    delta = dsp.shape(m["ref_db"], THIRD) - dsp.shape(m["cur_db"], THIRD)
    sm = np.convolve(delta, [0.25, 0.5, 0.25], mode="same")
    sm[0], sm[-1] = delta[0], delta[-1]
    corr = np.clip(sm * strength, cut_cap, boost_cap)

    # per-stem gains: cuts -> all; boosts -> owners only, not below low_zero
    gains: list[np.ndarray] = []
    for si in range(len(names)):
        g = np.zeros(len(THIRD))
        for bi, fc in enumerate(THIRD):
            c = corr[bi]
            if c < 0:
                g[bi] = c
            elif fc >= low_zero and share[si, bi] >= owner_thresh:
                g[bi] = c
        gains.append(g)

    # apply EQ, then one global headroom trim (preserves inter-stem balance)
    outs = [dsp.zero_phase_eq(x, sr, THIRD, gains[i]) for i, (_, x) in enumerate(raw)]
    gpeak = max(float(np.abs(o).max()) for o in outs)
    ceil = 10 ** (ceil_dbfs / 20.0)
    trim = min(1.0, ceil / gpeak) if gpeak > 0 else 1.0

    eq_sig = None
    per_stem_eq = {}
    for (name, _), out in zip(raw, outs, strict=True):  # one EQ'd output per stem
        out = out * trim
        io.write_aiff24(os.path.join(out_dir, name), out, sr)
        per_stem_eq[name] = {k: round(v, 1) for k, v in
                             dsp.group_avg(gains[names.index(name)], THIRD).items()}
        mm = dsp.mono(out)
        if eq_sig is None:
            eq_sig = mm.copy()
        else:
            n = min(len(eq_sig), len(mm))
            eq_sig = eq_sig[:n] + mm[:n]

    assert eq_sig is not None
    fe, pe = dsp.psd(eq_sig, sr, nperseg)
    new_db = dsp.band_db(fe, pe, THIRD)
    before = dsp.group_avg(dsp.shape(m["ref_db"], THIRD) - dsp.shape(m["cur_db"], THIRD), THIRD)
    after = dsp.group_avg(dsp.shape(m["ref_db"], THIRD) - dsp.shape(new_db, THIRD), THIRD)

    # diagnose stubborn residuals: low-band shortfalls that EQ can't close are an
    # *extension/sustain* problem (close mics lack fundamental), not a level one.
    low_bands = {"sub 20-60", "low 60-120"}
    notes: list[str] = []
    for band, val in after.items():
        if val >= 2.5:
            if band in low_bands:
                notes.append(f"{band}: still {val:+.1f} dB short — likely extension/"
                             "sustain, not level (close mics lack fundamental); add a "
                             "sub-harmonic generator or saturation at the mix, not more EQ")
            else:
                notes.append(f"{band}: still {val:+.1f} dB short — raise --strength "
                             "(or --boost-cap if the owner boost is capped) to close more")
        elif val <= -2.5:
            notes.append(f"{band}: kit {abs(val):.1f} dB hot vs reference")
    if not notes:
        notes.append("all 6 macro bands within 2.5 dB of the reference")

    return {
        "flow": "reference-match", "reference": ref_path, "aligned_dir": aligned_dir,
        "out_dir": out_dir, "strength": strength,
        "global_trim_db": round(20 * np.log10(trim), 2),
        "ref_tilt": round(dsp.tilt(m["ref_db"], THIRD), 2),
        "kit_tilt_before": round(dsp.tilt(m["cur_db"], THIRD), 2),
        "kit_tilt_after": round(dsp.tilt(new_db, THIRD), 2),
        "residual_before": {k: round(v, 2) for k, v in before.items()},
        "residual_after": {k: round(v, 2) for k, v in after.items()},
        "per_stem_eq": per_stem_eq, "notes": notes,
    }
