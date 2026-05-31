"""mix: role-driven balance + pan summed to a stereo bus; flat mode = unity bounce."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")
pytest.importorskip("pyloudnorm")

from drum_prep.kit import resolve_kit  # noqa: E402
from drum_prep.mix import mix_kit  # noqa: E402

SR = 48000
CEIL = 10 ** (-1.0 / 20.0)


def _w(p, x, subtype="FLOAT") -> None:
    sf.write(str(p), x, SR, subtype=subtype)


def _kit_dir(tmp_path, n=SR * 8):
    rng = np.random.default_rng(0)
    _w(tmp_path / "overhead.wav",
       np.column_stack([rng.standard_normal(n), rng.standard_normal(n)]).astype(np.float32) * 0.3)
    _w(tmp_path / "kick in.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "snare top.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "hi hat.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    return resolve_kit(str(tmp_path), strict=False)


def test_mix_produces_stereo_bus(tmp_path) -> None:
    kit = _kit_dir(tmp_path)
    res = mix_kit(kit, str(tmp_path), out_dir=str(tmp_path / "mix"),
                  feel="roomy", perspective="drummer", dur=0)
    y, sr = sf.read(res["out"], always_2d=True)
    assert y.shape[1] == 2 and sr == SR
    assert np.max(np.abs(y)) <= CEIL + 1e-3
    assert res["peak_dbfs"] <= -1.0 + 0.05
    roles = {r["role"] for r in res["balance"]}
    assert {"overhead", "kick_in", "snare_top", "hihat"} <= roles
    # drummer perspective flips the overhead image
    assert any("flipped" in r["place"] for r in res["balance"] if r["role"] == "overhead")
    # hi-hat is panned (not centred)
    assert any(r["role"] == "hihat" and "pan" in r["place"] for r in res["balance"])


def test_flat_mode_unity_bounce(tmp_path) -> None:
    kit = _kit_dir(tmp_path)
    res = mix_kit(kit, str(tmp_path), out_dir=str(tmp_path / "mix"), flat=True, dur=0)
    assert res["flat"] is True and res["feel"] is None
    y, _ = sf.read(res["out"], always_2d=True)
    assert y.shape[1] == 2 and np.max(np.abs(y)) <= CEIL + 1e-3
