"""Filename role auto-detection (pure stdlib — runs without the drum-prep extra)."""
from __future__ import annotations

from drum_prep.roles import Role, detect_role


def test_basic_role_mapping() -> None:
    cases = {
        "kick in.aif": Role.KICK_IN,
        "kick beater.aif": Role.KICK_BEATER,
        "snare top.aif": Role.SNARE_TOP,
        "snare bottom.aif": Role.SNARE_BOTTOM,
        "snare.aif": Role.SNARE_TOP,
        "hi-hat.aif": Role.HIHAT,
        "overheads - stereo.aif": Role.OVERHEAD,
        "OH L.aif": Role.OVERHEAD_L,
        "oh right.aif": Role.OVERHEAD_R,
        "drum room.aif": Role.ROOM,
        "tom floor.aif": Role.TOM,
        "ride.wav": Role.RIDE,
        "crash.wav": Role.CRASH,
        "weird mic.aif": Role.UNKNOWN,
    }
    for filename, role in cases.items():
        assert detect_role(filename)[0] == role, filename


def test_fx_returns_detected() -> None:
    # effect returns are FX, not mics — checked before kick/snare so "snare plate"
    # does not become a second snare_top (the bug that stole snare_bottom's partner).
    for filename in ("snare plate.aif", "snare plate - left.wav", "drum reverb.wav",
                     "fx return.wav", "snare send.wav", "verb.aif"):
        assert detect_role(filename)[0] == Role.FX, filename
    assert detect_role("snare top.aif")[0] == Role.SNARE_TOP  # a real mic stays a mic


def test_confidence_ordering() -> None:
    assert detect_role("snare top.aif")[1] == 1.0       # exact keyword
    assert detect_role("weird mic.aif")[1] == 0.0       # no match
    # weak substring match scores below an exact keyword
    role, conf = detect_role("over head.aif")
    assert role == Role.OVERHEAD and conf == 0.6
