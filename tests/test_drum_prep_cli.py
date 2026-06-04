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


def test_stem_mix_bad_spec_json_is_clean_error(tmp_path) -> None:
    # A malformed --spec must produce a clean CLI error that NAMES the file, not a
    # bare decoder message or a traceback.
    src = tmp_path / "stems"
    src.mkdir()
    spec = tmp_path / "spec.json"
    spec.write_text("{not valid json")
    res = CliRunner().invoke(main, ["stem-mix", str(src), "--spec", str(spec)])
    assert res.exit_code != 0
    assert "invalid JSON" in res.output and "spec.json" in res.output


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


# --- _go error handling: expected failures become clean one-line CLI errors ----

def test_go_kit_error_is_clean_exit(tmp_path, monkeypatch) -> None:
    from drum_prep.kit import KitError

    def boom(kit, **kw):
        raise KitError("no overheads to align to")

    monkeypatch.setattr("drum_prep.phase_align.phase_align", boom)
    res = CliRunner().invoke(main, ["phase-align", _kit(tmp_path)])
    assert res.exit_code != 0
    assert "no overheads to align to" in res.output


def test_go_import_error_hints_extra(tmp_path, monkeypatch) -> None:
    def boom(kit, **kw):
        raise ImportError("No module named 'scipy'")

    monkeypatch.setattr("drum_prep.phase_align.phase_align", boom)
    res = CliRunner().invoke(main, ["phase-align", _kit(tmp_path)])
    assert res.exit_code != 0
    assert "missing DSP dependency" in res.output
    assert "uv sync --extra drum-prep" in res.output


def test_go_soundfile_error_matched_by_class_name(tmp_path, monkeypatch) -> None:
    # soundfile's LibsndfileError isn't importable without the extra, so _go
    # matches it by class NAME — a locally-defined look-alike must take that path.
    class LibsndfileError(RuntimeError):
        pass

    def boom(kit, **kw):
        raise LibsndfileError("System error.")

    monkeypatch.setattr("drum_prep.phase_align.phase_align", boom)
    res = CliRunner().invoke(main, ["phase-align", _kit(tmp_path)])
    assert res.exit_code != 0
    assert "could not read audio" in res.output


def test_go_unexpected_error_propagates(tmp_path, monkeypatch) -> None:
    # A genuinely unexpected error is NOT swallowed into a clean message — it
    # propagates so the bug is visible (the final re-raise branch of _go).
    def boom(kit, **kw):
        raise RuntimeError("unexpected bug")

    monkeypatch.setattr("drum_prep.phase_align.phase_align", boom)
    res = CliRunner().invoke(main, ["phase-align", _kit(tmp_path)])
    assert res.exit_code != 0
    assert isinstance(res.exception, RuntimeError)
