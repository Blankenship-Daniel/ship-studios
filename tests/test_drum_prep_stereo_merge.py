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


def test_ambiguous_side_raises(tmp_path) -> None:
    # Two files collapsing to the same (stem, side) must error, not silently drop one.
    rng = np.random.default_rng(2)
    x = (rng.standard_normal(SR) * 0.3).astype(np.float32)
    _w(tmp_path / "oh - l.wav", x)
    _w(tmp_path / "oh - left.wav", x)   # same stem 'oh', same side L
    _w(tmp_path / "oh - right.wav", x)
    with pytest.raises(ValueError, match="ambiguous"):
        stereo_merge.find_pairs(str(tmp_path))


def test_stereo_side_rejected_not_silently_mono_summed(tmp_path) -> None:
    # A genuinely STEREO side must be rejected, not averaged down to mono — which
    # would silently destroy its L/R data and write two identical mono channels.
    rng = np.random.default_rng(3)
    stereo = (rng.standard_normal((SR, 2)) * 0.3).astype(np.float32)  # a 2-channel "side"
    mono = (rng.standard_normal(SR) * 0.3).astype(np.float32)
    _w(tmp_path / "oh - left.wav", stereo)
    _w(tmp_path / "oh - right.wav", mono)
    with pytest.raises(ValueError, match="single channel"):
        stereo_merge.merge_dir(str(tmp_path))


def test_subtype_mismatch_reported(tmp_path) -> None:
    # The merged file carries ONE subtype (the left's); a differing right subtype
    # is coerced, which must be reported, not lossy-by-stealth.
    rng = np.random.default_rng(0)
    base = (rng.standard_normal(SR) * 0.3).astype(np.float32)
    _w(tmp_path / "oh - left.wav", base, subtype="PCM_24")   # left drives the subtype
    _w(tmp_path / "oh - right.wav", base, subtype="FLOAT")
    m = stereo_merge.merge_dir(str(tmp_path))["merged"][0]
    assert m["subtype_mismatch"] is True
    assert m["right_subtype"] == "FLOAT"
    assert io.subtype_of(m["out"]) == "PCM_24"              # output follows the left


def test_lone_single_char_side_not_paired(tmp_path) -> None:
    # A lone 'tom r.wav' (no single-char partner 'tom l.wav') is more likely
    # "right-of-kit tom" than half a stereo pair — it must NOT be mis-read as a side.
    rng = np.random.default_rng(4)
    x = (rng.standard_normal(SR) * 0.3).astype(np.float32)
    _w(tmp_path / "tom r.wav", x)
    _w(tmp_path / "kick in.wav", x)
    assert stereo_merge.find_pairs(str(tmp_path)) == []


def test_single_char_pair_honoured(tmp_path) -> None:
    # But a genuine single-char 'room l'/'room r' pair (both halves present) still
    # merges — the single-char token counts when its single-char partner exists.
    rng = np.random.default_rng(5)
    x = (rng.standard_normal(SR) * 0.3).astype(np.float32)
    _w(tmp_path / "room l.wav", x)
    _w(tmp_path / "room r.wav", x)
    assert stereo_merge.find_pairs(str(tmp_path)) == [
        ("room", "room l.wav", "room r.wav")]


def test_align_phase_locks_right_to_left(tmp_path) -> None:
    # align=True opts into phase-locking R to L (collapsing a spaced image); after
    # it, the two output channels are time-aligned (near-zero inter-channel lag).
    pytest.importorskip("scipy")
    from drum_prep import dsp

    base = np.random.default_rng(0).standard_normal(SR * 3) * 0.3
    _w(tmp_path / "oh - left.wav", base.astype(np.float32))
    _w(tmp_path / "oh - right.wav", dsp.fractional_delay(base, 30).astype(np.float32))  # R lags L
    m = stereo_merge.merge_dir(str(tmp_path), align=True)["merged"][0]
    assert m["aligned"] is True
    y, _ = sf.read(m["out"], always_2d=True)
    d, _ = dsp.estimate(y[:, 1], y[:, 0], 100)             # R-vs-L lag after align
    assert abs(d) < 2


def test_reverb_pair_flagged(tmp_path) -> None:
    rng = np.random.default_rng(1)
    L = (rng.standard_normal(SR * 3) * 0.3).astype(np.float32)
    R = (-np.roll(L, 600) + (rng.standard_normal(SR * 3) * 0.05).astype(np.float32)).astype(np.float32)
    _w(tmp_path / "snare plate - left.wav", L)
    _w(tmp_path / "snare plate - right.wav", R)
    rev = stereo_merge.merge_dir(str(tmp_path))["merged"][0]["review"]
    assert rev["polarity"] == "inverted"
    assert rev["likely_reverb_return"] is True
