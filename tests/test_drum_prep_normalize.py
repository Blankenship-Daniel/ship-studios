"""normalize: global gain preserves inter-mic balance; per-file maximizes each stem."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep import io  # noqa: E402
from drum_prep.normalize import normalize_kit  # noqa: E402

SR = 48000


def _w(p, x, subtype="FLOAT") -> None:
    sf.write(str(p), x, SR, subtype=subtype)


def _peak_db(path) -> float:
    y, _ = sf.read(str(path), always_2d=True)
    return 20 * np.log10(np.max(np.abs(y)))


def test_global_preserves_balance(tmp_path) -> None:
    rng = np.random.default_rng(0)
    a = (rng.standard_normal(SR) * 0.6).astype(np.float32)
    _w(tmp_path / "kick in.wav", a)
    _w(tmp_path / "snare top.wav", (a * 0.5).astype(np.float32))
    _w(tmp_path / "overhead.wav", np.column_stack([a * 0.3, a * 0.2]).astype(np.float32))

    res = normalize_kit(str(tmp_path), target_dbfs=-1.0, mode="global")
    assert res["balance_preserved"] is True
    assert res["gain_spread_db"] < 0.01
    peaks = [_peak_db(tmp_path / "normalized" / f["file"]) for f in res["files"]]
    assert abs(max(peaks) - (-1.0)) < 0.05               # loudest hits target
    assert io.subtype_of(str(tmp_path / "normalized" / "kick in.wav")) == "FLOAT"


def test_per_file_each_hits_target(tmp_path) -> None:
    rng = np.random.default_rng(1)
    a = (rng.standard_normal(SR) * 0.6).astype(np.float32)
    _w(tmp_path / "kick in.wav", a)
    _w(tmp_path / "snare top.wav", (a * 0.3).astype(np.float32))
    res = normalize_kit(str(tmp_path), target_dbfs=-1.0, mode="per_file")
    for f in res["files"]:
        assert abs(f["out_peak_dbfs"] - (-1.0)) < 0.05
