"""sub-design: an envelope-followed sine sub adds low-end under a kick."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep.sub_design import add_sub, estimate_fundamental  # noqa: E402

SR = 48000


def _kick(n_hits=4, f0=70.0):
    """A few decaying f0 sine bursts — a usable synthetic kick."""
    sig = np.zeros(SR * 2)
    for h in range(n_hits):
        s = int(h * 0.5 * SR)
        tt = np.arange(SR // 2) / SR
        sig[s:s + len(tt)] += np.exp(-30 * tt) * np.sin(2 * np.pi * f0 * tt)
    return (0.6 * sig / (np.abs(sig).max() + 1e-9)).astype(np.float32)


def test_estimate_fundamental_near_70(tmp_path) -> None:
    assert abs(estimate_fundamental(_kick(f0=70.0).astype(np.float64), SR) - 70.0) < 6.0


def test_add_sub_increases_low_end(tmp_path) -> None:
    src = tmp_path / "kick.wav"
    sf.write(str(src), _kick(), SR, subtype="FLOAT")
    out = tmp_path / "kick_sub.wav"
    res = add_sub(str(src), str(out), amount_db=-3.0)
    assert res["low_60_gain_db"] > 0.5                       # measurably more sub
    assert 30.0 <= res["sub_hz"] <= 80.0
    y, _ = sf.read(str(out), always_2d=True)
    assert np.max(np.abs(y)) <= 10 ** (-1.0 / 20.0) + 1e-3   # anti-clipped
