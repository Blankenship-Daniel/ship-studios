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

from pathlib import PurePosixPath
from typing import Any, Protocol

from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER

#: Verified ``export-deliverables`` preset names (stemmy-loops ``_dsp/deliverables.py``
#: ``_PRESETS``). The server raises ``ValueError("unknown preset")`` for anything
#: else — these are NOT free-form "<sr>/<bits>" labels.
DEFAULT_PRESETS: list[str] = [
    "distribution_44k_16",  # 44.1 kHz / 16-bit
    "production_48k_24",    # 48 kHz / 24-bit
    "master_96k_24",        # 96 kHz / 24-bit
]

#: A release target ("spotify", "club", …) means two different things to the two
#: servers, which use *disjoint* vocabularies — passing a streaming-service name
#: to the wrong one is rejected. Keep both mappings here so a single
#: ``target_platform`` arg drives both calls correctly:
#:   * ``mastering-feedback`` wants a critique "mood"
#:     (``Literal["general","streaming","club","broadcast","vinyl"]``).
#:   * ``check-streaming-targets`` wants a streaming-service name
#:     (``spotify``/``apple_music``/``youtube``/``tidal``).
_FEEDBACK_MOODS: frozenset[str] = frozenset(
    {"general", "streaming", "club", "broadcast", "vinyl"}
)
#: Streaming-service aliases -> the exact name ``check-streaming-targets`` expects.
_STREAMING_SERVICES: dict[str, str] = {
    "spotify": "spotify",
    "apple": "apple_music",
    "apple_music": "apple_music",
    "youtube": "youtube",
    "tidal": "tidal",
}
#: The full set the CLI ``--platform`` choice accepts (services + critique moods).
PLATFORM_CHOICES: list[str] = sorted(_STREAMING_SERVICES) + sorted(_FEEDBACK_MOODS)


def _feedback_mood(target_platform: str) -> str:
    """``mastering-feedback`` mood for a release target.

    Any streaming service maps to ``"streaming"``; an explicit critique mood
    (``club``/``broadcast``/``vinyl``/``general``) passes through; anything else
    falls back to ``"general"`` so the call is always schema-valid.
    """
    t = target_platform.lower()
    if t in _FEEDBACK_MOODS:
        return t
    return "streaming" if t in _STREAMING_SERVICES else "general"


def _streaming_service(target_platform: str) -> str | None:
    """``check-streaming-targets`` service name, or ``None`` if not a service."""
    return _STREAMING_SERVICES.get(target_platform.lower())


def _streaming_compliant(result: Any) -> bool | None:
    """Best-effort overall pass/fail from a ``check-streaming-targets`` result.

    The real tool returns ``{"platforms": [{"fully_compliant": bool, ...}, ...]}``.
    Returns ``True`` only when *every* reported platform is fully compliant,
    ``False`` when any is not, and ``None`` when the shape is unrecognised (a
    dict without a usable platform list, or plain text) — so a caller can see
    the verdict without auto-re-rendering. Never raises on an unexpected shape.
    """
    if not isinstance(result, dict):
        return None
    platforms = result.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        return None
    flags = [
        p["fully_compliant"]
        for p in platforms
        if isinstance(p, dict) and isinstance(p.get("fully_compliant"), bool)
    ]
    if not flags:
        return None
    return all(flags)


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
        {"path": mix_path, "target_platform": _feedback_mood(target_platform)},
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

    streaming_args: dict[str, Any] = {"path": out_path}
    service = _streaming_service(target_platform)
    if service is not None:
        # Limit the compliance report to the actual release service; without a
        # service (a critique-mood target like "club") check every default.
        streaming_args["platforms"] = [service]
    streaming = await rec.run(GEMINI_SERVER, "check-streaming-targets", streaming_args)
    compliant = _streaming_compliant(streaming)

    export_args: dict[str, Any] = {
        "path": out_path,
        "out_dir": deliverables_dir or _deliverables_dir(out_path),
        "presets": presets or DEFAULT_PRESETS,
        "tag": True,
    }
    await rec.run(LOOPS_SERVER, "export-deliverables", export_args)

    return {
        "pipeline": "master-track",
        "input": mix_path,
        "streaming_compliant": compliant,  # True/False/None — see _streaming_compliant
        "steps": rec.steps,
    }


#: Valid ``detect-mix-issues`` severity floors (the server's Literal). "minor"
#: is NOT one of them — it raises ValueError server-side.
SEVERITY_CHOICES: list[str] = ["any", "moderate", "serious"]


async def mix_check(
    hub: SupportsCallTool,
    mix_path: str,
    *,
    severity_threshold: str = "any",
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
        comp_in = (eq_out_path or _suffix_path(mix_path, "eq")) if eq_bands else mix_path
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
    match_strength: float = 0.5,
    match_phase: str = "minimum",
    match_out_path: str | None = None,
    eq_bands: list[dict[str, Any]] | None = None,
    eq_out_path: str | None = None,
    ab_out_path: str | None = None,
) -> dict[str, Any]:
    """Pipeline 3 — derive numeric + perceptual deltas, EQ-match, render an A/B.

    Order (verified tools): match-reference-numeric / compare-to-reference
    (gemini) -> compare-tonality (loops) -> match-eq (loops) -> apply-eq
    (loops) -> render-ab (loops). match-eq is the primary corrective: it renders
    the source-minus-reference delta as a min/linear-phase FIR toward the
    reference. apply-eq runs only when reconciled residual bands are supplied,
    layered on the matched output for surgical bells/tilt.
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

    corrected = match_out_path or _suffix_path(mix_path, "matched")
    await rec.run(
        LOOPS_SERVER,
        "match-eq",
        {
            "source_path": mix_path,
            "reference_path": ref_path,
            "out_path": corrected,
            "match_strength": match_strength,
            "phase": match_phase,
        },
    )

    if eq_bands is not None:
        residual = eq_out_path or _suffix_path(mix_path, "matched-eq")
        await rec.run(
            LOOPS_SERVER,
            "apply-eq",
            {"path": corrected, "out_path": residual, "bands": eq_bands},
        )
        corrected = residual

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
    max_total_loops: int | None = None,
    separate: bool = False,
    target_lufs: float = -10.0,
    ceiling_dbtp: float = -1.0,
    originator: str = "ship-studios",
    key: str | None = None,
    root_note: int | None = None,
    presets: list[str] | None = None,
    describe: bool = False,
) -> dict[str, Any]:
    """Pipeline 4 — extract loops, then clean/seam/master/tag/export EACH loop.

    Order (verified tools): find-loops (loops) -> for EVERY loop find-loops
    returned: clean-loop -> optimize-seam -> render-mastered -> tag-deliverable
    -> export-deliverables. Optional describe-loops (gemini-backed via the loops
    server) annotates the whole set once at the end. If the manifest can't be
    parsed (e.g. a shape change) or is empty, the chain falls back to running
    once on ``input_path``.

    ``top_n`` is forwarded to find-loops, where the server applies it PER bar
    length (so a 3-bar-length request can return up to 3*top_n diverse loops);
    the pipeline then processes exactly that set. ``max_total_loops`` is a
    SEPARATE optional cap on the *total* number of loops the per-loop chain
    runs over — only sliced when set, so the two never share a meaning.
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

    # find-loops already applied top_n (per bar length); don't re-cap by it here
    # — that would silently discard the diverse loops selected across other bar
    # lengths. Slice only by the explicit, separate max_total_loops when set.
    loop_paths = _loop_paths(manifest)
    if max_total_loops is not None:
        loop_paths = loop_paths[:max_total_loops]
    if not loop_paths:
        loop_paths = [input_path]
    manifest_out = manifest.get("out_dir") if isinstance(manifest, dict) else None

    deliverables: list[dict[str, Any]] = []
    for loop_in in loop_paths:
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
                "out_dir": deliverables_dir or _deliverables_dir(loop_in),
                "presets": presets or DEFAULT_PRESETS,
                "tag": True,
            },
        )
        deliverables.append({"loop": loop_in, "mastered": mastered, "tagged": tagged})

    if describe:
        describe_target = out_dir or manifest_out or _parent_dir(loop_paths[0])
        await rec.run(LOOPS_SERVER, "describe-loops", {"out_dir": describe_target})

    return {
        "pipeline": "loops-to-deliverables",
        "input": input_path,
        "bpm": bpm,
        "loops": deliverables,
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
    compare_prompt: str | None = None,
    compare_schema: dict[str, Any] | None = None,
    json_prompt: str | None = None,
    json_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pipeline 5 — Gemini perceptual analysis (no rendering).

    Runs only the verified gemini understanding tools the caller asks for:
    transcribe-audio, describe-audio-region, extract-audio-events,
    classify-audio, compare-audio-files (with an optional prompt/schema), and
    audio-to-json (the structured-extraction escape hatch). Never mutates audio.
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
        compare_args: dict[str, Any] = {"paths": [path, *compare_paths]}
        if compare_prompt is not None:
            compare_args["prompt"] = compare_prompt
        if compare_schema is not None:
            compare_args["schema"] = compare_schema
        await rec.run(GEMINI_SERVER, "compare-audio-files", compare_args)
    if json_schema is not None:
        await rec.run(
            GEMINI_SERVER,
            "audio-to-json",
            {
                "path": path,
                "prompt": json_prompt or "Extract structured data from this audio.",
                "schema": json_schema,
            },
        )

    return {"pipeline": "understand-audio", "input": path, "steps": rec.steps}


# --- small path helpers (pure string math, no filesystem touch) -------------


def _suffix_path(path: str, suffix: str) -> str:
    """Insert ``.<suffix>`` before the extension: a/b.wav -> a/b.<suffix>.wav."""
    p = PurePosixPath(path)
    return str(p.with_name(f"{p.stem}.{suffix}{p.suffix}"))


def _deliverables_dir(out_path: str) -> str:
    """Default deliverables dir for a rendered file.

    The documented layout puts deliverables at ``projects/<track>/deliverables/``
    — a *sibling* of ``masters/``, not a child. So when the file sits in a
    ``masters/`` dir, hop up one level; otherwise fall back to a sibling
    ``deliverables/`` next to the file.
    """
    parent = PurePosixPath(out_path).parent
    base = parent.parent if parent.name == "masters" else parent
    return str(base / "deliverables")


def _parent_dir(path: str) -> str:
    """Return the parent directory of ``path`` as a string."""
    return str(PurePosixPath(path).parent)


def _loop_paths(manifest: Any) -> list[str]:
    """All loop WAV paths from a find-loops result, best-effort.

    The real ``find-loops`` returns ``FindLoopsResponse`` →
    ``{"out_dir": str, "manifest": {"loops": [{"wav": <name relative to out_dir>,
    ...}], ...}}`` — the loop list is nested under ``manifest`` and each ``wav``
    is a *basename* that must be joined to ``out_dir``. A couple of alternate
    shapes are probed too so a manifest change degrades gracefully (callers fall
    back to ``input_path`` when this returns ``[]``); it never raises.
    """
    if not isinstance(manifest, dict):
        return []
    out_dir = manifest.get("out_dir")
    inner = manifest.get("manifest")
    loops = inner.get("loops") if isinstance(inner, dict) else manifest.get("loops")
    if not isinstance(loops, list):
        return []
    paths: list[str] = []
    for loop in loops:
        if not isinstance(loop, dict):
            continue
        name = next(
            (loop[k] for k in ("wav", "path", "wav_path", "file")
             if isinstance(loop.get(k), str)),
            None,
        )
        if name is None:
            continue
        if isinstance(out_dir, str) and not PurePosixPath(name).is_absolute():
            paths.append(str(PurePosixPath(out_dir) / name))
        else:
            paths.append(name)
    return paths
