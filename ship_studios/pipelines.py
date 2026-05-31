"""Async pipeline orchestrators.

Each function sequences ``hub.call_tool`` invocations across the two servers
in the exact order the blueprint defines, using ONLY verified tool names and
verified parameter keys. Every step appends a ``{server, tool, args, result}``
record to an ordered list so callers (and tests) can see precisely what ran.

Pipelines never invent tool names or parameters. The create -> mix -> master
-> deliver philosophy is encoded purely as call ordering here; the actual DSP
and perceptual work lives in the two sibling servers.

The ``hub`` argument is any object exposing
``async call_tool(server_key, name, args) -> result`` — the real
:class:`ship_studios.mcp_client.Hub` in production, a fake in tests.
"""
from __future__ import annotations

from typing import Any, Protocol

from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER


class SupportsCallTool(Protocol):
    """Structural type for whatever the pipelines drive (real Hub or fake)."""

    async def call_tool(
        self, server_key: str, name: str, args: dict[str, Any] | None = None
    ) -> Any: ...


class _Recorder:
    """Calls a tool through the hub and records the step for the result dict."""

    def __init__(self, hub: SupportsCallTool) -> None:
        self._hub = hub
        self.steps: list[dict[str, Any]] = []

    async def run(
        self, server_key: str, tool: str, args: dict[str, Any]
    ) -> Any:
        result = await self._hub.call_tool(server_key, tool, args)
        self.steps.append(
            {"server": server_key, "tool": tool, "args": args, "result": result}
        )
        return result


async def master_track(
    hub: SupportsCallTool,
    mix_path: str,
    out_path: str,
    *,
    target_lufs: float = -14.0,
    ceiling_dbtp: float = -1.0,
    target_platform: str = "spotify",
    high_pass_hz: float | None = None,
    transient_shape: float | None = None,
    bit_depth: int | None = None,
    sample_rate: int | None = None,
    deliverables_dir: str | None = None,
    presets: list[str] | None = None,
) -> dict[str, Any]:
    """Pipeline 1 — measure source, get a perceptual read, render, verify, export.

    Order (verified tools): measure-loudness / measure-spectrum /
    measure-stereo / check-clipping / measure-distortion (loops) ->
    mastering-feedback (gemini) -> render-mastered (loops) ->
    check-streaming-targets (gemini) -> export-deliverables (loops).
    """
    rec = _Recorder(hub)

    await rec.run(LOOPS_SERVER, "measure-loudness", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "measure-spectrum", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "measure-stereo", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "check-clipping", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "measure-distortion", {"path": mix_path})

    await rec.run(
        GEMINI_SERVER,
        "mastering-feedback",
        {"path": mix_path, "target_platform": target_platform},
    )

    render_args: dict[str, Any] = {
        "path": mix_path,
        "out_path": out_path,
        "target_lufs": target_lufs,
        "ceiling_dbtp": ceiling_dbtp,
    }
    if high_pass_hz is not None:
        render_args["high_pass_hz"] = high_pass_hz
    if transient_shape is not None:
        render_args["transient_shape"] = transient_shape
    if bit_depth is not None:
        render_args["bit_depth"] = bit_depth
    if sample_rate is not None:
        render_args["sample_rate"] = sample_rate
    await rec.run(LOOPS_SERVER, "render-mastered", render_args)

    await rec.run(GEMINI_SERVER, "check-streaming-targets", {"path": out_path})

    export_args: dict[str, Any] = {
        "path": out_path,
        "out_dir": deliverables_dir or _sibling_dir(out_path, "deliverables"),
        "presets": presets or ["44.1/16", "48/24", "96/24"],
        "tag": True,
    }
    await rec.run(LOOPS_SERVER, "export-deliverables", export_args)

    return {"pipeline": "master-track", "input": mix_path, "steps": rec.steps}


async def mix_check(
    hub: SupportsCallTool,
    mix_path: str,
    *,
    severity_threshold: str = "minor",
    eq_bands: list[dict[str, Any]] | None = None,
    eq_out_path: str | None = None,
    compress: bool = False,
    compress_out_path: str | None = None,
) -> dict[str, Any]:
    """Pipeline 2 — fuse perceptual + measurement views into corrective moves.

    Order (verified tools): detect-mix-issues / analyze-mix-balance (gemini)
    -> measure-loudness / measure-spectrum / measure-stereo (loops) ->
    find-resonances / find-sibilance / analyze-phase-mono (gemini) ->
    apply-eq [+ compress-loop] (loops). The EQ/compression steps only run
    when concrete moves are supplied — diagnosis alone never mutates audio.
    """
    rec = _Recorder(hub)

    await rec.run(
        GEMINI_SERVER,
        "detect-mix-issues",
        {"path": mix_path, "severity_threshold": severity_threshold},
    )
    await rec.run(GEMINI_SERVER, "analyze-mix-balance", {"path": mix_path})

    await rec.run(LOOPS_SERVER, "measure-loudness", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "measure-spectrum", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "measure-stereo", {"path": mix_path})

    await rec.run(GEMINI_SERVER, "find-resonances", {"path": mix_path})
    await rec.run(GEMINI_SERVER, "find-sibilance", {"path": mix_path})
    await rec.run(GEMINI_SERVER, "analyze-phase-mono", {"path": mix_path})

    if eq_bands is not None:
        await rec.run(
            LOOPS_SERVER,
            "apply-eq",
            {
                "path": mix_path,
                "out_path": eq_out_path or _suffix_path(mix_path, "eq"),
                "bands": eq_bands,
            },
        )
    if compress:
        comp_in = eq_out_path or _suffix_path(mix_path, "eq") if eq_bands else mix_path
        await rec.run(
            LOOPS_SERVER,
            "compress-loop",
            {
                "path": comp_in,
                "out_path": compress_out_path or _suffix_path(mix_path, "comp"),
            },
        )

    return {"pipeline": "mix-check", "input": mix_path, "steps": rec.steps}


async def reference_match(
    hub: SupportsCallTool,
    mix_path: str,
    ref_path: str,
    *,
    goal: str = "match the reference tonal balance and loudness",
    eq_bands: list[dict[str, Any]] | None = None,
    eq_out_path: str | None = None,
    ab_out_path: str | None = None,
) -> dict[str, Any]:
    """Pipeline 3 — derive numeric + perceptual deltas, EQ, render an A/B.

    Order (verified tools): match-reference-numeric / compare-to-reference
    (gemini) -> compare-tonality (loops) -> apply-eq (loops) -> render-ab
    (loops). apply-eq runs only when reconciled bands are supplied.
    """
    rec = _Recorder(hub)

    await rec.run(
        GEMINI_SERVER,
        "match-reference-numeric",
        {"mix_path": mix_path, "reference_path": ref_path},
    )
    await rec.run(
        GEMINI_SERVER,
        "compare-to-reference",
        {"mix_path": mix_path, "reference_path": ref_path, "goal": goal},
    )
    await rec.run(
        LOOPS_SERVER,
        "compare-tonality",
        {"loop_path": mix_path, "reference_path": ref_path},
    )

    corrected = mix_path
    if eq_bands is not None:
        corrected = eq_out_path or _suffix_path(mix_path, "matched")
        await rec.run(
            LOOPS_SERVER,
            "apply-eq",
            {"path": mix_path, "out_path": corrected, "bands": eq_bands},
        )

    await rec.run(
        LOOPS_SERVER,
        "render-ab",
        {
            "processed": corrected,
            "reference": ref_path,
            "out_path": ab_out_path or _suffix_path(mix_path, "ab"),
        },
    )

    return {
        "pipeline": "reference-match",
        "input": mix_path,
        "reference": ref_path,
        "steps": rec.steps,
    }


async def loops_to_deliverables(
    hub: SupportsCallTool,
    input_path: str,
    bpm: float,
    *,
    out_dir: str | None = None,
    deliverables_dir: str | None = None,
    bars: list[int] | None = None,
    top_n: int | None = None,
    separate: bool = False,
    target_lufs: float = -10.0,
    ceiling_dbtp: float = -1.0,
    originator: str = "ship-studios",
    key: str | None = None,
    root_note: int | None = None,
    presets: list[str] | None = None,
    describe: bool = False,
) -> dict[str, Any]:
    """Pipeline 4 — extract loops, clean/seam, master, tag, export.

    Order (verified tools): find-loops (loops) -> per-loop clean-loop ->
    optimize-seam -> render-mastered -> tag-deliverable -> export-deliverables
    (all loops). Optional describe-loops (gemini-backed via the loops server)
    attaches audible notes. This orchestrator runs the find + per-deliverable
    chain on the *representative* loop path returned by find-loops; callers
    that fan the chain across many loops re-enter per WAV.
    """
    rec = _Recorder(hub)

    find_args: dict[str, Any] = {"path": input_path, "bpm": bpm, "separate": separate}
    if bars is not None:
        find_args["bars"] = bars
    if top_n is not None:
        find_args["top_n"] = top_n
    if out_dir is not None:
        find_args["out_dir"] = out_dir
    manifest = await rec.run(LOOPS_SERVER, "find-loops", find_args)

    loop_in = _first_loop_path(manifest) or input_path
    cleaned = _suffix_path(loop_in, "clean")
    seamed = _suffix_path(loop_in, "seam")
    mastered = _suffix_path(loop_in, "master")
    tagged = _suffix_path(loop_in, "tagged")

    await rec.run(
        LOOPS_SERVER, "clean-loop", {"path": loop_in, "out_path": cleaned}
    )
    await rec.run(
        LOOPS_SERVER, "optimize-seam", {"path": cleaned, "out_path": seamed}
    )
    await rec.run(
        LOOPS_SERVER,
        "render-mastered",
        {
            "path": seamed,
            "out_path": mastered,
            "target_lufs": target_lufs,
            "ceiling_dbtp": ceiling_dbtp,
        },
    )

    tag_args: dict[str, Any] = {
        "path": mastered,
        "out_path": tagged,
        "bpm": bpm,
        "originator": originator,
    }
    if bars is not None and len(bars) == 1:
        tag_args["bars"] = bars[0]
    if key is not None:
        tag_args["key"] = key
    if root_note is not None:
        tag_args["root_note"] = root_note
    await rec.run(LOOPS_SERVER, "tag-deliverable", tag_args)

    await rec.run(
        LOOPS_SERVER,
        "export-deliverables",
        {
            "path": tagged,
            "out_dir": deliverables_dir or _sibling_dir(loop_in, "deliverables"),
            "presets": presets or ["44.1/16", "48/24", "96/24"],
            "tag": True,
        },
    )

    if describe:
        describe_target = out_dir or _parent_dir(loop_in)
        await rec.run(LOOPS_SERVER, "describe-loops", {"out_dir": describe_target})

    return {
        "pipeline": "loops-to-deliverables",
        "input": input_path,
        "bpm": bpm,
        "steps": rec.steps,
    }


async def understand_audio(
    hub: SupportsCallTool,
    path: str,
    *,
    transcribe: bool = True,
    diarize: bool = False,
    region: tuple[float, float, str] | None = None,
    event_description: str | None = None,
    labels: list[str] | None = None,
    multi_label: bool = False,
    compare_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Pipeline 5 — Gemini perceptual analysis (no rendering).

    Runs only the verified gemini understanding tools the caller asks for:
    transcribe-audio, describe-audio-region, extract-audio-events,
    classify-audio, compare-audio-files. Never mutates the audio.
    """
    rec = _Recorder(hub)

    if transcribe:
        await rec.run(
            GEMINI_SERVER,
            "transcribe-audio",
            {"path": path, "diarize": diarize},
        )
    if region is not None:
        start_s, end_s, prompt = region
        await rec.run(
            GEMINI_SERVER,
            "describe-audio-region",
            {"path": path, "start_s": start_s, "end_s": end_s, "prompt": prompt},
        )
    if event_description is not None:
        await rec.run(
            GEMINI_SERVER,
            "extract-audio-events",
            {"path": path, "event_description": event_description},
        )
    if labels is not None:
        await rec.run(
            GEMINI_SERVER,
            "classify-audio",
            {"path": path, "labels": labels, "multi_label": multi_label},
        )
    if compare_paths is not None:
        await rec.run(
            GEMINI_SERVER,
            "compare-audio-files",
            {"paths": [path, *compare_paths]},
        )

    return {"pipeline": "understand-audio", "input": path, "steps": rec.steps}


# --- small path helpers (pure string math, no filesystem touch) -------------


def _suffix_path(path: str, suffix: str) -> str:
    """Insert ``.<suffix>`` before the extension: a/b.wav -> a/b.<suffix>.wav."""
    from pathlib import PurePosixPath

    p = PurePosixPath(path)
    return str(p.with_name(f"{p.stem}.{suffix}{p.suffix}"))


def _sibling_dir(path: str, dirname: str) -> str:
    """Return ``<parent of path>/<dirname>`` as a string."""
    from pathlib import PurePosixPath

    return str(PurePosixPath(path).parent / dirname)


def _parent_dir(path: str) -> str:
    """Return the parent directory of ``path`` as a string."""
    from pathlib import PurePosixPath

    return str(PurePosixPath(path).parent)


def _first_loop_path(manifest: Any) -> str | None:
    """Best-effort extraction of the first loop WAV path from a find-loops result.

    find-loops returns manifest data; the manifest's exact shape is the
    loops server's contract, so we probe a couple of likely shapes and fall
    back to ``None`` (callers default to the original input). Kept defensive
    so a manifest-shape change never crashes the orchestrator.
    """
    if isinstance(manifest, dict):
        loops = manifest.get("loops")
        if isinstance(loops, list) and loops:
            first = loops[0]
            if isinstance(first, dict):
                for key in ("path", "wav", "wav_path", "file"):
                    val = first.get(key)
                    if isinstance(val, str):
                        return val
        for key in ("out_dir", "loop_path", "path"):
            val = manifest.get(key)
            if isinstance(val, str):
                return val
    return None
