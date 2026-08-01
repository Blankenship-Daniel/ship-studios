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


def test_retune_rejects_multiple_targets(tmp_path) -> None:
    # Conflicting targets must error, not silently let if/elif precedence decide.
    p = tmp_path / "tone.wav"
    sf.write(str(p), _tone(100.0), SR, subtype="FLOAT")
    with pytest.raises(ValueError, match="only one of"):
        retune(str(p), str(tmp_path / "x.wav"), target_hz=120.0, semitones=2)


def test_retune_rejects_out_of_range_ratio(tmp_path) -> None:
    # An extreme shift collapses to a no-op once the fraction denominator is
    # capped; reject it rather than silently return the input unchanged.
    p = tmp_path / "tone.wav"
    sf.write(str(p), _tone(100.0), SR, subtype="FLOAT")
    with pytest.raises(ValueError, match="outside the resampling range"):
        retune(str(p), str(tmp_path / "x.wav"), semitones=180)  # 15 octaves up -> 1/ratio rounds to 0


@pytest.mark.parametrize("hz", [54.0, 55.0, 61.7, 98.0])
@pytest.mark.parametrize("dur", [0.30, 0.50])
def test_measure_fundamental_is_accurate_to_a_few_cents(tmp_path, hz, dur) -> None:
    """The raw argmax bin is only good to +/- half a bin, which at this resolution
    is a MUSICAL error: a 0.3 s kick gives df = 3.33 Hz, so 55 Hz used to read
    56.67 Hz (+52 cents) and 54 Hz read 53.33 Hz (-22 cents). ``retune`` derives its
    resample ratio from this and re-measures the same way, so the error lands in the
    output sample while the report still looks self-consistent."""
    t = np.arange(int(SR * dur)) / SR
    sig = np.sin(2 * np.pi * hz * t) * np.exp(-t * 8) * 0.8
    p = tmp_path / "kick.wav"
    sf.write(str(p), sig, SR)

    got = measure_fundamental(str(p))["hz"]
    cents = 1200 * np.log2(got / hz)
    assert abs(cents) < 5, f"{got} Hz vs {hz} Hz = {cents:+.1f} cents"
