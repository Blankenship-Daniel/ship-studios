"""Flow 2.5 — mix a prepped multi-mic kit to a stereo bus (balance + pan + FX).

The stage neither stemmy (single-file tools) nor the rest of drum_prep
(tone/timing prep only) covers. Balance is set by measured per-stem integrated
loudness offsets relative to the overhead anchor, so it's role-driven and
deterministic. Panning follows a chosen perspective (drummer flips hi-hat to the
left and the overhead/room L/R image); a spaced room pair is channel-balanced;
an optional plate/FX file is folded in as a return. ``flat=True`` skips
balance/pan for a unity bounce (overhead/room stereo, mono mics centred).

No bus compression/limiting — glue and loudness stay with master-track. Writes a
24-bit WAV bus (+ optional excerpt). One global anti-clip trim preserves balance.
"""
from __future__ import annotations

import os
from typing import Any

import numpy as np

from drum_prep import dsp, io
from drum_prep.kit import Kit
from drum_prep.roles import Role

# per-role integrated-loudness offset (dB) vs the overhead anchor, per feel.
FEELS: dict[str, dict[str, float]] = {
    "roomy":   {"overhead": 0, "room": -5, "kick_in": -2, "kick_out": -2, "kick_sub": -2,
                "snare_top": -3, "hihat": -12, "ride": -12, "crash": -10, "tom": -8,
                "kick_beater": -16, "snare_bottom": -18, "fx": -19},
    "punchy":  {"overhead": -2, "room": -12, "kick_in": 0, "kick_out": 0, "kick_sub": 0,
                "snare_top": -1, "hihat": -9, "ride": -10, "crash": -9, "tom": -6,
                "kick_beater": -12, "snare_bottom": -14, "fx": -22},
    "natural": {"overhead": 0, "room": -8, "kick_in": -3, "kick_out": -3, "kick_sub": -3,
                "snare_top": -4, "hihat": -10, "ride": -11, "crash": -10, "tom": -7,
                "kick_beater": -15, "snare_bottom": -16, "fx": -20},
    # close-mic forward, room essentially out, overheads pulled in tight: a very
    # dry, punchy, "in the room with the kit" balance (vs punchy's -12 room).
    "dry":     {"overhead": -4, "room": -24, "kick_in": 0, "kick_out": 0, "kick_sub": 0,
                "snare_top": 0, "hihat": -8, "ride": -10, "crash": -9, "tom": -5,
                "kick_beater": -11, "snare_bottom": -13, "fx": -30},
}
_DEFAULT_OFFSET = -6.0
_CENTER = {Role.KICK_IN, Role.KICK_OUT, Role.KICK_SUB, Role.KICK_BEATER,
           Role.SNARE_TOP, Role.SNARE_BOTTOM}
_STEREO = {Role.OVERHEAD, Role.ROOM, Role.FX}


def _db(v: float) -> float:
    return 20.0 * np.log10(v) if v > 0 else float("-inf")


def _pan(mono: np.ndarray, theta: float) -> np.ndarray:
    """Equal-power pan; theta in [-1 (L), +1 (R)] -> (N, 2)."""
    a = (theta + 1.0) * np.pi / 4.0
    return np.column_stack([mono * np.cos(a), mono * np.sin(a)])


def _role_pan(role: Role, perspective: str, idx: int, n_same: int) -> float:
    """Base pan in AUDIENCE convention, mirrored for the drummer's perspective."""
    if role in _CENTER:
        base = 0.0
    elif role == Role.HIHAT:
        base = 0.5
    elif role == Role.RIDE:
        base = -0.4
    elif role == Role.CRASH:
        base = -0.45
    elif role == Role.TOM:
        base = 0.0 if n_same <= 1 else float(np.linspace(-0.35, 0.35, n_same)[idx])
    else:
        base = 0.0
    return base if perspective == "audience" else -base


def _balance_channels(x: np.ndarray) -> np.ndarray:
    """Even out a spaced stereo pair's L/R level asymmetry to equal RMS."""
    rms = np.sqrt(np.mean(x.astype(np.float64) ** 2, axis=0))
    tgt = float(rms.mean())
    # tgt/rms only where rms>0 (else gain 1.0); np.divide's `where` avoids the
    # divide-by-zero warning a plain np.where(rms>0, tgt/rms, 1.0) would still emit.
    g = np.divide(tgt, rms, out=np.ones_like(rms), where=rms > 0)
    return x * g


def mix_kit(kit: Kit, stems_dir: str, out_dir: str | None = None, feel: str = "roomy",
            perspective: str = "audience", plate: str | None = None,
            plate_offset: float = -19.0, flat: bool = False, ceil_dbfs: float = -1.0,
            out_name: str | None = None, t0: float = 44.0, dur: float = 12.0) -> dict:
    """Mix the kit stems in ``stems_dir`` (named per ``kit``) to one stereo bus."""
    import pyloudnorm as pyln

    if feel not in FEELS:
        raise ValueError(f"feel must be one of {list(FEELS)}")
    if perspective not in ("audience", "drummer"):
        raise ValueError("perspective must be 'audience' or 'drummer'")
    out_dir = out_dir or os.path.join(kit.src_dir, "mix")
    os.makedirs(out_dir, exist_ok=True)
    offsets = FEELS[feel]
    flip = perspective == "drummer"

    stems = [s for s in kit.stems if os.path.exists(os.path.join(stems_dir, s.name))]
    if not stems:
        raise ValueError(f"no kit stems found in {stems_dir!r}")

    # mix_kit balances against a STEREO overhead anchor and only treats the
    # pre-merged OVERHEAD role as stereo. A raw L/R overhead pair (overhead_l +
    # overhead_r, no merged OH) would otherwise (1) pick a kick/snare as the
    # anchor, mis-referencing every loudness offset, and (2) sum each OH side as
    # a dead-centre mono mic, collapsing the image. Refuse with guidance rather
    # than print a silently wrong mix — the merge is a documented prior step.
    has_oh = any(s.role == Role.OVERHEAD for s in stems)
    has_lr = (any(s.role == Role.OVERHEAD_L for s in stems)
              and any(s.role == Role.OVERHEAD_R for s in stems))
    if not has_oh and has_lr:
        raise ValueError(
            "found a raw L/R overhead pair (overhead_l + overhead_r) but no merged "
            "stereo overhead — mixing them as-is would collapse the overhead image "
            "and mis-anchor the balance. Merge first: `drum-prep overheads` (or run "
            "`drum-prep phase-align`, which merges the overheads into its output), "
            "then mix that stem set."
        )
    # When a merged OVERHEAD is present, any leftover raw overhead_l/overhead_r are
    # the SAME mics already captured by the merge. Summing all three would double-
    # (or triple-) count the overhead energy, and the raw sides would be treated as
    # mono mics and panned. Drop them in favour of the merged stereo OH, and report
    # what was excluded so the choice isn't silent.
    excluded_oh_sides: list[str] = []
    if has_oh and has_lr:
        excluded_oh_sides = [s.name for s in stems
                             if s.role in (Role.OVERHEAD_L, Role.OVERHEAD_R)]
        stems = [s for s in stems
                 if s.role not in (Role.OVERHEAD_L, Role.OVERHEAD_R)]

    sr, frames = io.summarize_inputs([os.path.join(stems_dir, s.name) for s in stems])
    meter = pyln.Meter(sr)

    anchor = next((s for s in stems if s.role == Role.OVERHEAD), None) or stems[0]
    ax, _ = io.read(os.path.join(stems_dir, anchor.name))
    # Measure the anchor the SAME way the per-stem loop measures each stem below
    # (to_stereo for a stereo role, else mono-sum). A blanket to_stereo() would
    # read a MONO fallback anchor ~3 dB hot (BS.1770 counts the duplicated
    # channel), skewing every loudness-matched gain vs the mono-measured stems.
    lufs_anchor = meter.integrated_loudness(
        io.to_stereo(ax) if anchor.role in _STEREO else dsp.mono(ax)
    )

    role_counts: dict[Role, int] = {}
    role_idx: dict[Role, int] = {}  # keyed by Role (like role_counts), not role.value
    for s in stems:
        role_counts[s.role] = role_counts.get(s.role, 0) + 1

    n = min(frames)
    # Stems are summed over their common length; flag if a longer stem is being
    # truncated so the trailing audio loss isn't silent.
    trunc_note = io.truncation_note(frames)
    mix = np.zeros((n, 2))
    rows: list[dict[str, Any]] = []
    for s in stems:
        x, _ = io.read(os.path.join(stems_dir, s.name))
        if flat:
            contrib = io.to_stereo(x)[:n]
            place = "stereo" if x.shape[1] == 2 else "center (unity)"
            gain_db = 0.0
        else:
            off = offsets.get(s.role.value, _DEFAULT_OFFSET)
            meas = io.to_stereo(x) if s.role in _STEREO else dsp.mono(x)
            lufs = meter.integrated_loudness(meas)
            gain = 10 ** ((lufs_anchor + off - lufs) / 20.0) if np.isfinite(lufs) else 1.0
            gain_db = _db(gain)
            if s.role in _STEREO:
                ch = io.to_stereo(x)
                # Channel-balance ONLY a genuine stereo room pair. The shape[1]==2
                # guard skips _balance_channels for a mono room mic (to_stereo has
                # already duplicated it to both channels, so it is balanced as-is).
                if s.role == Role.ROOM and x.shape[1] == 2:
                    ch = _balance_channels(ch)
                if flip:
                    ch = ch[:, ::-1]
                contrib = ch[:n] * gain
                place = f"stereo{' (L<->R flipped)' if flip else ''}"
            else:
                i = role_idx.get(s.role, 0)
                role_idx[s.role] = i + 1
                theta = float(np.clip(
                    _role_pan(s.role, perspective, i, role_counts[s.role]), -1.0, 1.0))
                contrib = _pan(x[:n, 0], theta) * gain
                place = "center" if theta == 0 else f"pan {round(theta * 100)}%"
        mix[:len(contrib)] += contrib[:n]
        rows.append({"stem": s.name, "role": s.role.value,
                     "offset_db": None if flat else offsets.get(s.role.value, _DEFAULT_OFFSET),
                     "gain_db": round(gain_db, 2), "place": place})

    plate_row: dict[str, Any] | None = None
    if plate and not flat:
        px, psr = io.read(plate)
        if psr != sr:
            raise ValueError(f"plate sr {psr} != kit sr {sr}")
        lufs_p = meter.integrated_loudness(io.to_stereo(px))
        gp = 10 ** ((lufs_anchor + plate_offset - lufs_p) / 20.0) if np.isfinite(lufs_p) else 1.0
        ch = io.to_stereo(px)
        if flip:
            ch = ch[:, ::-1]
        m = min(n, len(ch))
        mix[:m] += ch[:m] * gp
        plate_row = {"stem": os.path.basename(plate), "role": "fx (return)",
                     "offset_db": plate_offset, "gain_db": round(_db(gp), 2),
                     "place": f"stereo{' (flipped)' if flip else ''}"}
        rows.append(plate_row)

    raw_peak = float(np.max(np.abs(mix)))
    ceil_lin = 10 ** (ceil_dbfs / 20.0)
    trim = ceil_lin / raw_peak if raw_peak > ceil_lin else 1.0
    mix *= trim

    name = out_name or (f"drums-mix-{'flat' if flat else feel}-{perspective}.wav")
    out_path = os.path.join(out_dir, name)
    io.write_wav24(out_path, mix, sr)
    excerpt_path = None
    if dur and dur > 0:
        a, b = int(t0 * sr), int((t0 + dur) * sr)
        if b <= n:
            stem_name, ext = os.path.splitext(name)
            excerpt_path = os.path.join(out_dir, f"{stem_name}-excerpt{ext or '.wav'}")
            io.write_wav24(excerpt_path, mix[a:b], sr)

    final_peak = round(_db(float(np.max(np.abs(mix)))), 2)
    return {
        "flow": "mix", "stems_dir": stems_dir, "out": out_path, "excerpt": excerpt_path,
        "feel": None if flat else feel, "flat": flat, "perspective": perspective,
        "anchor": anchor.name, "anchor_lufs": round(float(lufs_anchor), 2),
        "global_trim_db": round(_db(trim), 2),
        "peak_dbfs": final_peak, "lufs": round(float(meter.integrated_loudness(mix)), 1),
        "channels": 2, "duration_s": round(n / sr, 2),
        "truncation_note": trunc_note,
        "excluded_overhead_sides": excluded_oh_sides or None,
        "plate": plate_row, "balance": rows,
    }
