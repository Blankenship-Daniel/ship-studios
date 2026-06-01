"""Mic-role taxonomy + filename auto-detection.

Pure stdlib (no numpy) so ``drum-prep detect`` works before the DSP extra is
installed. Detection is heuristic on the normalized filename; a committed
``kit.json`` (see :mod:`drum_prep.kit`) overrides anything it gets wrong.
"""
from __future__ import annotations

import re
from enum import Enum


class Role(str, Enum):  # noqa: UP042 - keep (str, Enum); StrEnum.__str__ differs (value vs "Role.X")
    OVERHEAD = "overhead"          # pre-merged stereo OH (the fixed reference)
    OVERHEAD_L = "overhead_l"      # mono OH left  (merged with R before use)
    OVERHEAD_R = "overhead_r"      # mono OH right
    ROOM = "room"                  # ambience: polarity-checked, timing kept
    KICK_IN = "kick_in"            # inside / main kick (anchors to OH, low-pass)
    KICK_BEATER = "kick_beater"    # batter-side click (partners to kick_in)
    KICK_OUT = "kick_out"          # front/resonant kick
    KICK_SUB = "kick_sub"          # sub mic
    SNARE_TOP = "snare_top"        # broadband snare anchor (-> OH)
    SNARE_BOTTOM = "snare_bottom"  # wires (partners to snare_top)
    HIHAT = "hihat"
    RIDE = "ride"
    CRASH = "crash"
    TOM = "tom"                    # generic; multiples disambiguated by label
    FX = "fx"                      # effect return/aux (plate/reverb/send) — NOT a mic
    UNKNOWN = "unknown"


def _norm(filename: str) -> str:
    base = filename.rsplit(".", 1)[0].lower()
    base = re.sub(r"[._\-]+", " ", base)
    return re.sub(r"\s+", " ", base).strip()


def detect_role(filename: str) -> tuple[Role, float]:
    """Return ``(Role, confidence)``. Confidence: 1.0 exact keyword, 0.6 weak,
    0.0 when nothing matched (``UNKNOWN``)."""
    base = _norm(filename)
    tok = set(base.split())

    def has_tok(*ws: str) -> bool:
        return any(w in tok for w in ws)

    def has_sub(*ws: str) -> bool:
        return any(w in base for w in ws)

    # effect returns FIRST — a "snare plate"/"reverb"/"send" is an aux, not a mic.
    # Checked before kick/snare so "snare plate" -> FX (not a 2nd snare_top that
    # would steal snare_bottom's partner link and get phase-aligned to noise).
    if (has_tok("fx", "aux", "verb", "plate", "send", "return", "echo", "delay")
            or has_sub("reverb", "plate", " fx", "aux", "effect")):
        return Role.FX, 1.0

    # overheads (check L/R / stereo qualifiers)
    if has_tok("oh", "ohs") or has_sub("overhead", "over head"):
        conf = 1.0 if has_tok("oh", "ohs") or "overhead" in base else 0.6
        if has_sub("stereo"):
            return Role.OVERHEAD, conf
        if has_tok("l", "left") or base.endswith(" l"):
            return Role.OVERHEAD_L, conf
        if has_tok("r", "right") or base.endswith(" r"):
            return Role.OVERHEAD_R, conf
        return Role.OVERHEAD, conf

    if has_tok("room", "amb", "ambience", "far") or has_sub("room", "ambience"):
        return Role.ROOM, 1.0 if has_tok("room", "amb", "ambience") else 0.6

    if has_tok("kick", "kik", "bd") or has_sub("kick", "bass drum"):
        conf = 1.0 if has_tok("kick", "kik", "bd") or "kick" in base else 0.6
        if has_tok("beater", "batter") or has_sub("beater", "batter"):
            return Role.KICK_BEATER, conf
        if has_tok("out", "outside", "front", "reso") or has_sub("outside", "front"):
            return Role.KICK_OUT, conf
        if has_tok("sub"):
            return Role.KICK_SUB, conf
        return Role.KICK_IN, conf  # explicit 'in'/'inside' and bare 'kick'

    if has_tok("snare", "sn", "snr") or has_sub("snare"):
        conf = 1.0 if has_tok("snare") or "snare" in base else 0.6
        if has_tok("bottom", "bot", "btm", "under", "wire", "wires") or has_sub("bottom", "under"):
            return Role.SNARE_BOTTOM, conf
        return Role.SNARE_TOP, conf

    if has_tok("hihat", "hat", "hats", "hh") or has_sub("hi-hat", "hihat", "hi hat"):
        return Role.HIHAT, 1.0 if has_tok("hihat", "hat", "hats", "hh") or has_sub("hihat", "hi hat") else 0.6

    if has_tok("ride") or has_sub("ride"):
        return Role.RIDE, 1.0 if has_tok("ride") else 0.6
    if has_tok("crash") or has_sub("crash"):
        return Role.CRASH, 1.0 if has_tok("crash") else 0.6
    if has_tok("tom", "toms", "rack", "floor", "ft") or has_sub("tom"):
        return Role.TOM, 1.0 if has_tok("tom", "toms") or "tom" in base else 0.6

    return Role.UNKNOWN, 0.0


def detect_roles(filenames: list[str]) -> dict[str, tuple[Role, float]]:
    return {f: detect_role(f) for f in filenames}
