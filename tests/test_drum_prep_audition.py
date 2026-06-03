"""audition flow: the two halves of each A/B are loudness-matched."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")
pyln = pytest.importorskip("pyloudnorm")

from drum_prep.audition import render_auditions  # noqa: E402
from drum_prep.kit import Kit  # noqa: E402

SR = 48000


def test_audition_halves_loudness_matched(tmp_path) -> None:
    n = SR * 14
    sig = np.random.default_rng(0).standard_normal(n) * 0.3
    aligned = tmp_path / "phase-aligned"
    matched = tmp_path / "ref-matched"
    aligned.mkdir()
    matched.mkdir()
    sf.write(str(aligned / "snare.aif"), sig, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(matched / "snare.aif"), sig * 0.5, SR, subtype="PCM_24", format="AIFF")  # quieter "after"
    ref = np.random.default_rng(1).standard_normal(n) * 0.1
    refp = tmp_path / "ref.wav"
    sf.write(str(refp), np.column_stack([ref, ref]), SR, subtype="PCM_24")

    kit = Kit(src_dir=str(tmp_path), stems=[])
    render_auditions(kit, str(refp), aligned_dir=str(aligned), matched_dir=str(matched),
                     out_dir=str(tmp_path / "auditions"), t0=0.0, dur=12.0)

    y, _ = sf.read(str(tmp_path / "auditions" / "AB_before-vs-after.wav"))
    nb, gp = int(12 * SR), int(0.6 * SR)
    meter = pyln.Meter(SR)
    lb = meter.integrated_loudness(y[:nb])
    la = meter.integrated_loudness(y[nb + gp: nb + gp + nb])
    assert abs(lb - la) < 0.5
    assert np.abs(y).max() <= 0.95 + 1e-3


def _stage(tmp_path):
    """Minimal aligned/ref-matched/ref setup for the guard tests."""
    n = SR * 14
    sig = np.random.default_rng(0).standard_normal(n) * 0.3
    aligned = tmp_path / "phase-aligned"
    matched = tmp_path / "ref-matched"
    aligned.mkdir()
    matched.mkdir()
    sf.write(str(aligned / "snare.aif"), sig, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(matched / "snare.aif"), sig * 0.5, SR, subtype="PCM_24", format="AIFF")
    ref = np.random.default_rng(1).standard_normal(n) * 0.1
    refp = tmp_path / "ref.wav"
    sf.write(str(refp), np.column_stack([ref, ref]), SR, subtype="PCM_24")
    return Kit(src_dir=str(tmp_path), stems=[]), str(refp), str(aligned), str(matched)


def test_audition_nonpositive_dur_raises(tmp_path) -> None:
    # dur<=0 yields an empty excerpt that would crash pick_excerpt with an opaque
    # numpy error before the _MIN_MATCH_S guard — reject it up front instead.
    kit, refp, aligned, matched = _stage(tmp_path)
    with pytest.raises(ValueError, match="must be > 0"):
        render_auditions(kit, refp, aligned_dir=aligned, matched_dir=matched,
                         out_dir=str(tmp_path / "auditions"), t0=0.0, dur=0)


def test_audition_too_short_excerpt_raises(tmp_path) -> None:
    # A positive-but-tiny window measures -inf LUFS and would emit an UNMATCHED
    # A/B claiming to be matched; the _MIN_MATCH_S guard must reject it clearly.
    kit, refp, aligned, matched = _stage(tmp_path)
    with pytest.raises(ValueError, match="too short"):
        render_auditions(kit, refp, aligned_dir=aligned, matched_dir=matched,
                         out_dir=str(tmp_path / "auditions"), t0=0.0, dur=0.1)
