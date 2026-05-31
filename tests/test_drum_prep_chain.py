"""End-to-end chain: stages run in order and populate the output dirs."""
from __future__ import annotations

import os

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
sf = pytest.importorskip("soundfile")
pytest.importorskip("pyloudnorm")

from drum_prep import dsp  # noqa: E402
from drum_prep.chain import run_chain  # noqa: E402
from tests.drumkit_synth import write  # noqa: E402

SR = 48000


def test_chain_end_to_end(tmp_path) -> None:
    n = SR * 14
    rng = np.random.default_rng(0)
    base = rng.standard_normal(n) * 0.2

    def w(name, sig):
        write(tmp_path / name, sig, SR)

    w("overheads - stereo.aif", np.column_stack([base, base]))
    for name, lead in [("snare top.aif", 90), ("hi-hat.aif", 63), ("kick in.aif", 144)]:
        w(name, dsp.fractional_delay(base, -lead))
    w("snare bottom.aif", -dsp.fractional_delay(base, -75))
    w("kick beater.aif", dsp.fractional_delay(base, -212))
    w("drum room.aif", np.column_stack([rng.standard_normal(n) * 0.1] * 2))
    ref = dsp.lowpass(rng.standard_normal(n), 4000.0, SR)  # darker reference
    refp = tmp_path / "ref.wav"
    w("ref.wav", np.column_stack([ref, ref]))

    res = run_chain(str(tmp_path), str(refp), max_lag=400, excerpt_s=2.0, t0=0.0, dur=12.0)
    assert [s["flow"] for s in res["stages"]] == ["phase-align", "reference-match", "audition"]
    assert os.path.isdir(tmp_path / "phase-aligned")
    assert os.path.isdir(tmp_path / "ref-matched")
    assert (tmp_path / "auditions" / "AB_before-vs-after.wav").exists()
