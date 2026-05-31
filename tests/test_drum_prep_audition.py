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
