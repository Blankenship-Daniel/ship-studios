"""stem-mix: arbitrary named stems balanced to a target LUFS, summed to stereo."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")
pytest.importorskip("pyloudnorm")

from drum_prep.stem_mix import _balance, mix_stems  # noqa: E402

SR = 48000
CEIL = 10 ** (-1.0 / 20.0)


def _w(p, x) -> None:
    sf.write(str(p), x, SR, subtype="FLOAT")


def test_balances_and_sums_to_stereo(tmp_path) -> None:
    rng = np.random.default_rng(0)
    n = SR * 8
    _w(tmp_path / "bass.wav", (rng.standard_normal(n) * 0.6).astype(np.float32))       # loud mono
    _w(tmp_path / "keys.wav", (rng.standard_normal(n) * 0.05).astype(np.float32))      # quiet mono
    _w(tmp_path / "gtr.wav",
       np.column_stack([rng.standard_normal(n), rng.standard_normal(n)]).astype(np.float32) * 0.2)
    res = mix_stems(str(tmp_path), out_dir=str(tmp_path / "mix"), target_lufs=-18.0, dur=0)
    y, sr = sf.read(res["out"], always_2d=True)
    assert y.shape[1] == 2 and sr == SR
    assert np.max(np.abs(y)) <= CEIL + 1e-3
    # the quiet stem must get a large positive makeup; the loud one a cut
    g = {r["stem"]: r["gain_db"] for r in res["stems"]}
    assert g["keys.wav"] > g["bass.wav"]


def test_mixed_samplerate_raises(tmp_path) -> None:
    """A stem at a different SR must error clearly, not sum time-misaligned."""
    rng = np.random.default_rng(2)
    sf.write(str(tmp_path / "a.wav"),
             (rng.standard_normal(SR * 2) * 0.3).astype(np.float32), SR, subtype="FLOAT")
    sf.write(str(tmp_path / "b.wav"),
             (rng.standard_normal(44100 * 2) * 0.3).astype(np.float32), 44100, subtype="FLOAT")
    with pytest.raises(ValueError, match="sample-rate mismatch"):
        mix_stems(str(tmp_path), out_dir=str(tmp_path / "mix"), dur=0)


def test_spec_overrides(tmp_path) -> None:
    rng = np.random.default_rng(1)
    n = SR * 8
    _w(tmp_path / "bass.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    _w(tmp_path / "vox.wav", (rng.standard_normal(n) * 0.3).astype(np.float32))
    res = mix_stems(str(tmp_path), out_dir=str(tmp_path / "mix"),
                    spec={"vox.wav": {"mute": True}, "bass.wav": {"gain_db": -6, "pan": -0.5}}, dur=0)
    rows = {r["stem"]: r for r in res["stems"]}
    assert rows["vox.wav"].get("muted") is True
    assert "pan" in rows["bass.wav"]["place"] and rows["bass.wav"]["offset_db"] == -6
    assert res["ignored_spec_keys"] is None       # every spec key matched a stem


def test_unmatched_spec_key_surfaced(tmp_path) -> None:
    # A spec key that matches no stem (typo / renamed file) is silently dropped by
    # the mix; surface it so an unapplied override isn't mistaken for applied.
    rng = np.random.default_rng(4)
    _w(tmp_path / "bass.wav", (rng.standard_normal(SR * 4) * 0.3).astype(np.float32))
    res = mix_stems(str(tmp_path), out_dir=str(tmp_path / "mix"),
                    spec={"typo.wav": {"gain_db": -6}}, dur=0)
    assert res["ignored_spec_keys"] == ["typo.wav"]


def test_pan_clamped_no_polarity_flip(tmp_path) -> None:
    # pan > 1 from user JSON must be clamped to 1: unclamped, the equal-power
    # balance computes a NEGATIVE left-channel gain (cos past 90 deg), inverting
    # polarity. After the clamp the left channel is fully attenuated to ~silence
    # (left gain ~0 at hard-right), never a phase-flipped copy of the input.
    rng = np.random.default_rng(7)
    n = SR * 4
    sig = (rng.standard_normal(n) * 0.4).astype(np.float32)
    # a single, isolated stereo stem so the bus IS this stem (scaled): no other
    # source to mask a polarity inversion.
    _w(tmp_path / "wide.wav", np.column_stack([sig, sig]).astype(np.float32))
    res = mix_stems(str(tmp_path), out_dir=str(tmp_path / "mix"),
                    spec={"wide.wav": {"pan": 1.5}}, dur=0)
    y, _ = sf.read(res["out"], always_2d=True)
    # hard-right clamp: left channel attenuated to ~silence, NOT an inverted copy.
    assert np.max(np.abs(y[:, 0])) < 1e-3
    # the right channel must stay in-polarity with the source (positive correlation).
    rr = y[: len(sig), 1]
    assert float(np.dot(rr, sig[: len(rr)])) > 0


def test_stereo_balance_is_equal_power() -> None:
    # The stereo balance law must PRESERVE loudness (L**2 + R**2 constant) across
    # the pan range — the same constant-power law _pan uses for mono — not the old
    # linear [1-pan, 1] law that quietened the bus as a stem was panned.
    rng = np.random.default_rng(3)
    sig = rng.standard_normal(4096)
    stereo = np.column_stack([sig, sig])              # identical L/R -> exactly equal energy
    base = float(np.sum(stereo ** 2))
    for pan in (-1.0, -0.5, 0.0, 0.3, 0.7, 1.0):
        assert abs(float(np.sum(_balance(stereo, pan) ** 2)) - base) <= base * 1e-9
    # the per-side gain weights are equal-power (gL**2 + gR**2 == 2) at every pan
    for pan in (-1.0, -0.3, 0.0, 0.7, 1.0):
        a = (pan + 1.0) * np.pi / 4.0
        assert abs((np.sqrt(2) * np.cos(a)) ** 2 + (np.sqrt(2) * np.sin(a)) ** 2 - 2.0) < 1e-9
    assert np.allclose(_balance(stereo, 0.0), stereo)  # center is an exact no-op


def test_panning_a_stereo_stem_preserves_bus_loudness(tmp_path) -> None:
    # Integration regression: an isolated equal-L/R stereo stem mixed at center vs
    # hard-panned must land at the SAME bus loudness (the old law dropped it as the
    # stem was panned). Quiet stem so no anti-clip trim fires (asserted).
    rng = np.random.default_rng(11)
    sig = (rng.standard_normal(SR * 6) * 0.1).astype(np.float32)
    _w(tmp_path / "pad.wav", np.column_stack([sig, sig]))
    center = mix_stems(str(tmp_path), out_dir=str(tmp_path / "c"),
                       spec={"pad.wav": {"pan": 0.0}}, dur=0)
    panned = mix_stems(str(tmp_path), out_dir=str(tmp_path / "p"),
                       spec={"pad.wav": {"pan": 0.7}}, dur=0)
    assert abs(center["global_trim_db"]) < 0.01 and abs(panned["global_trim_db"]) < 0.01
    assert abs(center["lufs"] - panned["lufs"]) < 0.5  # loudness preserved across pan


def test_truncation_note_on_unequal_stems(tmp_path) -> None:
    # Stems are summed over the common (shortest) length; the dropped trailing
    # audio must be flagged and the sum must run to the shorter length.
    rng = np.random.default_rng(0)
    _w(tmp_path / "a.wav", (rng.standard_normal(SR * 8) * 0.3).astype(np.float32))
    _w(tmp_path / "b.wav", (rng.standard_normal(SR * 6) * 0.3).astype(np.float32))   # shorter
    res = mix_stems(str(tmp_path), out_dir=str(tmp_path / "mix"), dur=0)
    assert res["truncation_note"] is not None
    assert str(SR * 6) in res["truncation_note"] and str(SR * 8) in res["truncation_note"]
    assert res["duration_s"] == round(SR * 6 / SR, 2)
    y, _ = sf.read(res["out"], always_2d=True)
    assert y.shape[0] == SR * 6                    # summed over the shortest stem
