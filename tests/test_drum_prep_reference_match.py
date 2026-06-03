"""reference-match flow: shrinks a known tonal delta; analyze is read-only."""
from __future__ import annotations

import os

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
sf = pytest.importorskip("soundfile")

from drum_prep.kit import Kit  # noqa: E402
from drum_prep.reference_match import analyze, apply_match  # noqa: E402
from tests.drumkit_synth import colored_noise  # noqa: E402

SR = 48000


def _build(tmp_path):
    n = SR * 4
    aligned = tmp_path / "phase-aligned"
    aligned.mkdir()
    kick = colored_noise(SR, n, -9.0, seed=1)        # low-heavy
    oh = colored_noise(SR, n, +1.0, seed=2)          # bright
    sf.write(str(aligned / "kick in.aif"), kick, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(aligned / "overheads - stereo.aif"), np.column_stack([oh, oh]), SR,
             subtype="PCM_24", format="AIFF")
    ref = colored_noise(SR, n, -4.0, seed=3)         # target tilt
    refp = tmp_path / "ref.wav"
    sf.write(str(refp), np.column_stack([ref, ref]), SR, subtype="PCM_24")
    return Kit(src_dir=str(tmp_path), stems=[]), str(refp), str(aligned)


def test_reference_match_reduces_delta(tmp_path) -> None:
    kit, refp, aligned = _build(tmp_path)
    res = apply_match(kit, refp, aligned_dir=aligned,
                      out_dir=str(tmp_path / "ref-matched"), strength=1.0)
    rb, ra = res["residual_before"], res["residual_after"]
    bands = ["low 60-120", "mid 400-2k", "presence 2-6k", "air 6-20k"]
    assert sum(abs(ra[b]) for b in bands) < sum(abs(rb[b]) for b in bands)
    # global trim brings the loudest stem to ~ -1 dBFS, no clipping
    peak = max(np.abs(sf.read(str(tmp_path / "ref-matched" / f))[0]).max()
               for f in ("kick in.aif", "overheads - stereo.aif"))
    assert peak <= 10 ** (-1.0 / 20) + 1e-3


def test_low_band_shortfall_flagged_as_extension(tmp_path) -> None:
    # A reference far more low-heavy than the kit can reach (owner boost capped low)
    # leaves a stubborn low-band residual. That's an EXTENSION/sustain problem, not
    # a level one — the notes must route the user away from "more EQ".
    n = SR * 4
    aligned = tmp_path / "phase-aligned"
    aligned.mkdir()
    kick = colored_noise(SR, n, -9.0, seed=1)
    oh = colored_noise(SR, n, +2.0, seed=2)
    sf.write(str(aligned / "kick in.aif"), kick, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(aligned / "overheads - stereo.aif"), np.column_stack([oh, oh]), SR,
             subtype="PCM_24", format="AIFF")
    ref = colored_noise(SR, n, -24.0, seed=3)        # extreme low tilt the kit can't match
    refp = tmp_path / "ref.wav"
    sf.write(str(refp), np.column_stack([ref, ref]), SR, subtype="PCM_24")
    kit = Kit(src_dir=str(tmp_path), stems=[])
    res = apply_match(kit, str(refp), aligned_dir=str(aligned), out_dir=str(tmp_path / "rm"),
                      strength=1.0, boost_cap=0.5, cut_cap=-2.0)
    assert any("extension" in t or "sustain" in t for t in res["notes"]), res["notes"]


def test_short_reference_loop(tmp_path) -> None:
    # a one-bar loop shorter than nperseg used to crash welch (noverlap >= nperseg)
    kit, _, aligned = _build(tmp_path)
    short = np.random.default_rng(7).standard_normal(4000) * 0.3   # < 8192 samples
    refp = tmp_path / "shortref.wav"
    sf.write(str(refp), np.column_stack([short, short]), SR, subtype="PCM_24")
    res = apply_match(kit, str(refp), aligned_dir=aligned, out_dir=str(tmp_path / "rm"))
    assert "residual_after" in res


def test_reference_sr_mismatch_raises(tmp_path) -> None:
    kit, _, aligned = _build(tmp_path)                    # stems at 48 kHz
    ref = np.random.default_rng(8).standard_normal(44100 * 2) * 0.3
    refp = tmp_path / "ref441.wav"
    sf.write(str(refp), np.column_stack([ref, ref]), 44100, subtype="PCM_24")
    with pytest.raises(ValueError):
        apply_match(kit, str(refp), aligned_dir=aligned, out_dir=str(tmp_path / "rm2"))


def test_analyze_is_read_only(tmp_path) -> None:
    kit, refp, aligned = _build(tmp_path)
    before = set(os.listdir(tmp_path))
    out = analyze(kit, refp, aligned_dir=aligned)
    assert out["flow"] == "analyze" and "delta_6band" in out
    assert set(os.listdir(tmp_path)) == before   # nothing written
