"""io helpers: channel coercion, sample-rate validation, format-preserving write."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep import io  # noqa: E402

SR = 48000


def _w(p, x, sr=SR, subtype="FLOAT") -> None:
    sf.write(str(p), x, sr, subtype=subtype)


def test_to_stereo_coerces_shapes() -> None:
    mono = np.arange(4, dtype=float)
    st = io.to_stereo(mono)
    assert st.shape == (4, 2)
    assert np.array_equal(st[:, 0], st[:, 1])  # mono duplicated to both channels
    already = np.zeros((4, 2))
    assert io.to_stereo(already).shape == (4, 2)
    wide = np.zeros((4, 5))
    assert io.to_stereo(wide).shape == (4, 2)  # keeps first two of >2


def test_collapse_if_mono() -> None:
    col = np.zeros((4, 1))
    assert io.collapse_if_mono(col).shape == (4,)
    stereo = np.zeros((4, 2))
    assert io.collapse_if_mono(stereo).shape == (4, 2)  # untouched


def test_read_mono_sums_channels(tmp_path) -> None:
    x = np.column_stack([np.ones(8), -np.ones(8)]).astype(np.float32)  # L=+1, R=-1
    _w(tmp_path / "s.wav", x)
    m, sr = io.read_mono(str(tmp_path / "s.wav"))
    assert sr == SR and m.ndim == 1
    assert np.allclose(m, 0.0, atol=1e-4)  # mean of +1/-1 == 0


def test_common_samplerate_agreement(tmp_path) -> None:
    _w(tmp_path / "a.wav", np.zeros(SR, dtype=np.float32))
    _w(tmp_path / "b.wav", np.zeros(SR, dtype=np.float32))
    assert io.common_samplerate([str(tmp_path / "a.wav"), str(tmp_path / "b.wav")]) == SR


def test_common_samplerate_mismatch_raises(tmp_path) -> None:
    _w(tmp_path / "a.wav", np.zeros(SR, dtype=np.float32), sr=48000)
    _w(tmp_path / "b.wav", np.zeros(44100, dtype=np.float32), sr=44100)
    with pytest.raises(ValueError, match="sample-rate mismatch"):
        io.common_samplerate([str(tmp_path / "a.wav"), str(tmp_path / "b.wav")])


def test_common_samplerate_empty_raises() -> None:
    with pytest.raises(ValueError, match="no inputs"):
        io.common_samplerate([])


def test_summarize_inputs_returns_sr_and_frames(tmp_path) -> None:
    _w(tmp_path / "a.wav", np.zeros(SR, dtype=np.float32))          # 1.0 s
    _w(tmp_path / "b.wav", np.zeros(SR * 2, dtype=np.float32))      # 2.0 s
    sr, frames = io.summarize_inputs([str(tmp_path / "a.wav"), str(tmp_path / "b.wav")])
    assert sr == SR
    assert frames == [SR, SR * 2]


def test_summarize_inputs_mismatch_raises(tmp_path) -> None:
    _w(tmp_path / "a.wav", np.zeros(SR, dtype=np.float32), sr=48000)
    _w(tmp_path / "b.wav", np.zeros(44100, dtype=np.float32), sr=44100)
    with pytest.raises(ValueError, match="sample-rate mismatch"):
        io.summarize_inputs([str(tmp_path / "a.wav"), str(tmp_path / "b.wav")])


def test_truncation_note_threshold() -> None:
    assert io.truncation_note([100, 100]) is None
    assert io.truncation_note([100, 101]) is None        # 1-frame diff suppressed
    note = io.truncation_note([100, 200])
    assert note is not None and "200" in note and "100" in note
    assert io.truncation_note([]) is None


def test_write_wav_preserves_subtype(tmp_path) -> None:
    src = tmp_path / "src.wav"
    _w(src, np.zeros((SR, 2), dtype=np.float32), subtype="PCM_24")
    out = tmp_path / "out.wav"
    io.write_wav(str(out), np.zeros((SR, 2)), SR, subtype=io.subtype_of(str(src)))
    assert io.subtype_of(str(out)) == "PCM_24"


def test_write_wav_aif_extension_writes_aiff(tmp_path) -> None:
    # The 3-letter ``.aif`` extension is not inferable by soundfile; write_wav must
    # derive format=AIFF explicitly or it would crash with a raw TypeError mid-batch.
    out = tmp_path / "stem.aif"
    io.write_wav(str(out), np.zeros((SR, 2)), SR, subtype="PCM_24")
    info = sf.info(str(out))
    assert info.format == "AIFF" and info.subtype == "PCM_24"


def test_write_aiff24_writes_24bit_aiff(tmp_path) -> None:
    # The alignment/match flows write 24-bit AIFF; pin that container + subtype at
    # the writer so a regression there is caught regardless of caller.
    out = tmp_path / "stem.aif"
    io.write_aiff24(str(out), np.zeros((SR, 2)), SR)
    info = sf.info(str(out))
    assert info.format == "AIFF" and info.subtype == "PCM_24"


def test_write_wav24_writes_24bit_wav(tmp_path) -> None:
    out = tmp_path / "bus.wav"
    io.write_wav24(str(out), np.zeros((SR, 2)), SR)
    info = sf.info(str(out))
    assert info.format == "WAV" and info.subtype == "PCM_24"
