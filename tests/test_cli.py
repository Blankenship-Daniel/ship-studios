"""CLI dispatches each subcommand to the right pipeline; doctor reports state.

The pipeline functions are replaced with recording stubs and ``open_hub`` is
replaced with a no-op async context manager, so the CLI runs end to end with
no subprocess, server, or audio. Assertions are about which pipeline got
called with which parsed args.
"""
from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from ship_studios import cli

_PATH_EXTS = (".wav", ".aif", ".aiff", ".flac")


@pytest.fixture
def runner():
    """A CliRunner that pre-creates any audio-path token in an isolated CWD.

    The CLI now validates input paths with ``click.Path(exists=True)``, so the
    dispatch tests (which pass bare names like ``mix.wav``) need those files to
    exist. Audio-extension tokens are created inside an isolated filesystem for
    the invoke; the relative arg strings are unchanged, so the recorded-arg
    assertions still hold. Invocations with no audio tokens (e.g. ``doctor``)
    run unwrapped.
    """
    base = CliRunner()

    class _FileMakingRunner:
        def invoke(self, cli_obj, argv=None, **kwargs):
            toks = [t for t in (argv or [])
                    if isinstance(t, str) and t.endswith(_PATH_EXTS)]
            if not toks:
                return base.invoke(cli_obj, argv, **kwargs)
            with base.isolated_filesystem():
                for t in toks:
                    p = Path(t)
                    if str(p.parent) != ".":
                        p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(b"")
                return base.invoke(cli_obj, argv, **kwargs)

        def __getattr__(self, name):
            return getattr(base, name)

    return _FileMakingRunner()


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
        "house_curve",
        "batch_master",
        "stem_master",
        "unmask_stems",
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


def test_master_defaults_out_into_masters_dir(
    runner: CliRunner, patched_pipelines
) -> None:
    # README documents `ship-studios master <mix> --target-lufs ...` with no
    # --out, so it must default sensibly. Per CLAUDE.md the master lands in the
    # project's masters/ dir (sibling of mix/), never inside mix/.
    result = runner.invoke(
        cli.main, ["master", "projects/song/mix/final.wav", "--target-lufs", "-14"]
    )
    assert result.exit_code == 0, result.output
    _, args, _ = patched_pipelines[0]
    assert args == (
        "projects/song/mix/final.wav",
        "projects/song/masters/final.master.wav",
    )


def test_master_default_out_falls_back_to_masters_sibling(
    runner: CliRunner, patched_pipelines
) -> None:
    # A loose mix not under a mix/ dir still lands in a masters/ dir beside it,
    # never overwriting the source next to it.
    result = runner.invoke(cli.main, ["master", "song/bounce.wav"])
    assert result.exit_code == 0, result.output
    _, args, _ = patched_pipelines[0]
    assert args == ("song/bounce.wav", "song/masters/bounce.master.wav")


def test_master_rejects_missing_input(patched_pipelines) -> None:
    # The input path is validated up front (click.Path(exists=True)): a missing
    # file is a usage error (exit 2) BEFORE any server is spawned, not a late
    # failure after the MCP handshake. Uses a bare CliRunner (the `runner`
    # fixture would auto-create the token).
    base = CliRunner()
    with base.isolated_filesystem():
        result = base.invoke(cli.main, ["master", "nope.wav"])
    assert result.exit_code == 2
    assert "does not exist" in result.output
    assert len(patched_pipelines) == 0  # never reached the pipeline


def test_mix_check_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main, ["mix-check", "mix.wav", "--severity", "serious"]
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "mix_check"
    assert args == ("mix.wav",)
    assert kwargs["severity_threshold"] == "serious"


def test_mix_check_corrective_flags(runner: CliRunner, patched_pipelines) -> None:
    # The bool corrective flags enable each tool with default settings ({}).
    result = runner.invoke(
        cli.main,
        ["mix-check", "mix.wav", "--deess", "--de-harsh", "--excite",
         "--compress", "--multiband"],
    )
    assert result.exit_code == 0, result.output
    name, _, kwargs = patched_pipelines[0]
    assert name == "mix_check"
    assert kwargs["deess"] == {}
    assert kwargs["suppress"] == {}
    assert kwargs["excite"] == {}
    assert kwargs["multiband"] == {}
    assert kwargs["compress"] is True


def test_mix_check_no_corrective_flags_is_diagnose_only(
    runner: CliRunner, patched_pipelines
) -> None:
    result = runner.invoke(cli.main, ["mix-check", "mix.wav"])
    assert result.exit_code == 0, result.output
    _, _, kwargs = patched_pipelines[0]
    assert kwargs["deess"] is None
    assert kwargs["suppress"] is None
    assert kwargs["excite"] is None
    assert kwargs["multiband"] is None
    assert kwargs["dynamic_eq_bands"] is None
    assert kwargs["compress"] is False


def test_mix_check_rejects_invalid_severity(runner: CliRunner, patched_pipelines) -> None:
    # "minor"/"major" are NOT valid detect-mix-issues floors; the CLI must reject
    # them up front (Choice) rather than fail at the server.
    result = runner.invoke(cli.main, ["mix-check", "mix.wav", "--severity", "minor"])
    assert result.exit_code == 2
    assert "is not one of" in result.output


def test_master_rejects_invalid_platform(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(cli.main, ["master", "mix.wav", "--platform", "soundcloud"])
    assert result.exit_code == 2
    assert "is not one of" in result.output


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


def test_master_assistant_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main,
        ["master", "mix.wav", "--assistant", "--intent", "warm",
         "--intensity", "strong", "--style", "indie"],
    )
    assert result.exit_code == 0, result.output
    name, _, kwargs = patched_pipelines[0]
    assert name == "master_track"
    assert kwargs["assistant"] is True
    assert kwargs["intent"] == "warm"
    assert kwargs["intensity"] == "strong"
    assert kwargs["style"] == "indie"


def test_house_curve_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main,
        ["house-curve", "mix.wav", "--reference", "a.wav", "--reference", "b.wav",
         "--match-strength", "0.75"],
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "house_curve"
    assert args == ("mix.wav", ["a.wav", "b.wav"])
    assert kwargs["match_strength"] == 0.75


def test_house_curve_requires_a_reference(runner: CliRunner, patched_pipelines) -> None:
    # --reference is required (multiple); missing it is a usage error, not a crash.
    result = runner.invoke(cli.main, ["house-curve", "mix.wav"])
    assert result.exit_code == 2


def test_batch_master_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main, ["batch-master", "a.wav", "b.wav", "--target-lufs", "-12"]
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "batch_master"
    assert args == (["a.wav", "b.wav"],)
    assert kwargs["target_lufs"] == -12.0


def test_batch_master_requires_a_mix(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(cli.main, ["batch-master"])
    assert result.exit_code == 2


def test_stem_master_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main, ["stem-master", "kick.wav", "bass.wav", "--cross-check"]
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "stem_master"
    # the dict is keyed by filename stem (no extension).
    assert args == ({"kick": "kick.wav", "bass": "bass.wav"},)
    assert kwargs["cross_check"] is True


def test_stem_master_requires_two_stems(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(cli.main, ["stem-master", "only.wav"])
    assert result.exit_code == 2


def test_stem_master_rejects_duplicate_names(runner: CliRunner, patched_pipelines) -> None:
    # Same basename in two dirs would collide in the name->path dict.
    result = runner.invoke(cli.main, ["stem-master", "a/kick.wav", "b/kick.wav"])
    assert result.exit_code == 2
    assert "duplicate stem name" in result.output


def test_unmask_stems_dispatch(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main, ["unmask-stems", "kick.wav", "bass.wav", "--cross-check"]
    )
    assert result.exit_code == 0, result.output
    name, args, kwargs = patched_pipelines[0]
    assert name == "unmask_stems"
    assert args == ({"kick": "kick.wav", "bass": "bass.wav"},)
    assert kwargs["cross_check"] is True


def test_unmask_stems_requires_two_stems(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(cli.main, ["unmask-stems", "only.wav"])
    assert result.exit_code == 2


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


def test_loops_rejects_non_integer_bars(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(cli.main, ["loops", "d.wav", "--bpm", "120", "--bars", "1,x,4"])
    assert result.exit_code == 2
    assert "integers" in result.output


def test_loops_rejects_out_of_range_bars(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(cli.main, ["loops", "d.wav", "--bpm", "120", "--bars", "999"])
    assert result.exit_code == 2
    assert "out of range" in result.output


def test_loops_rejects_out_of_range_root_note(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main, ["loops", "d.wav", "--bpm", "120", "--root-note", "200"]
    )
    assert result.exit_code == 2


def test_loops_rejects_unknown_preset(runner: CliRunner, patched_pipelines) -> None:
    # The old free-form "<sr>/<bits>" labels are rejected up front (parity with
    # --platform/--severity), not deep at export-deliverables.
    result = runner.invoke(
        cli.main, ["loops", "d.wav", "--bpm", "120", "--presets", "44.1/16"]
    )
    assert result.exit_code == 2
    assert "unknown preset" in result.output


def test_loops_parses_valid_presets(runner: CliRunner, patched_pipelines) -> None:
    result = runner.invoke(
        cli.main,
        ["loops", "d.wav", "--bpm", "120", "--presets", "distribution_44k_16,master_96k_24"],
    )
    assert result.exit_code == 0, result.output
    _, _, kwargs = patched_pipelines[0]
    assert kwargs["presets"] == ["distribution_44k_16", "master_96k_24"]


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


def test_understand_bare_defaults_to_transcription(runner: CliRunner, patched_pipelines) -> None:
    # No specific analysis requested -> the default transcribe stays on.
    result = runner.invoke(cli.main, ["understand", "ref.wav"])
    assert result.exit_code == 0, result.output
    _, _, kwargs = patched_pipelines[0]
    assert kwargs["transcribe"] is True


def test_understand_specific_request_auto_skips_transcribe(
    runner: CliRunner, patched_pipelines
) -> None:
    # A label-only (or region/event/compare/json) ask must NOT also fire a paid
    # default transcribe-audio call when the user never opted into transcription.
    result = runner.invoke(cli.main, ["understand", "ref.wav", "--labels", "house,techno"])
    assert result.exit_code == 0, result.output
    _, _, kwargs = patched_pipelines[0]
    assert kwargs["transcribe"] is False
    assert kwargs["labels"] == ["house", "techno"]


def test_understand_explicit_transcribe_overrides_auto_skip(
    runner: CliRunner, patched_pipelines
) -> None:
    # An explicit --transcribe always wins, even alongside a specific analysis.
    result = runner.invoke(
        cli.main, ["understand", "ref.wav", "--transcribe", "--labels", "house"]
    )
    assert result.exit_code == 0, result.output
    _, _, kwargs = patched_pipelines[0]
    assert kwargs["transcribe"] is True


def test_understand_region_only_auto_skips_transcribe(
    runner: CliRunner, patched_pipelines
) -> None:
    result = runner.invoke(
        cli.main, ["understand", "ref.wav", "--region", "30", "45", "what is here?"]
    )
    assert result.exit_code == 0, result.output
    _, _, kwargs = patched_pipelines[0]
    assert kwargs["transcribe"] is False


def test_understand_explicit_no_transcribe_still_works(
    runner: CliRunner, patched_pipelines
) -> None:
    # Explicit --no-transcribe with no other request: a valid no-op pipeline.
    result = runner.invoke(cli.main, ["understand", "ref.wav", "--no-transcribe"])
    assert result.exit_code == 0, result.output
    _, _, kwargs = patched_pipelines[0]
    assert kwargs["transcribe"] is False


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
    # doctor now requires a pyproject.toml to consider a sibling "synced", not
    # just a present directory.
    (loops / "pyproject.toml").write_text("[project]\nname='x'\n")
    (gemini / "pyproject.toml").write_text("[project]\nname='y'\n")
    monkeypatch.setenv("SHIP_STUDIOS_LOOPS_DIR", str(loops))
    monkeypatch.setenv("SHIP_STUDIOS_GEMINI_DIR", str(gemini))

    result = runner.invoke(cli.main, ["doctor"])
    # uv may or may not be installed in the sandbox, so the exit code isn't
    # asserted here; the sibling repos are present and reported as ok.
    assert "[ok ] stemmy-loops" in result.output
    assert "[ok ] stemmy-gemini" in result.output


def test_doctor_flags_present_but_unsynced_sibling(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # A directory with no pyproject.toml is present but not the synced repo.
    loops = tmp_path / "stemmy-loops-mcp"
    gemini = tmp_path / "stemmy-gemini-mcp"
    loops.mkdir()
    gemini.mkdir()  # both exist but neither has a pyproject.toml
    monkeypatch.setenv("SHIP_STUDIOS_LOOPS_DIR", str(loops))
    monkeypatch.setenv("SHIP_STUDIOS_GEMINI_DIR", str(gemini))
    result = runner.invoke(cli.main, ["doctor"])
    assert result.exit_code == 1
    assert "no pyproject.toml" in result.output


def test_main_group_has_all_subcommands() -> None:
    assert set(cli.main.commands) >= {
        "master",
        "batch-master",
        "mix-check",
        "reference-match",
        "house-curve",
        "stem-master",
        "unmask-stems",
        "loops",
        "understand",
        "doctor",
    }


def test_run_turns_any_error_into_clean_exit() -> None:
    # The CLI boundary must convert ANY failure into a one-line error + exit 1,
    # never a traceback (covers McpError/OSError/ToolCallError uniformly).
    async def boom() -> dict[str, Any]:
        raise RuntimeError("kaboom")

    with pytest.raises(SystemExit) as exc:
        cli._run(boom())
    assert exc.value.code == 1


def test_format_error_flattens_exception_group() -> None:
    # anyio task groups wrap failures in an ExceptionGroup; the leaf messages
    # must survive into the user-facing line.
    eg = ExceptionGroup("grp", [OSError("uv not found"), RuntimeError("boom")])
    msg = cli._format_error(eg)
    assert "uv not found" in msg
    assert "boom" in msg


def test_run_reports_exception_group_leaf(capsys) -> None:
    async def boom() -> dict[str, Any]:
        raise ExceptionGroup("grp", [RuntimeError("connection closed")])

    with pytest.raises(SystemExit):
        cli._run(boom())
    err = capsys.readouterr().err
    assert "connection closed" in err


def test_run_exits_130_on_keyboard_interrupt(capsys) -> None:
    # Ctrl-C must exit 130 quietly, not dump a traceback or print "Error:".
    async def interrupted() -> dict[str, Any]:
        raise KeyboardInterrupt

    with pytest.raises(SystemExit) as exc:
        cli._run(interrupted())
    assert exc.value.code == 130
    out = capsys.readouterr()
    assert "Interrupted" in out.err
    assert "Error:" not in out.err
