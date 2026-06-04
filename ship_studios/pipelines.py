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

from ship_studios import perf
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


class _Recorder:
    """Calls a tool through the hub and records the step for the result dict."""

    def __init__(self, hub: SupportsCallTool) -> None:
        self._hub = hub
        self.steps: list[dict[str, Any]] = []

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
    """
    rec = _Recorder(hub)

    await rec.run(LOOPS_SERVER, "measure-loudness", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "measure-spectrum", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "measure-stereo", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "check-clipping", {"path": mix_path})
    await rec.run(LOOPS_SERVER, "measure-distortion", {"path": mix_path})

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
        await rec.run(GEMINI_SERVER, "master-assistant", plan_args)
    else:
        await rec.run(
            GEMINI_SERVER,
            "mastering-feedback",
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
) -> dict[str, Any]:
    """Pipeline 6 — master a folder of mixes to ONE shared target + album pass.

    Per track: the full master-track chain (measure -> mastering-feedback ->
    render-mastered -> check-streaming-targets -> export-deliverables) to the
    SHARED ``target_lufs`` / ``ceiling_dbtp``. Then a cross-track pass —
    measure-loudness over every master + analyze-album-normalization (the shared
    album gain a platform will actually apply). The consistency read is the
    headline; hand any not-release-ready track to mix-check first.
    """
    if not mix_paths:
        raise ValueError("batch_master needs at least one mix path")

    tracks: list[dict[str, Any]] = []
    masters: list[str] = []
    steps: list[dict[str, Any]] = []
    for mix in mix_paths:
        out = _master_out(mix, masters_dir)
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
        )
        tracks.append(
            {
                "input": mix,
                "master": out,
                "streaming_compliant": res.get("streaming_compliant"),
            }
        )
        masters.append(out)
        steps.extend(res.get("steps", []))

    # Cross-track album pass — consistency table + shared album-gain projection.
    rec = _Recorder(hub)
    for master in masters:
        await rec.run(LOOPS_SERVER, "measure-loudness", {"path": master})
    await rec.run(
        LOOPS_SERVER,
        "analyze-album-normalization",
        {"paths": masters, "target_lufs": target_lufs, "ceiling_dbtp": ceiling_dbtp},
    )
    steps.extend(rec.steps)

    return {
        "pipeline": "batch-master",
        "inputs": list(mix_paths),
        "masters": masters,
        "tracks": tracks,
        "steps": steps,
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

    # Corrective chain — each step reads the running ``cur`` (the prior step's
    # output) and writes a fresh suffixed file, so order matches the doc recipe.
    cur = mix_path
    if eq_bands is not None:
        out = eq_out_path or _suffix_path(mix_path, "eq")
        await rec.run(
            LOOPS_SERVER, "apply-eq", {"path": cur, "out_path": out, "bands": eq_bands}
        )
        cur = out
    if deess is not None:
        out = _suffix_path(mix_path, "deess")
        await rec.run(LOOPS_SERVER, "de-ess", {**deess, "path": cur, "out_path": out})
        cur = out
    if suppress is not None:
        out = _suffix_path(mix_path, "deharsh")
        await rec.run(
            LOOPS_SERVER, "suppress-resonances", {**suppress, "path": cur, "out_path": out}
        )
        cur = out
    if dynamic_eq_bands is not None:
        out = _suffix_path(mix_path, "dyneq")
        await rec.run(
            LOOPS_SERVER,
            "apply-dynamic-eq",
            {"path": cur, "out_path": out, "bands": dynamic_eq_bands},
        )
        cur = out
    if excite is not None:
        out = _suffix_path(mix_path, "excite")
        await rec.run(LOOPS_SERVER, "excite-loop", {**excite, "path": cur, "out_path": out})
        cur = out
    if compress:
        out = compress_out_path or _suffix_path(mix_path, "comp")
        await rec.run(LOOPS_SERVER, "compress-loop", {"path": cur, "out_path": out})
        cur = out
    if multiband is not None:
        out = _suffix_path(mix_path, "mbcomp")
        await rec.run(
            LOOPS_SERVER, "multiband-compress", {**multiband, "path": cur, "out_path": out}
        )
        cur = out

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
        "build-target-profile",
        {"paths": list(reference_paths), "out_json": profile},
    )
    match = await rec.run(
        LOOPS_SERVER,
        "match-to-profile",
        {"path": mix_path, "profile_json": profile},
    )

    curve = _profile_delta_curve(match)
    output = mix_path
    if curve is not None:
        output = out_path or _suffix_path(mix_path, "house-matched")
        await rec.run(
            LOOPS_SERVER,
            "match-eq",
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
        "steps": rec.steps,
    }


async def _apply_stem_corrections(
    rec: _Recorder, path: str, spec: dict[str, Any]
) -> str:
    """Apply one stem's opt-in corrective chain, returning the final output path.

    Order: apply-eq -> de-ess -> suppress-resonances -> apply-dynamic-eq ->
    compress-loop -> multiband-compress -> shape-bands. Each step reads the prior
    step's output; ``path``/``out_path`` are injected last so a spec dict can't
    hijack the chain. ``deess`` / ``suppress`` / ``multiband`` / ``shape_bands``
    are tuning-kwarg dicts, ``eq_bands`` / ``dynamic_eq_bands`` carry EQ moves,
    and ``compress`` is a bool.
    """
    cur = path
    eq_bands = spec.get("eq_bands")
    if eq_bands is not None:
        out = _suffix_path(path, "eq")
        await rec.run(
            LOOPS_SERVER, "apply-eq", {"path": cur, "out_path": out, "bands": eq_bands}
        )
        cur = out
    deess = spec.get("deess")
    if deess is not None:
        out = _suffix_path(path, "deess")
        await rec.run(LOOPS_SERVER, "de-ess", {**deess, "path": cur, "out_path": out})
        cur = out
    suppress = spec.get("suppress")
    if suppress is not None:
        out = _suffix_path(path, "deharsh")
        await rec.run(
            LOOPS_SERVER, "suppress-resonances", {**suppress, "path": cur, "out_path": out}
        )
        cur = out
    dyn = spec.get("dynamic_eq_bands")
    if dyn is not None:
        out = _suffix_path(path, "dyneq")
        await rec.run(
            LOOPS_SERVER, "apply-dynamic-eq", {"path": cur, "out_path": out, "bands": dyn}
        )
        cur = out
    if spec.get("compress"):
        out = _suffix_path(path, "comp")
        await rec.run(LOOPS_SERVER, "compress-loop", {"path": cur, "out_path": out})
        cur = out
    multiband = spec.get("multiband")
    if multiband is not None:
        out = _suffix_path(path, "mbcomp")
        await rec.run(
            LOOPS_SERVER, "multiband-compress", {**multiband, "path": cur, "out_path": out}
        )
        cur = out
    shape = spec.get("shape_bands")
    if shape is not None:
        out = _suffix_path(path, "shaped")
        await rec.run(LOOPS_SERVER, "shape-bands", {**shape, "path": cur, "out_path": out})
        cur = out
    return cur


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
        await rec.run(LOOPS_SERVER, "measure-loudness", {"path": path})
        await rec.run(LOOPS_SERVER, "measure-spectrum", {"path": path})

    await rec.run(
        GEMINI_SERVER,
        "analyze-stem-masking",
        {"stems": dict(stems), "max_conflicts": max_conflicts},
    )
    if cross_check:
        await rec.run(LOOPS_SERVER, "detect-masking", {"paths": list(stems.values())})

    corrected: dict[str, str] = dict(stems)
    for name, path in stems.items():
        spec = corrections.get(name)
        if spec:
            corrected[name] = await _apply_stem_corrections(rec, path, spec)

    await rec.run(
        GEMINI_SERVER,
        "analyze-stem-masking",
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
        "analyze-stem-masking",
        {"stems": dict(stems), "max_conflicts": max_conflicts},
    )
    if cross_check:
        await rec.run(LOOPS_SERVER, "detect-masking", {"paths": list(stems.values())})

    corrected: dict[str, str] = dict(stems)
    for name, path in stems.items():
        spec = corrections.get(name)
        if spec:
            corrected[name] = await _apply_stem_corrections(rec, path, spec)

    await rec.run(
        GEMINI_SERVER,
        "analyze-stem-masking",
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
