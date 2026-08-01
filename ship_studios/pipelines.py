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

Result contract
---------------
Every pipeline returns a ``dict[str, Any]`` carrying at least ``"pipeline"``
(the pipeline's hyphenated name) and ``"steps"`` (the ordered list of
:class:`Step` records — one per tool call, on success AND failure). Most also
carry ``"input"`` plus a pipeline-specific result key:

* ``master_track`` — ``input`` + ``streaming_compliant`` (``True``/``False``/``None``).
* ``batch_master`` — ``inputs`` + ``masters`` (the SUCCEEDED master paths) +
  ``tracks`` (per-track ``{input, master, streaming_compliant[, error]}``) +
  ``album`` (a ``{ok, failed, compliant, noncompliant, unknown}`` tally).
* ``mix_check`` — ``input`` + ``output`` (the final corrected WAV; ``== input``
  when no corrective move ran).
* ``reference_match`` — ``input`` + ``reference``.
* ``house_curve`` — ``input`` + ``profile`` + ``output`` + ``matched`` (bool).
* ``stem_master`` / ``unmask_stems`` — ``stems`` + ``corrected`` (name->path).
* ``loops_to_deliverables`` — ``input`` + ``bpm`` + ``loops`` + ``fell_back``
  (bool; processed ``input`` itself because no loops were parseable) +
  ``loop_count``.
* ``understand_audio`` — ``input``.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Protocol, TypedDict

from ship_studios import perf
from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER, GeminiTool, LoopsTool

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

#: Centralized CLI choice constants mirroring the sibling servers' Literals — the
#: same single-source-of-truth pattern as ``PLATFORM_CHOICES``. The CLI imports
#: these instead of re-listing them inline.
#:   * ``INTENT_CHOICES`` — ``master-assistant`` ``intent``.
#:   * ``INTENSITY_CHOICES`` — ``master-assistant`` ``intensity``.
#:   * ``MATCH_PHASE_CHOICES`` — ``match-eq`` ``phase`` (reference-match / house-curve).
INTENT_CHOICES: list[str] = ["loud", "dynamic", "warm", "bright", "balanced", "punchy"]
INTENSITY_CHOICES: list[str] = ["subtle", "medium", "strong"]
MATCH_PHASE_CHOICES: list[str] = ["minimum", "linear", "tilt_only"]


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
    # An entry we cannot read is UNKNOWN, not compliant: dropping it made
    # [{spotify: true}, {tidal: null}] report full compliance while tidal's verdict
    # was never established. Any unreadable entry -> None (unknown overall).
    flags = []
    for p in platforms:
        if not isinstance(p, dict) or not isinstance(p.get("fully_compliant"), bool):
            return None
        flags.append(p["fully_compliant"])
    if not flags:
        return None
    return all(flags)


def _profile_delta_curve(result: Any) -> list[dict[str, float]] | None:
    """Extract a ``match-eq`` ``delta_db_curve`` from a ``match-to-profile`` result.

    ``match-to-profile`` returns ``{"bands": [{"freq_hz", "delta_db", ...}]}``
    where ``delta_db = input − target`` — the same source-minus-reference sign
    ``match-eq``'s ``delta_db_curve`` expects — so we forward ``freq_hz`` +
    ``delta_db`` per band to render the correction. Returns ``None`` when the
    shape is unrecognised (e.g. a fake hub) so the caller skips the render
    gracefully. Never raises.
    """
    if not isinstance(result, dict):
        return None
    bands = result.get("bands")
    if not isinstance(bands, list) or not bands:
        return None
    curve: list[dict[str, float]] = []
    for b in bands:
        if (
            isinstance(b, dict)
            and isinstance(b.get("freq_hz"), (int, float))
            and isinstance(b.get("delta_db"), (int, float))
        ):
            curve.append(
                {"freq_hz": float(b["freq_hz"]), "delta_db": float(b["delta_db"])}
            )
    return curve or None


class SupportsCallTool(Protocol):
    """Structural type for whatever the pipelines drive (real Hub or fake)."""

    async def call_tool(
        self, server_key: str, name: str, args: dict[str, Any] | None = None
    ) -> Any: ...


class Step(TypedDict):
    """One recorded tool call in a pipeline's ``"steps"`` list.

    ``server``/``tool``/``args`` say what was invoked, ``result`` is the tool's
    return (``None`` if it raised), ``elapsed_s`` the wall time, and ``ok``
    whether it succeeded. A failed step is still recorded — it is the one you
    most want in the trace.
    """

    server: str
    tool: str
    args: dict[str, Any]
    result: Any
    elapsed_s: float
    ok: bool


class _Recorder:
    """Calls a tool through the hub and records the step for the result dict."""

    def __init__(self, hub: SupportsCallTool) -> None:
        self._hub = hub
        self.steps: list[Step] = []

    async def run(
        self, server_key: str, tool: str, args: dict[str, Any]
    ) -> Any:
        # Time + record every step, on success AND failure: a failed step is the
        # one you most want in the trace. The extra keys (elapsed_s/ok) are additive
        # — the step dict stays a superset of {server,tool,args,result}. The finally
        # runs before the exception propagates (it does not swallow it).
        start = perf.now()
        result: Any = None
        ok = False
        try:
            result = await self._hub.call_tool(server_key, tool, args)
            ok = True
            return result
        finally:
            self.steps.append(
                {
                    "server": server_key,
                    "tool": tool,
                    "args": args,
                    "result": result,
                    "elapsed_s": round(perf.now() - start, 6),
                    "ok": ok,
                }
            )


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
    assistant: bool = False,
    intent: str = "balanced",
    intensity: str = "medium",
    style: str | None = None,
    _recorder: _Recorder | None = None,
) -> dict[str, Any]:
    """Pipeline 1 — measure source, get a perceptual read, render, verify, export.

    Order (verified tools): measure-loudness / measure-spectrum /
    measure-stereo / check-clipping / measure-distortion (loops) ->
    mastering-feedback (gemini) -> render-mastered (loops) ->
    check-streaming-targets (gemini) -> export-deliverables (loops).

    The perceptual/plan step is ``mastering-feedback`` by default; set
    ``assistant=True`` to use ``master-assistant`` instead (driven by
    ``intent`` / ``intensity`` / ``style``), the doc's step-6 alternative that
    returns a complete typed mastering-chain plan. Either way the render still
    targets ``target_lufs`` / ``ceiling_dbtp`` — the plan is advisory.

    ``_recorder`` lets a caller supply the step sink instead of receiving it only
    via the return value. batch_master passes one so that when a track RAISES, the
    steps it already completed are still in the caller's trace — otherwise `res` is
    never bound, `steps.extend(res[...])` is skipped, and the failing track
    contributes nothing at all, contradicting both this module's docstring and
    ``Step``'s ("a failed step is still recorded — it is the one you most want").
    """
    rec = _recorder if _recorder is not None else _Recorder(hub)

    await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_LOUDNESS, {"path": mix_path})
    await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_SPECTRUM, {"path": mix_path})
    await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_STEREO, {"path": mix_path})
    await rec.run(LOOPS_SERVER, LoopsTool.CHECK_CLIPPING, {"path": mix_path})
    await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_DISTORTION, {"path": mix_path})

    mood = _feedback_mood(target_platform)
    if assistant:
        plan_args: dict[str, Any] = {
            "path": mix_path,
            "intent": intent,
            "intensity": intensity,
            "target_platform": mood,
        }
        if style is not None:
            plan_args["style"] = style
        await rec.run(GEMINI_SERVER, GeminiTool.MASTER_ASSISTANT, plan_args)
    else:
        await rec.run(
            GEMINI_SERVER,
            GeminiTool.MASTERING_FEEDBACK,
            {"path": mix_path, "target_platform": mood},
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
    await rec.run(LOOPS_SERVER, LoopsTool.RENDER_MASTERED, render_args)

    streaming_args: dict[str, Any] = {"path": out_path}
    service = _streaming_service(target_platform)
    if service is not None:
        # Limit the compliance report to the actual release service; without a
        # service (a critique-mood target like "club") check every default.
        streaming_args["platforms"] = [service]
    streaming = await rec.run(
        GEMINI_SERVER, GeminiTool.CHECK_STREAMING_TARGETS, streaming_args
    )
    compliant = _streaming_compliant(streaming)

    export_args: dict[str, Any] = {
        "path": out_path,
        "out_dir": deliverables_dir or _deliverables_dir(out_path),
        "presets": presets or DEFAULT_PRESETS,
        "tag": True,
    }
    await rec.run(LOOPS_SERVER, LoopsTool.EXPORT_DELIVERABLES, export_args)

    return {
        "pipeline": "master-track",
        "input": mix_path,
        "streaming_compliant": compliant,  # True/False/None — see _streaming_compliant
        "steps": rec.steps,
    }


async def batch_master(
    hub: SupportsCallTool,
    mix_paths: list[str],
    *,
    target_lufs: float = -14.0,
    ceiling_dbtp: float = -1.0,
    target_platform: str = "spotify",
    high_pass_hz: float | None = None,
    transient_shape: float | None = None,
    bit_depth: int | None = None,
    sample_rate: int | None = None,
    masters_dir: str | None = None,
    deliverables_dir: str | None = None,
    presets: list[str] | None = None,
    assistant: bool = False,
    intent: str = "balanced",
    intensity: str = "medium",
    style: str | None = None,
    continue_on_error: bool = True,
) -> dict[str, Any]:
    """Pipeline 6 — master a folder of mixes to ONE shared target + album pass.

    Per track: the full master-track chain (measure -> mastering-feedback ->
    render-mastered -> check-streaming-targets -> export-deliverables) to the
    SHARED ``target_lufs`` / ``ceiling_dbtp``. Then a cross-track pass —
    measure-loudness over every master + analyze-album-normalization (the shared
    album gain a platform will actually apply). The consistency read is the
    headline; hand any not-release-ready track to mix-check first.

    One bad track does not sink the batch: by default
    (``continue_on_error=True``) a track whose master chain raises is recorded
    in ``tracks`` with its ``error`` and ``streaming_compliant=None`` and the
    run continues; the album pass then runs over only the masters that
    SUCCEEDED. Pass ``continue_on_error=False`` to re-raise on the first
    failure. The returned ``album`` summary tallies the outcome
    (``{ok, failed, compliant, noncompliant, unknown}``).
    """
    if not mix_paths:
        raise ValueError("batch_master needs at least one mix path")

    tracks: list[dict[str, Any]] = []
    masters: list[str] = []
    steps: list[Step] = []
    outs = _unique_master_outs(mix_paths, masters_dir)
    for mix, out in zip(mix_paths, outs, strict=True):
        track_rec = _Recorder(hub)
        try:
            res = await master_track(
                hub,
                mix,
                out,
                target_lufs=target_lufs,
                ceiling_dbtp=ceiling_dbtp,
                target_platform=target_platform,
                high_pass_hz=high_pass_hz,
                transient_shape=transient_shape,
                bit_depth=bit_depth,
                sample_rate=sample_rate,
                deliverables_dir=deliverables_dir,
                presets=presets,
                assistant=assistant,
                intent=intent,
                intensity=intensity,
                style=style,
                _recorder=track_rec,
            )
        except Exception as exc:
            steps.extend(track_rec.steps)  # keep what this track DID do, incl. the failure
            if not continue_on_error:
                raise
            tracks.append(
                {
                    "input": mix,
                    "master": out,
                    "error": str(exc),
                    "streaming_compliant": None,
                }
            )
            continue
        tracks.append(
            {
                "input": mix,
                "master": out,
                "streaming_compliant": res.get("streaming_compliant"),
            }
        )
        masters.append(out)
        steps.extend(res.get("steps", []))

    # Cross-track album pass over the masters that SUCCEEDED — consistency table
    # + shared album-gain projection. Skip cleanly if every track failed.
    if masters:
        rec = _Recorder(hub)
        for master in masters:
            await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_LOUDNESS, {"path": master})
        await rec.run(
            LOOPS_SERVER,
            LoopsTool.ANALYZE_ALBUM_NORMALIZATION,
            {"paths": masters, "target_lufs": target_lufs, "ceiling_dbtp": ceiling_dbtp},
        )
        steps.extend(rec.steps)

    compliants = [t.get("streaming_compliant") for t in tracks]
    album = {
        "ok": len(masters),
        "failed": sum(1 for t in tracks if "error" in t),
        "compliant": sum(1 for c in compliants if c is True),
        "noncompliant": sum(1 for c in compliants if c is False),
        "unknown": sum(1 for c in compliants if c is None),
    }

    return {
        "pipeline": "batch-master",
        "inputs": list(mix_paths),
        "masters": masters,
        "tracks": tracks,
        "album": album,
        "steps": steps,
    }


#: Valid ``detect-mix-issues`` severity floors (the server's Literal). "minor"
#: is NOT one of them — it raises ValueError server-side.
SEVERITY_CHOICES: list[str] = ["any", "moderate", "serious"]


async def _run_corrective_chain(
    rec: _Recorder,
    path: str,
    spec: dict[str, Any],
    *,
    base_path: str | None = None,
    include_excite: bool,
    include_shape: bool,
    eq_out_path: str | None = None,
    compress_out_path: str | None = None,
) -> str:
    """Apply the shared opt-in per-stem corrective chain; return the final path.

    The ONE ordered chain ``mix_check`` and ``_apply_stem_corrections`` share:
    ``apply-eq -> de-ess -> suppress-resonances -> apply-dynamic-eq ->
    [excite-loop] -> compress-loop -> multiband-compress -> [shape-bands]``.
    ``excite-loop`` runs only when ``include_excite`` (mix-check), ``shape-bands``
    only when ``include_shape`` (the stem helper) — every other step is gated
    purely on a supplied move in ``spec``. Each step reads the prior step's
    output (``cur``) and writes a fresh suffixed file; the suffix is derived from
    ``base_path`` (defaults to ``path``, so a stem suffixes off its own name and
    mix-check off the mix). ``path``/``out_path`` are injected LAST so a spec dict
    can't hijack the chain. ``eq_out_path`` / ``compress_out_path`` override the
    default suffix for those two steps (the mix-check custom-out flags).

    ``spec`` keys: ``eq_bands`` / ``dynamic_eq_bands`` (EQ move lists),
    ``deess`` / ``suppress`` / ``excite`` / ``multiband`` / ``shape_bands``
    (tuning-kwarg dicts; ``{}`` = tool defaults), ``compress`` (bool).
    """
    base = base_path if base_path is not None else path
    cur = path
    eq_bands = spec.get("eq_bands")
    if eq_bands is not None:
        out = eq_out_path or _suffix_path(base, "eq")
        await rec.run(
            LOOPS_SERVER, LoopsTool.APPLY_EQ, {"path": cur, "out_path": out, "bands": eq_bands}
        )
        cur = out
    deess = spec.get("deess")
    if deess is not None:
        out = _suffix_path(base, "deess")
        await rec.run(LOOPS_SERVER, LoopsTool.DE_ESS, {**deess, "path": cur, "out_path": out})
        cur = out
    suppress = spec.get("suppress")
    if suppress is not None:
        out = _suffix_path(base, "deharsh")
        await rec.run(
            LOOPS_SERVER, LoopsTool.SUPPRESS_RESONANCES, {**suppress, "path": cur, "out_path": out}
        )
        cur = out
    dyn = spec.get("dynamic_eq_bands")
    if dyn is not None:
        out = _suffix_path(base, "dyneq")
        await rec.run(
            LOOPS_SERVER, LoopsTool.APPLY_DYNAMIC_EQ, {"path": cur, "out_path": out, "bands": dyn}
        )
        cur = out
    if include_excite:
        excite = spec.get("excite")
        if excite is not None:
            out = _suffix_path(base, "excite")
            await rec.run(
                LOOPS_SERVER, LoopsTool.EXCITE_LOOP, {**excite, "path": cur, "out_path": out}
            )
            cur = out
    if spec.get("compress"):
        out = compress_out_path or _suffix_path(base, "comp")
        await rec.run(LOOPS_SERVER, LoopsTool.COMPRESS_LOOP, {"path": cur, "out_path": out})
        cur = out
    multiband = spec.get("multiband")
    if multiband is not None:
        out = _suffix_path(base, "mbcomp")
        await rec.run(
            LOOPS_SERVER, LoopsTool.MULTIBAND_COMPRESS, {**multiband, "path": cur, "out_path": out}
        )
        cur = out
    if include_shape:
        shape = spec.get("shape_bands")
        if shape is not None:
            out = _suffix_path(base, "shaped")
            await rec.run(
                LOOPS_SERVER, LoopsTool.SHAPE_BANDS, {**shape, "path": cur, "out_path": out}
            )
            cur = out
    return cur


async def mix_check(
    hub: SupportsCallTool,
    mix_path: str,
    *,
    severity_threshold: str = "any",
    eq_bands: list[dict[str, Any]] | None = None,
    eq_out_path: str | None = None,
    deess: dict[str, Any] | None = None,
    suppress: dict[str, Any] | None = None,
    dynamic_eq_bands: list[dict[str, Any]] | None = None,
    excite: dict[str, Any] | None = None,
    compress: bool = False,
    compress_out_path: str | None = None,
    multiband: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pipeline 2 — fuse perceptual + measurement views into corrective moves.

    Order (verified tools): detect-mix-issues / analyze-mix-balance (gemini)
    -> measure-loudness / measure-spectrum / measure-stereo (loops) ->
    find-resonances / find-sibilance / analyze-phase-mono (gemini) -> the
    corrective chain (loops), each step reading the previous step's output:
    apply-eq -> de-ess -> suppress-resonances -> apply-dynamic-eq ->
    excite-loop -> compress-loop -> multiband-compress. Every corrective step is
    opt-in (gated on a supplied move) — diagnosis alone never mutates audio.
    ``deess`` / ``suppress`` / ``excite`` / ``multiband`` are tuning-kwarg dicts
    (``{}`` = the tool's defaults); ``eq_bands`` / ``dynamic_eq_bands`` carry the
    EQ moves. Returns ``output`` = the final corrected WAV (== ``input`` if no
    corrective move ran).
    """
    rec = _Recorder(hub)

    await rec.run(
        GEMINI_SERVER,
        GeminiTool.DETECT_MIX_ISSUES,
        {"path": mix_path, "severity_threshold": severity_threshold},
    )
    await rec.run(GEMINI_SERVER, GeminiTool.ANALYZE_MIX_BALANCE, {"path": mix_path})

    await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_LOUDNESS, {"path": mix_path})
    await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_SPECTRUM, {"path": mix_path})
    await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_STEREO, {"path": mix_path})

    await rec.run(GEMINI_SERVER, GeminiTool.FIND_RESONANCES, {"path": mix_path})
    await rec.run(GEMINI_SERVER, GeminiTool.FIND_SIBILANCE, {"path": mix_path})
    await rec.run(GEMINI_SERVER, GeminiTool.ANALYZE_PHASE_MONO, {"path": mix_path})

    # Corrective chain — the shared opt-in chain (apply-eq -> de-ess ->
    # suppress-resonances -> apply-dynamic-eq -> excite-loop -> compress-loop ->
    # multiband-compress). mix-check includes excite-loop but NOT shape-bands.
    spec: dict[str, Any] = {
        "eq_bands": eq_bands,
        "deess": deess,
        "suppress": suppress,
        "dynamic_eq_bands": dynamic_eq_bands,
        "excite": excite,
        "compress": compress,
        "multiband": multiband,
    }
    cur = await _run_corrective_chain(
        rec,
        mix_path,
        spec,
        include_excite=True,
        include_shape=False,
        eq_out_path=eq_out_path,
        compress_out_path=compress_out_path,
    )

    return {
        "pipeline": "mix-check",
        "input": mix_path,
        "output": cur,
        "steps": rec.steps,
    }


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
        GeminiTool.MATCH_REFERENCE_NUMERIC,
        {"mix_path": mix_path, "reference_path": ref_path},
    )
    await rec.run(
        GEMINI_SERVER,
        GeminiTool.COMPARE_TO_REFERENCE,
        {"mix_path": mix_path, "reference_path": ref_path, "goal": goal},
    )
    await rec.run(
        LOOPS_SERVER,
        LoopsTool.COMPARE_TONALITY,
        {"loop_path": mix_path, "reference_path": ref_path},
    )

    corrected = match_out_path or _suffix_path(mix_path, "matched")
    await rec.run(
        LOOPS_SERVER,
        LoopsTool.MATCH_EQ,
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
            LoopsTool.APPLY_EQ,
            {"path": corrected, "out_path": residual, "bands": eq_bands},
        )
        corrected = residual

    await rec.run(
        LOOPS_SERVER,
        LoopsTool.RENDER_AB,
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


async def house_curve(
    hub: SupportsCallTool,
    mix_path: str,
    reference_paths: list[str],
    *,
    profile_json: str | None = None,
    match_strength: float = 0.5,
    match_phase: str = "minimum",
    out_path: str | None = None,
) -> dict[str, Any]:
    """Pipeline — build one shared house curve from refs, match a mix to it.

    Order (verified tools): build-target-profile (loops; power-averages the
    references into a reusable profile JSON) -> match-to-profile (loops; the
    mix's per-band delta vs the profile) -> match-eq (loops; renders the delta
    as a min/linear-phase FIR correction). The match-eq render runs only when a
    per-band delta is recoverable from match-to-profile (a real hub); the
    profile + delta read are always produced. For a whole EP, reuse the one
    ``profile_json`` across every mix so the set shares a target ([[house-curve]]).
    """
    if not reference_paths:
        raise ValueError("house_curve needs at least one reference path")
    rec = _Recorder(hub)

    profile = profile_json or _profile_json_path(mix_path)
    await rec.run(
        LOOPS_SERVER,
        LoopsTool.BUILD_TARGET_PROFILE,
        {"paths": list(reference_paths), "out_json": profile},
    )
    match = await rec.run(
        LOOPS_SERVER,
        LoopsTool.MATCH_TO_PROFILE,
        {"path": mix_path, "profile_json": profile},
    )

    # An unreadable match-to-profile result means NO correction can be rendered:
    # house_curve then returns output == input with `matched: false`. That is a
    # no-op, not a match — surface it as a warning so a scripted EP loop can't
    # "match" every mix to nothing and still look successful.
    curve = _profile_delta_curve(match)
    output = mix_path
    if curve is not None:
        output = out_path or _suffix_path(mix_path, "house-matched")
        await rec.run(
            LOOPS_SERVER,
            LoopsTool.MATCH_EQ,
            {
                "source_path": mix_path,
                "delta_db_curve": curve,
                "out_path": output,
                "match_strength": match_strength,
                "phase": match_phase,
            },
        )

    return {
        "pipeline": "house-curve",
        "input": mix_path,
        "profile": profile,
        "output": output,
        "matched": curve is not None,
        "warning": None if curve is not None else (
            "no per-band delta was recoverable from match-to-profile — NO correction "
            "was rendered and `output` is the unmodified input"
        ),
        "steps": rec.steps,
    }


async def _apply_stem_corrections(
    rec: _Recorder, path: str, spec: dict[str, Any]
) -> str:
    """Apply one stem's opt-in corrective chain, returning the final output path.

    Order: apply-eq -> de-ess -> suppress-resonances -> apply-dynamic-eq ->
    compress-loop -> multiband-compress -> shape-bands. The stem chain includes
    shape-bands but NOT excite-loop — the only difference from the mix-check
    chain; both run through the shared :func:`_run_corrective_chain`. Each step
    reads the prior step's output; ``path``/``out_path`` are injected last so a
    spec dict can't hijack the chain. ``deess`` / ``suppress`` / ``multiband`` /
    ``shape_bands`` are tuning-kwarg dicts, ``eq_bands`` / ``dynamic_eq_bands``
    carry EQ moves, and ``compress`` is a bool.
    """
    return await _run_corrective_chain(
        rec, path, spec, include_excite=False, include_shape=True
    )


async def stem_master(
    hub: SupportsCallTool,
    stems: dict[str, str],
    *,
    corrections: dict[str, dict[str, Any]] | None = None,
    cross_check: bool = False,
    max_conflicts: int = 8,
) -> dict[str, Any]:
    """Pipeline — per-stem corrective mixdown prep + masking verification.

    The MCP-drivable half of stem-master (CLAUDE.md): per stem measure ->
    analyze-stem-masking (the stem map) [+ optional detect-masking cross-check]
    -> per-stem corrective chain (apply-eq -> de-ess -> suppress-resonances ->
    apply-dynamic-eq -> compress-loop -> multiband-compress -> shape-bands, each
    opt-in per stem) -> re-run analyze-stem-masking to confirm the overlaps
    shrank. ``stems`` maps a stem NAME to its path (the shape analyze-stem-masking
    takes); ``corrections`` maps a stem NAME to its moves — cut the loser, don't
    boost the winner.

    Summing the corrected stems is LOCAL DSP outside this DSP-free hub
    (``drum-prep stem-mix``), and the summed bus then goes through
    ``master_track`` — both are separate downstream stages, so this returns the
    ``corrected`` stem paths for that handoff. ``unmask-stems`` is the
    masking-only subset (the masking map + EQ cuts + re-score).
    """
    if len(stems) < 2:
        raise ValueError("stem_master needs at least two stems")
    rec = _Recorder(hub)
    corrections = corrections or {}

    for path in stems.values():
        await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_LOUDNESS, {"path": path})
        await rec.run(LOOPS_SERVER, LoopsTool.MEASURE_SPECTRUM, {"path": path})

    await rec.run(
        GEMINI_SERVER,
        GeminiTool.ANALYZE_STEM_MASKING,
        {"stems": dict(stems), "max_conflicts": max_conflicts},
    )
    if cross_check:
        await rec.run(LOOPS_SERVER, LoopsTool.DETECT_MASKING, {"paths": list(stems.values())})

    corrected: dict[str, str] = dict(stems)
    for name, path in stems.items():
        spec = corrections.get(name)
        if spec:
            corrected[name] = await _apply_stem_corrections(rec, path, spec)

    await rec.run(
        GEMINI_SERVER,
        GeminiTool.ANALYZE_STEM_MASKING,
        {"stems": corrected, "max_conflicts": max_conflicts},
    )

    return {
        "pipeline": "stem-master",
        "stems": dict(stems),
        "corrected": corrected,
        "steps": rec.steps,
    }


async def unmask_stems(
    hub: SupportsCallTool,
    stems: dict[str, str],
    *,
    corrections: dict[str, dict[str, Any]] | None = None,
    cross_check: bool = False,
    max_conflicts: int = 8,
) -> dict[str, Any]:
    """Pipeline — the masking-only subset of stem-master.

    analyze-stem-masking (the map) [+ optional detect-masking cross-check] ->
    complementary EQ cuts on the LOSING stem of each collision (apply-eq /
    apply-dynamic-eq via ``corrections``) -> re-run analyze-stem-masking to prove
    the overlap shrank. No per-stem measure baseline, no tone/dynamics shaping,
    no summing, no mastering — the focused ([[unmask-stems]]) subset of
    [[stem-master]]. ``stems`` is a NAME->path dict; ``corrections`` maps a stem
    NAME to its cuts (typically ``eq_bands`` / ``dynamic_eq_bands`` — cut the
    loser, don't boost the winner). Returns the ``corrected`` paths.
    """
    if len(stems) < 2:
        raise ValueError("unmask_stems needs at least two stems")
    rec = _Recorder(hub)
    corrections = corrections or {}

    await rec.run(
        GEMINI_SERVER,
        GeminiTool.ANALYZE_STEM_MASKING,
        {"stems": dict(stems), "max_conflicts": max_conflicts},
    )
    if cross_check:
        await rec.run(LOOPS_SERVER, LoopsTool.DETECT_MASKING, {"paths": list(stems.values())})

    corrected: dict[str, str] = dict(stems)
    for name, path in stems.items():
        spec = corrections.get(name)
        if spec:
            corrected[name] = await _apply_stem_corrections(rec, path, spec)

    await rec.run(
        GEMINI_SERVER,
        GeminiTool.ANALYZE_STEM_MASKING,
        {"stems": corrected, "max_conflicts": max_conflicts},
    )

    return {
        "pipeline": "unmask-stems",
        "stems": dict(stems),
        "corrected": corrected,
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
    once on ``input_path`` and the returned dict reports ``fell_back=True``.

    ``top_n`` is forwarded to find-loops, where the server applies it PER bar
    length (so a 3-bar-length request can return up to 3*top_n diverse loops);
    the pipeline then processes exactly that set. ``max_total_loops`` is a
    SEPARATE optional cap on the *total* number of loops the per-loop chain
    runs over — only sliced when set, so the two never share a meaning.

    The result carries ``fell_back`` (bool — the input itself was processed
    because no loops were parseable/found) and ``loop_count`` (the number of
    loops actually processed).
    """
    rec = _Recorder(hub)

    find_args: dict[str, Any] = {"path": input_path, "bpm": bpm, "separate": separate}
    if bars is not None:
        find_args["bars"] = bars
    if top_n is not None:
        find_args["top_n"] = top_n
    if out_dir is not None:
        find_args["out_dir"] = out_dir
    manifest = await rec.run(LOOPS_SERVER, LoopsTool.FIND_LOOPS, find_args)

    # find-loops already applied top_n (per bar length); don't re-cap by it here
    # — that would silently discard the diverse loops selected across other bar
    # lengths. Slice only by the explicit, separate max_total_loops when set.
    parsed = _loop_paths(manifest)  # None = unparseable, [] = parseable-but-empty
    loop_paths = parsed if parsed is not None else []
    # ``loops_found`` = how many the manifest actually yielded, captured BEFORE the
    # max_total_loops slice (the slice used to run first, so a 20-loop find capped to
    # 5 reported `loops_found: 5` — indistinguishable from a find that only located 5).
    loops_found = len(loop_paths)
    if max_total_loops is not None:
        loop_paths = loop_paths[:max_total_loops]
    # Surface the fallback so a 1-loop run on the SOURCE isn't mistaken for a real
    # 1-loop find; ``fell_back`` (with the ``fell_back_to_input`` alias) flags both
    # the unparseable-shape and empty cases.
    fell_back = parsed is None or not loop_paths
    fell_back_to_input = fell_back
    if fell_back:
        loop_paths = [input_path]
    manifest_out = manifest.get("out_dir") if isinstance(manifest, dict) else None

    deliverables: list[dict[str, Any]] = []
    for loop_in in loop_paths:
        cleaned = _suffix_path(loop_in, "clean")
        seamed = _suffix_path(loop_in, "seam")
        mastered = _suffix_path(loop_in, "master")
        tagged = _suffix_path(loop_in, "tagged")

        await rec.run(
            LOOPS_SERVER, LoopsTool.CLEAN_LOOP, {"path": loop_in, "out_path": cleaned}
        )
        await rec.run(
            LOOPS_SERVER, LoopsTool.OPTIMIZE_SEAM, {"path": cleaned, "out_path": seamed}
        )
        await rec.run(
            LOOPS_SERVER,
            LoopsTool.RENDER_MASTERED,
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
        await rec.run(LOOPS_SERVER, LoopsTool.TAG_DELIVERABLE, tag_args)

        await rec.run(
            LOOPS_SERVER,
            LoopsTool.EXPORT_DELIVERABLES,
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
        await rec.run(LOOPS_SERVER, LoopsTool.DESCRIBE_LOOPS, {"out_dir": describe_target})

    return {
        "pipeline": "loops-to-deliverables",
        "input": input_path,
        "bpm": bpm,
        "loops_found": loops_found,  # loops parsed from the manifest (0 on fallback)
        "fell_back_to_input": fell_back_to_input,  # True == processed the source, not loops
        "loops": deliverables,
        "fell_back": fell_back,
        "loop_count": len(loop_paths),
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
            GeminiTool.TRANSCRIBE_AUDIO,
            {"path": path, "diarize": diarize},
        )
    if region is not None:
        start_s, end_s, prompt = region
        await rec.run(
            GEMINI_SERVER,
            GeminiTool.DESCRIBE_AUDIO_REGION,
            {"path": path, "start_s": start_s, "end_s": end_s, "prompt": prompt},
        )
    if event_description is not None:
        await rec.run(
            GEMINI_SERVER,
            GeminiTool.EXTRACT_AUDIO_EVENTS,
            {"path": path, "event_description": event_description},
        )
    if labels is not None:
        await rec.run(
            GEMINI_SERVER,
            GeminiTool.CLASSIFY_AUDIO,
            {"path": path, "labels": labels, "multi_label": multi_label},
        )
    if compare_paths is not None:
        compare_args: dict[str, Any] = {"paths": [path, *compare_paths]}
        if compare_prompt is not None:
            compare_args["prompt"] = compare_prompt
        if compare_schema is not None:
            compare_args["schema"] = compare_schema
        await rec.run(GEMINI_SERVER, GeminiTool.COMPARE_AUDIO_FILES, compare_args)
    if json_schema is not None:
        await rec.run(
            GEMINI_SERVER,
            GeminiTool.AUDIO_TO_JSON,
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


def _profile_json_path(mix_path: str) -> str:
    """Default house-profile JSON beside the mix: a/b.wav -> a/b.house-profile.json."""
    p = PurePosixPath(mix_path)
    return str(p.with_name(f"{p.stem}.house-profile.json"))


def _master_out(mix_path: str, masters_dir: str | None) -> str:
    """Master output path for a mix, honoring the ``masters/`` layout.

    With an explicit ``masters_dir`` the file lands there; otherwise it follows
    the project layout (a mix in ``mix/`` -> the sibling ``masters/``; else a
    ``masters/`` dir beside the mix), matching the single-file CLI default.
    """
    p = PurePosixPath(mix_path)
    name = f"{p.stem}.master{p.suffix}"
    if masters_dir is not None:
        return str(PurePosixPath(masters_dir) / name)
    project = p.parent.parent if p.parent.name == "mix" else p.parent
    return str(project / "masters" / name)


def _unique_master_outs(mix_paths: list[str], masters_dir: str | None) -> list[str]:
    """Master output path per mix, disambiguated so no two collide.

    With an explicit ``masters_dir`` every master is named from the mix's BASENAME
    alone, so ``projects/a/mix/intro.wav`` and ``projects/b/mix/intro.wav`` both
    became ``<masters_dir>/intro.master.wav``: the second silently overwrote the
    first, ``masters`` held the same path twice, and the album-normalization pass
    measured one file as two "tracks", skewing the shared-gain projection. On a
    collision, prefix the mix's project directory (the parent of ``mix/`` when the
    documented layout is in play, else the immediate parent).
    """
    outs = [_master_out(m, masters_dir) for m in mix_paths]
    seen: dict[str, int] = {}
    for o in outs:
        seen[o] = seen.get(o, 0) + 1
    if all(c == 1 for c in seen.values()):
        return outs

    resolved: list[str] = []
    used: set[str] = set()
    for mix, out in zip(mix_paths, outs, strict=True):
        if seen[out] == 1:
            resolved.append(out)
            used.add(out)
            continue
        p = PurePosixPath(mix)
        project = p.parent.parent if p.parent.name == "mix" else p.parent
        op = PurePosixPath(out)
        cand = str(op.with_name(f"{project.name}-{op.name}")) if project.name else out
        # still ambiguous (same project name from different trees) -> number it
        n = 2
        base = cand
        while cand in used:
            bp = PurePosixPath(base)
            cand = str(bp.with_name(f"{bp.stem}-{n}{bp.suffix}"))
            n += 1
        resolved.append(cand)
        used.add(cand)
    return resolved


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


def _loop_paths(manifest: Any) -> list[str] | None:
    """All loop WAV paths from a find-loops result, best-effort.

    The real ``find-loops`` returns ``FindLoopsResponse`` →
    ``{"out_dir": str, "manifest": {"loops": [{"wav": <name relative to out_dir>,
    ...}], ...}}`` — the loop list is nested under ``manifest`` and each ``wav``
    is a *basename* that must be joined to ``out_dir``. A couple of alternate
    shapes are probed too so a manifest change degrades gracefully; it never
    raises.

    Returns ``None`` when the manifest shape is UNPARSEABLE (not a dict, or no
    recognizable loops container) — the caller can't tell whether loops exist and
    falls back. Returns ``[]`` when the manifest parses cleanly but finds zero
    loops (a genuinely empty result). The caller treats both as "fall back to the
    input", but the distinction lets observability/tests tell them apart.
    """
    if not isinstance(manifest, dict):
        return None
    out_dir = manifest.get("out_dir")
    inner = manifest.get("manifest")
    loops = inner.get("loops") if isinstance(inner, dict) else manifest.get("loops")
    if not isinstance(loops, list):
        return None
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
