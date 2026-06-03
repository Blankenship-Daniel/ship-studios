"""Kit detection, manifest overlay, and validation (stdlib — no extra needed)."""
from __future__ import annotations

import json

import pytest

from drum_prep.kit import (
    KitError,
    ambience_stems,
    anchored_to_oh,
    detect_kit,
    overhead_reference,
    partner_pairs,
    resolve_kit,
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


def test_fx_with_partner_excluded_and_flagged(tmp_path) -> None:
    # An FX/return (plate/reverb/send) given a partner in kit.json must NOT enter
    # partner_pairs — aligning it would corrupt the return — and must be flagged by
    # validation, the same rule as ambience/room. (FX is excluded from anchored_to_oh
    # but used to slip into partner_pairs.)
    src = _make(tmp_path, ["overheads - stereo.aif", "snare top.aif", "snare plate.aif"])
    (tmp_path / "kit.json").write_text(json.dumps(
        {"stems": [{"file": "snare plate.aif", "role": "fx", "partner": "snare top.aif"}]}))
    kit = resolve_kit(src, strict=False)
    assert kit.by_name("snare plate.aif").role == Role.FX
    assert not any(p.role == Role.FX for p, _ in partner_pairs(kit))
    assert ("snare plate.aif", "snare top.aif") not in {(p.name, a.name) for p, a in partner_pairs(kit)}
    assert any("snare plate.aif" in w and "partner" in w for w in kit.warnings)


def test_fx_with_partner_fails_strict(tmp_path) -> None:
    src = _make(tmp_path, ["overheads - stereo.aif", "snare top.aif", "snare plate.aif"])
    (tmp_path / "kit.json").write_text(json.dumps(
        {"stems": [{"file": "snare plate.aif", "role": "fx", "partner": "snare top.aif"}]}))
    with pytest.raises(KitError, match="partner"):
        resolve_kit(src, strict=True)


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


def test_manifest_entry_missing_file_key_is_kit_error(tmp_path) -> None:
    src = _make(tmp_path, ["overheads - stereo.aif"])
    (tmp_path / "kit.json").write_text(json.dumps({"stems": [{"role": "kick_in"}]}))
    with pytest.raises(KitError, match="required 'file'"):
        resolve_kit(src)


def test_manifest_unknown_role_is_kit_error(tmp_path) -> None:
    src = _make(tmp_path, ["overheads - stereo.aif", "x.aif"])
    (tmp_path / "kit.json").write_text(json.dumps({"stems": [{"file": "x.aif", "role": "bongo"}]}))
    with pytest.raises(KitError, match="unknown role"):
        resolve_kit(src)


def test_manifest_bad_field_types_are_kit_errors(tmp_path) -> None:
    src = _make(tmp_path, ["overheads - stereo.aif", "k.aif"])
    (tmp_path / "kit.json").write_text(json.dumps(
        {"stems": [{"file": "k.aif", "role": "kick_in", "lowpass_hz": "loud"}]}))
    with pytest.raises(KitError, match="lowpass_hz"):
        resolve_kit(src)
    (tmp_path / "kit.json").write_text(json.dumps(
        {"stems": [{"file": "k.aif", "role": "kick_in", "polarity_lock": 2}]}))
    with pytest.raises(KitError, match="polarity_lock"):
        resolve_kit(src)
    # a float 1.0 must NOT slip through the polarity_lock check (1.0 == 1 under `in`)
    (tmp_path / "kit.json").write_text(json.dumps(
        {"stems": [{"file": "k.aif", "role": "kick_in", "polarity_lock": 1.0}]}))
    with pytest.raises(KitError, match="polarity_lock"):
        resolve_kit(src)
    # ambience must be a bool, not a truthy string/int
    (tmp_path / "kit.json").write_text(json.dumps(
        {"stems": [{"file": "k.aif", "role": "kick_in", "ambience": "yes"}]}))
    with pytest.raises(KitError, match="ambience"):
        resolve_kit(src)


def test_manifest_accepts_valid_optional_fields(tmp_path) -> None:
    src = _make(tmp_path, ["overheads - stereo.aif", "k.aif"])
    (tmp_path / "kit.json").write_text(json.dumps(
        {"stems": [{"file": "k.aif", "role": "kick_in",
                    "lowpass_hz": 80, "polarity_lock": -1, "ambience": False}]}))
    kit = resolve_kit(src)
    ks = kit.by_name("k.aif")
    assert ks.lowpass_hz == 80 and ks.polarity_lock == -1 and ks.ambience is False
