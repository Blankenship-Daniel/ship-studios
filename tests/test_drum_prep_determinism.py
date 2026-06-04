"""Determinism guard for the seed-free, FFT-based drum_prep DSP (Stage 2).

``*.wav`` is gitignored, so we cannot commit a golden render. Instead:

* **Reproducibility** — the same input renders bit-for-bit identically across two
  invocations (no hidden seed / global state). Machine-independent.
* **Pinned signature** — a compact numeric fingerprint, compared with tolerance so
  cross-version BLAS/FFT float drift passes but a real numerics change trips CI.
  Regenerate ``_EXPECTED`` deliberately if the DSP is changed on purpose.

``zero_phase_eq`` is the canonical target: a real (zero-phase) magnitude curve via
rfft/irfft — deterministic by construction.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from drum_prep import dsp  # noqa: E402

SR = 48000
_CENTERS = np.array([100.0, 1000.0, 8000.0])
_GAINS = np.array([3.0, -2.0, 4.0])


def _signal():
    t = np.arange(SR) / SR
    return (np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 3000 * t)).astype(np.float64)


def test_zero_phase_eq_is_bit_reproducible() -> None:
    x = _signal()
    a = dsp.zero_phase_eq(x.copy(), SR, _CENTERS, _GAINS)
    b = dsp.zero_phase_eq(x.copy(), SR, _CENTERS, _GAINS)
    np.testing.assert_array_equal(a, b)


def test_zero_phase_eq_signature_pinned() -> None:
    out = dsp.zero_phase_eq(_signal(), SR, _CENTERS, _GAINS)
    sig = np.array(
        [
            float(out.sum()),
            float(np.abs(out).max()),
            float(out[1000, 0]),
            float(out[20000, 0]),
        ]
    )
    # Pinned 2026-06-03; regenerate intentionally if the DSP changes on purpose.
    _EXPECTED = np.array(
        [-5.8975047068088315e-12, 1.7318588841243159, -0.5799149890996891, -1.0044422251914829]
    )
    np.testing.assert_allclose(sig, _EXPECTED, rtol=1e-6, atol=1e-9)
