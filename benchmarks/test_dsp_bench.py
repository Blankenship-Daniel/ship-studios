"""Render-time regression benchmarks for the deterministic drum_prep DSP.

OPT-IN — this directory is outside ``[tool.pytest.ini_options].testpaths`` (which
is ``["tests"]``), so the offline suite never collects it. Run explicitly:

    uv run --extra bench --extra drum-prep pytest benchmarks/

Save a baseline and fail on a regression with pytest-benchmark's own flags:

    uv run --extra bench --extra drum-prep pytest benchmarks/ --benchmark-autosave
    uv run --extra bench --extra drum-prep pytest benchmarks/ \
        --benchmark-compare=0001 --benchmark-compare-fail=mean:5%

That comparison is a LOCAL workflow, deliberately not a CI gate: a 5% wall-clock
threshold on shared CI runners is noise, not signal, and would fail at random. CI
instead RUNS this suite (the `bench` job) so the benchmarks cannot bit-rot —
compare against a saved baseline on one machine when you need the real number.

Benchmark ONLY deterministic local DSP — never the Gemini-network or the
non-deterministic VST/Pedalboard paths (their variance swamps the signal).
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from drum_prep import dsp  # noqa: E402

SR = 48000


def _signal(seconds: float = 2.0):
    t = np.arange(int(SR * seconds)) / SR
    return (np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 3000 * t)).astype(np.float64)


def test_zero_phase_eq_benchmark(benchmark) -> None:
    x = _signal()
    centers = np.array([100.0, 1000.0, 8000.0])
    gains = np.array([3.0, -2.0, 4.0])
    out = benchmark(dsp.zero_phase_eq, x, SR, centers, gains)
    assert out.shape[0] == x.shape[0]


def test_estimate_benchmark(benchmark) -> None:
    """The real per-kit hotspot: FFT cross-correlation lag estimation, run on a
    realistic 40 s @ 48 kHz window (the ``pick_excerpt`` default) against a
    known-lag delayed copy with a realistic ``max_lag``."""
    a = _signal(40.0)
    lag = 137  # a known integer lag, well inside max_lag
    b = np.roll(a, lag)
    max_lag = 4800  # 100 ms at 48 kHz — the alignment search range
    d_star, peak = benchmark(dsp.estimate, a, b, max_lag)
    assert np.isfinite(d_star) and np.isfinite(peak)
    # estimate maximizes sum a[n]b[n-d]; with b = roll(a, lag) (b[n] = a[n-lag])
    # the peak is at d = -lag, so the recovered lag is -d_star (sub-sample exact).
    assert abs(-d_star - lag) < 1.0  # recovers the planted lag to sub-sample


def test_align_to_benchmark(benchmark) -> None:
    """``align_to`` is the full per-mic alignment driver (envelope-coarse ->
    waveform-refine + polarity), the genuine per-kit cost. Benchmark it on a
    realistic 40 s @ 48 kHz target vs a known-lag delayed reference."""
    ref = _signal(40.0)
    target = np.roll(ref, 137)
    max_lag = 4800
    delay, pol, pre_corr, post_corr = benchmark(dsp.align_to, target, ref, max_lag, SR)
    assert all(np.isfinite(v) for v in (delay, pol, pre_corr, post_corr))


# NOTE: drum_prep.reference_match._measure is intentionally NOT benchmarked here:
# it takes a directory + reference path and reads WAVs off disk (io.read), so a
# benchmark would be dominated by disk I/O variance rather than the DSP. The
# array-callable DSP primitives above cover the genuine per-kit hotspot instead.
