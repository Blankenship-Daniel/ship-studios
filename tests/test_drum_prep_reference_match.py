"""reference-match flow: shrinks a known tonal delta; analyze is read-only."""
from __future__ import annotations

import os

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
sf = pytest.importorskip("soundfile")

from drum_prep import dsp  # noqa: E402
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


def test_match_routing_cuts_to_all_boosts_to_owner(tmp_path) -> None:
    # Pin the routing DIRECTLY (the aggregate residual test is too insensitive to
    # catch a routing regression): a band needing a CUT must show the cut on a
    # NON-owner stem (cuts -> all), while a band needing a BOOST must be non-zero
    # ONLY on the owner and exactly 0.0 on non-owners (boosts -> owners).
    n = SR * 4
    aligned = tmp_path / "phase-aligned"
    aligned.mkdir()
    kick = colored_noise(SR, n, -12.0, seed=1)       # low-heavy: owns sub/low, NOT highs
    oh = colored_noise(SR, n, +6.0, seed=2)          # bright: owns lowmid/mid/highs
    sf.write(str(aligned / "kick in.aif"), kick, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(aligned / "overheads - stereo.aif"), np.column_stack([oh, oh]), SR,
             subtype="PCM_24", format="AIFF")
    ref = colored_noise(SR, n, 0.0, seed=3)          # flat: kit is hot in air, lean in lowmid
    refp = tmp_path / "ref.wav"
    sf.write(str(refp), np.column_stack([ref, ref]), SR, subtype="PCM_24")
    kit = Kit(src_dir=str(tmp_path), stems=[])
    res = apply_match(kit, str(refp), aligned_dir=str(aligned),
                      out_dir=str(tmp_path / "rm"), strength=1.0)
    pe = res["per_stem_eq"]

    # CUT band (air): kit is hot vs the flat ref -> a cut. The kick does NOT own
    # the air band, yet the cut still lands on it (cuts -> all stems) and matches
    # the cut on the owner OH.
    assert pe["kick in.aif"]["air 6-20k"] < 0.0
    assert pe["kick in.aif"]["air 6-20k"] == pe["overheads - stereo.aif"]["air 6-20k"]

    # BOOST band (lowmid 120-400): kit is lean there -> a boost. Only the OH owns
    # it, so the OH gets a positive gain and the non-owner kick gets exactly 0.0.
    assert pe["overheads - stereo.aif"]["lowmid 120-400"] > 0.0
    assert pe["kick in.aif"]["lowmid 120-400"] == 0.0


def test_kit_sum_is_coherent_not_power_sum(tmp_path) -> None:
    # Two stems sharing a CORRELATED low-frequency component must reinforce in the
    # TIME domain (~+6 dB for two identical copies), the way they sum in a DAW. A
    # power-sum (adding band energies) would undercount the correlated lows by ~3
    # dB and over-boost them in the match — this is the only test that catches a
    # power-sum regression. Probe _measure's coherent cur_db directly.
    from drum_prep.reference_match import _measure
    n = SR * 4
    aligned = tmp_path / "phase-aligned"
    aligned.mkdir()
    # a shared low sine in two stems (perfectly correlated) + independent broadband
    t = np.arange(n) / SR
    low = 0.3 * np.sin(2 * np.pi * 80.0 * t)
    rng = np.random.default_rng(0)
    s1 = low + 0.02 * rng.standard_normal(n)
    s2 = low + 0.02 * rng.standard_normal(n)         # SAME low, different noise
    sf.write(str(aligned / "kick in.aif"), s1, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(aligned / "overheads - stereo.aif"), np.column_stack([s2, s2]), SR,
             subtype="PCM_24", format="AIFF")
    ref = colored_noise(SR, n, 0.0, seed=3)
    refp = tmp_path / "ref.wav"
    sf.write(str(refp), np.column_stack([ref, ref]), SR, subtype="PCM_24")

    m = _measure(str(aligned), str(refp), 16384)
    bi = int(np.argmin(np.abs(dsp.THIRD_OCT - 80.0)))   # the 80 Hz band index
    # coherent sum (s1+s2 ~ 2*low) is +6 dB over a single stem's 80 Hz band.
    single = m["raw"][0][1]
    fs, ps = dsp.psd(dsp.mono(single), m["sr"], 16384)
    single_db = dsp.band_db(fs, ps, dsp.THIRD_OCT)[bi]
    coherent_db = m["cur_db"][bi]
    # +6 dB coherent, vs only +3 dB if it were a power-sum. Bracket the coherent
    # value well clear of the power-sum value.
    assert coherent_db - single_db > 5.0      # near +6 (coherent), not +3 (power)


def test_analyze_is_read_only(tmp_path) -> None:
    kit, refp, aligned = _build(tmp_path)
    before = set(os.listdir(tmp_path))
    out = analyze(kit, refp, aligned_dir=aligned)
    assert out["flow"] == "analyze" and "delta_6band" in out
    assert set(os.listdir(tmp_path)) == before   # nothing written
