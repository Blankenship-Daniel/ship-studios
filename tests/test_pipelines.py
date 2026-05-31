"""Each pipeline calls the verified tools on the verified servers, in order.

All MCP calls go through the transport-free :class:`RecordingHub`, so these
assertions are about *intent* — which tool, on which server, with which arg
keys — not about real DSP. The expected sequences mirror the blueprint
exactly; if a step is reordered or a tool renamed, these fail.
"""
from __future__ import annotations

import pytest

from ship_studios import pipelines
from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER


async def test_master_track_sequence(recording_hub) -> None:
    result = await pipelines.master_track(
        recording_hub,
        "projects/song/mix/mix.wav",
        "projects/song/master/master.wav",
        target_lufs=-14.0,
        ceiling_dbtp=-1.0,
        target_platform="spotify",
    )

    assert recording_hub.server_tool_sequence == [
        (LOOPS_SERVER, "measure-loudness"),
        (LOOPS_SERVER, "measure-spectrum"),
        (LOOPS_SERVER, "measure-stereo"),
        (LOOPS_SERVER, "check-clipping"),
        (LOOPS_SERVER, "measure-distortion"),
        (GEMINI_SERVER, "mastering-feedback"),
        (LOOPS_SERVER, "render-mastered"),
        (GEMINI_SERVER, "check-streaming-targets"),
        (LOOPS_SERVER, "export-deliverables"),
    ]
    assert result["pipeline"] == "master-track"


async def test_master_track_render_uses_verified_arg_keys(recording_hub) -> None:
    await pipelines.master_track(
        recording_hub, "m.wav", "out.wav", target_lufs=-9.0, ceiling_dbtp=-0.8,
        high_pass_hz=30.0, transient_shape=0.5, bit_depth=24, sample_rate=48000,
    )
    args = recording_hub.args_for("render-mastered")
    assert set(args) == {
        "path", "out_path", "target_lufs", "ceiling_dbtp",
        "high_pass_hz", "transient_shape", "bit_depth", "sample_rate",
    }
    assert args["target_lufs"] == -9.0
    assert args["ceiling_dbtp"] == -0.8


async def test_master_track_optional_render_args_omitted_by_default(
    recording_hub,
) -> None:
    await pipelines.master_track(recording_hub, "m.wav", "out.wav")
    args = recording_hub.args_for("render-mastered")
    # Defaults must NOT silently inject optional params the user didn't set.
    assert set(args) == {"path", "out_path", "target_lufs", "ceiling_dbtp"}


async def test_master_track_mastering_feedback_passes_platform(recording_hub) -> None:
    await pipelines.master_track(
        recording_hub, "m.wav", "o.wav", target_platform="club"
    )
    assert recording_hub.args_for("mastering-feedback") == {
        "path": "m.wav",
        "target_platform": "club",
    }


async def test_master_track_export_presets_and_tag(recording_hub) -> None:
    await pipelines.master_track(recording_hub, "m.wav", "o.wav")
    args = recording_hub.args_for("export-deliverables")
    assert args["presets"] == ["44.1/16", "48/24", "96/24"]
    assert args["tag"] is True
    assert set(args) == {"path", "out_dir", "presets", "tag"}


async def test_mix_check_diagnostic_sequence(recording_hub) -> None:
    await pipelines.mix_check(recording_hub, "mix.wav", severity_threshold="major")
    assert recording_hub.server_tool_sequence == [
        (GEMINI_SERVER, "detect-mix-issues"),
        (GEMINI_SERVER, "analyze-mix-balance"),
        (LOOPS_SERVER, "measure-loudness"),
        (LOOPS_SERVER, "measure-spectrum"),
        (LOOPS_SERVER, "measure-stereo"),
        (GEMINI_SERVER, "find-resonances"),
        (GEMINI_SERVER, "find-sibilance"),
        (GEMINI_SERVER, "analyze-phase-mono"),
    ]
    assert recording_hub.args_for("detect-mix-issues") == {
        "path": "mix.wav",
        "severity_threshold": "major",
    }


async def test_mix_check_applies_eq_when_bands_supplied(recording_hub) -> None:
    bands = [{"type": "bell", "freq_hz": 320.0, "gain_db": -3.0, "q": 1.4}]
    await pipelines.mix_check(recording_hub, "mix.wav", eq_bands=bands)
    args = recording_hub.args_for("apply-eq")
    assert args["bands"] == bands
    assert set(args) == {"path", "out_path", "bands"}


async def test_mix_check_compress_chains_off_eq_output(recording_hub) -> None:
    bands = [{"type": "high_shelf", "freq_hz": 8000.0, "gain_db": 2.0, "q": 0.7}]
    await pipelines.mix_check(
        recording_hub, "mix.wav", eq_bands=bands, compress=True
    )
    seq = recording_hub.tool_sequence
    assert seq[-2:] == ["apply-eq", "compress-loop"]
    eq_out = recording_hub.args_for("apply-eq")["out_path"]
    # compressor reads the EQ'd output, not the raw mix.
    assert recording_hub.args_for("compress-loop")["path"] == eq_out


async def test_mix_check_no_mutation_without_moves(recording_hub) -> None:
    await pipelines.mix_check(recording_hub, "mix.wav")
    assert "apply-eq" not in recording_hub.tool_sequence
    assert "compress-loop" not in recording_hub.tool_sequence


async def test_reference_match_sequence(recording_hub) -> None:
    await pipelines.reference_match(recording_hub, "mix.wav", "ref.wav")
    assert recording_hub.server_tool_sequence == [
        (GEMINI_SERVER, "match-reference-numeric"),
        (GEMINI_SERVER, "compare-to-reference"),
        (LOOPS_SERVER, "compare-tonality"),
        (LOOPS_SERVER, "render-ab"),
    ]


async def test_reference_match_numeric_uses_mix_and_reference_keys(
    recording_hub,
) -> None:
    await pipelines.reference_match(recording_hub, "mix.wav", "ref.wav")
    assert recording_hub.args_for("match-reference-numeric") == {
        "mix_path": "mix.wav",
        "reference_path": "ref.wav",
    }
    # compare-tonality uses loop_path / reference_path (its own verified keys).
    assert recording_hub.args_for("compare-tonality") == {
        "loop_path": "mix.wav",
        "reference_path": "ref.wav",
    }


async def test_reference_match_render_ab_uses_processed_and_reference(
    recording_hub,
) -> None:
    await pipelines.reference_match(recording_hub, "mix.wav", "ref.wav")
    args = recording_hub.args_for("render-ab")
    assert args["processed"] == "mix.wav"
    assert args["reference"] == "ref.wav"
    assert "out_path" in args


async def test_reference_match_eq_feeds_render_ab(recording_hub) -> None:
    bands = [{"type": "low_shelf", "freq_hz": 100.0, "gain_db": -2.0, "q": 0.7}]
    await pipelines.reference_match(recording_hub, "mix.wav", "ref.wav", eq_bands=bands)
    seq = recording_hub.tool_sequence
    assert seq == [
        "match-reference-numeric",
        "compare-to-reference",
        "compare-tonality",
        "apply-eq",
        "render-ab",
    ]
    eq_out = recording_hub.args_for("apply-eq")["out_path"]
    assert recording_hub.args_for("render-ab")["processed"] == eq_out


async def test_loops_to_deliverables_sequence() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub(
        canned={"find-loops": {"loops": [{"path": "out/loop_01.wav"}]}}
    )
    await pipelines.loops_to_deliverables(
        hub, "drums.wav", 120.0, bars=[4], key="Am", out_dir="out"
    )
    assert hub.tool_sequence == [
        "find-loops",
        "clean-loop",
        "optimize-seam",
        "render-mastered",
        "tag-deliverable",
        "export-deliverables",
    ]
    # every step after find-loops operates on the loop path it returned.
    assert hub.args_for("clean-loop")["path"] == "out/loop_01.wav"


async def test_loops_to_deliverables_find_loops_args(recording_hub) -> None:
    await pipelines.loops_to_deliverables(
        recording_hub, "mix.wav", 124.0, bars=[1, 2, 4], top_n=5, separate=True,
        out_dir="artifacts/run",
    )
    args = recording_hub.args_for("find-loops")
    assert args["path"] == "mix.wav"
    assert args["bpm"] == 124.0
    assert args["bars"] == [1, 2, 4]
    assert args["top_n"] == 5
    assert args["separate"] is True
    assert args["out_dir"] == "artifacts/run"


async def test_loops_to_deliverables_tag_uses_verified_keys(recording_hub) -> None:
    await pipelines.loops_to_deliverables(
        recording_hub, "drums.wav", 90.0, bars=[2], key="Gm",
        root_note=43, originator="ship-studios",
    )
    args = recording_hub.args_for("tag-deliverable")
    assert args["bpm"] == 90.0
    assert args["originator"] == "ship-studios"
    assert args["bars"] == 2  # single-element bar list collapses to scalar
    assert args["key"] == "Gm"
    assert args["root_note"] == 43


async def test_loops_to_deliverables_describe_optional(recording_hub) -> None:
    await pipelines.loops_to_deliverables(
        recording_hub, "drums.wav", 100.0, describe=False
    )
    assert "describe-loops" not in recording_hub.tool_sequence

    hub2 = type(recording_hub)()  # fresh hub for the describe=True case
    await pipelines.loops_to_deliverables(
        hub2, "drums.wav", 100.0, out_dir="out", describe=True
    )
    assert hub2.tool_sequence[-1] == "describe-loops"
    assert hub2.args_for("describe-loops") == {"out_dir": "out"}


async def test_understand_audio_runs_only_requested_tools(recording_hub) -> None:
    await pipelines.understand_audio(
        recording_hub,
        "ref.wav",
        transcribe=True,
        diarize=True,
        region=(60.0, 75.0, "what happens here?"),
        event_description="kick drum hits",
        labels=["house", "techno"],
        multi_label=True,
        compare_paths=["other.wav"],
    )
    assert recording_hub.server_tool_sequence == [
        (GEMINI_SERVER, "transcribe-audio"),
        (GEMINI_SERVER, "describe-audio-region"),
        (GEMINI_SERVER, "extract-audio-events"),
        (GEMINI_SERVER, "classify-audio"),
        (GEMINI_SERVER, "compare-audio-files"),
    ]
    assert recording_hub.args_for("transcribe-audio") == {
        "path": "ref.wav",
        "diarize": True,
    }
    assert recording_hub.args_for("describe-audio-region") == {
        "path": "ref.wav",
        "start_s": 60.0,
        "end_s": 75.0,
        "prompt": "what happens here?",
    }
    assert recording_hub.args_for("classify-audio") == {
        "path": "ref.wav",
        "labels": ["house", "techno"],
        "multi_label": True,
    }
    # compare-audio-files prepends the primary path.
    assert recording_hub.args_for("compare-audio-files") == {
        "paths": ["ref.wav", "other.wav"]
    }


async def test_understand_audio_default_is_just_transcription(recording_hub) -> None:
    await pipelines.understand_audio(recording_hub, "ref.wav")
    assert recording_hub.tool_sequence == ["transcribe-audio"]


async def test_understand_audio_can_skip_transcription(recording_hub) -> None:
    await pipelines.understand_audio(
        recording_hub, "ref.wav", transcribe=False, labels=["kick", "snare"]
    )
    assert recording_hub.tool_sequence == ["classify-audio"]


@pytest.mark.parametrize(
    "pipeline_result_key, coro_factory",
    [
        ("master-track", lambda h: pipelines.master_track(h, "m.wav", "o.wav")),
        ("mix-check", lambda h: pipelines.mix_check(h, "m.wav")),
        (
            "reference-match",
            lambda h: pipelines.reference_match(h, "m.wav", "r.wav"),
        ),
        (
            "loops-to-deliverables",
            lambda h: pipelines.loops_to_deliverables(h, "m.wav", 120.0),
        ),
        ("understand-audio", lambda h: pipelines.understand_audio(h, "m.wav")),
    ],
)
async def test_pipelines_return_structured_steps(
    recording_hub, pipeline_result_key, coro_factory
) -> None:
    result = await coro_factory(recording_hub)
    assert result["pipeline"] == pipeline_result_key
    assert isinstance(result["steps"], list)
    assert result["steps"], "every pipeline should record at least one step"
    for step in result["steps"]:
        assert set(step) >= {"server", "tool", "args", "result"}
