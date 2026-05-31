"""stereo-merge: L/R pairs found, merged to stereo, format preserved, review computed."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep import io, stereo_merge  # noqa: E402

SR = 48000


def _w(p, x, subtype="FLOAT") -> None:
    sf.write(str(p), x, SR, subtype=subtype)


def test_find_pairs_and_merge(tmp_path) -> None:
    rng = np.random.default_rng(0)
    base = (rng.standard_normal(SR * 3) * 0.3).astype(np.float32)
    right = np.roll(base, 5) + (rng.standard_normal(SR * 3) * 0.05).astype(np.float32)
    _w(tmp_path / "overhead - left.wav", base)
    _w(tmp_path / "overhead - right.wav", right.astype(np.float32))
    _w(tmp_path / "kick in.wav", base)  # mono, must not pair

    assert stereo_merge.find_pairs(str(tmp_path)) == [
        ("overhead", "overhead - left.wav", "overhead - right.wav")]

    res = stereo_merge.merge_dir(str(tmp_path))
    assert res["pairs"] == 1
    out = res["merged"][0]["out"]
    y, sr = sf.read(out, always_2d=True)
    assert y.shape[1] == 2 and sr == SR
    assert res["merged"][0]["verified"] is True
    assert io.subtype_of(out) == "FLOAT"  # source format preserved
    assert {"corr_lag0", "best_lag_ms", "polarity", "mono_sum_loss_db",
            "likely_reverb_return"} <= set(res["merged"][0]["review"])


def test_reverb_pair_flagged(tmp_path) -> None:
    rng = np.random.default_rng(1)
    L = (rng.standard_normal(SR * 3) * 0.3).astype(np.float32)
    R = (-np.roll(L, 600) + (rng.standard_normal(SR * 3) * 0.05).astype(np.float32)).astype(np.float32)
    _w(tmp_path / "snare plate - left.wav", L)
    _w(tmp_path / "snare plate - right.wav", R)
    rev = stereo_merge.merge_dir(str(tmp_path))["merged"][0]["review"]
    assert rev["polarity"] == "inverted"
    assert rev["likely_reverb_return"] is True
