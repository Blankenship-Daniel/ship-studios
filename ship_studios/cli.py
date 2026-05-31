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
from typing import Any, Awaitable

import click

from ship_studios import __version__, config


def _run(coro: Awaitable[dict[str, Any]]) -> None:
    """Drive an async pipeline to completion and pretty-print its result."""
    result: dict[str, Any] = asyncio.run(coro)  # type: ignore[arg-type]
    click.echo(json.dumps(result, indent=2, default=str))


def _default_out(path: str, suffix: str) -> str:
    """Default output path: ``<dir>/<stem>.<suffix><ext>`` next to ``path``."""
    from pathlib import Path

    p = Path(path)
    return str(p.with_name(f"{p.stem}.{suffix}{p.suffix}"))


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
@click.option("--platform", "target_platform", default="spotify", show_default=True)
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
@click.option("--severity", "severity_threshold", default="minor", show_default=True,
              help="Lowest severity of mix issue to report.")
def mix_check_cmd(mix_path: str, severity_threshold: str) -> None:
    """Diagnose a mix (perceptual + measurement) and surface concrete moves."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import mix_check

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await mix_check(
                hub, mix_path, severity_threshold=severity_threshold
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
def reference_match_cmd(
    mix_path: str, ref_path: str, goal: str, ab_out_path: str | None
) -> None:
    """Match a mix to a reference and render a loudness-matched A/B audition."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import reference_match

    async def _go() -> dict[str, Any]:
        async with open_hub() as hub:
            return await reference_match(
                hub, mix_path, ref_path, goal=goal, ab_out_path=ab_out_path
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
    describe: bool,
) -> None:
    """Slice a stem/mix into cleaned, mastered, tagged loop deliverables."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import loops_to_deliverables

    bar_list = [int(b) for b in bars.split(",") if b.strip()] if bars else None

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
def understand(
    path: str,
    transcribe: bool,
    diarize: bool,
    region: tuple[float, float, str] | None,
    event_description: str | None,
    labels: str | None,
    multi_label: bool,
    compare_paths: tuple[str, ...],
) -> None:
    """Gemini perceptual analysis (transcribe/region/events/classify/compare)."""
    from ship_studios.mcp_client import open_hub
    from ship_studios.pipelines import understand_audio

    label_list = [s.strip() for s in labels.split(",") if s.strip()] if labels else None
    compares = list(compare_paths) or None

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
        ok = ok and present
        mark = "ok " if present else "MISSING"
        click.echo(f"  [{mark}] {label}: {directory}")
        if not present:
            click.echo(
                f"        expected the repo here; clone it or set "
                f"{'SHIP_STUDIOS_LOOPS_DIR' if label == 'stemmy-loops' else 'SHIP_STUDIOS_GEMINI_DIR'}"
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
