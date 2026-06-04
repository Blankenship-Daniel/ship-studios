"""mix: role-driven balance + pan summed to a stereo bus; flat mode = unity bounce."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")
pytest.importorskip("pyloudnorm")

from drum_prep.kit import resolve_kit  # noqa: E402
from drum_prep.mix import _balance_channels, mix_kit  # noqa: E402
from drum_prep.roles import Role  # noqa: E402

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


def test_mono_anchor_measured_as_mono_not_stereo(tmp_path) -> None:
    # With no overhead, the anchor falls back to a MONO close mic. It must be
    # measured the same way (mono-sum) as the other mono stems — a blanket
    # to_stereo() would read it ~3 dB hot and skew every loudness-matched gain.
    # The anchor stem's own gain then equals its feel offset exactly
    # (lufs_anchor == its own lufs), so kick_in (stems[0]) lands at the -2 dB
    # roomy offset, not -2+3 = +1.
    from drum_prep.mix import FEELS

    rng = np.random.default_rng(0)
    n = SR * 8
    _w(tmp_path / "kick in.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "snare top.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    kit = resolve_kit(str(tmp_path), strict=False)
    res = mix_kit(kit, str(tmp_path), out_dir=str(tmp_path / "mix"), feel="roomy", dur=0)
    rows = {r["role"]: r for r in res["balance"]}
    assert rows["kick_in"]["gain_db"] == pytest.approx(FEELS["roomy"]["kick_in"], abs=0.05)


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


def test_plate_return_folded_in(tmp_path) -> None:
    # The optional plate/FX return is summed as a stereo return at its own offset,
    # and (drummer perspective) its image is flipped like the overheads.
    kit = _kit_dir(tmp_path)
    rng = np.random.default_rng(5)
    n = SR * 8
    _w(tmp_path / "plate.wav",
       np.column_stack([rng.standard_normal(n), rng.standard_normal(n)]).astype(np.float32) * 0.2)
    res = mix_kit(kit, str(tmp_path), out_dir=str(tmp_path / "mix"),
                  feel="roomy", perspective="drummer", plate=str(tmp_path / "plate.wav"), dur=0)
    assert res["plate"] is not None
    assert res["plate"]["role"] == "fx (return)"
    assert res["plate"]["offset_db"] == -19.0
    assert "flipped" in res["plate"]["place"]


def test_plate_samplerate_mismatch_raises(tmp_path) -> None:
    kit = _kit_dir(tmp_path)
    rng = np.random.default_rng(6)
    sf.write(str(tmp_path / "plate441.wav"),
             np.column_stack([rng.standard_normal(44100 * 2),
                              rng.standard_normal(44100 * 2)]).astype(np.float32),
             44100, subtype="FLOAT")
    with pytest.raises(ValueError, match="plate sr"):
        mix_kit(kit, str(tmp_path), out_dir=str(tmp_path / "mix"),
                plate=str(tmp_path / "plate441.wav"), dur=0)


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


def test_balance_channels_evens_a_real_stereo_pair() -> None:
    # _balance_channels equalizes the L/R RMS of a GENUINELY asymmetric stereo pair
    # (it's only meant for a 2-channel room) — the operation the mono-room guard
    # must keep AWAY from a single mono mic.
    rng = np.random.default_rng(2)
    x = np.column_stack([rng.standard_normal(SR), rng.standard_normal(SR) * 0.25])  # R quiet
    y = _balance_channels(x)
    rms = np.sqrt(np.mean(y ** 2, axis=0))
    assert abs(rms[0] - rms[1]) < 1e-9            # channels brought to equal RMS


def test_mono_room_passes_through_unchanged(tmp_path) -> None:
    # A MONO room mic must NOT be channel-balanced (to_stereo duplicates it to two
    # identical channels; _balance_channels is for a real spaced pair). The mono
    # room must reach the bus as a centred, identical-L/R contribution.
    rng = np.random.default_rng(8)
    n = SR * 4
    _w(tmp_path / "overhead.wav",
       np.column_stack([rng.standard_normal(n), rng.standard_normal(n)]).astype(np.float32) * 0.3)
    _w(tmp_path / "kick in.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "room.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))  # MONO room
    kit = resolve_kit(str(tmp_path), strict=False)
    assert any(s.role == Role.ROOM for s in kit.stems)            # detected as room
    res = mix_kit(kit, str(tmp_path), out_dir=str(tmp_path / "mix"), dur=0)
    room = next(r for r in res["balance"] if r["role"] == "room")
    assert room["place"].startswith("stereo")                    # placed as a stereo return
    y, _ = sf.read(res["out"], always_2d=True)
    assert y.shape[1] == 2 and np.max(np.abs(y)) <= CEIL + 1e-3   # mix is well-formed


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
