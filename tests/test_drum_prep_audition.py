"""audition flow: the two halves of each A/B are loudness-matched."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")
pyln = pytest.importorskip("pyloudnorm")

from drum_prep.audition import _kit_sum, render_auditions  # noqa: E402
from drum_prep.kit import Kit, KitStem  # noqa: E402
from drum_prep.roles import Role  # noqa: E402

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


def test_kit_sum_drops_orphan_stems(tmp_path) -> None:
    # A renamed/removed stem can leave an ORPHAN file in the aligned dir; summing
    # the whole dir would double-count it. With a kit declaring its real stems,
    # _kit_sum must intersect to the kit's files and ignore the orphan.
    n = SR * 2
    aligned = tmp_path / "phase-aligned"
    aligned.mkdir()
    snare = np.random.default_rng(0).standard_normal(n) * 0.3
    oh = np.random.default_rng(1).standard_normal(n) * 0.3
    sf.write(str(aligned / "snare.aif"), snare, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(aligned / "overheads - stereo.aif"), np.column_stack([oh, oh]), SR,
             subtype="PCM_24", format="AIFF")
    # the orphan (a stale rename) — present on disk but NOT in the kit
    sf.write(str(aligned / "snare OLD.aif"), snare, SR, subtype="PCM_24", format="AIFF")

    kit = Kit(src_dir=str(tmp_path), stems=[
        KitStem(name="snare.aif", role=Role.SNARE_TOP),
        KitStem(name="overheads - stereo.aif", role=Role.OVERHEAD),
    ])
    from drum_prep.audition import _kit_keep
    summed, _ = _kit_sum(str(aligned), _kit_keep(kit))
    # expected coherent sum from the READ-BACK files (the deterministic ground
    # truth; avoids 24-bit round-trip drift): snare(centred) + OH, WITHOUT the
    # orphan copy of snare.
    sn = sf.read(str(aligned / "snare.aif"), always_2d=True, dtype="float64")[0]
    ohr = sf.read(str(aligned / "overheads - stereo.aif"), always_2d=True, dtype="float64")[0]
    expect = np.column_stack([sn[:, 0], sn[:, 0]]) + ohr
    assert np.allclose(summed, expect, atol=1e-9)
    # summing the whole dir (no keep) double-counts the orphan -> the snare's
    # contribution is doubled, a clearly different sum.
    all_summed, _ = _kit_sum(str(aligned), None)
    assert not np.allclose(all_summed, expect, atol=1e-4)
    assert np.allclose(all_summed, expect + np.column_stack([sn[:, 0], sn[:, 0]]), atol=1e-9)


def test_audition_too_short_excerpt_raises(tmp_path) -> None:
    # A positive-but-tiny window measures -inf LUFS and would emit an UNMATCHED
    # A/B claiming to be matched; the _MIN_MATCH_S guard must reject it clearly.
    kit, refp, aligned, matched = _stage(tmp_path)
    with pytest.raises(ValueError, match="too short"):
        render_auditions(kit, refp, aligned_dir=aligned, matched_dir=matched,
                         out_dir=str(tmp_path / "auditions"), t0=0.0, dur=0.1)


def test_audition_reported_lufs_matches_trimmed_file(tmp_path) -> None:
    # When the anti-clip trim fires, the reported lufs_before must reflect the
    # WRITTEN (post-trim) file — not the pre-trim measurement, which overstated the
    # files by the trim amount. `before` is only scaled by the trim, so its file
    # loudness == reported lufs_before exactly (within meter precision).
    n = SR * 14
    sig = np.random.default_rng(0).standard_normal(n) * 0.6  # hot -> trim WILL fire
    aligned = tmp_path / "phase-aligned"
    matched = tmp_path / "ref-matched"
    aligned.mkdir()
    matched.mkdir()
    sf.write(str(aligned / "snare.aif"), sig, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(matched / "snare.aif"), sig * 0.5, SR, subtype="PCM_24", format="AIFF")
    ref = np.random.default_rng(1).standard_normal(n) * 0.1
    refp = tmp_path / "ref.wav"
    sf.write(str(refp), np.column_stack([ref, ref]), SR, subtype="PCM_24")

    kit = Kit(src_dir=str(tmp_path), stems=[])
    res = render_auditions(kit, str(refp), aligned_dir=str(aligned), matched_dir=str(matched),
                           out_dir=str(tmp_path / "auditions"), t0=0.0, dur=12.0)
    ab = next(a for a in res["auditions"] if a["name"] == "before-vs-after")

    y, _ = sf.read(str(tmp_path / "auditions" / "AB_before-vs-after.wav"))
    assert abs(np.abs(y).max() - 0.95) < 0.02  # trim engaged (clamped to the ceiling)
    file_before = pyln.Meter(SR).integrated_loudness(y[: int(12 * SR)])
    assert abs(ab["lufs_before"] - file_before) < 0.3  # reported == the written file
