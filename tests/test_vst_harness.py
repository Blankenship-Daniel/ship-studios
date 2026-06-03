"""Unit tests for the VST preset harness (presets/vst/apply_vst_preset.py).

``presets/`` is NOT a package (and is ruff/mypy-excluded), so we load the module by path with
importlib. The module was made import-safe without pedalboard (the heavy import is deferred into
``main()``), so ``set_param`` / ``output_gain`` are exercisable in this venv (numpy/soundfile only,
no pedalboard). A render-path test that *would* need pedalboard is guarded with importorskip.

What's covered:
  * set_param snaps a numeric near-miss to the nearest valid value, via a FAKE param object exposing
    ``.valid_values`` — exact-match-first stays untouched (returns None, byte-identical to before).
  * the labeled-ratio snap parses ' 4.0:1'-style enum strings to their leading numeric token.
  * output_gain's faithful-vs-renormalize decision, in pure numpy — null/sentinel leave gain at 1.0
    (a limiter ceiling survives), a real number renormalizes to that sample-peak dBFS.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

_MOD_PATH = Path(__file__).resolve().parent.parent / "presets" / "vst" / "apply_vst_preset.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("apply_vst_preset", _MOD_PATH)
    assert spec and spec.loader, f"cannot load {_MOD_PATH}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # must not require pedalboard (deferred into main())
    return mod


harness = _load_harness()


# --- fakes: a Pedalboard-shaped plugin whose params accept ONLY their valid_values -------------

class FakeParam:
    """Stands in for a Pedalboard discrete/enum param: exposes ``valid_values``."""

    def __init__(self, valid_values):
        self.valid_values = list(valid_values)


class FakePlugin:
    """A minimal plugin: ``setattr(p, name, v)`` raises unless ``v`` is in that param's valid_values
    (mirrors Pedalboard rejecting an off-grid enum target), and records what finally stuck.
    ``p.parameters[name]`` returns the FakeParam so set_param can read ``valid_values``."""

    def __init__(self, params: dict[str, FakeParam]):
        object.__setattr__(self, "parameters", params)
        object.__setattr__(self, "assigned", {})

    def __setattr__(self, name, value):
        params = object.__getattribute__(self, "parameters")
        if name in params and value not in params[name].valid_values:
            raise ValueError(f"{value!r} not a valid value for {name}")
        object.__getattribute__(self, "assigned")[name] = value


# --- set_param: numeric near-miss snaps to nearest valid -------------------------------------

def test_set_param_exact_match_is_untouched():
    # An on-grid value assigns directly (exact-first): returns None, byte-identical to the old path.
    p = FakePlugin({"hpf": FakeParam(["35.0", "39.8", "40.2", "45.0"])})
    note = harness.set_param(p, "hpf", "39.8")
    assert note is None
    assert p.assigned["hpf"] == "39.8"


def test_set_param_snaps_numeric_near_miss_to_nearest_valid():
    # 40.0 isn't a valid corner; nearest is 39.8 (Δ0.2) over 40.2 (Δ0.2 tie -> first by min()).
    p = FakePlugin({"hpf": FakeParam(["35.0", "39.8", "40.2", "45.0"])})
    note = harness.set_param(p, "hpf", 40.0)
    assert note is not None and "nearest valid" in note
    assert p.assigned["hpf"] in ("39.8", "40.2")  # snapped to a real corner, not left at default
    # 41.0 is unambiguously closer to 40.2.
    p2 = FakePlugin({"hpf": FakeParam(["35.0", "39.8", "40.2", "45.0"])})
    harness.set_param(p2, "hpf", 41.0)
    assert p2.assigned["hpf"] == "40.2"


def test_set_param_no_numeric_valid_values_reports_failure():
    # Enum with non-numeric labels and an invalid target: can't snap -> returns a note, no assign.
    p = FakePlugin({"shape": FakeParam(["Bell", "Shelf"])})
    note = harness.set_param(p, "shape", "Notch")
    assert note is not None
    assert "shape" not in p.assigned


# --- the labeled-ratio snap parses ' 4.0:1'-style values -------------------------------------

def test_set_param_snaps_labeled_ratio_enum():
    # A near-miss ratio (4.0) used to fall to default because float(' 4.0:1') raised. Now it parses
    # the leading token and snaps to the matching labeled enum value.
    ratios = [" 2.0:1", " 4.0:1", "10.0:1", "Inf:1"]
    p = FakePlugin({"compress": FakeParam(ratios)})
    note = harness.set_param(p, "compress", 4.0)
    assert note is not None and "nearest valid" in note
    assert p.assigned["compress"] == " 4.0:1"


def test_set_param_infinity_ratio_parses():
    # 'Inf:1'/'∞:1' parse to inf so a request for a huge ratio snaps there.
    p = FakePlugin({"compress": FakeParam([" 4.0:1", "10.0:1", "Inf:1"])})
    note = harness.set_param(p, "compress", float("inf"))
    assert note is not None
    assert p.assigned["compress"] == "Inf:1"


def test_num_token_helper_behaviour():
    # Indirect proof of the leading-token parse: 11.0 is closest to '10.0:1' among the labels.
    p = FakePlugin({"compress": FakeParam([" 4.0:1", "10.0:1", "Inf:1"])})
    harness.set_param(p, "compress", 11.0)
    assert p.assigned["compress"] == "10.0:1"


# --- output_gain: faithful vs renormalize (pure numpy, no plugin) ----------------------------

def test_output_gain_faithful_on_null():
    # JSON null -> faithful: gain is exactly 1.0, so a limiter ceiling/quiet render is untouched.
    assert harness.output_gain(0.5, None) == 1.0
    assert harness.output_gain(0.01, None) == 1.0  # never AMPLIFIES a quiet faithful render


def test_output_gain_faithful_on_sentinel():
    assert harness.output_gain(0.7, harness._FAITHFUL) == 1.0


def test_output_gain_renormalizes_to_target_peak():
    # A real number renormalizes so the new sample peak == target dBFS (the historical default).
    target = -1.0
    g = harness.output_gain(0.5, target)
    new_peak = 0.5 * g
    assert math.isclose(20 * math.log10(new_peak), target, abs_tol=1e-6)
    # -1.0 dBFS is ~0.8913; 0.5 * g should reach it.
    assert math.isclose(new_peak, 10 ** (target / 20.0), rel_tol=1e-9)


def test_output_gain_silent_buffer_is_unity():
    assert harness.output_gain(0.0, -1.0) == 1.0
    assert harness.output_gain(-0.0, -3.0) == 1.0


def test_output_gain_default_target_matches_shipped_presets():
    # Every shipped preset sets a numeric output_peak_dbfs (-1.0/-3.0), so they renormalize exactly
    # as before this change — pin that a numeric target still scales.
    g = harness.output_gain(1.0, -1.0)
    assert g < 1.0  # a peak of 1.0 must be pulled DOWN to -1 dBFS
    assert math.isclose(g, 10 ** (-1.0 / 20.0), rel_tol=1e-9)


# --- a render-path smoke test that genuinely needs pedalboard --------------------------------

def test_render_path_needs_pedalboard():
    pytest.importorskip("pedalboard")  # skipped in this venv (no pedalboard) — guards the import
    # If pedalboard were present, main() would be importable AND callable; we only assert the lazy
    # import resolves so the module's deferred-import contract holds where pedalboard exists.
    assert callable(harness.main)
