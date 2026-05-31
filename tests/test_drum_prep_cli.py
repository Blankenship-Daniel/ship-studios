"""CLI: detect output + option parsing (flow funcs stubbed to avoid heavy DSP)."""
from __future__ import annotations

import json

import pytest

np = pytest.importorskip("numpy")  # phase-align/chain handlers import DSP modules

from click.testing import CliRunner  # noqa: E402

from drum_prep.cli import main  # noqa: E402

_FULL = ["overheads - stereo.aif", "drum room.aif", "kick in.aif", "kick beater.aif",
         "snare top.aif", "snare bottom.aif", "hi-hat.aif"]


def _kit(tmp_path):
    for n in _FULL:
        (tmp_path / n).write_bytes(b"")
    return str(tmp_path)


def test_detect_outputs_roles(tmp_path) -> None:
    res = CliRunner().invoke(main, ["detect", _kit(tmp_path)])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert any(s["role"] == "overhead" for s in data["stems"])


def test_phase_align_parses_options(tmp_path, monkeypatch) -> None:
    captured: dict = {}

    def fake(kit, **kw):
        captured.update(kw)
        return {"flow": "phase-align", "ok": True}

    monkeypatch.setattr("drum_prep.phase_align.phase_align", fake)
    res = CliRunner().invoke(main, ["phase-align", _kit(tmp_path),
                                    "--max-lag", "400", "--kick-lowpass", "120"])
    assert res.exit_code == 0, res.output
    assert captured["max_lag"] == 400 and captured["kick_lowpass"] == 120.0
    assert json.loads(res.output)["ok"] is True


def test_chain_invokes_run_chain(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("drum_prep.chain.run_chain",
                        lambda *a, **k: {"flow": "chain", "ok": True})
    res = CliRunner().invoke(main, ["chain", _kit(tmp_path),
                                    "--reference", str(tmp_path / "kick in.aif")])
    assert res.exit_code == 0, res.output
    assert json.loads(res.output)["ok"] is True
