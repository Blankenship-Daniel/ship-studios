"""``ship-studios`` console-script entry point.

A small click group that wires CLI args into the async pipeline functions
via the MCP Hub. Five pipeline subcommands (master, mix-check,
reference-match, loops, understand) plus a ``doctor`` that checks env vars
and sibling-repo presence and prints setup guidance.

Imports stay lazy: ``doctor`` only touches :mod:`ship_studios.config` (no
SDK), and the pipeline subcommands import the Hub + pipelines inside their
handlers, so ``ship-studios doctor`` works before the MCP SDK or the sibling
servers are installed.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from typing import Any

import click

from ship_studios import __version__, config

# Choice lists only (pure data, no MCP SDK) so the click decorators can constrain
# --platform/--severity at import time; `doctor` stays SDK-free (pipelines imports
# nothing heavier than config).
from ship_studios.pipelines import DEFAULT_PRESETS, PLATFORM_CHOICES, SEVERITY_CHOICES


def _format_error(exc: BaseException) -> str:
    """Flatten an exception to a single readable line for the CLI.

    The MCP SDK runs sessions inside anyio task groups, so a setup/transport
    failure can surface as a (possibly nested) ``ExceptionGroup`` rather than the
    bare ``ToolCallError`` / ``OSError`` / ``McpError`` — peel it to the leaf
    messages so the user sees the real cause, not ``unhandled errors in a TaskGroup``.
    """
    if isinstance(exc, BaseExceptionGroup):
        leaves: list[str] = []

        def _collect(group: BaseExceptionGroup) -> None:
            for sub in group.exceptions:
                if isinstance(sub, BaseExceptionGroup):
                    _collect(sub)
                else:
                    leaves.append(str(sub) or type(sub).__name__)

        _collect(exc)
        return "; ".join(leaves) or str(exc)
    return str(exc) or type(exc).__name__


def _run(coro: Coroutine[Any, Any, dict[str, Any]]) -> None:
    """Drive an async pipeline to completion and pretty-print its result.

    This is the CLI boundary: any ``Exception`` — a ``ToolCallError`` from a tool,
    an ``OSError`` when ``uv`` is missing, an ``McpError`` when the spawned server
    dies during the handshake, or an ``ExceptionGroup`` raised out of the SDK's
    anyio task groups — becomes a clean one-line stderr message + exit 1 instead of
    a Python traceback (mirroring ``drum_prep.cli._go``). A ``KeyboardInterrupt``
    (Ctrl-C) exits 130 quietly. Other ``BaseException``\\ s (e.g. a task-group
    ``CancelledError``) propagate — the caller asked for them.
    """
    try:
        result = asyncio.run(coro)
    except KeyboardInterrupt:
        click.echo("Interrupted.", err=True)
        raise SystemExit(130) from None
    except Exception as exc:
        click.echo(click.style(f"Error: {_format_error(exc)}", fg="red"), err=True)
        raise SystemExit(1) from exc
    click.echo(json.dumps(result, indent=2, default=str))


def _default_master_out(mix_path: str) -> str:
    """Default master output: ``<project>/masters/<stem>.master<ext>``.

    Honors the project layout (CLAUDE.md: "Always master into ``masters/``, never
    overwrite ``mix/``"). When the mix sits in a ``mix/`` dir, the master goes to
    the sibling ``masters/``; otherwise a ``masters/`` dir beside the mix. The
    loops ``render-mastered`` tool creates the parent dir, so it need not exist.
    """
    from pathlib import Path

    p = Path(mix_path)
    project = p.parent.parent if p.parent.name == "mix" else p.parent
    return str(project / "masters" / f"{p.stem}.master{p.suffix}")


def _parse_bars(bars: str | None) -> list[int] | None:
    """Parse ``--bars`` (e.g. ``1,2,4``) into validated positive ints.

    Raises a clean Click error (not a traceback) on non-numeric or out-of-range
    input so the user gets actionable feedback instead of an uncaught ValueError.
    """
    if not bars:
        return None
    out: list[int] = []
    for tok in (t.strip() for t in bars.split(",")):
        if not tok:
            continue
        try:
            n = int(tok)
        except ValueError:
            raise click.BadParameter(
                f"bar lengths must be integers; got {tok!r}", param_hint="--bars"
            ) from None
        if not 1 <= n <= 64:
            raise click.BadParameter(
                f"bar length {n} out of range (1-64)", param_hint="--bars"
            )
        out.append(n)
    return out or None


def _parse_presets(presets: str | None) -> list[str] | None:
    """Parse ``--presets`` (comma-separated) into validated export-preset names.

    Mirrors the server allow-list (``pipelines.DEFAULT_PRESETS``); an unknown name
    is rejected up front with a clean Click error — parity with ``--platform`` /
    ``--severity`` — instead of failing deep in ``export-deliverables`` with a
    ``ValueError("unknown preset")``.
    """
    if not presets:
        return None
    out: list[str] = []
    for tok in (t.strip() for t in presets.split(",")):
        if not tok:
            continue
        if tok not in DEFAULT_PRESETS:
            raise click.BadParameter(
                f"unknown preset {tok!r}; choose from {', '.join(DEFAULT_PRESETS)}",
                param_hint="--presets",
            )
        out.append(tok)
    return out or None


def _load_eq_bands(
    path: str | None, *, hint: str = "--eq-json"
) -> list[dict[str, Any]] | None:
    """Load corrective EQ bands from a JSON file (a list of band dicts).

    Lets the headless CLI reach the band-driven steps (apply-eq / apply-dynamic-eq)
    of mix-check / reference-match (otherwise unreachable). Raises a clean Click
    error on a missing file or a payload that isn't a JSON list of objects.
    """
    if not path:
        return None
    from pathlib import Path

    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise click.BadParameter(f"file not found: {path}", param_hint=hint) from None
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"invalid JSON in {path}: {exc}", param_hint=hint) from None
    if not (isinstance(data, list) and all(isinstance(b, dict) for b in data)):
        raise click.BadParameter(
            "expected a JSON list of band objects, e.g. "
            '[{"freq_hz": 200, "gain_db": -2, "q": 1.0, "type": "bell"}]',
            param_hint=hint,
        )
    return data


def _load_json_obj(path: str | None, hint: str) -> dict[str, Any] | None:
    """Load a JSON object (e.g. a JSON Schema) from ``path``; clean error on bad input."""
    if not path:
        return None
    from pathlib import Path

    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise click.BadParameter(f"file not found: {path}", param_hint=hint) from None
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"invalid JSON in {path}: {exc}", param_hint=hint) from None
    if not isinstance(data, dict):
        raise click.BadParameter("expected a JSON object", param_hint=hint)
    return data


@click.group()
@click.version_option(__version__, prog_name="ship-studios")
def main() -> None:
    """Headless hub over the stemmy-loops + stemmy-gemini MCP servers."""


@main.command()
@click.argument("mix_path", type=click.Path())
@click.option("--out", "out_path", type=click.Path(), default=None,
              help="Where to write the rendered master WAV "
                   "(default: <project>/masters/<stem>.master.wav).")
@click.option("--target-lufs", default=-14.0, show_default=True, type=float)
@click.option("--ceiling-dbtp", default=-1.0, show_default=True, type=float)
@click.option("--platform", "target_platform", default="spotify", show_default=True,
              type=click.Choice(PLATFORM_CHOICES),
              help="Release target. Streaming services (spotify/apple_music/youtube/"
                   "tidal) drive the compliance check and map to the 'streaming' "
                   "mastering critique; general/club/broadcast/vinyl set the critique mood.")
@click.option("--high-pass-hz", type=float, default=None)
@click.option("--transient-shape", type=float, default=None)
@click.option("--bit-depth", type=int, default=None)
@click.option("--sample-rate", type=int, default=None)
@click.option("--deliverables-dir", type=click.Path(), default=None)
@click.option("--assistant", is_flag=True, default=False,
              help="Use master-assistant (a typed chain plan) for the perceptual "
                   "step instead of mastering-feedback.")
@click.option("--intent", default="balanced", show_default=True,
              type=click.Choice(
                  ["loud", "dynamic", "warm", "bright", "balanced", "punchy"]),
              help="master-assistant creative intent (with --assistant).")
@click.option("--intensity", default="medium", show_default=True,
              type=click.Choice(["subtle", "medium", "strong"]),
              help="master-assistant intensity (with --assistant).")
@click.option("--style", default=None,
              help="master-assistant style / genre hint (with --assistant).")
def master(
    mix_path: str,
    out_path: str | None,
    target_lufs: float,
    ceiling_dbtp: float,
    target_platform: str,
    high_pass_hz: float | None,
    transient_shape: float | None,
    bit_depth: int | None,
    sample_rate: int | None,
    deliverables_dir: str | None,
    assistant: bool,
    intent: str,
    intensity: str,
    style: str | None,
) -> None:
    """Master a near-final mix and export the deliverable format matrix."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import master_track

    resolved_out = out_path or _default_master_out(mix_path)

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await master_track(
                hub,
                mix_path,
                resolved_out,
                target_lufs=target_lufs,
                ceiling_dbtp=ceiling_dbtp,
                target_platform=target_platform,
                high_pass_hz=high_pass_hz,
                transient_shape=transient_shape,
                bit_depth=bit_depth,
                sample_rate=sample_rate,
                deliverables_dir=deliverables_dir,
                assistant=assistant,
                intent=intent,
                intensity=intensity,
                style=style,
            )

    _run(_go())


@main.command(name="house-curve")
@click.argument("mix_path", type=click.Path())
@click.option("--reference", "reference_paths", multiple=True, required=True,
              type=click.Path(),
              help="Reference track to fold into the house curve (repeatable).")
@click.option("--profile-json", "profile_json", type=click.Path(), default=None,
              help="Where to write/read the shared profile JSON "
                   "(default: <mix>.house-profile.json). Reuse it across an EP.")
@click.option("--match-strength", type=click.FloatRange(0.0, 1.0), default=0.5,
              show_default=True,
              help="How much of the mix->profile delta match-eq corrects.")
@click.option("--match-phase", type=click.Choice(["minimum", "linear", "tilt_only"]),
              default="minimum", show_default=True,
              help="match-eq filter realization.")
@click.option("--out", "out_path", type=click.Path(), default=None,
              help="Where to write the corrected mix "
                   "(default: <mix>.house-matched.wav).")
def house_curve_cmd(mix_path: str, reference_paths: tuple[str, ...],
                    profile_json: str | None, match_strength: float,
                    match_phase: str, out_path: str | None) -> None:
    """Build a shared house curve from references and match a mix toward it."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import house_curve

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await house_curve(
                hub, mix_path, list(reference_paths),
                profile_json=profile_json, match_strength=match_strength,
                match_phase=match_phase, out_path=out_path,
            )

    _run(_go())


def _expand_mix_paths(paths: tuple[str, ...]) -> list[str]:
    """Expand CLI mix args: a lone directory -> its sorted ``*.wav`` children.

    Otherwise the paths pass through unchanged (so tests need no filesystem).
    """
    from pathlib import Path

    if len(paths) == 1 and Path(paths[0]).is_dir():
        wavs = sorted(str(p) for p in Path(paths[0]).glob("*.wav"))
        if not wavs:
            raise click.BadParameter(
                f"no .wav files in {paths[0]}", param_hint="MIX_PATHS"
            )
        return wavs
    return list(paths)


@main.command(name="batch-master")
@click.argument("mix_paths", nargs=-1, required=True, type=click.Path())
@click.option("--target-lufs", default=-14.0, show_default=True, type=float)
@click.option("--ceiling-dbtp", default=-1.0, show_default=True, type=float)
@click.option("--platform", "target_platform", default="spotify", show_default=True,
              type=click.Choice(PLATFORM_CHOICES),
              help="Shared release target for the whole set.")
@click.option("--masters-dir", type=click.Path(), default=None,
              help="Write every master here (default: each mix's project masters/).")
@click.option("--deliverables-dir", type=click.Path(), default=None)
@click.option("--bit-depth", type=int, default=None)
@click.option("--sample-rate", type=int, default=None)
def batch_master_cmd(mix_paths: tuple[str, ...], target_lufs: float,
                     ceiling_dbtp: float, target_platform: str,
                     masters_dir: str | None, deliverables_dir: str | None,
                     bit_depth: int | None, sample_rate: int | None) -> None:
    """Master a set of mixes to one shared target + a cross-track album pass.

    MIX_PATHS are the mix files; pass a single directory to master every .wav in it.
    """
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import batch_master

    mixes = _expand_mix_paths(mix_paths)

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await batch_master(
                hub, mixes,
                target_lufs=target_lufs, ceiling_dbtp=ceiling_dbtp,
                target_platform=target_platform, masters_dir=masters_dir,
                deliverables_dir=deliverables_dir, bit_depth=bit_depth,
                sample_rate=sample_rate,
            )

    _run(_go())


@main.command(name="unmask-stems")
@click.argument("stem_paths", nargs=-1, required=True, type=click.Path())
@click.option("--corrections-json", "corrections_json", type=click.Path(), default=None,
              help="JSON object mapping a stem NAME (filename without extension) to "
                   "its complementary EQ cuts (eq_bands / dynamic_eq_bands).")
@click.option("--cross-check", is_flag=True, default=False,
              help="Also run the loops detect-masking cross-check.")
@click.option("--max-conflicts", type=int, default=8, show_default=True,
              help="Max masking conflicts analyze-stem-masking reports.")
def unmask_stems_cmd(stem_paths: tuple[str, ...], corrections_json: str | None,
                     cross_check: bool, max_conflicts: int) -> None:
    """Score cross-stem masking, cut the losing stems, and re-score to prove it.

    The masking-only subset of stem-master — no tone/dynamics shaping, no sum,
    no master. Pass two or more stem files.
    """
    from pathlib import Path

    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import unmask_stems

    if len(stem_paths) < 2:
        raise click.BadParameter(
            "pass at least two stem files", param_hint="STEM_PATHS"
        )
    stems: dict[str, str] = {}
    for p in stem_paths:
        name = Path(p).stem
        if name in stems:
            raise click.BadParameter(
                f"duplicate stem name {name!r} (rename so the names are unique)",
                param_hint="STEM_PATHS",
            )
        stems[name] = p
    corrections = _load_json_obj(corrections_json, "--corrections-json")

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await unmask_stems(
                hub, stems, corrections=corrections,
                cross_check=cross_check, max_conflicts=max_conflicts,
            )

    _run(_go())


@main.command(name="stem-master")
@click.argument("stem_paths", nargs=-1, required=True, type=click.Path())
@click.option("--corrections-json", "corrections_json", type=click.Path(), default=None,
              help="JSON object mapping a stem NAME (filename without extension) to "
                   "its corrective moves (eq_bands / deess / suppress / "
                   "dynamic_eq_bands / compress / multiband / shape_bands).")
@click.option("--cross-check", is_flag=True, default=False,
              help="Also run the loops detect-masking cross-check.")
@click.option("--max-conflicts", type=int, default=8, show_default=True,
              help="Max masking conflicts analyze-stem-masking reports.")
def stem_master_cmd(stem_paths: tuple[str, ...], corrections_json: str | None,
                    cross_check: bool, max_conflicts: int) -> None:
    """Per-stem corrective + masking verification (sum + master are separate).

    Pass two or more stem files. Then sum the corrected stems with
    `drum-prep stem-mix` and master the bus with `ship-studios master` — those
    stages are local DSP / a separate pipeline, by design.
    """
    from pathlib import Path

    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import stem_master

    if len(stem_paths) < 2:
        raise click.BadParameter(
            "pass at least two stem files", param_hint="STEM_PATHS"
        )
    stems: dict[str, str] = {}
    for p in stem_paths:
        name = Path(p).stem
        if name in stems:
            raise click.BadParameter(
                f"duplicate stem name {name!r} (rename so the names are unique)",
                param_hint="STEM_PATHS",
            )
        stems[name] = p
    corrections = _load_json_obj(corrections_json, "--corrections-json")

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await stem_master(
                hub, stems, corrections=corrections,
                cross_check=cross_check, max_conflicts=max_conflicts,
            )

    _run(_go())


@main.command(name="mix-check")
@click.argument("mix_path", type=click.Path())
@click.option("--severity", "severity_threshold", default="any", show_default=True,
              type=click.Choice(SEVERITY_CHOICES),
              help="Lowest severity floor to report (any reports everything).")
@click.option("--eq-json", "eq_json", type=click.Path(), default=None,
              help="JSON list of corrective EQ bands to apply after diagnosis "
                   '(e.g. [{"freq_hz":200,"gain_db":-2,"q":1,"type":"bell"}]).')
@click.option("--eq-out", "eq_out_path", type=click.Path(), default=None,
              help="Where to write the EQ'd mix (with --eq-json).")
@click.option("--deess", is_flag=True, default=False,
              help="Also de-ess (tame sibilance) with default settings.")
@click.option("--de-harsh", "de_harsh", is_flag=True, default=False,
              help="Also run suppress-resonances (Soothe-style de-harsh).")
@click.option("--dynamic-eq-json", "dynamic_eq_json", type=click.Path(), default=None,
              help="JSON list of dynamic-EQ bands (level-dependent carves).")
@click.option("--excite", is_flag=True, default=False,
              help="Also add band-limited air/presence (excite-loop).")
@click.option("--compress", is_flag=True, default=False,
              help="Also run compress-loop.")
@click.option("--multiband", is_flag=True, default=False,
              help="Also run multiband-compress (per-band dynamics).")
def mix_check_cmd(mix_path: str, severity_threshold: str, eq_json: str | None,
                  eq_out_path: str | None, deess: bool, de_harsh: bool,
                  dynamic_eq_json: str | None, excite: bool, compress: bool,
                  multiband: bool) -> None:
    """Diagnose a mix (perceptual + measurement) and surface concrete moves.

    The corrective steps are opt-in and chain in order: --eq-json, --deess,
    --de-harsh, --dynamic-eq-json, --excite, --compress, --multiband. The bool
    flags run their tool with default settings; the *-json flags carry EQ moves.
    """
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import mix_check

    eq_bands = _load_eq_bands(eq_json)
    dyn_bands = _load_eq_bands(dynamic_eq_json, hint="--dynamic-eq-json")

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await mix_check(
                hub, mix_path, severity_threshold=severity_threshold,
                eq_bands=eq_bands, eq_out_path=eq_out_path,
                deess={} if deess else None,
                suppress={} if de_harsh else None,
                dynamic_eq_bands=dyn_bands,
                excite={} if excite else None,
                compress=compress,
                multiband={} if multiband else None,
            )

    _run(_go())


@main.command(name="reference-match")
@click.argument("mix_path", type=click.Path())
@click.option("--reference", "ref_path", required=True, type=click.Path(),
              help="Reference track to match the mix toward.")
@click.option("--goal", default="match the reference tonal balance and loudness",
              show_default=True)
@click.option("--match-strength", type=click.FloatRange(0.0, 1.0), default=0.5,
              show_default=True,
              help="How much of the mix->reference delta match-eq corrects "
                   "(0=none, 1=fully flatten toward the reference).")
@click.option("--match-phase", type=click.Choice(["minimum", "linear", "tilt_only"]),
              default="minimum", show_default=True,
              help="match-eq filter realization (FIR phase, or 1 kHz tilt shelves).")
@click.option("--match-out", "match_out_path", type=click.Path(), default=None,
              help="Where to write the match-eq corrected mix.")
@click.option("--ab-out", "ab_out_path", type=click.Path(), default=None,
              help="Where to write the A/B audition WAV.")
@click.option("--eq-json", "eq_json", type=click.Path(), default=None,
              help="JSON list of SURGICAL residual EQ bands, layered on the "
                   "match-eq'd mix before the A/B (match-eq always runs first).")
@click.option("--eq-out", "eq_out_path", type=click.Path(), default=None,
              help="Where to write the residual-EQ'd mix (with --eq-json).")
def reference_match_cmd(
    mix_path: str, ref_path: str, goal: str,
    match_strength: float, match_phase: str, match_out_path: str | None,
    ab_out_path: str | None, eq_json: str | None, eq_out_path: str | None,
) -> None:
    """Match a mix to a reference and render a loudness-matched A/B audition."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import reference_match

    eq_bands = _load_eq_bands(eq_json)

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await reference_match(
                hub, mix_path, ref_path, goal=goal,
                match_strength=match_strength, match_phase=match_phase,
                match_out_path=match_out_path, ab_out_path=ab_out_path,
                eq_bands=eq_bands, eq_out_path=eq_out_path,
            )

    _run(_go())


@main.command()
@click.argument("input_path", type=click.Path())
@click.option("--bpm", required=True, type=click.FloatRange(min=1, max=400),
              help="Known tempo of the source (1-400 BPM).")
@click.option("--out-dir", type=click.Path(), default=None,
              help="Where find-loops writes loop WAVs + manifest.json.")
@click.option("--deliverables-dir", type=click.Path(), default=None)
@click.option("--bars", default=None,
              help="Comma-separated bar lengths, e.g. 1,2,4.")
@click.option("--top-n", type=int, default=None)
@click.option("--separate", is_flag=True, default=False,
              help="Run Demucs first (input is a full mix, not a drum stem).")
@click.option("--target-lufs", default=-10.0, show_default=True, type=float)
@click.option("--ceiling-dbtp", default=-1.0, show_default=True, type=float)
@click.option("--originator", default="ship-studios", show_default=True)
@click.option("--key", default=None)
@click.option("--root-note", type=click.IntRange(0, 127), default=None,
              help="MIDI root note (0-127) embedded in the loop tags.")
@click.option("--presets", default=None,
              help="Comma-separated export presets (default: distribution_44k_16,"
                   "production_48k_24,master_96k_24).")
@click.option("--describe", is_flag=True, default=False,
              help="Attach Gemini-backed audible descriptions to the set.")
def loops(
    input_path: str,
    bpm: float,
    out_dir: str | None,
    deliverables_dir: str | None,
    bars: str | None,
    top_n: int | None,
    separate: bool,
    target_lufs: float,
    ceiling_dbtp: float,
    originator: str,
    key: str | None,
    root_note: int | None,
    presets: str | None,
    describe: bool,
) -> None:
    """Slice a stem/mix into cleaned, mastered, tagged loop deliverables."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import loops_to_deliverables

    bar_list = _parse_bars(bars)
    preset_list = _parse_presets(presets)

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await loops_to_deliverables(
                hub,
                input_path,
                bpm,
                out_dir=out_dir,
                deliverables_dir=deliverables_dir,
                bars=bar_list,
                top_n=top_n,
                separate=separate,
                target_lufs=target_lufs,
                ceiling_dbtp=ceiling_dbtp,
                originator=originator,
                key=key,
                root_note=root_note,
                presets=preset_list,
                describe=describe,
            )

    _run(_go())


@main.command()
@click.argument("path", type=click.Path())
@click.option("--transcribe/--no-transcribe", default=True, show_default=True,
              help="Transcribe speech (the default). Auto-skips when you request a "
                   "more specific analysis (region/event/labels/compare/json) without "
                   "explicitly asking to transcribe — pass --transcribe to force it.")
@click.option("--diarize", is_flag=True, default=False)
@click.option("--region", nargs=3, type=(float, float, str), default=None,
              help="START_S END_S PROMPT — Q&A a time window.")
@click.option("--event", "event_description", default=None,
              help="Detect timestamped instances of a described event.")
@click.option("--labels", default=None,
              help="Comma-separated labels for zero-shot classification.")
@click.option("--multi-label", is_flag=True, default=False)
@click.option("--compare", "compare_paths", multiple=True, type=click.Path(),
              help="Additional file(s) to compare against PATH.")
@click.option("--compare-prompt", "compare_prompt", default=None,
              help="Prompt to focus the comparison (with --compare).")
@click.option("--compare-schema", "compare_schema_path", type=click.Path(), default=None,
              help="JSON Schema file to structure the comparison output.")
@click.option("--json-prompt", "json_prompt", default=None,
              help="Prompt for audio-to-json structured extraction (with --json-schema).")
@click.option("--json-schema", "json_schema_path", type=click.Path(), default=None,
              help="JSON Schema file -> run audio-to-json structured extraction on PATH.")
def understand(
    path: str,
    transcribe: bool,
    diarize: bool,
    region: tuple[float, float, str] | None,
    event_description: str | None,
    labels: str | None,
    multi_label: bool,
    compare_paths: tuple[str, ...],
    compare_prompt: str | None,
    compare_schema_path: str | None,
    json_prompt: str | None,
    json_schema_path: str | None,
) -> None:
    """Gemini perceptual analysis (transcribe/region/events/classify/compare/json)."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import understand_audio

    label_list = [s.strip() for s in labels.split(",") if s.strip()] if labels else None
    compares = list(compare_paths) or None
    compare_schema = _load_json_obj(compare_schema_path, "--compare-schema")
    json_schema = _load_json_obj(json_schema_path, "--json-schema")

    # Don't fire a paid transcribe-audio call by default when the user asked for a
    # more specific analysis (region/event/labels/compare/json) but never
    # explicitly opted into transcription. An explicit --transcribe/--no-transcribe
    # always wins; --transcribe alone (no other request) still transcribes.
    ctx = click.get_current_context()
    transcribe_explicit = (
        ctx.get_parameter_source("transcribe") != click.core.ParameterSource.DEFAULT
    )
    wants_specific = any(
        x is not None for x in (region, event_description, label_list, compares,
                                json_schema)
    )
    if transcribe and not transcribe_explicit and wants_specific:
        transcribe = False

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await understand_audio(
                hub,
                path,
                transcribe=transcribe,
                diarize=diarize,
                region=region,
                event_description=event_description,
                labels=label_list,
                multi_label=multi_label,
                compare_paths=compares,
                compare_prompt=compare_prompt,
                compare_schema=compare_schema,
                json_prompt=json_prompt,
                json_schema=json_schema,
            )

    _run(_go())


@main.command()
def doctor() -> None:
    """Check env vars + sibling repos and print setup guidance.

    Pure config + filesystem probing — never imports the MCP SDK or launches
    a server, so it works as a first-run diagnostic before anything is set up.
    Exits non-zero if any required piece is missing.
    """
    import os

    ok = True

    click.echo("ship-studios doctor")
    click.echo("=" * 40)

    click.echo("\nSibling MCP servers:")
    for label, directory, script in (
        ("stemmy-loops", config.loops_dir(), config.LOOPS_CONSOLE_SCRIPT),
        ("stemmy-gemini", config.gemini_dir(), config.GEMINI_CONSOLE_SCRIPT),
    ):
        present = directory.is_dir()
        # A bare directory isn't enough — flag a dir that doesn't look like the
        # synced repo (no pyproject.toml), which would otherwise read "ok" and
        # then fail at launch with a confusing uv error.
        looks_synced = present and (directory / "pyproject.toml").is_file()
        ok = ok and looks_synced
        mark = "ok " if looks_synced else "MISSING"
        click.echo(f"  [{mark}] {label}: {directory}")
        if not present:
            click.echo(
                f"        expected the repo here; clone it or set "
                f"{'SHIP_STUDIOS_LOOPS_DIR' if label == 'stemmy-loops' else 'SHIP_STUDIOS_GEMINI_DIR'}"
            )
        elif not looks_synced:
            click.echo(
                "        directory exists but has no pyproject.toml — not the "
                "synced repo? run `uv sync` in it (see CLAUDE.md setup)."
            )
        else:
            click.echo(
                f"        launch: uv --directory {directory} run {script}"
            )

    click.echo("\nEnvironment:")
    for var in config.ENV_VARS:
        present = bool(os.environ.get(var))
        # Keys are optional in the strict sense (only some tools need each),
        # but the doctor flags an unset key as a setup gap so the user knows
        # which tools will fail. Missing keys don't fail the run themselves.
        mark = "ok " if present else "unset"
        click.echo(f"  [{mark}] {var}")
        if not present:
            click.echo(
                f"        set {var} in your shell or .env "
                f"(needed by the LLM/Gemini-backed tools)"
            )

    click.echo("\n'uv' on PATH:")
    import shutil

    uv = shutil.which("uv")
    if uv:
        click.echo(f"  [ok ] uv: {uv}")
    else:
        ok = False
        click.echo("  [MISSING] uv not found on PATH — install from https://docs.astral.sh/uv/")

    click.echo()
    if ok:
        click.echo("All required components present.")
    else:
        click.echo("Setup incomplete — resolve the items marked MISSING above.")
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
