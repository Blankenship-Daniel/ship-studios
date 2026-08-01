"""sub-design: an envelope-followed sine sub adds low-end under a kick."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep.sub_design import add_sub, estimate_fundamental  # noqa: E402

SR = 48000


def _kick(n_hits=4, f0=70.0):
    """A few decaying f0 sine bursts — a usable synthetic kick."""
    sig = np.zeros(SR * 2)
    for h in range(n_hits):
        s = int(h * 0.5 * SR)
        tt = np.arange(SR // 2) / SR
        sig[s:s + len(tt)] += np.exp(-30 * tt) * np.sin(2 * np.pi * f0 * tt)
    return (0.6 * sig / (np.abs(sig).max() + 1e-9)).astype(np.float32)


def test_estimate_fundamental_near_70(tmp_path) -> None:
    assert abs(estimate_fundamental(_kick(f0=70.0).astype(np.float64), SR) - 70.0) < 6.0


def test_add_sub_increases_low_end(tmp_path) -> None:
    src = tmp_path / "kick.wav"
    sf.write(str(src), _kick(), SR, subtype="FLOAT")
    out = tmp_path / "kick_sub.wav"
    res = add_sub(str(src), str(out), amount_db=-3.0)
    assert res["low_60_gain_db"] > 0.5                       # measurably more sub
    assert 30.0 <= res["sub_hz"] <= 80.0
    # full return-dict contract: flow tag, the gain/trim it applied, and the
    # before/after low-band measurements it reports.
    assert res["flow"] == "sub-design"
    assert res["amount_db"] == -3.0
    assert isinstance(res["sub_gain_db"], float)
    assert isinstance(res["anti_clip_trim_db"], float)
    assert res["low_60_after_db"] > res["low_60_before_db"]
    y, _ = sf.read(str(out), always_2d=True)
    assert np.max(np.abs(y)) <= 10 ** (-1.0 / 20.0) + 1e-3   # anti-clipped


def test_add_sub_honors_sub_hz_override(tmp_path) -> None:
    # An explicit sub_hz must win over the estimated fundamental.
    src = tmp_path / "kick.wav"
    sf.write(str(src), _kick(f0=70.0), SR, subtype="FLOAT")
    out = tmp_path / "kick_sub.wav"
    res = add_sub(str(src), str(out), sub_hz=50.0, amount_db=-3.0)
    assert res["sub_hz"] == 50.0


@pytest.mark.parametrize("kick_phase", [0.0, np.pi, np.pi / 2, 3 * np.pi / 4])
def test_sub_reinforces_regardless_of_the_kicks_phase(tmp_path, kick_phase) -> None:
    """The sub must ADD low end whatever phase the kick's fundamental starts at.

    The sub used to be free-running (phase 0 at t=0) with no relationship to the
    kick, so at the default — sub_hz ON the kick's own fundamental — the relative
    phase decided the outcome: measured +4.62 dB at one kick phase and **-10.05 dB**
    at anti-phase, i.e. the "reinforcement" removed 10 dB of low end. Nothing warned;
    `low_60_gain_db` was computed and reported but never checked.
    """
    sr = 48000
    t = np.arange(int(sr * 0.4)) / sr
    kick = np.sin(2 * np.pi * 55 * t + kick_phase) * np.exp(-t * 9) * 0.7
    src = tmp_path / "kick.wav"
    sf.write(str(src), np.column_stack([kick, kick]), sr)

    res = add_sub(str(src), str(tmp_path / "out.wav"), sub_hz=55.0)
    assert res["low_60_gain_db"] > 2.0, res


def test_sub_reports_a_fundamental_above_the_sub_range(tmp_path) -> None:
    """A 100 Hz kick silently got an 80 Hz sub — a detuned, beating layer.

    ``estimate_fundamental`` searched [30, 120] while the caller clamped to [30, 80],
    so the two disagreed with no signal to the operator.
    """
    sr = 48000
    t = np.arange(int(sr * 0.4)) / sr
    kick = np.sin(2 * np.pi * 100 * t) * np.exp(-t * 9) * 0.7
    src = tmp_path / "kick100.wav"
    sf.write(str(src), np.column_stack([kick, kick]), sr)

    res = add_sub(str(src), str(tmp_path / "out100.wav"))
    assert res["notes"], "a clamped fundamental must be reported"
    assert "100" in " ".join(res["notes"]) or "sub range" in " ".join(res["notes"])
