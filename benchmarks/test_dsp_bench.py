"""Render-time regression benchmarks for the deterministic drum_prep DSP.

OPT-IN — this directory is outside ``[tool.pytest.ini_options].testpaths`` (which
is ``["tests"]``), so the offline suite never collects it. Run explicitly:

    uv run --extra bench --extra drum-prep pytest benchmarks/

Save a baseline and fail CI on a regression with pytest-benchmark's own flags:

    uv run --extra bench --extra drum-prep pytest benchmarks/ --benchmark-autosave
    uv run --extra bench --extra drum-prep pytest benchmarks/ \
        --benchmark-compare=0001 --benchmark-compare-fail=mean:5%

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
