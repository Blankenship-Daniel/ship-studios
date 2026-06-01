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


def _default_out(path: str, suffix: str) -> str:
    """Default output path: ``<dir>/<stem>.<suffix><ext>`` next to ``path``."""
    from pathlib import Path

    p = Path(path)
    return str(p.with_name(f"{p.stem}.{suffix}{p.suffix}"))


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


def _load_eq_bands(path: str | None) -> list[dict[str, Any]] | None:
    """Load corrective EQ bands from a JSON file (a list of band dicts).

    Lets the headless CLI reach the apply-eq branch of mix-check / reference-match
    (otherwise unreachable). Raises a clean Click error on a missing file or a
    payload that isn't a JSON list of objects.
    """
    if not path:
        return None
    from pathlib import Path

    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise click.BadParameter(f"file not found: {path}", param_hint="--eq-json") from None
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"invalid JSON in {path}: {exc}", param_hint="--eq-json") from None
    if not (isinstance(data, list) and all(isinstance(b, dict) for b in data)):
        raise click.BadParameter(
            "expected a JSON list of band objects, e.g. "
            '[{"freq_hz": 200, "gain_db": -2, "q": 1.0, "type": "bell"}]',
            param_hint="--eq-json",
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
                   "(default: <mix dir>/<stem>.master.wav).")
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
) -> None:
    """Master a near-final mix and export the deliverable format matrix."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import master_track

    resolved_out = out_path or _default_out(mix_path, "master")

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
@click.option("--compress", is_flag=True, default=False,
              help="Also run compress-loop after EQ.")
def mix_check_cmd(mix_path: str, severity_threshold: str, eq_json: str | None,
                  eq_out_path: str | None, compress: bool) -> None:
    """Diagnose a mix (perceptual + measurement) and surface concrete moves."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import mix_check

    eq_bands = _load_eq_bands(eq_json)

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await mix_check(
                hub, mix_path, severity_threshold=severity_threshold,
                eq_bands=eq_bands, eq_out_path=eq_out_path, compress=compress,
            )

    _run(_go())


@main.command(name="reference-match")
@click.argument("mix_path", type=click.Path())
@click.option("--reference", "ref_path", required=True, type=click.Path(),
              help="Reference track to match the mix toward.")
@click.option("--goal", default="match the reference tonal balance and loudness",
              show_default=True)
@click.option("--ab-out", "ab_out_path", type=click.Path(), default=None,
              help="Where to write the A/B audition WAV.")
@click.option("--eq-json", "eq_json", type=click.Path(), default=None,
              help="JSON list of corrective EQ bands to close the gap before the "
                   "A/B (otherwise the A/B compares the RAW mix to the reference).")
@click.option("--eq-out", "eq_out_path", type=click.Path(), default=None,
              help="Where to write the corrected mix (with --eq-json).")
def reference_match_cmd(
    mix_path: str, ref_path: str, goal: str, ab_out_path: str | None,
    eq_json: str | None, eq_out_path: str | None,
) -> None:
    """Match a mix to a reference and render a loudness-matched A/B audition."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import reference_match

    eq_bands = _load_eq_bands(eq_json)

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await reference_match(
                hub, mix_path, ref_path, goal=goal, ab_out_path=ab_out_path,
                eq_bands=eq_bands, eq_out_path=eq_out_path,
            )

    _run(_go())


@main.command()
@click.argument("input_path", type=click.Path())
@click.option("--bpm", required=True, type=float, help="Known tempo of the source.")
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
@click.option("--transcribe/--no-transcribe", default=True, show_default=True)
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
