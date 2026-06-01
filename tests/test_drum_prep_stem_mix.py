"""stem-mix: arbitrary named stems balanced to a target LUFS, summed to stereo."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")
pytest.importorskip("pyloudnorm")

from drum_prep.stem_mix import mix_stems  # noqa: E402

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
