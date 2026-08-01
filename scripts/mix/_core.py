"""Pure-numpy/scipy DSP cores shared by the scripts/mix recipes — NO pedalboard, NO stemmy.

These are the load-bearing, deterministic numerics extracted out of the CLI scripts
(process_stems.py / balance_stems.py / warm_bus.py) so they become importable + unit-testable
WITHOUT loading pedalboard (the Studer/API color stages) or the stemmy tool surface. The scripts
call these for the exact same math they used inline, so the CLI stays byte-identical; the
pedalboard/stemmy stages live only in each script's CLI path.

Everything here depends only on numpy (+ scipy for the zero-phase tilt, + pyloudnorm for the LUFS
balance), all present in the plain `mixing` venv — so a test can import this module by path and
exercise the proven behavior on synthetic stems.
"""
import math
import os
from pathlib import Path

import numpy as np


def repo_root():
    """The ship-studios checkout this script lives in, derived from ``__file__``.

    Replaces the hardcoded ``/Users/ship/Documents/code/ship-studios`` that was
    copy-pasted across the scripts/mix recipes — those broke on any other checkout
    (and in CI) with a bare FileNotFoundError at subprocess spawn.
    """
    return Path(__file__).resolve().parent.parent.parent


def sibling_dir(name):
    """Locate a sibling MCP repo (``stemmy-loops-mcp`` / ``stemmy-gemini-mcp``).

    Prefers ship_studios.config, which already resolves siblings from the MAIN
    checkout even when running inside a .claude/worktrees/ worktree — the exact
    case a bare ``repo_root().parent / name`` gets wrong. Falls back to that
    simple guess when ship_studios isn't importable (these scripts often run under
    the stemmy-loops `vst` venv, which need not have this package installed).
    Honors the documented SHIP_STUDIOS_*_DIR overrides via config.
    """
    try:
        from ship_studios import config
        key = {"stemmy-loops-mcp": config.LOOPS_SERVER,
               "stemmy-gemini-mcp": config.GEMINI_SERVER}.get(name)
        if key is not None:
            return Path(config.server_dir(key))
    except Exception:
        pass
    env = {"stemmy-loops-mcp": "SHIP_STUDIOS_LOOPS_DIR",
           "stemmy-gemini-mcp": "SHIP_STUDIOS_GEMINI_DIR"}.get(name)
    if env and os.environ.get(env):
        return Path(os.environ[env])
    return repo_root().parent / name


def sibling_python(name="stemmy-loops-mcp"):
    """The sibling repo's venv interpreter (for the VST/stemmy subprocess stages)."""
    return sibling_dir(name) / ".venv" / "bin" / "python"


def peak_normalize(y, peak_dbfs=-1.0):
    """Scale `y` so its absolute peak sits at `peak_dbfs` dBFS (the process_stems invariant).

    Identical math to process_stems.color()'s post-render normalize: a silent buffer (peak 0)
    is returned unchanged. `y` is any-shape float array; returns a new array (input untouched).
    """
    y = np.asarray(y, dtype=np.float32)
    pk = float(np.max(np.abs(y))) if y.size else 0.0
    if pk > 0:
        return y * ((10 ** (peak_dbfs / 20.0)) / pk)
    return y


def lufs_gain(meas_lufs, target_lufs):
    """Linear gain to move a stem from its measured integrated LUFS to a target (balance_stems).

    A louder source (higher `meas_lufs`) yields a SMALLER gain — i.e. more attenuation — which is
    the whole point of balancing by measured loudness rather than peak/RMS.
    """
    return 10 ** ((target_lufs - meas_lufs) / 20.0)


def pan_to_stereo(a, pan):
    """Equal-power pan a mono buffer into stereo, or pass a stereo buffer through (balance_stems).

    Mono -> (n,2) equal-power (cos/sin) pan; (n,1) -> duplicated; (n,2) -> unchanged. Matches the
    inline math in balance_stems exactly (th = (pan+1)*0.25*pi).
    """
    if a.ndim == 1:
        th = (pan + 1) * 0.25 * math.pi
        return np.stack([a * math.cos(th), a * math.sin(th)], 1)
    return a if a.shape[1] == 2 else np.repeat(a, 2, 1)


def balance_to_bus(meter, stems, headroom_db=-6.0):
    """Sum measured-LUFS-balanced, panned stems into one stereo bus (the balance_stems core).

    `stems` = list of (a, target_lufs, pan) where `a` is a loaded float array (mono 1-D or (n,ch)).
    Returns (bus, rows): `bus` is the (n,2) summed bus peak-trimmed to `headroom_db`; `rows` is a list
    of dicts {meas, target, gain_db, pan, skipped} so the caller can print the balance table. Robustness
    (FIX 2): a non-finite integrated LUFS (a sub-gate-length / near-silent stem reads -inf -> infinite
    gain -> NaN-poisoned bus) is SKIPPED with skipped=True rather than summed in. Identical numerics to
    balance_stems for every finite stem (gain, equal-power pan, headroom trim).
    """
    arrs = [np.asarray(a) for a, _, _ in stems]
    if not arrs:
        raise ValueError("balance_to_bus needs at least one stem")
    n = min(len(a) for a in arrs)
    bus = np.zeros((n, 2), np.float32)
    rows = []
    for (a, target_lufs, pan), a_full in zip(stems, arrs, strict=True):
        a = a_full[:n]
        meas = meter.integrated_loudness(a)
        if not np.isfinite(meas):                       # FIX 2: drop the stem, don't NaN the bus
            rows.append(dict(meas=meas, target=target_lufs, gain_db=float("nan"),
                             pan=float(pan), skipped=True))
            continue
        gain = lufs_gain(meas, target_lufs)
        st = pan_to_stereo(a, float(pan))
        bus[: len(st)] += st * gain
        rows.append(dict(meas=meas, target=target_lufs,
                         gain_db=20 * math.log10(max(gain, 1e-9)), pan=float(pan), skipped=False))
    peak = float(np.max(np.abs(bus)))
    if peak > 0:
        bus *= (10 ** (headroom_db / 20.0)) / peak
    return bus, rows


def warm_tilt_eq(x, sr, low_shelf_gain_db=1.5, bell_gain_db=-1.5, hs_gain_db=-4.0,
                 hs_freq_hz=6000.0, low_shelf_freq_hz=180.0, bell_freq_hz=2500.0):
    """Pure-numpy zero-phase warm tilt EQ matching the warm_bus recipe SIGN convention.

    The warm-bus tone is a TILT: low-shelf BOOST (default +1.5 dB @180), presence-bell CUT
    (default -1.5 dB @2.5k), high-shelf CUT (default -4 dB @6k) — i.e. lows up / highs down = warm.
    Implemented as a real, symmetric (zero-phase) magnitude curve applied via rFFT, so it adds NO
    phase shift — the property the warm chain depends on (the alignment must survive the tone match).

    NOTE: this is the testable, dependency-free MIRROR of the recipe. warm_bus's CLI still renders the
    tilt through stemmy's apply_eq(phase='zero') so its output stays byte-identical; this core exists so
    the proven sign/zero-phase behavior is assertable without pedalboard/stemmy. Returns same-shape array.
    """
    x = np.asarray(x, dtype=np.float64)
    axis = -1
    n = x.shape[axis]
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    # real, symmetric magnitude response -> zero-phase. Smooth shelves/bell as gaussian-ish bumps.
    def _shelf(f0, gain_db, low):
        g = 10 ** (gain_db / 20.0)
        # sigmoid transition centered at f0 (1 octave width); low-shelf boosts below f0, high-shelf above.
        t = 1.0 / (1.0 + (freqs / max(f0, 1e-6)) ** 2)        # ~1 below f0, ~0 above
        if not low:
            t = 1.0 - t                                       # high-shelf acts above f0
        return 1.0 + (g - 1.0) * t

    def _bell(f0, gain_db, q=0.9):
        g = 10 ** (gain_db / 20.0)
        bw = f0 / max(q, 1e-6)
        shape = np.exp(-0.5 * ((freqs - f0) / (bw / 2.0)) ** 2)
        return 1.0 + (g - 1.0) * shape

    H = (_shelf(low_shelf_freq_hz, low_shelf_gain_db, low=True)
         * _bell(bell_freq_hz, bell_gain_db)
         * _shelf(hs_freq_hz, hs_gain_db, low=False))
    H = H.astype(np.float64)                                   # real -> zero-phase by construction
    if x.ndim == 1:
        return np.fft.irfft(np.fft.rfft(x) * H, n=n).astype(np.float32)
    out = np.empty_like(x, dtype=np.float32)
    for ch in range(x.shape[0]):
        out[ch] = np.fft.irfft(np.fft.rfft(x[ch]) * H, n=n).astype(np.float32)
    return out
