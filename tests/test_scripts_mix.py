"""Tests for the pure-DSP cores extracted from scripts/mix (UNIT G).

scripts/ is excluded from ruff/mypy and is NOT an importable package, so we load each module by
PATH via importlib (registering it in sys.modules so its own ``from _core import ...`` resolves).
These assert the load-bearing, behavior-preserving numerics of the recipes WITHOUT needing pedalboard
or the stemmy tool surface (the scripts defer those imports into their CLI paths):

  * process_stems  — every processed stem is peak-normalized to its target dBFS (the documented
    'process_stems always colors+normalizes' invariant).
  * balance_stems  — gains come from MEASURED INTEGRATED LUFS (louder-LUFS -> larger attenuation),
    and a non-finite LUFS stem is skipped instead of NaN-poisoning the bus (FIX 2).
  * warm_bus       — the tilt-EQ core applies the warm sign (low boost / high cut) and is a real,
    symmetric (zero-phase) operation.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

_MIX_DIR = Path(__file__).resolve().parents[1] / "scripts" / "mix"


def _load(name: str):
    """Import a scripts/mix module by path, registering it so its own ``from _core import`` works."""
    if name in sys.modules:
        return sys.modules[name]
    # ensure scripts/mix is importable for the module's own ``from _core import ...``
    sys.path.insert(0, str(_MIX_DIR))
    spec = importlib.util.spec_from_file_location(name, _MIX_DIR / f"{name}.py")
    assert spec and spec.loader, f"cannot load {name}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def core():
    return _load("_core")


def _band_energy(sig: np.ndarray, sr: int, lo: float, hi: float) -> float:
    X = np.fft.rfft(sig)
    f = np.fft.rfftfreq(len(sig), 1.0 / sr)
    m = (f >= lo) & (f < hi)
    return float(np.sum(np.abs(X[m]) ** 2))


# --- process_stems: the always-normalize invariant -----------------------------------------------

def test_peak_normalize_hits_target_dbfs(core):
    """A processed buffer is scaled so its absolute peak sits exactly at the target dBFS."""
    rng = np.random.default_rng(0)
    y = (rng.standard_normal((2, 48000)) * 0.07).astype(np.float32)   # quiet, off the ceiling
    out = core.peak_normalize(y, peak_dbfs=-1.0)
    pk = float(np.max(np.abs(out)))
    assert pk == pytest.approx(10 ** (-1.0 / 20.0), rel=1e-5)         # -1 dBFS
    # different target -> different ceiling (the knob is honored)
    out6 = core.peak_normalize(y, peak_dbfs=-6.0)
    assert float(np.max(np.abs(out6))) == pytest.approx(10 ** (-6.0 / 20.0), rel=1e-5)


def test_peak_normalize_silence_is_safe(core):
    """A silent (peak 0) buffer is passed through unchanged — no divide-by-zero / NaN."""
    z = np.zeros((2, 1000), np.float32)
    out = core.peak_normalize(z, peak_dbfs=-1.0)
    assert np.array_equal(out, z) and np.all(np.isfinite(out))


def test_process_stems_module_uses_the_core(core):
    """The script wires the shared core in (the invariant lives in one place)."""
    ps = _load("process_stems")
    assert ps.peak_normalize is core.peak_normalize


# --- balance_stems: gains derived from measured INTEGRATED LUFS -----------------------------------

def test_balance_gain_is_lufs_derived_not_peak_or_rms(core):
    """A louder-LUFS stem gets a LARGER attenuation than a quieter one at the same target.

    Proves the gain tracks measured integrated loudness: same target LUFS, the hotter source is
    pulled down harder. (A peak/RMS rule would not give this clean LUFS-difference relationship.)
    """
    import pyloudnorm as pyln
    sr = 48000
    n = sr * 2
    rng = np.random.default_rng(1)
    loud = (rng.standard_normal(n) * 0.5).astype(np.float32)
    quiet = (rng.standard_normal(n) * 0.05).astype(np.float32)   # ~20 dB quieter
    meter = pyln.Meter(sr)

    _bus, rows = core.balance_to_bus(
        meter, [(loud, -20.0, 0.0), (quiet, -20.0, 0.0)], headroom_db=-6.0
    )
    loud_row, quiet_row = rows
    assert not loud_row["skipped"] and not quiet_row["skipped"]
    # louder measured LUFS -> more negative gain (more attenuation) to reach the same target
    assert loud_row["meas"] > quiet_row["meas"]
    assert loud_row["gain_db"] < quiet_row["gain_db"]
    # and the gain is exactly the LUFS delta (the formula, not an approximation)
    expected = -20.0 - loud_row["meas"]
    assert loud_row["gain_db"] == pytest.approx(expected, abs=1e-4)


def test_lufs_gain_formula(core):
    """lufs_gain is the dB-difference exponential; +/- direction is correct."""
    assert core.lufs_gain(-10.0, -20.0) == pytest.approx(10 ** (-10.0 / 20.0))  # pull a hot stem down
    assert core.lufs_gain(-30.0, -20.0) == pytest.approx(10 ** (10.0 / 20.0))   # bring a quiet stem up
    assert core.lufs_gain(-14.0, -14.0) == pytest.approx(1.0)                    # match -> unity


def test_balance_skips_nonfinite_lufs_stem_no_nan(core):
    """FIX 2: a near-silent / sub-gate-length stem (-inf LUFS) is dropped, never NaN-poisons the bus."""
    import pyloudnorm as pyln
    sr = 48000
    n = sr * 2
    rng = np.random.default_rng(2)
    good = (rng.standard_normal(n) * 0.3).astype(np.float32)
    silent = np.zeros(n, np.float32)                      # integrated LUFS -> -inf
    meter = pyln.Meter(sr)

    bus, rows = core.balance_to_bus(
        meter, [(good, -20.0, 0.0), (silent, -20.0, 0.0)], headroom_db=-6.0
    )
    assert not np.isfinite(rows[1]["meas"])              # the silent stem really read non-finite
    assert rows[1]["skipped"] is True
    assert rows[0]["skipped"] is False
    assert np.all(np.isfinite(bus))                     # the guard kept the bus clean
    assert float(np.max(np.abs(bus))) > 0.0            # the good stem still summed in


def test_balance_to_bus_byte_identical_to_inline(core):
    """Behavior-preserving: the core reproduces the original inline balance math exactly."""
    import pyloudnorm as pyln
    sr = 48000
    n = sr * 2
    rng = np.random.default_rng(3)
    a = (rng.standard_normal(n) * 0.4).astype(np.float32)
    b = (rng.standard_normal(n) * 0.1).astype(np.float32)
    st = (rng.standard_normal((n, 2)) * 0.2).astype(np.float32)
    spec = [(a, -20.0, -0.3), (b, -18.0, 0.0), (st, -16.0, 0.2)]
    meter = pyln.Meter(sr)

    # original inline algorithm, transcribed from the pre-refactor balance_stems.main()
    N = min(len(x) for x, _, _ in spec)
    ref = np.zeros((N, 2), np.float32)
    for x, tl, pan in spec:
        x = x[:N]
        meas = meter.integrated_loudness(x)
        gain = 10 ** ((tl - meas) / 20.0)
        if x.ndim == 1:
            th = (pan + 1) * 0.25 * math.pi
            s = np.stack([x * math.cos(th), x * math.sin(th)], 1)
        else:
            s = x if x.shape[1] == 2 else np.repeat(x, 2, 1)
        ref[: len(s)] += s * gain
    peak = float(np.max(np.abs(ref)))
    if peak > 0:
        ref *= (10 ** (-6.0 / 20.0)) / peak

    bus, _rows = core.balance_to_bus(meter, spec, headroom_db=-6.0)
    assert np.array_equal(bus, ref)


def test_pan_to_stereo_equal_power(core):
    """Mono center pan is equal-power (3 dB down per side); stereo passes through."""
    mono = np.ones(100, np.float32)
    st = core.pan_to_stereo(mono, 0.0)
    assert st.shape == (100, 2)
    assert st[0, 0] == pytest.approx(math.cos(math.pi / 4), rel=1e-5)
    assert st[0, 1] == pytest.approx(math.sin(math.pi / 4), rel=1e-5)
    # hard left
    left = core.pan_to_stereo(mono, -1.0)
    assert left[0, 1] == pytest.approx(0.0, abs=1e-6)
    # already-stereo is untouched
    stereo = np.ones((100, 2), np.float32)
    assert core.pan_to_stereo(stereo, 0.5) is stereo


# --- warm_bus: warm tilt sign + zero-phase -------------------------------------------------------

def test_warm_tilt_sign_low_up_high_down(core):
    """The warm tilt boosts lows and cuts highs (the recipe: low-shelf + / high-shelf -)."""
    sr = 48000
    n = sr
    x = np.random.default_rng(4).standard_normal(n).astype(np.float32)
    y = core.warm_tilt_eq(x, sr)   # defaults: low +1.5, bell -1.5@2.5k, high -4@6k
    low = _band_energy(y, sr, 40, 200) / _band_energy(x, sr, 40, 200)
    high = _band_energy(y, sr, 8000, 16000) / _band_energy(x, sr, 8000, 16000)
    assert low > 1.0   # lows lifted
    assert high < 1.0  # highs pulled down -> warm
    assert y.shape == x.shape and y.dtype == np.float32


def test_warm_tilt_is_zero_phase(core):
    """Real, symmetric magnitude => zero-phase: the impulse response is circularly symmetric."""
    sr = 48000
    n = 4096
    imp = np.zeros(n, np.float32)
    imp[0] = 1.0
    h = core.warm_tilt_eq(imp, sr)
    # h[k] == h[-k] (circular) for a zero-phase filter
    sym_err = float(np.max(np.abs(h[1:] - h[:0:-1])))
    assert sym_err < 1e-6


def test_warm_tilt_flat_settings_is_near_identity(core):
    """All-zero gains -> the curve is unity -> output ~= input (a sanity floor on the core)."""
    sr = 48000
    x = np.random.default_rng(5).standard_normal(sr).astype(np.float32)
    y = core.warm_tilt_eq(x, sr, low_shelf_gain_db=0.0, bell_gain_db=0.0, hs_gain_db=0.0)
    assert np.max(np.abs(y - x)) < 1e-4


def test_warm_bus_module_uses_the_core(core):
    """warm_bus exposes the shared peak_normalize + the testable tilt mirror."""
    wb = _load("warm_bus")
    assert wb.peak_normalize is core.peak_normalize
    assert wb.warm_tilt_eq is core.warm_tilt_eq
