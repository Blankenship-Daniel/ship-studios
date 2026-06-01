"""tune: measure a sample's fundamental and retune it by resampling."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep.tune import hz_to_note, measure_fundamental, retune  # noqa: E402

SR = 48000


def _tone(hz, n=SR) -> np.ndarray:
    t = np.arange(n) / SR
    return (0.5 * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_measure_and_note(tmp_path) -> None:
    p = tmp_path / "tone.wav"
    sf.write(str(p), _tone(100.0), SR, subtype="FLOAT")
    m = measure_fundamental(str(p))
    assert abs(m["hz"] - 100.0) < 5.0
    assert hz_to_note(440.0)["note"] == "A4"


def test_retune_to_target_hz(tmp_path) -> None:
    p = tmp_path / "tone.wav"
    sf.write(str(p), _tone(100.0), SR, subtype="FLOAT")
    res = retune(str(p), str(tmp_path / "out.wav"), target_hz=120.0)
    assert abs(res["to_hz"] - 120.0) < 5.0
    assert res["frames_out"] < res["frames_in"]              # higher pitch => shorter


def test_retune_semitones_octave(tmp_path) -> None:
    p = tmp_path / "tone.wav"
    sf.write(str(p), _tone(100.0), SR, subtype="FLOAT")
    res = retune(str(p), str(tmp_path / "oct.wav"), semitones=12)
    assert abs(res["to_hz"] - 200.0) < 8.0


def test_retune_to_target_midi(tmp_path) -> None:
    # MIDI 57 = A3 = 220 Hz (within the drum-range measurement band). Start from
    # ~110 (A2) and tune up an octave.
    p = tmp_path / "a2.wav"
    sf.write(str(p), _tone(110.0), SR, subtype="FLOAT")
    res = retune(str(p), str(tmp_path / "a3.wav"), target_midi=57)
    assert abs(res["to_hz"] - 220.0) < 8.0
    out, _ = sf.read(str(tmp_path / "a3.wav"), always_2d=True)
    assert out.shape[1] == 1  # mono in -> mono out


def test_retune_requires_one_target(tmp_path) -> None:
    p = tmp_path / "tone.wav"
    sf.write(str(p), _tone(100.0), SR, subtype="FLOAT")
    with pytest.raises(ValueError):
        retune(str(p), str(tmp_path / "x.wav"))  # no target given
