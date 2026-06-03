"""phase-align flow: recovers known per-mic delays + a known polarity flip."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
sf = pytest.importorskip("soundfile")

from drum_prep import dsp  # noqa: E402
from drum_prep.kit import resolve_kit  # noqa: E402
from drum_prep.phase_align import phase_align  # noqa: E402

SR = 48000


def _w(path, sig):
    sf.write(str(path), sig, SR, subtype="PCM_24", format="AIFF")


def test_phase_align_recovers_topology(tmp_path) -> None:
    n = SR * 3
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    _w(tmp_path / "overheads - stereo.aif", np.column_stack([base, base]))
    # close mics LEAD the OH by known amounts -> need positive correcting delay
    for name, lead in [("snare top.aif", 90), ("hi-hat.aif", 63), ("kick in.aif", 144)]:
        _w(tmp_path / name, dsp.fractional_delay(base, -lead))
    _w(tmp_path / "snare bottom.aif", -dsp.fractional_delay(base, -75))   # inverted, leads 75
    _w(tmp_path / "kick beater.aif", dsp.fractional_delay(base, -212))
    _w(tmp_path / "drum room.aif", np.column_stack([np.random.default_rng(9).standard_normal(n) * 0.1] * 2))

    kit = resolve_kit(str(tmp_path))
    res = phase_align(kit, max_lag=400, excerpt_s=2.0)
    by = {r["name"]: r for r in res["results"]}

    assert abs(by["snare top.aif"]["delay_samples"] - 90) < 2
    assert abs(by["hi-hat.aif"]["delay_samples"] - 63) < 2
    assert abs(by["kick in.aif"]["delay_samples"] - 144) < 4   # low-passed, looser
    assert by["snare bottom.aif"]["polarity"] == -1
    assert abs(by["snare bottom.aif"]["delay_samples"] - 75) < 4
    assert all(v > 0.5 for v in res["validation"].values())

    out, _ = sf.read(str(tmp_path / "phase-aligned" / "snare top.aif"))
    assert len(out) == n          # length preserved
    # outputs keep the 24-bit AIFF source format (the alignment writer contract)
    info = sf.info(str(tmp_path / "phase-aligned" / "snare top.aif"))
    assert info.format == "AIFF" and info.subtype == "PCM_24"


def test_phase_align_room_is_polarity_only(tmp_path) -> None:
    # Room/ambience is polarity-checked but its TIMING is kept (delay stays 0 —
    # rooms are deliberately excluded from the partner/anchor alignment). A bug
    # that delayed the room would otherwise pass unnoticed. Use a room correlated
    # to the OH (delayed + inverted) so the polarity sign is deterministic.
    n = SR * 3
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    _w(tmp_path / "overheads - stereo.aif", np.column_stack([base, base]))
    _w(tmp_path / "snare top.aif", dsp.fractional_delay(base, -50))
    room = -dsp.fractional_delay(base, 400)        # delayed + polarity-flipped vs OH
    _w(tmp_path / "drum room.aif", np.column_stack([room, room]))

    kit = resolve_kit(str(tmp_path))
    res = phase_align(kit, max_lag=600, excerpt_s=2.0)
    by = {r["name"]: r for r in res["results"]}
    assert by["drum room.aif"]["delay_samples"] == 0.0        # timing kept
    assert by["drum room.aif"]["polarity"] == -1
    assert by["drum room.aif"]["note"] == "ambience (timing kept)"


def test_phase_align_shorter_close_mic(tmp_path) -> None:
    # a close mic shorter than the OH excerpt window used to crash normcorr
    n = SR * 3
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    _w(tmp_path / "overheads - stereo.aif", np.column_stack([base, base]))
    _w(tmp_path / "snare top.aif", dsp.fractional_delay(base, -50)[: n - 2000])
    kit = resolve_kit(str(tmp_path))
    res = phase_align(kit, max_lag=300, excerpt_s=5.0)   # window = full OH > mic length
    by = {r["name"]: r for r in res["results"]}
    assert abs(by["snare top.aif"]["delay_samples"] - 50) < 4


def test_phase_align_stem_shorter_than_excerpt_start_skips(tmp_path) -> None:
    # The excerpt slice is derived from the (full) overheads; a close mic shorter
    # than sl.start gives sig[sl] an EMPTY array -> a bare np.fft.rfft([]) raises
    # 'Invalid number of FFT data points (0)'. Shape the OH so the loudest window
    # starts LATE (quiet first half, loud second half), then truncate a close mic
    # to before that start: the flow must SKIP it cleanly with a warning, not crash.
    n = SR * 4
    rng = np.random.default_rng(0)
    base = rng.standard_normal(n) * 0.2
    loud = base.copy()
    loud[: n // 2] *= 0.02                       # quiet first half -> loudest window is late
    _w(tmp_path / "overheads - stereo.aif", np.column_stack([loud, loud]))
    _w(tmp_path / "snare top.aif", dsp.fractional_delay(base, -50))   # full length, aligns
    _w(tmp_path / "hi-hat.aif", base[: n // 4])  # shorter than the late excerpt start

    kit = resolve_kit(str(tmp_path))
    res = phase_align(kit, max_lag=300, excerpt_s=1.0)   # 1 s window lands in the loud half
    by = {r["name"]: r for r in res["results"]}
    # the short mic is skipped (delay kept 0) with a clear note + warning, no crash
    assert by["hi-hat.aif"]["delay_samples"] == 0.0
    assert "too short" in by["hi-hat.aif"]["note"]
    assert any("hi-hat.aif" in w and "skipped" in w for w in res["warnings"])
    # the full-length mic still aligns normally
    assert abs(by["snare top.aif"]["delay_samples"] - 50) < 4
    # the skipped stem is still written through (timing kept), readable
    out, _ = sf.read(str(tmp_path / "phase-aligned" / "hi-hat.aif"))
    assert len(out) == n // 4


def test_phase_align_lr_overhead_pair(tmp_path) -> None:
    n = SR * 3
    base = np.random.default_rng(0).standard_normal(n) * 0.2
    _w(tmp_path / "OH left.aif", base)
    _w(tmp_path / "OH right.aif", base * 0.9)        # spaced pair: kept as L/R
    _w(tmp_path / "snare top.aif", dsp.fractional_delay(base, -50))

    kit = resolve_kit(str(tmp_path))
    assert kit.overhead_mode == "lr_pair"
    res = phase_align(kit, max_lag=300, excerpt_s=2.0)
    merged = tmp_path / "phase-aligned" / "overheads-merged.aif"
    assert merged.exists()
    arr, _ = sf.read(str(merged))
    assert arr.ndim == 2 and arr.shape[1] == 2     # stereo OH written
    by = {r["name"]: r for r in res["results"]}
    assert abs(by["snare top.aif"]["delay_samples"] - 50) < 3
