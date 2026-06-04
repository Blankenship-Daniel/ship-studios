"""overheads flow: resolve_overhead() topology + merge_overheads() write/no-op.

Covers resolve_overhead() across the three branches — a pre-merged stereo OH
(early return), an L/R pair kept as a spaced image (align=False), and an L/R
pair phase-locked (align=True) — and merge_overheads() both branches (already a
stereo OH -> no-op; an L/R pair -> a written, re-detect-safe subdir file).
Fully offline: signals are synthesized into tmp_path, no real audio/keys/network.
"""
from __future__ import annotations

import os

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
sf = pytest.importorskip("soundfile")

from drum_prep import dsp, overheads  # noqa: E402
from drum_prep.kit import resolve_kit  # noqa: E402

SR = 48000


def _w(path, sig) -> None:
    sf.write(str(path), sig, SR, subtype="PCM_24", format="AIFF")


# --------------------------------------------------------------------------- #
# resolve_overhead
# --------------------------------------------------------------------------- #
def test_resolve_overhead_stereo_early_return(tmp_path) -> None:
    # A pre-merged stereo OH *is* the reference: read + coerce to stereo, return
    # its basename. No L/R merge happens. Give the two channels distinct content
    # so the returned array is the real file, not a centred mono duplicate.
    n = SR * 2
    rng = np.random.default_rng(0)
    left = rng.standard_normal(n) * 0.2
    right = rng.standard_normal(n) * 0.2
    _w(tmp_path / "overheads - stereo.aif", np.column_stack([left, right]))

    kit = resolve_kit(str(tmp_path))
    assert kit.overhead_mode == "stereo"
    arr, sr, name = overheads.resolve_overhead(kit)

    assert sr == SR
    assert name == "overheads - stereo.aif"   # the source stem's basename
    assert arr.ndim == 2 and arr.shape[1] == 2
    assert arr.shape[0] == n
    # the two channels are NOT collapsed to mono (distinct source content kept)
    assert not np.allclose(arr[:, 0], arr[:, 1])


def test_resolve_overhead_lr_pair_unaligned_keeps_image(tmp_path) -> None:
    # An L/R pair (no pre-merged OH) stacks into stereo. With align=False the
    # inter-channel timing of a spaced pair is preserved (R is NOT phase-locked
    # to L), so the known L->R lag survives in the merged image.
    n = SR * 2
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    right = dsp.fractional_delay(base, 30)        # R lags L by 30 samples
    _w(tmp_path / "OH left.aif", base)
    _w(tmp_path / "OH right.aif", right)

    kit = resolve_kit(str(tmp_path))
    assert kit.overhead_mode == "lr_pair"
    arr, sr, name = overheads.resolve_overhead(kit, align=False)

    assert sr == SR
    assert name == "overheads-merged.aif"
    assert arr.ndim == 2 and arr.shape[1] == 2
    assert arr.shape[0] == n
    # spaced-pair image kept: R still lags L by ~30 (timing preserved)
    d, _ = dsp.estimate(arr[:, 1], arr[:, 0], 100)
    assert abs(d - 30) < 2


def test_resolve_overhead_lr_pair_aligned_phase_locks(tmp_path) -> None:
    # align=True opts into phase-locking R to L (collapsing a spaced image) via
    # dsp.align_to + fractional_delay (overheads.py:40-42). After it the two
    # output channels are time-aligned (near-zero inter-channel lag).
    n = SR * 2
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    right = dsp.fractional_delay(base, 30)        # R lags L by 30 samples
    _w(tmp_path / "OH left.aif", base)
    _w(tmp_path / "OH right.aif", right)

    kit = resolve_kit(str(tmp_path))
    assert kit.overhead_mode == "lr_pair"
    arr, sr, name = overheads.resolve_overhead(kit, align=True, max_lag=200)

    assert sr == SR
    assert name == "overheads-merged.aif"
    assert arr.ndim == 2 and arr.shape[1] == 2
    # phase-locked: R now coincides with L (lag collapsed to ~0)
    d, _ = dsp.estimate(arr[:, 1], arr[:, 0], 100)
    assert abs(d) < 2


def test_resolve_overhead_lr_samplerate_mismatch_raises(tmp_path) -> None:
    # The L/R pair must share a sample rate (they get column-stacked) — a stray
    # off-SR side raises KitError rather than silently mis-stacking.
    from drum_prep.kit import KitError

    n = SR * 1
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    sf.write(str(tmp_path / "OH left.aif"), base, SR, subtype="PCM_24", format="AIFF")
    sf.write(str(tmp_path / "OH right.aif"), base, 44100, subtype="PCM_24", format="AIFF")

    kit = resolve_kit(str(tmp_path))
    assert kit.overhead_mode == "lr_pair"
    with pytest.raises(KitError, match="sample-rate mismatch"):
        overheads.resolve_overhead(kit)


# --------------------------------------------------------------------------- #
# merge_overheads
# --------------------------------------------------------------------------- #
def test_merge_overheads_already_stereo_is_noop(tmp_path) -> None:
    # A pre-merged stereo OH needs no merge: the flow reports merged=False and
    # points at the existing reference, writing nothing new.
    n = SR * 1
    rng = np.random.default_rng(0)
    stereo = np.column_stack([rng.standard_normal(n) * 0.2, rng.standard_normal(n) * 0.2])
    src = tmp_path / "overheads - stereo.aif"
    _w(src, stereo)

    kit = resolve_kit(str(tmp_path))
    res = overheads.merge_overheads(kit)

    assert res["flow"] == "overheads"
    assert res["merged"] is False
    assert res["reference"] == str(src)
    assert "output" not in res
    # nothing written into a 'stereo' subdir
    assert not os.path.isdir(tmp_path / "stereo")


def test_merge_overheads_lr_writes_stereo_subdir(tmp_path) -> None:
    # An L/R pair is merged + written to a 'stereo' SUBDIR (not src_dir, so a
    # later resolve_kit doesn't re-detect it as a third overhead). Default path,
    # default align=False.
    n = SR * 2
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    _w(tmp_path / "OH left.aif", base)
    _w(tmp_path / "OH right.aif", base * 0.9)

    kit = resolve_kit(str(tmp_path))
    res = overheads.merge_overheads(kit)

    assert res["flow"] == "overheads"
    assert res["merged"] is True
    assert res["sr"] == SR
    assert res["aligned"] is False
    assert res["frames"] == n
    out = res["output"]
    assert out == os.path.join(str(tmp_path), "stereo", "overheads-merged.aif")
    assert os.path.exists(out)
    # the written file is real stereo, full length, 24-bit AIFF
    arr, sr = sf.read(out)
    assert sr == SR
    assert arr.ndim == 2 and arr.shape[1] == 2
    assert arr.shape[0] == n
    info = sf.info(out)
    assert info.format == "AIFF" and info.subtype == "PCM_24"


def test_merge_overheads_lr_honors_out_path_and_align(tmp_path) -> None:
    # An explicit out_path + align=True is respected end to end.
    n = SR * 2
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    _w(tmp_path / "OH left.aif", base)
    _w(tmp_path / "OH right.aif", dsp.fractional_delay(base, 25))   # R lags L

    kit = resolve_kit(str(tmp_path))
    out = str(tmp_path / "merged" / "oh.aif")
    res = overheads.merge_overheads(kit, out_path=out, align=True)

    assert res["merged"] is True
    assert res["aligned"] is True
    assert res["output"] == out
    assert os.path.exists(out)
    arr, _ = sf.read(out)
    assert arr.ndim == 2 and arr.shape[1] == 2
    # align collapsed the inter-channel lag
    d, _ = dsp.estimate(arr[:, 1], arr[:, 0], 100)
    assert abs(d) < 2
