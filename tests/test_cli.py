"""CLI dispatches each subcommand to the right pipeline; doctor reports state.

The pipeline functions are replaced with recording stubs and ``open_hub`` is
replaced with a no-op async context manager, so the CLI runs end to end with
no subprocess, server, or audio. Assertions are about which pipeline got
called with which parsed args.
"""
from __future__ import annotations

import contextlib
from typing import Any

import pytest
from click.testing import CliRunner

from ship_studios import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def patched_pipelines(monkeypatch: pytest.MonkeyPatch):
    """Replace pipelines + open_hub so CLI handlers run without a real Hub.

    Records ``(name, args, kwargs)`` for each pipeline the CLI invokes.
    """
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    from ship_studios import pipelines as real_pipelines

    def make_stub(name: str):
        async def stub(hub: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
            calls.append((name, args, kwargs))
            return {"pipeline": name, "steps": []}

        return stub

    for fn_name in (
        "master_track",
        "mix_check",
        "reference_match",
        "loops_to_deliverables",
        "understand_audio",
    ):
        monkeypatch.setattr(real_pipelines, fn_name, make_stub(fn_name), raising=True)

    @contextlib.asynccontextmanager
    async def fake_open_hub(server_keys=None):
        yield object()  # a sentinel "hub"; stubs ignore it

    monkeypatch.setattr(cli, "open_hub", fake_open_hub, raising=False)
    # cli imports open_hub lazily inside each handler from mcp_client, so patch
    # there too.
    from ship_studios import mcp_client

    monkeypatch.setattr(mcp_client, "open_hub", fake_open_hub, raising=True)

    return calls


def test_master_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main,
        ["master", "mix.wav", "--out", "master.wav",
         "--target-lufs", "-9", "--platform", "club"],
    )
    assert result.exit_code == 0, result.output
    assert len(patched_pipelines) == 1
    name, args, kwargs = patched_pipelines[0]
    assert name == "master_track"
    assert args == ("mix.wav", "master.wav")
    assert kwargs["target_lufs"] == -9.0
    assert kwargs["target_platform"] == "club"


def test_master_defaults_out_path_next_to_mix(
    runner: CliRunner, patched_pipelines
) -> None:
    # README documents `ship-studios master <mix> --target-lufs ...` with no
    # --out, so it must default sensibly rather than error.
    result = runner.invoke(
        cli.main, ["master", "projects/song/mix/final.wav", "--target-lufs", "-14"]
    )
    assert result.exit_code == 0, result.output
    _, args, _ = patched_pipelines[0]
    assert args == ("projects/song/mix/final.wav", "projects/song/mix/final.master.wav")


def test_mix_check_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main, ["mix-check", "mix.wav", "--severity", "major"]
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "mix_check"
    assert args == ("mix.wav",)
    assert kwargs["severity_threshold"] == "major"


def test_reference_match_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main,
        ["reference-match", "mix.wav", "--reference", "ref.wav",
         "--goal", "warmer low end"],
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "reference_match"
    assert args == ("mix.wav", "ref.wav")
    assert kwargs["goal"] == "warmer low end"


def test_loops_dispatch_parses_bars(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main,
        ["loops", "drums.wav", "--bpm", "120", "--bars", "1,2,4",
         "--top-n", "5", "--separate", "--key", "Am"],
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "loops_to_deliverables"
    assert args == ("drums.wav", 120.0)
    assert kwargs["bars"] == [1, 2, 4]
    assert kwargs["top_n"] == 5
    assert kwargs["separate"] is True
    assert kwargs["key"] == "Am"


def test_understand_dispatch_parses_labels_and_compare(
    runner: CliRunner, patched_pipelines
) -> None:
    result = runner.invoke(
        cli.main,
        ["understand", "ref.wav", "--labels", "house, techno",
         "--compare", "a.wav", "--compare", "b.wav", "--no-transcribe"],
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "understand_audio"
    assert args == ("ref.wav",)
    assert kwargs["labels"] == ["house", "techno"]
    assert kwargs["compare_paths"] == ["a.wav", "b.wav"]
    assert kwargs["transcribe"] is False


def test_understand_region_three_args(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main,
        ["understand", "ref.wav", "--region", "30", "45", "describe the drop"],
    )
    assert result.exit_code == 0, result.output
    _, _, kwargs = patched_pipelines[0]
    assert kwargs["region"] == (30.0, 45.0, "describe the drop")


def test_doctor_reports_missing_env(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = runner.invoke(cli.main, ["doctor"])
    # Both keys unset is a setup gap, but doctor exit code is driven by the
    # sibling dirs + uv (hard requirements), not the optional keys.
    assert "ANTHROPIC_API_KEY" in result.output
    assert "GEMINI_API_KEY" in result.output
    assert "[unset]" in result.output


def test_doctor_reports_present_env(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    result = runner.invoke(cli.main, ["doctor"])
    assert "[ok ] ANTHROPIC_API_KEY" in result.output
    assert "[ok ] GEMINI_API_KEY" in result.output


def test_doctor_flags_missing_sibling(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # Point the sibling dirs at nonexistent locations -> doctor must fail.
    monkeypatch.setenv("SHIP_STUDIOS_LOOPS_DIR", str(tmp_path / "missing-loops"))
    monkeypatch.setenv("SHIP_STUDIOS_GEMINI_DIR", str(tmp_path / "missing-gemini"))
    result = runner.invoke(cli.main, ["doctor"])
    assert result.exit_code == 1
    assert "MISSING" in result.output
    assert "Setup incomplete" in result.output


def test_doctor_passes_when_siblings_present(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    loops = tmp_path / "stemmy-loops-mcp"
    gemini = tmp_path / "stemmy-gemini-mcp"
    loops.mkdir()
    gemini.mkdir()
    monkeypatch.setenv("SHIP_STUDIOS_LOOPS_DIR", str(loops))
    monkeypatch.setenv("SHIP_STUDIOS_GEMINI_DIR", str(gemini))

    result = runner.invoke(cli.main, ["doctor"])
    # uv may or may not be installed in the sandbox, so the exit code isn't
    # asserted here; the sibling repos are present and reported as ok.
    assert "[ok ] stemmy-loops" in result.output
    assert "[ok ] stemmy-gemini" in result.output


def test_main_group_has_all_subcommands() -> None:
    assert set(cli.main.commands) >= {
        "master",
        "mix-check",
        "reference-match",
        "loops",
        "understand",
        "doctor",
    }
