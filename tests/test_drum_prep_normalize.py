"""normalize: global gain preserves inter-mic balance; per-file maximizes each stem."""
from __future__ import annotations

import json

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep import io  # noqa: E402
from drum_prep.cli import _json_safe  # noqa: E402
from drum_prep.normalize import normalize_kit  # noqa: E402

SR = 48000


def _w(p, x, subtype="FLOAT") -> None:
    sf.write(str(p), x, SR, subtype=subtype)


def _peak_db(path) -> float:
    y, _ = sf.read(str(path), always_2d=True)
    return 20 * np.log10(np.max(np.abs(y)))


def test_global_preserves_balance(tmp_path) -> None:
    rng = np.random.default_rng(0)
    a = (rng.standard_normal(SR) * 0.6).astype(np.float32)
    _w(tmp_path / "kick in.wav", a)
    _w(tmp_path / "snare top.wav", (a * 0.5).astype(np.float32))
    _w(tmp_path / "overhead.wav", np.column_stack([a * 0.3, a * 0.2]).astype(np.float32))

    res = normalize_kit(str(tmp_path), target_dbfs=-1.0, mode="global")
    assert res["balance_preserved"] is True
    assert res["gain_spread_db"] < 0.01
    peaks = [_peak_db(tmp_path / "normalized" / f["file"]) for f in res["files"]]
    assert abs(max(peaks) - (-1.0)) < 0.05               # loudest hits target
    assert io.subtype_of(str(tmp_path / "normalized" / "kick in.wav")) == "FLOAT"


def test_per_file_each_hits_target(tmp_path) -> None:
    rng = np.random.default_rng(1)
    a = (rng.standard_normal(SR) * 0.6).astype(np.float32)
    _w(tmp_path / "kick in.wav", a)
    _w(tmp_path / "snare top.wav", (a * 0.3).astype(np.float32))
    res = normalize_kit(str(tmp_path), target_dbfs=-1.0, mode="per_file")
    for f in res["files"]:
        assert abs(f["out_peak_dbfs"] - (-1.0)) < 0.05
    # the symmetric guardrail to test_global_preserves_balance: per_file does NOT
    # preserve the inter-mic balance (each stem gets a different gain).
    assert res["balance_preserved"] is False
    assert res["gain_spread_db"] > 0.01           # ~10 dB spread for this 0.6 vs 0.18 set


def test_json_safe_maps_non_finite_to_null() -> None:
    # The flows emit float('-inf') (silent stem -> -inf dBFS) / nan; the CLI's
    # sanitizer must turn every non-finite into JSON null so json.dumps never
    # emits the non-standard -Infinity/NaN tokens a strict parser rejects.
    raw = {"a": float("-inf"), "b": float("inf"), "c": float("nan"),
           "d": [1.0, float("-inf"), {"e": float("nan")}], "f": -1.0, "g": "ok"}
    safe = _json_safe(raw)
    assert safe["a"] is None and safe["b"] is None and safe["c"] is None
    assert safe["d"] == [1.0, None, {"e": None}]
    assert safe["f"] == -1.0 and safe["g"] == "ok"
    s = json.dumps(safe, allow_nan=False)        # backstop: must not raise
    assert "Infinity" not in s and "NaN" not in s
    assert json.loads(s)["a"] is None            # round-trips through a strict parser


def test_silent_kit_serializes_to_null(tmp_path) -> None:
    # A fully silent stem gives -inf dBFS rows; the sanitized result must serialize
    # cleanly (no -Infinity token) and round-trip.
    _w(tmp_path / "dead.wav", np.zeros(SR, dtype=np.float32))
    _w(tmp_path / "live.wav", (np.random.default_rng(0).standard_normal(SR) * 0.5)
       .astype(np.float32))
    res = normalize_kit(str(tmp_path), target_dbfs=-1.0, mode="per_file")
    s = json.dumps(_json_safe(res), allow_nan=False)   # backstop on real flow output
    parsed = json.loads(s)
    dead = next(r for r in parsed["files"] if r["file"] == "dead.wav")
    assert dead["in_peak_dbfs"] is None                # -inf dBFS -> null, not "-Infinity"
