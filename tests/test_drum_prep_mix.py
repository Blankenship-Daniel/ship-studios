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
    # "unity bounce" means NO per-stem loudness offset or panning was applied —
    # assert the defining behaviour, not just shape/ceiling.
    for row in res["balance"]:
        assert row["gain_db"] == 0.0, row
        assert row["offset_db"] is None, row
    places = {r["role"]: r["place"] for r in res["balance"]}
    assert places["overhead"] == "stereo"          # stereo mic kept stereo, not flipped/panned
    assert places["kick_in"] == "center (unity)"    # mono mic centred, not panned


def test_lr_pair_overhead_refused_with_guidance(tmp_path) -> None:
    # A raw L/R overhead pair (no merged stereo overhead) must be refused with a
    # clear message rather than silently mono-collapsed / mis-anchored.
    rng = np.random.default_rng(1)
    n = SR * 4
    _w(tmp_path / "overhead L.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "overhead R.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "kick in.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    kit = resolve_kit(str(tmp_path), strict=False)
    with pytest.raises(ValueError, match="overhead"):
        mix_kit(kit, str(tmp_path), out_dir=str(tmp_path / "mix"), dur=0)


def test_merged_overhead_drops_redundant_raw_sides(tmp_path) -> None:
    # A merged stereo overhead PLUS leftover raw L/R sides must NOT triple-count
    # the overheads: the raw sides are dropped in favour of the merge, and the
    # exclusion is reported (not silent).
    rng = np.random.default_rng(3)
    n = SR * 4
    _w(tmp_path / "overhead.wav",
       np.column_stack([rng.standard_normal(n), rng.standard_normal(n)]).astype(np.float32) * 0.3)
    _w(tmp_path / "overhead L.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "overhead R.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "kick in.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    kit = resolve_kit(str(tmp_path), strict=False)
    res = mix_kit(kit, str(tmp_path), out_dir=str(tmp_path / "mix"), dur=0)
    assert set(res["excluded_overhead_sides"]) == {"overhead L.wav", "overhead R.wav"}
    roles = {r["role"] for r in res["balance"]}
    assert "overhead" in roles
    assert "overhead_l" not in roles and "overhead_r" not in roles
