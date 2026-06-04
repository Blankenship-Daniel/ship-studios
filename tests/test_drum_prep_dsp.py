"""Numeric core: delay recovery, polarity, partner composition, zero-phase EQ."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from drum_prep import dsp  # noqa: E402
from tests.drumkit_synth import colored_noise  # noqa: E402

SR = 48000


def test_fractional_delay_and_estimate() -> None:
    n = SR
    x = np.random.default_rng(0).standard_normal(n)
    y = dsp.fractional_delay(x, 13.0)               # y lags x by 13
    d, peak = dsp.estimate(y, x, 100)
    assert abs(d - 13.0) < 0.1 and peak > 0


def test_estimate_clamps_short_segment_without_crashing() -> None:
    # n <= max_lag would, unclamped, wrap the circular correlation into a corrupt
    # out-of-range lag (or IndexError). The clamp must instead return a finite
    # value bounded by the available correlation range — no crash, no garbage.
    x = np.random.default_rng(0).standard_normal(64)
    y = dsp.fractional_delay(x, 5.0)
    d, peak = dsp.estimate(y, x, 500)          # max_lag (500) >> segment (64)
    nfft = 1 << int(np.ceil(np.log2(2 * len(x))))
    assert np.isfinite(d) and np.isfinite(peak)
    assert abs(d) <= nfft                      # within the clamped range, not wrapped garbage


def test_estimate_empty_arrays_return_zero_without_overflow() -> None:
    # n == 0 hits log2(0) -> int(ceil(-inf)) -> OverflowError. Both-empty inputs
    # must degrade to (0.0, 0.0): stereo_merge/overheads call align_to (-> estimate)
    # without an explicit non-empty guard of their own.
    d, peak = dsp.estimate(np.array([]), np.array([]), 100)
    assert (d, peak) == (0.0, 0.0)


def test_align_recovers_delay_and_polarity() -> None:
    n = SR
    ref = np.random.default_rng(1).standard_normal(n)
    mic = -dsp.fractional_delay(ref, 20.0)          # inverted + lagging by 20
    d, pol, _, post = dsp.align_to(mic, ref, 200, SR)
    assert pol == -1.0
    aligned = dsp.fractional_delay(mic, d) * pol
    assert dsp.normcorr(aligned, ref) > 0.99


def test_partner_composition() -> None:
    n = SR
    ref = np.random.default_rng(2).standard_normal(n)
    anchor = dsp.fractional_delay(ref, 15.0)
    partner = -dsp.fractional_delay(anchor, 7.0)     # inverted, vs anchor
    d_an, pol_an, _, _ = dsp.align_to(anchor, ref, 200, SR)
    d_pa, pol_pa, _, _ = dsp.align_to(partner, anchor, 200, SR)
    aligned = dsp.fractional_delay(partner, d_pa + d_an) * (pol_pa * pol_an)
    assert dsp.normcorr(aligned, ref) > 0.98


def test_zero_phase_eq_preserves_lag() -> None:
    n = SR
    a = np.random.default_rng(3).standard_normal(n)
    b = dsp.fractional_delay(a, 9.0)
    d0, _ = dsp.estimate(b, a, 100)
    g = np.full(len(dsp.THIRD_OCT), -3.0)            # broad cut
    ae = dsp.zero_phase_eq(a, SR, dsp.THIRD_OCT, g)[:, 0]
    be = dsp.zero_phase_eq(b, SR, dsp.THIRD_OCT, g)[:, 0]
    d1, _ = dsp.estimate(be, ae, 100)
    assert abs(d1 - d0) < 0.5


def test_zero_phase_eq_sloped_curve_preserves_lag() -> None:
    # A FLAT gain can't catch a phase-corrupting curve — a non-symmetric (complex)
    # filter would shift the lag MORE where it boosts than where it cuts. Use a
    # sloped/notched curve (+6 dB lows, a -6 dB mid notch, -6 dB highs) and assert
    # the recovered lag survives unchanged: the only way that holds is a real,
    # zero-phase magnitude curve.
    n = SR
    a = np.random.default_rng(11).standard_normal(n)
    b = dsp.fractional_delay(a, 9.0)
    d0, _ = dsp.estimate(b, a, 100)
    centers = dsp.THIRD_OCT
    g = np.where(centers < 200, 6.0, np.where(centers > 4000, -6.0, 0.0))
    g[np.argmin(np.abs(centers - 1000))] = -6.0      # add a 1 kHz notch
    ae = dsp.zero_phase_eq(a, SR, centers, g)[:, 0]
    be = dsp.zero_phase_eq(b, SR, centers, g)[:, 0]
    d1, _ = dsp.estimate(be, ae, 100)
    assert abs(d1 - d0) < 0.5


def test_estimate_declines_when_window_outside_search_range() -> None:
    # halfwidth window wholly outside [-max_lag, max_lag] used to return a bogus
    # lag (idx 0 == -max_lag) with a misleading peak. The guard must decline with
    # a clean zero lag / zero peak instead.
    x = np.random.default_rng(0).standard_normal(SR)
    y = dsp.fractional_delay(x, 5.0)
    d, peak = dsp.estimate(y, x, 100, center=10_000, halfwidth=10)   # center >> max_lag
    assert d == 0.0 and peak == 0.0


def test_pick_excerpt_nonpositive_seconds_falls_back() -> None:
    # seconds<=0 -> win<=0; csum[:-0] is empty (argmax crash) / negative win is a
    # bogus reversed slice. The guard returns the whole signal instead.
    ref = np.random.default_rng(0).standard_normal(SR)
    for sec in (0.0, -1.0):
        sl = dsp.pick_excerpt(ref, SR, sec)
        assert sl == slice(0, len(ref))


def _measured_tilt(y: np.ndarray) -> float:
    f, p = dsp.psd(y, SR)
    return dsp.tilt(dsp.band_db(f, p, dsp.THIRD_OCT), dsp.THIRD_OCT)


def test_tilt_tracks_relative_difference() -> None:
    # Constant-Q band power adds a fixed +3 dB/oct baseline (band width grows with
    # frequency); it cancels in a ref-vs-kit difference, which is what the match
    # uses. So assert the tilt DIFFERENCE matches the applied amplitude-tilt gap.
    n = SR * 4
    t_dark = _measured_tilt(colored_noise(SR, n, -6.0, seed=5))
    t_bright = _measured_tilt(colored_noise(SR, n, 0.0, seed=5))
    assert abs((t_dark - t_bright) - (-6.0)) < 1.0
    assert t_dark < t_bright


def test_tilt_rejects_nonpositive_centers() -> None:
    # A 0 Hz center -> log2(0) -> polyfit "SVD did not converge". Reject it clearly.
    db = np.array([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="positive frequencies"):
        dsp.tilt(db, np.array([0.0, 1000.0, 2000.0]))
    # a valid positive-frequency call still works.
    assert np.isfinite(dsp.tilt(db, np.array([250.0, 1000.0, 4000.0])))
