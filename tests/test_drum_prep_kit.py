"""Kit detection, manifest overlay, and validation (stdlib — no extra needed)."""
from __future__ import annotations

import json

import pytest

from drum_prep.kit import (
    KitError, ambience_stems, anchored_to_oh, detect_kit, overhead_reference,
    partner_pairs, resolve_kit,
)
from drum_prep.roles import Role

_FULL = ["overheads - stereo.aif", "drum room.aif", "kick in.aif", "kick beater.aif",
         "snare top.aif", "snare bottom.aif", "hi-hat.aif"]


def _make(tmp_path, names):
    for n in names:
        (tmp_path / n).write_bytes(b"")  # detection is filename-only
    return str(tmp_path)


def test_detect_topology(tmp_path) -> None:
    kit = detect_kit(_make(tmp_path, _FULL))
    assert overhead_reference(kit).role == Role.OVERHEAD
    pairs = {(p.name, a.name) for p, a in partner_pairs(kit)}
    assert ("snare bottom.aif", "snare top.aif") in pairs
    assert ("kick beater.aif", "kick in.aif") in pairs
    assert any(s.name == "drum room.aif" for s in ambience_stems(kit))
    anchors = {s.name for s in anchored_to_oh(kit)}
    assert {"snare top.aif", "kick in.aif", "hi-hat.aif"} <= anchors
    assert "snare bottom.aif" not in anchors  # has a partner


def test_manifest_overrides_detection(tmp_path) -> None:
    src = _make(tmp_path, ["weird.aif", "overheads - stereo.aif"])
    (tmp_path / "kit.json").write_text(json.dumps({"stems": [{"file": "weird.aif", "role": "snare_top"}]}))
    kit = resolve_kit(src)
    assert kit.by_name("weird.aif").role == Role.SNARE_TOP


def test_missing_overhead_fails_strict(tmp_path) -> None:
    with pytest.raises(KitError):
        resolve_kit(_make(tmp_path, ["kick in.aif", "snare top.aif"]), strict=True)


def test_unknown_warns_nonstrict(tmp_path) -> None:
    kit = resolve_kit(_make(tmp_path, ["overheads - stereo.aif", "weird.aif"]), strict=False)
    assert any("weird.aif" in w for w in kit.warnings)


def test_manifest_missing_file_errors(tmp_path) -> None:
    src = _make(tmp_path, ["overheads - stereo.aif"])
    (tmp_path / "kit.json").write_text(json.dumps({"stems": [{"file": "nope.aif", "role": "kick_in"}]}))
    with pytest.raises(KitError):
        resolve_kit(src)


def test_manifest_role_fix_rewires_partner(tmp_path) -> None:
    # snare-top mis-detected (UNKNOWN); manifest fixes it -> snare-bottom must re-wire to it
    src = _make(tmp_path, ["overheads - stereo.aif", "weird.aif", "snare bottom.aif"])
    (tmp_path / "kit.json").write_text(json.dumps({"stems": [{"file": "weird.aif", "role": "snare_top"}]}))
    kit = resolve_kit(src)
    pairs = {(p.name, a.name) for p, a in partner_pairs(kit)}
    assert ("snare bottom.aif", "weird.aif") in pairs


def test_overhead_mode_recomputed_after_manifest(tmp_path) -> None:
    src = _make(tmp_path, ["L.aif", "R.aif"])  # both UNKNOWN by filename
    (tmp_path / "kit.json").write_text(json.dumps({"stems": [
        {"file": "L.aif", "role": "overhead_l"}, {"file": "R.aif", "role": "overhead_r"}]}))
    kit = resolve_kit(src)
    assert kit.overhead_mode == "lr_pair"


def test_duplicate_singleton_fails_strict(tmp_path) -> None:
    # both "snare.aif" and "snare top.aif" resolve to SNARE_TOP
    src = _make(tmp_path, ["overheads - stereo.aif", "snare.aif", "snare top.aif"])
    with pytest.raises(KitError):
        resolve_kit(src, strict=True)
