"""presets/vst/probe_plugin.py — the headless RENDERS/PASSTHROUGH verdict helper.

This probe is the backstop the whole ``vst-*`` skill suite and
``demo/headless-safe-titles.txt`` rest on: "loads != renders". Its
differs-from-current logic had no tests, and was comparing enum LABELS against
Pedalboard's NORMALIZED float, so it never fired.

Pure-logic tests only — ``extreme``/``same_value`` need no plugin or Pedalboard.
Loaded by path under a namespaced module name (``presets/`` is not a package).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "presets" / "vst" / "probe_plugin.py"


def _load():
    spec = importlib.util.spec_from_file_location("ship_studios_tests.probe_plugin", _SRC)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)      # deliberately NOT added to sys.modules
    except Exception as exc:              # pragma: no cover - needs the `vst` extra
        pytest.skip(f"probe_plugin needs the vst extra: {exc}", allow_module_level=True)
    return mod


probe_plugin = _load()


class FakeParam:
    """A Pedalboard-shaped discrete/enum param: only ``valid_values``."""

    def __init__(self, valid_values, raw_value=None):
        self.valid_values = list(valid_values)
        self.raw_value = raw_value


# --- same_value: the comparison that makes every differs-from-current check work ---

@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("Off", "Off", True),
        ("Off", "On", False),
        ("40.2", 40.2, True),        # enum label vs cooked float
        ("4.0", "4", True),          # formatting difference
        (" 4.0:1", "4.0:1", True),   # ratio labels differing only by spacing are the same value
        ("Off", 0.0, False),         # label vs NORMALIZED raw_value: must NOT match
        (None, "Off", False),
        ("Off", None, False),
    ],
)
def test_same_value(a, b, expected) -> None:
    assert probe_plugin.same_value(a, b) is expected


def test_same_value_strips_whitespace() -> None:
    assert probe_plugin.same_value(" 4.0:1 ", "4.0:1") is True


# --- extreme: must pick an end DIFFERENT from the param's present value ---

def test_extreme_avoids_the_current_enum_value() -> None:
    """The case the retry loop exists for: an enum whose default sits at index 0.

    Pushing vv[0] against a param already at vv[0] renders default-vs-default, reads
    delta 0, and reports a false PASSTHROUGH.
    """
    par = FakeParam(["Off", "Low", "High"])
    assert probe_plugin.extreme(par, current="Off") == "High"


def test_extreme_takes_the_first_end_when_current_differs() -> None:
    par = FakeParam(["Off", "Low", "High"])
    assert probe_plugin.extreme(par, current="High") == "Off"


def test_extreme_matches_a_numeric_current_against_string_valid_values() -> None:
    """A cooked float current ``40.2`` must be recognised as equal to label '40.2'."""
    par = FakeParam(["40.2", "39.8", "35.0"])
    assert probe_plugin.extreme(par, current=40.2) == "35.0"


def test_extreme_with_no_current_returns_the_first_end() -> None:
    par = FakeParam(["Off", "High"])
    assert probe_plugin.extreme(par, current=None) == "Off"


def test_extreme_single_valued_enum_returns_its_only_value() -> None:
    par = FakeParam(["Only"])
    assert probe_plugin.extreme(par, current="Only") == "Only"


# --- numeric (non-enum) params fall through to min/max ---

class NumParam:
    def __init__(self, min_value=None, max_value=None):
        self.valid_values = None
        self.min_value = min_value
        self.max_value = max_value


def test_extreme_numeric_prefers_min_then_max() -> None:
    assert probe_plugin.extreme(NumParam(min_value=-24.0, max_value=24.0)) == -24.0
    assert probe_plugin.extreme(NumParam(min_value=None, max_value=24.0)) == 24.0
    assert probe_plugin.extreme(NumParam()) is None


def test_extreme_numeric_ignores_non_finite_bounds() -> None:
    assert probe_plugin.extreme(NumParam(min_value=float("-inf"), max_value=6.0)) == 6.0
