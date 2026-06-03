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
    # A critique "mood" passes straight through to mastering-feedback.
    await pipelines.master_track(
        recording_hub, "m.wav", "o.wav", target_platform="club"
    )
    assert recording_hub.args_for("mastering-feedback") == {
        "path": "m.wav",
        "target_platform": "club",
    }


async def test_master_track_maps_streaming_service_to_valid_vocabularies(
    recording_hub,
) -> None:
    # The default release target "spotify" is NOT a mastering-feedback mood; it
    # must map to "streaming" there, and reach check-streaming-targets as the
    # actual service name. (Regression guard for the broken default invocation.)
    await pipelines.master_track(recording_hub, "m.wav", "o.wav", target_platform="spotify")
    assert recording_hub.args_for("mastering-feedback")["target_platform"] == "streaming"
    assert recording_hub.args_for("check-streaming-targets") == {
        "path": "o.wav",
        "platforms": ["spotify"],
    }


async def test_master_track_apple_alias_normalizes(recording_hub) -> None:
    await pipelines.master_track(recording_hub, "m.wav", "o.wav", target_platform="apple")
    assert recording_hub.args_for("check-streaming-targets")["platforms"] == ["apple_music"]


async def test_master_track_mood_target_skips_platform_filter(recording_hub) -> None:
    # A non-service target (e.g. "vinyl") checks all default platforms.
    await pipelines.master_track(recording_hub, "m.wav", "o.wav", target_platform="vinyl")
    assert recording_hub.args_for("check-streaming-targets") == {"path": "o.wav"}
    assert recording_hub.args_for("mastering-feedback")["target_platform"] == "vinyl"


async def test_master_track_export_presets_and_tag(recording_hub) -> None:
    await pipelines.master_track(recording_hub, "m.wav", "o.wav")
    args = recording_hub.args_for("export-deliverables")
    # Must be the stemmy-loops verified preset names, not free-form "<sr>/<bits>".
    assert args["presets"] == pipelines.DEFAULT_PRESETS
    assert args["presets"] == [
        "distribution_44k_16",
        "production_48k_24",
        "master_96k_24",
    ]
    assert args["tag"] is True
    assert set(args) == {"path", "out_dir", "presets", "tag"}


async def test_mix_check_diagnostic_sequence(recording_hub) -> None:
    await pipelines.mix_check(recording_hub, "mix.wav", severity_threshold="serious")
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
        "severity_threshold": "serious",
    }


async def test_master_track_assistant_replaces_feedback(recording_hub) -> None:
    await pipelines.master_track(
        recording_hub, "m.wav", "o.wav", assistant=True,
        intent="warm", intensity="strong", style="indie",
    )
    seq = recording_hub.tool_sequence
    assert "master-assistant" in seq
    assert "mastering-feedback" not in seq
    args = recording_hub.args_for("master-assistant")
    assert args["intent"] == "warm"
    assert args["intensity"] == "strong"
    assert args["style"] == "indie"
    assert args["target_platform"] == "streaming"  # spotify -> streaming mood


async def test_master_track_assistant_omits_style_when_none(recording_hub) -> None:
    await pipelines.master_track(recording_hub, "m.wav", "o.wav", assistant=True)
    assert "style" not in recording_hub.args_for("master-assistant")


async def test_master_track_default_step_is_feedback(recording_hub) -> None:
    await pipelines.master_track(recording_hub, "m.wav", "o.wav")
    assert "mastering-feedback" in recording_hub.tool_sequence
    assert "master-assistant" not in recording_hub.tool_sequence


async def test_house_curve_renders_match_eq_from_profile_delta() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub(canned={"match-to-profile": {
        "profile_path": "p.json",
        "bands": [
            {"freq_hz": 100.0, "delta_db": 2.0},
            {"freq_hz": 1000.0, "delta_db": -1.5},
        ],
    }})
    result = await pipelines.house_curve(hub, "mix.wav", ["a.wav", "b.wav"])
    assert hub.server_tool_sequence == [
        (LOOPS_SERVER, "build-target-profile"),
        (LOOPS_SERVER, "match-to-profile"),
        (LOOPS_SERVER, "match-eq"),
    ]
    # build + match share the one profile JSON.
    prof = hub.args_for("build-target-profile")["out_json"]
    assert hub.args_for("build-target-profile")["paths"] == ["a.wav", "b.wav"]
    assert hub.args_for("match-to-profile")["profile_json"] == prof
    # match-eq is driven by the per-band delta from match-to-profile.
    assert hub.args_for("match-eq")["delta_db_curve"] == [
        {"freq_hz": 100.0, "delta_db": 2.0},
        {"freq_hz": 1000.0, "delta_db": -1.5},
    ]
    assert hub.args_for("match-eq")["source_path"] == "mix.wav"
    assert result["matched"] is True
    assert result["output"] == hub.args_for("match-eq")["out_path"]


async def test_house_curve_analysis_only_without_delta(recording_hub) -> None:
    # The default hub returns {} -> no recoverable delta -> no match-eq render.
    result = await pipelines.house_curve(recording_hub, "mix.wav", ["a.wav"])
    assert recording_hub.server_tool_sequence == [
        (LOOPS_SERVER, "build-target-profile"),
        (LOOPS_SERVER, "match-to-profile"),
    ]
    assert result["matched"] is False
    assert result["output"] == "mix.wav"


async def test_house_curve_reuses_supplied_profile(recording_hub) -> None:
    await pipelines.house_curve(
        recording_hub, "mix.wav", ["a.wav"], profile_json="shared/ep.json"
    )
    assert recording_hub.args_for("build-target-profile")["out_json"] == "shared/ep.json"
    assert recording_hub.args_for("match-to-profile")["profile_json"] == "shared/ep.json"


async def test_house_curve_requires_references(recording_hub) -> None:
    with pytest.raises(ValueError):
        await pipelines.house_curve(recording_hub, "mix.wav", [])


async def test_batch_master_per_track_then_album_pass() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub()
    result = await pipelines.batch_master(
        hub, ["projects/ep/mix/a.wav", "projects/ep/mix/b.wav"]
    )
    masters = [
        "projects/ep/masters/a.master.wav",
        "projects/ep/masters/b.master.wav",
    ]
    assert result["pipeline"] == "batch-master"
    assert result["masters"] == masters
    seq = hub.tool_sequence
    # each track went through the full master chain
    assert seq.count("render-mastered") == 2
    assert seq.count("export-deliverables") == 2
    # the album pass closes it out: measure-loudness per master, then album norm
    assert seq[-3:] == [
        "measure-loudness",
        "measure-loudness",
        "analyze-album-normalization",
    ]
    assert hub.args_for("analyze-album-normalization")["paths"] == masters
    # every render hit the SAME shared target, into masters/
    renders = [c.args for c in hub.calls if c.tool == "render-mastered"]
    assert [r["out_path"] for r in renders] == masters
    assert all(r["target_lufs"] == -14.0 for r in renders)


async def test_batch_master_masters_dir_override() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub()
    result = await pipelines.batch_master(
        hub, ["a.wav", "b.wav"], masters_dir="out/masters"
    )
    assert result["masters"] == [
        "out/masters/a.master.wav",
        "out/masters/b.master.wav",
    ]


async def test_batch_master_requires_paths(recording_hub) -> None:
    with pytest.raises(ValueError):
        await pipelines.batch_master(recording_hub, [])


async def test_mix_check_default_severity_is_server_valid(recording_hub) -> None:
    # Bare mix-check must send a floor the real detect-mix-issues accepts.
    await pipelines.mix_check(recording_hub, "mix.wav")
    sev = recording_hub.args_for("detect-mix-issues")["severity_threshold"]
    assert sev in pipelines.SEVERITY_CHOICES


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


async def test_mix_check_corrective_chain_order(recording_hub) -> None:
    # Every corrective step, in the doc's order, each chaining off the previous.
    await pipelines.mix_check(
        recording_hub,
        "mix.wav",
        eq_bands=[{"type": "bell", "freq_hz": 320.0, "gain_db": -2.0, "q": 1.4}],
        deess={},
        suppress={},
        dynamic_eq_bands=[
            {"freq_hz": 200.0, "gain_db": -3.0, "q": 1.0, "threshold_db": -24.0}
        ],
        excite={},
        compress=True,
        multiband={},
    )
    assert recording_hub.tool_sequence[-7:] == [
        "apply-eq",
        "de-ess",
        "suppress-resonances",
        "apply-dynamic-eq",
        "excite-loop",
        "compress-loop",
        "multiband-compress",
    ]
    # Each step reads the previous step's output — the chain is wired correctly.
    a = recording_hub
    assert a.args_for("de-ess")["path"] == a.args_for("apply-eq")["out_path"]
    assert a.args_for("suppress-resonances")["path"] == a.args_for("de-ess")["out_path"]
    assert (
        a.args_for("apply-dynamic-eq")["path"]
        == a.args_for("suppress-resonances")["out_path"]
    )
    assert a.args_for("excite-loop")["path"] == a.args_for("apply-dynamic-eq")["out_path"]
    assert a.args_for("compress-loop")["path"] == a.args_for("excite-loop")["out_path"]
    assert (
        a.args_for("multiband-compress")["path"] == a.args_for("compress-loop")["out_path"]
    )


async def test_mix_check_output_is_last_corrective_file(recording_hub) -> None:
    result = await pipelines.mix_check(recording_hub, "mix.wav", deess={})
    # output points at the final corrective render, not the raw mix.
    assert result["output"] == recording_hub.args_for("de-ess")["out_path"]
    assert result["output"] != "mix.wav"


async def test_mix_check_output_is_input_when_no_moves(recording_hub) -> None:
    result = await pipelines.mix_check(recording_hub, "mix.wav")
    assert result["output"] == "mix.wav"


async def test_mix_check_deess_settings_forwarded_path_protected(recording_hub) -> None:
    # Tuning kwargs pass through; an out_path inside the dict can't hijack the
    # chain (the pipeline injects path/out_path last).
    await pipelines.mix_check(
        recording_hub,
        "mix.wav",
        deess={"center_hz": 7000.0, "reduction_db": 5.0, "out_path": "HACKED.wav"},
    )
    args = recording_hub.args_for("de-ess")
    assert args["center_hz"] == 7000.0
    assert args["reduction_db"] == 5.0
    assert args["path"] == "mix.wav"
    assert args["out_path"] != "HACKED.wav"


async def test_mix_check_multiband_is_a_compress_alternative(recording_hub) -> None:
    await pipelines.mix_check(recording_hub, "mix.wav", multiband={})
    seq = recording_hub.tool_sequence
    assert "multiband-compress" in seq
    assert "compress-loop" not in seq
    assert recording_hub.args_for("multiband-compress")["path"] == "mix.wav"


async def test_reference_match_sequence(recording_hub) -> None:
    await pipelines.reference_match(recording_hub, "mix.wav", "ref.wav")
    assert recording_hub.server_tool_sequence == [
        (GEMINI_SERVER, "match-reference-numeric"),
        (GEMINI_SERVER, "compare-to-reference"),
        (LOOPS_SERVER, "compare-tonality"),
        (LOOPS_SERVER, "match-eq"),
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


async def test_reference_match_match_eq_uses_source_and_reference(
    recording_hub,
) -> None:
    # match-eq is the primary corrective: it measures source-minus-reference
    # itself, so it takes source_path + reference_path (not a band list).
    await pipelines.reference_match(recording_hub, "mix.wav", "ref.wav")
    args = recording_hub.args_for("match-eq")
    assert args["source_path"] == "mix.wav"
    assert args["reference_path"] == "ref.wav"
    assert args["match_strength"] == 0.5
    assert args["phase"] == "minimum"
    assert "out_path" in args


async def test_reference_match_render_ab_uses_processed_and_reference(
    recording_hub,
) -> None:
    await pipelines.reference_match(recording_hub, "mix.wav", "ref.wav")
    args = recording_hub.args_for("render-ab")
    # The A/B plays the match-eq'd output, not the raw mix.
    assert args["processed"] == recording_hub.args_for("match-eq")["out_path"]
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
        "match-eq",
        "apply-eq",
        "render-ab",
    ]
    # Residual apply-eq layers on the matched output, then the A/B plays that.
    match_out = recording_hub.args_for("match-eq")["out_path"]
    assert recording_hub.args_for("apply-eq")["path"] == match_out
    eq_out = recording_hub.args_for("apply-eq")["out_path"]
    assert recording_hub.args_for("render-ab")["processed"] == eq_out


#: The real find-loops return (FindLoopsResponse): out_dir + nested manifest,
#: each loop a basename under "wav". Mirror it so the parsing is actually tested.
def _find_loops_canned(out_dir: str, *wavs: str) -> dict:
    return {
        "find-loops": {
            "out_dir": out_dir,
            "manifest": {"bpm": 120.0, "loops": [{"wav": w} for w in wavs]},
        }
    }


async def test_loops_to_deliverables_sequence() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub(canned=_find_loops_canned("out", "loop_01.wav"))
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
    # the loop "wav" basename must be joined to the manifest out_dir, and the
    # chain operates on a real loop WAV (NOT the output directory — the C2 bug).
    assert hub.args_for("clean-loop")["path"] == "out/loop_01.wav"


async def test_loops_to_deliverables_processes_every_loop() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub(
        canned=_find_loops_canned("out", "a.wav", "b.wav", "c.wav")
    )
    result = await pipelines.loops_to_deliverables(hub, "drums.wav", 120.0)
    # the per-loop chain runs once PER loop, not just the first.
    assert hub.tool_sequence.count("render-mastered") == 3
    assert hub.tool_sequence.count("export-deliverables") == 3
    assert [d["loop"] for d in result["loops"]] == ["out/a.wav", "out/b.wav", "out/c.wav"]


async def test_loops_to_deliverables_falls_back_when_manifest_unparseable() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub(canned={"find-loops": {"unexpected": "shape"}})
    await pipelines.loops_to_deliverables(hub, "drums.wav", 120.0)
    # unknown manifest shape -> chain still runs once, on the input itself.
    assert hub.args_for("clean-loop")["path"] == "drums.wav"


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


async def test_understand_audio_zero_steps_when_all_disabled(recording_hub) -> None:
    # --no-transcribe with no other request -> a valid no-op (no tools called).
    await pipelines.understand_audio(recording_hub, "ref.wav", transcribe=False)
    assert recording_hub.tool_sequence == []


async def test_understand_audio_compare_schema_and_prompt(recording_hub) -> None:
    schema = {"type": "object", "properties": {"verdict": {"type": "string"}}}
    await pipelines.understand_audio(
        recording_hub, "a.wav", transcribe=False, compare_paths=["b.wav"],
        compare_prompt="which is brighter?", compare_schema=schema,
    )
    args = recording_hub.args_for("compare-audio-files")
    assert args == {
        "paths": ["a.wav", "b.wav"],
        "prompt": "which is brighter?",
        "schema": schema,
    }


async def test_understand_audio_runs_audio_to_json(recording_hub) -> None:
    schema = {"type": "object", "properties": {"bpm": {"type": "number"}}}
    await pipelines.understand_audio(
        recording_hub, "a.wav", transcribe=False, json_schema=schema, json_prompt="extract bpm",
    )
    assert recording_hub.args_for("audio-to-json") == {
        "path": "a.wav", "prompt": "extract bpm", "schema": schema,
    }


async def test_understand_audio_json_schema_uses_default_prompt(recording_hub) -> None:
    schema = {"type": "object", "properties": {"bpm": {"type": "number"}}}
    await pipelines.understand_audio(
        recording_hub, "a.wav", transcribe=False, json_schema=schema,
    )
    assert (recording_hub.args_for("audio-to-json")["prompt"]
            == "Extract structured data from this audio.")


async def test_understand_audio_json_prompt_without_schema_is_noop(recording_hub) -> None:
    # The schema is the trigger: a json_prompt with no schema records no call
    # (a documented no-op, not a silent partial extraction).
    await pipelines.understand_audio(
        recording_hub, "a.wav", transcribe=False, json_prompt="extract bpm",
    )
    assert "audio-to-json" not in recording_hub.tool_sequence


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


# --- integration-contract guards (the blind spot that let the preset bug ship) ---

# The stemmy-loops export-deliverables tool accepts ONLY these names and raises
# ValueError("unknown preset") otherwise. RecordingHub can't reach the real tool,
# so assert our outgoing presets stay inside the allow-list here.
_VALID_EXPORT_PRESETS = {"distribution_44k_16", "production_48k_24", "master_96k_24"}


def test_default_presets_match_server_allow_list() -> None:
    assert set(pipelines.DEFAULT_PRESETS) <= _VALID_EXPORT_PRESETS


async def test_master_track_presets_are_server_valid(recording_hub) -> None:
    await pipelines.master_track(recording_hub, "m.wav", "o.wav")
    presets = recording_hub.args_for("export-deliverables")["presets"]
    assert set(presets) <= _VALID_EXPORT_PRESETS, f"invalid: {set(presets) - _VALID_EXPORT_PRESETS}"


async def test_loops_presets_are_server_valid(recording_hub) -> None:
    await pipelines.loops_to_deliverables(recording_hub, "d.wav", 120.0)
    presets = recording_hub.args_for("export-deliverables")["presets"]
    assert set(presets) <= _VALID_EXPORT_PRESETS, f"invalid: {set(presets) - _VALID_EXPORT_PRESETS}"


# mastering-feedback / detect-mix-issues accept ONLY these Literals server-side.
_VALID_FEEDBACK_MOODS = {"general", "streaming", "club", "broadcast", "vinyl"}
_VALID_SEVERITIES = {"any", "moderate", "serious"}


@pytest.mark.parametrize("platform", pipelines.PLATFORM_CHOICES)
async def test_every_platform_choice_maps_to_valid_feedback_mood(
    recording_hub, platform
) -> None:
    await pipelines.master_track(recording_hub, "m.wav", "o.wav", target_platform=platform)
    mood = recording_hub.args_for("mastering-feedback")["target_platform"]
    assert mood in _VALID_FEEDBACK_MOODS, f"{platform!r} -> invalid mood {mood!r}"


def test_severity_choices_are_server_valid() -> None:
    assert set(pipelines.SEVERITY_CHOICES) <= _VALID_SEVERITIES


def test_deliverables_dir_is_masters_sibling_not_child() -> None:
    # Documented layout: projects/<t>/deliverables (sibling of masters/), not
    # projects/<t>/masters/deliverables.
    assert (
        pipelines._deliverables_dir("projects/song/masters/song.master.wav")
        == "projects/song/deliverables"
    )
    # Non-masters location: deliverables sits next to the file.
    assert pipelines._deliverables_dir("a/b/loop.wav") == "a/b/deliverables"


async def test_pipeline_propagates_tool_call_error() -> None:
    """A failing tool must surface as ToolCallError, not be swallowed mid-pipeline."""
    from ship_studios.mcp_client import ToolCallError

    class _BoomHub:
        async def call_tool(self, server_key, name, args=None):
            raise ToolCallError(server_key, name, "boom")

    with pytest.raises(ToolCallError):
        await pipelines.master_track(_BoomHub(), "m.wav", "o.wav")


# --- FIX 1: top_n forwards to find-loops but never re-caps the returned set -----


async def test_loops_to_deliverables_does_not_recap_returned_loops() -> None:
    # top_n is PER-bar-length on the server; find-loops can return more than top_n
    # total across bar lengths. The pipeline must process every loop it returned,
    # not silently slice down to top_n again (the C-unit bug).
    from tests.conftest import RecordingHub

    hub = RecordingHub(canned=_find_loops_canned("out", "a.wav", "b.wav", "c.wav"))
    result = await pipelines.loops_to_deliverables(hub, "drums.wav", 120.0, top_n=2)
    assert hub.args_for("find-loops")["top_n"] == 2  # still forwarded to the server
    # all three returned loops are processed (not capped back to 2).
    assert [d["loop"] for d in result["loops"]] == ["out/a.wav", "out/b.wav", "out/c.wav"]
    assert hub.tool_sequence.count("render-mastered") == 3


async def test_loops_to_deliverables_max_total_loops_caps_separately() -> None:
    # The explicit, separate cap DOES slice the total set when set.
    from tests.conftest import RecordingHub

    hub = RecordingHub(canned=_find_loops_canned("out", "a.wav", "b.wav", "c.wav"))
    result = await pipelines.loops_to_deliverables(
        hub, "drums.wav", 120.0, top_n=5, max_total_loops=2
    )
    assert hub.args_for("find-loops")["top_n"] == 5  # top_n is untouched
    assert [d["loop"] for d in result["loops"]] == ["out/a.wav", "out/b.wav"]
    assert hub.tool_sequence.count("render-mastered") == 2


# --- FIX 2: master-track surfaces a derived streaming-compliance verdict --------


def test_streaming_compliant_all_true() -> None:
    res = {"platforms": [{"name": "spotify", "fully_compliant": True}]}
    assert pipelines._streaming_compliant(res) is True


def test_streaming_compliant_any_false() -> None:
    res = {"platforms": [
        {"name": "spotify", "fully_compliant": True},
        {"name": "tidal", "fully_compliant": False},
    ]}
    assert pipelines._streaming_compliant(res) is False


@pytest.mark.parametrize(
    "res",
    [
        "some text result",                       # not a dict
        {},                                       # no platforms key
        {"platforms": []},                        # empty list
        {"platforms": "nope"},                    # wrong type
        {"platforms": [{"name": "x"}]},           # platform lacks the bool flag
        {"platforms": [{"fully_compliant": "y"}]},  # flag not a bool
    ],
)
def test_streaming_compliant_none_on_unexpected_shape(res) -> None:
    # Defensive: never raise, return None when the verdict isn't discoverable.
    assert pipelines._streaming_compliant(res) is None


async def test_master_track_surfaces_streaming_compliant() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub(canned={
        "check-streaming-targets": {"platforms": [
            {"name": "spotify", "fully_compliant": True}
        ]}
    })
    result = await pipelines.master_track(hub, "m.wav", "o.wav", target_platform="spotify")
    assert result["streaming_compliant"] is True


async def test_master_track_streaming_compliant_false_when_noncompliant() -> None:
    from tests.conftest import RecordingHub

    hub = RecordingHub(canned={
        "check-streaming-targets": {"platforms": [
            {"name": "spotify", "fully_compliant": False}
        ]}
    })
    result = await pipelines.master_track(hub, "m.wav", "o.wav", target_platform="spotify")
    assert result["streaming_compliant"] is False


async def test_master_track_streaming_compliant_none_on_text_result(recording_hub) -> None:
    # The default RecordingHub returns {} (unrecognised) -> verdict is None, no raise.
    result = await pipelines.master_track(recording_hub, "m.wav", "o.wav")
    assert result["streaming_compliant"] is None


# --- FIX 4: live tool-name contract test (spelling = hyphen vs underscore) ------

#: Every distinct (server, tool) pair any pipeline can emit. Collected by driving
#: the pipelines (all conditional branches included) against a RecordingHub so the
#: set tracks the code instead of being hand-maintained — the one place that
#: enforces the exact tool spelling against the LIVE servers.
async def _all_emitted_server_tool_pairs() -> set[tuple[str, str]]:
    from tests.conftest import RecordingHub

    pairs: set[tuple[str, str]] = set()

    def _collect(hub: RecordingHub) -> None:
        pairs.update(hub.server_tool_sequence)

    # master-track (a streaming-service target exercises check-streaming-targets'
    # platforms branch).
    h = RecordingHub()
    await pipelines.master_track(h, "m.wav", "o.wav", target_platform="spotify")
    _collect(h)

    # master-track via the master-assistant plan step (covers master-assistant).
    h = RecordingHub()
    await pipelines.master_track(h, "m.wav", "o.wav", assistant=True, style="indie")
    _collect(h)

    # mix-check with EVERY corrective branch so the live contract sees them all
    # (apply-eq, de-ess, suppress-resonances, apply-dynamic-eq, excite-loop,
    # compress-loop, multiband-compress).
    h = RecordingHub()
    await pipelines.mix_check(
        h, "m.wav",
        eq_bands=[{"type": "bell", "freq_hz": 1.0, "gain_db": 0.0, "q": 1.0}],
        deess={}, suppress={},
        dynamic_eq_bands=[
            {"freq_hz": 1.0, "gain_db": 0.0, "q": 1.0, "threshold_db": -24.0}
        ],
        excite={}, compress=True, multiband={},
    )
    _collect(h)

    # reference-match WITH the apply-eq branch.
    h = RecordingHub()
    await pipelines.reference_match(
        h, "m.wav", "r.wav",
        eq_bands=[{"type": "bell", "freq_hz": 1.0, "gain_db": 0.0, "q": 1.0}],
    )
    _collect(h)

    # loops-to-deliverables with describe (covers find-loops..describe-loops).
    h = RecordingHub(canned=_find_loops_canned("out", "a.wav"))
    await pipelines.loops_to_deliverables(h, "d.wav", 120.0, out_dir="out", describe=True)
    _collect(h)

    # understand-audio with EVERY analysis enabled (every gemini understanding tool).
    h = RecordingHub()
    await pipelines.understand_audio(
        h, "a.wav", transcribe=True, region=(0.0, 1.0, "?"),
        event_description="kick", labels=["x"], compare_paths=["b.wav"],
        json_schema={"type": "object"},
    )
    _collect(h)

    # house-curve (build-target-profile -> match-to-profile -> match-eq), with a
    # canned profile delta so the match-eq render branch fires.
    h = RecordingHub(
        canned={"match-to-profile": {"bands": [{"freq_hz": 1.0, "delta_db": 0.0}]}}
    )
    await pipelines.house_curve(h, "m.wav", ["r.wav"])
    _collect(h)

    # batch-master (per-track master chain + analyze-album-normalization).
    h = RecordingHub()
    await pipelines.batch_master(h, ["m.wav"])
    _collect(h)

    return pairs


def _live_contract_reason() -> str | None:
    """Why the live contract test should skip, or None if it can run.

    Opt-in by default: launching two real ``uv run`` subprocesses is slow and
    needs synced sibling repos, so we only do it when SHIP_STUDIOS_LIVE_CONTRACT
    is truthy. Even then we bail cleanly if the SDK or a sibling repo is absent.
    """
    import os

    if not os.environ.get("SHIP_STUDIOS_LIVE_CONTRACT"):
        return "set SHIP_STUDIOS_LIVE_CONTRACT=1 to launch the real servers"
    try:
        import mcp  # noqa: F401
    except ImportError:
        return "mcp SDK not installed in this venv"
    from ship_studios import config

    for label, directory in (
        ("stemmy-loops", config.loops_dir()),
        ("stemmy-gemini", config.gemini_dir()),
    ):
        if not (directory / "pyproject.toml").is_file():
            return f"{label} sibling not synced at {directory}"
    return None


async def test_live_tool_names_exist_on_servers() -> None:
    """Open the REAL hub; assert every tool a pipeline emits exists live.

    This is the ONLY test that enforces the hyphen-vs-underscore tool-name
    contract against the actual servers; everything else runs against a fake.
    Fully guarded — it SKIPS (never fails) when launching the real servers isn't
    feasible, with a reason. Also checks the shadow allow-lists are subsets of the
    live vocabularies wherever those are discoverable from the tool surface.
    """
    reason = _live_contract_reason()
    if reason is not None:
        pytest.skip(f"live contract test skipped — {reason}")

    from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER
    from ship_studios.mcp_client import open_hub

    emitted = await _all_emitted_server_tool_pairs()

    async with open_hub() as hub:
        live: dict[str, set[str]] = {}
        for key in (LOOPS_SERVER, GEMINI_SERVER):
            tools = await hub.list_tools(key)
            live[key] = {t.name for t in tools}

    # 1) Every (server, tool) a pipeline emits must exist on that server, spelled
    #    exactly. A hyphen/underscore typo fails right here.
    missing = sorted(
        f"{server}:{tool}" for server, tool in emitted if tool not in live[server]
    )
    assert not missing, f"pipeline tools absent from the live servers: {missing}"

    # 2) Shadow allow-lists vs the live vocabulary, where discoverable. The export
    #    presets / feedback moods / severities / streaming services live in each
    #    tool's input *schema* (an enum), which isn't exposed uniformly across SDK
    #    versions — so probe defensively and only assert when we actually find the
    #    enum. (A missing enum degrades to "couldn't verify", not a failure.)
    schemas = {}
    async with open_hub() as hub:
        for key in (LOOPS_SERVER, GEMINI_SERVER):
            schemas[key] = {
                t.name: getattr(t, "inputSchema", None) for t in await hub.list_tools(key)
            }

    def _enum_for(server: str, tool: str, field: str) -> set[str] | None:
        schema = schemas.get(server, {}).get(tool)
        if not isinstance(schema, dict):
            return None
        props = schema.get("properties")
        if not isinstance(props, dict):
            return None
        spec = props.get(field)
        if not isinstance(spec, dict):
            return None
        # A scalar enum sits at properties.<field>.enum; an array param (e.g.
        # check-streaming-targets.platforms) carries it under items.enum.
        enum = spec.get("enum")
        if enum is None and isinstance(spec.get("items"), dict):
            enum = spec["items"].get("enum")
        return set(enum) if isinstance(enum, list) and all(
            isinstance(v, str) for v in enum
        ) else None

    checks = [
        ("export presets", _enum_for(LOOPS_SERVER, "export-deliverables", "presets"),
         set(pipelines.DEFAULT_PRESETS)),
        ("feedback moods", _enum_for(GEMINI_SERVER, "mastering-feedback", "target_platform"),
         pipelines._FEEDBACK_MOODS),
        ("severities", _enum_for(GEMINI_SERVER, "detect-mix-issues", "severity_threshold"),
         set(pipelines.SEVERITY_CHOICES)),
        ("streaming services", _enum_for(GEMINI_SERVER, "check-streaming-targets", "platforms"),
         set(pipelines._STREAMING_SERVICES.values())),
    ]
    for label, live_vocab, ours in checks:
        if live_vocab is None:
            continue  # enum not discoverable from this server's schema; skip silently
        extra = ours - live_vocab
        assert not extra, f"{label}: {sorted(extra)} not in live vocabulary {sorted(live_vocab)}"
