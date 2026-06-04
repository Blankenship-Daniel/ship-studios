"""``drum-prep`` console script — local multi-mic drum-stem DSP.

A separate entry point from ``ship-studios`` on purpose: the hub orchestrates
the MCP servers and stays DSP-free, while this drives the local drum_prep flows.
Style mirrors ``ship_studios/cli.py`` — Click group, lazy imports inside
handlers (so ``--help`` and ``detect`` work before the ``drum-prep`` extra is
installed), and JSON pretty-printed results.
"""
from __future__ import annotations

import json
import math
import os
from collections.abc import Callable
from typing import Any

import click

from drum_prep import __version__
from drum_prep.kit import KitError


def _json_safe(obj: Any) -> Any:
    """Recursively replace non-finite floats (inf/-inf/nan) with None.

    The flows put ``float('-inf')`` (silence -> -inf dBFS) and pyloudnorm's -inf
    into result dicts; ``json.dumps`` would emit the non-standard tokens
    ``-Infinity``/``NaN`` that strict parsers reject. Map them to JSON ``null``
    so the output round-trips through any conformant parser.
    """
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _echo(result: dict[str, Any]) -> None:
    # allow_nan=False is a backstop: a non-finite float the sanitizer missed
    # raises here (loud) rather than emitting an invalid -Infinity/NaN token.
    click.echo(json.dumps(_json_safe(result), indent=2, default=str, allow_nan=False))


#: soundfile raises ``LibsndfileError`` (MRO: …RuntimeError, NOT ValueError) on a
#: missing/non-audio file. Match by class name so _go can surface it cleanly
#: without importing soundfile (the --help/detect paths must work without the
#: drum-prep extra installed).
_SOUNDFILE_ERRORS = {"LibsndfileError", "SoundFileError", "SoundFileRuntimeError"}


def _go(thunk: Callable[[], dict[str, Any]]) -> None:
    """Run a flow, turning expected failures into clean CLI errors."""
    try:
        _echo(thunk())
    except ImportError as exc:
        raise click.ClickException(
            f"missing DSP dependency ({exc}). Install with: uv sync --extra drum-prep"
        ) from exc
    except (KitError, ValueError, FileNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:
        # a bad/non-audio --reference/--plate/--include path reaches soundfile;
        # turn that into a clean CLI error too, not a raw traceback.
        if type(exc).__name__ in _SOUNDFILE_ERRORS:
            raise click.ClickException(f"could not read audio: {exc}") from exc
        raise


_SRC = click.argument("src", type=click.Path(exists=True, file_okay=False))
_MANIFEST = click.option("--manifest", type=click.Path(), default=None,
                         help="kit.json (default: <SRC>/kit.json if present).")
_REF = click.option("--reference", "reference", type=click.Path(exists=True, dir_okay=False),
                    default=None, help="Reference audio (overrides kit.json 'reference').")


@click.group()
@click.version_option(__version__, prog_name="drum-prep")
def main() -> None:
    """Phase-align, reference-match, and audition a multi-mic drum kit (local DSP)."""


@main.command()
@_SRC
@_MANIFEST
@click.option("--write-manifest", "write_manifest", type=click.Path(), default=None,
              help="Write the resolved kit to this kit.json for editing.")
@click.option("--strict/--no-strict", default=False, show_default=True,
              help="Fail on unresolved roles instead of warning.")
def detect(src: str, manifest: str | None, write_manifest: str | None, strict: bool) -> None:
    """Auto-detect mic roles; optionally write an editable kit.json."""
    def run() -> dict[str, Any]:
        from drum_prep import kit as kitmod

        k = kitmod.resolve_kit(src, manifest, strict)
        out = k.to_dict()
        out["warnings"] = k.warnings
        if write_manifest:
            kitmod.save_manifest(k, write_manifest)
            out["wrote_manifest"] = write_manifest
        return out
    _go(run)


@main.command()
@_SRC
@_MANIFEST
@click.option("--out", "out_path", type=click.Path(), default=None,
              help="Output stereo overhead (default: <SRC>/stereo/overheads-merged.aif).")
@click.option("--align", is_flag=True, default=False,
              help="Phase-lock R to L (collapses a spaced-pair image; off by default).")
def overheads(src: str, manifest: str | None, out_path: str | None, align: bool) -> None:
    """Merge an L/R overhead pair into one stereo reference (no-op if already stereo)."""
    def run() -> dict[str, Any]:
        from drum_prep.kit import resolve_kit
        from drum_prep.overheads import merge_overheads

        return merge_overheads(resolve_kit(src, manifest, strict=False), out_path, align)
    _go(run)


@main.command(name="stereo-merge")
@_SRC
@click.option("--out-dir", type=click.Path(), default=None,
              help="Output dir (default: <SRC>/stereo/).")
@click.option("--align", is_flag=True, default=False,
              help="Phase-lock R to L (collapses a spaced image; off by default).")
def stereo_merge_cmd(src: str, out_dir: str | None, align: bool) -> None:
    """Merge every '<name> - left/right' pair into a stereo file (subtype-preserving;
    container follows the output extension)."""
    def run() -> dict[str, Any]:
        from drum_prep.stereo_merge import merge_dir

        return merge_dir(src, out_dir, align)
    _go(run)


@main.command()
@_SRC
@click.option("--out-dir", type=click.Path(), default=None,
              help="Output dir (default: <SRC>/normalized/).")
@click.option("--target-dbfs", default=-1.0, show_default=True, type=float)
@click.option("--mode", type=click.Choice(["global", "per-file"]), default="global",
              show_default=True,
              help="global preserves kit balance; per-file maximizes each stem (changes balance).")
@click.option("--include", "include", multiple=True, type=click.Path(exists=True, dir_okay=False),
              help="Extra file(s) folded into the SAME global gain "
                   "(e.g. an fx return). Repeatable.")
def normalize(src: str, out_dir: str | None, target_dbfs: float, mode: str,
              include: tuple[str, ...]) -> None:
    """Gain-stage the kit (balance-preserving global gain by default)."""
    def run() -> dict[str, Any]:
        from drum_prep.normalize import normalize_kit

        return normalize_kit(src, out_dir, target_dbfs, mode.replace("-", "_"), tuple(include))
    _go(run)


@main.command()
@_SRC
@_MANIFEST
@click.option("--stems-dir", type=click.Path(), default=None,
              help="Stems to mix (default: <SRC>/ref-matched/ if present, else <SRC>).")
@click.option("--out-dir", type=click.Path(), default=None,
              help="Output dir (default: <SRC>/mix/).")
@click.option("--feel", type=click.Choice(["roomy", "punchy", "natural", "dry"]), default="roomy",
              show_default=True)
@click.option("--perspective", type=click.Choice(["audience", "drummer"]), default="audience",
              show_default=True)
@click.option("--plate", type=click.Path(exists=True, dir_okay=False), default=None,
              help="Optional FX/plate return file to fold in as a reverb return.")
@click.option("--plate-offset", default=-19.0, show_default=True, type=float)
@click.option("--flat", is_flag=True, default=False,
              help="Unity bounce (no balance/pan), just anti-clip — a print of the prepped kit.")
@click.option("--t0", default=44.0, show_default=True, type=float, help="Excerpt start (s).")
@click.option("--dur", default=12.0, show_default=True, type=float,
              help="Excerpt length (s); 0 to skip.")
def mix(src: str, manifest: str | None, stems_dir: str | None, out_dir: str | None,
        feel: str, perspective: str, plate: str | None, plate_offset: float,
        flat: bool, t0: float, dur: float) -> None:
    """Mix the prepped kit to a stereo bus (balance + pan + FX return)."""
    def run() -> dict[str, Any]:
        from drum_prep.kit import resolve_kit
        from drum_prep.mix import mix_kit

        kit = resolve_kit(src, manifest, strict=False)
        rm = os.path.join(src, "ref-matched")
        sd = stems_dir or (rm if os.path.isdir(rm) else src)
        return mix_kit(kit, sd, out_dir=out_dir, feel=feel, perspective=perspective,
                       plate=plate, plate_offset=plate_offset, flat=flat, t0=t0, dur=dur)
    _go(run)


@main.command(name="stem-mix")
@_SRC
@click.option("--out-dir", type=click.Path(), default=None,
              help="Output dir (default: <SRC>/mix/).")
@click.option("--target-lufs", default=-18.0, show_default=True, type=float)
@click.option("--spec", type=click.Path(exists=True), default=None,
              help='JSON balance spec {filename: {gain_db, pan, mute}}.')
@click.option("--t0", default=0.0, show_default=True, type=float)
@click.option("--dur", default=0.0, show_default=True, type=float,
              help="Excerpt length (0 = skip).")
def stem_mix_cmd(src: str, out_dir: str | None, target_lufs: float, spec: str | None,
                 t0: float, dur: float) -> None:
    """Mix arbitrary named stems to a stereo bus (role-agnostic song mix)."""
    def run() -> dict[str, Any]:
        from drum_prep.stem_mix import mix_stems

        if spec:
            with open(spec) as fh:
                sp = json.load(fh)
        else:
            sp = None
        return mix_stems(src, out_dir, target_lufs, sp, t0=t0, dur=dur)
    _go(run)


@main.command(name="sub-design")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", "out_path", type=click.Path(), required=True)
@click.option("--sub-hz", default=None, type=float,
              help="Sub frequency (default: detected fundamental).")
@click.option("--amount-db", default=-3.0, show_default=True, type=float,
              help="Sub level relative to the kick.")
def sub_design_cmd(path: str, out_path: str, sub_hz: float | None, amount_db: float) -> None:
    """Add an envelope-followed sine sub under a kick (low-end EXTENSION, not EQ)."""
    def run() -> dict[str, Any]:
        from drum_prep.sub_design import add_sub

        return add_sub(path, out_path, sub_hz=sub_hz, amount_db=amount_db)
    _go(run)


@main.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", "out_path", type=click.Path(), default=None,
              help="Output WAV (omit to only measure the fundamental).")
@click.option("--target-hz", default=None, type=float)
@click.option("--target-midi", default=None, type=int)
@click.option("--semitones", default=None, type=float)
def tune(path: str, out_path: str | None, target_hz: float | None,
         target_midi: int | None, semitones: float | None) -> None:
    """Measure a drum sample's fundamental; with --out, retune it (resample — samples only)."""
    def run() -> dict[str, Any]:
        from drum_prep.tune import measure_fundamental, retune

        if out_path is None:
            return {"flow": "tune", **measure_fundamental(path)}
        return retune(path, out_path, target_hz, target_midi, semitones)
    _go(run)


@main.command(name="verify-tags")
@_SRC
def verify_tags_cmd(src: str) -> None:
    """Verify deliverables (WAV/AIFF/FLAC) carry embedded metadata (WAV RIFF INFO /
    AIFF text chunks) + a .tags.json sidecar."""
    def run() -> dict[str, Any]:
        from drum_prep.qc import verify_dir

        return verify_dir(src)
    _go(run)


@main.command(name="phase-align")
@_SRC
@_MANIFEST
@click.option("--out-dir", type=click.Path(), default=None,
              help="Output dir (default: <SRC>/phase-aligned/).")
@click.option("--max-lag", default=600, show_default=True, type=int)
@click.option("--excerpt-s", default=40.0, show_default=True, type=float)
@click.option("--kick-lowpass", default=180.0, show_default=True, type=float)
@click.option("--strict/--no-strict", default=True, show_default=True)
def phase_align_cmd(src: str, manifest: str | None, out_dir: str | None,
                    max_lag: int, excerpt_s: float, kick_lowpass: float, strict: bool) -> None:
    """Phase-align every close mic to the overheads."""
    def run() -> dict[str, Any]:
        from drum_prep.kit import resolve_kit
        from drum_prep.phase_align import phase_align

        kit = resolve_kit(src, manifest, strict)
        return phase_align(kit, out_dir=out_dir, max_lag=max_lag,
                           excerpt_s=excerpt_s, kick_lowpass=kick_lowpass)
    _go(run)


@main.command()
@_SRC
@_REF
@_MANIFEST
@click.option("--aligned-dir", type=click.Path(), default=None,
              help="Aligned stems dir (default: <SRC>/phase-aligned/).")
def analyze(src: str, reference: str | None, manifest: str | None, aligned_dir: str | None) -> None:
    """Read-only tonal report: reference vs kit + per-band ownership."""
    def run() -> dict[str, Any]:
        from drum_prep.kit import resolve_kit
        from drum_prep.reference_match import analyze as analyze_flow

        kit = resolve_kit(src, manifest, strict=False)
        return analyze_flow(kit, reference, aligned_dir=aligned_dir)
    _go(run)


@main.command(name="reference-match")
@_SRC
@_REF
@_MANIFEST
@click.option("--aligned-dir", type=click.Path(), default=None)
@click.option("--out-dir", type=click.Path(), default=None,
              help="Output dir (default: <SRC>/ref-matched/).")
@click.option("--strength", default=0.75, show_default=True, type=float)
@click.option("--boost-cap", default=6.0, show_default=True, type=float)
@click.option("--cut-cap", default=-8.0, show_default=True, type=float)
@click.option("--owner-thresh", default=0.20, show_default=True, type=float)
@click.option("--low-zero", default=30.0, show_default=True, type=float)
@click.option("--ceil-dbfs", default=-1.0, show_default=True, type=float)
def reference_match_cmd(src: str, reference: str | None, manifest: str | None,
                        aligned_dir: str | None, out_dir: str | None, strength: float,
                        boost_cap: float, cut_cap: float, owner_thresh: float,
                        low_zero: float, ceil_dbfs: float) -> None:
    """Per-stem reference-match EQ of the aligned kit."""
    def run() -> dict[str, Any]:
        from drum_prep.kit import resolve_kit
        from drum_prep.reference_match import apply_match

        kit = resolve_kit(src, manifest, strict=False)
        return apply_match(kit, reference, aligned_dir=aligned_dir, out_dir=out_dir,
                           strength=strength, boost_cap=boost_cap, cut_cap=cut_cap,
                           owner_thresh=owner_thresh, low_zero=low_zero, ceil_dbfs=ceil_dbfs)
    _go(run)


@main.command()
@_SRC
@_REF
@_MANIFEST
@click.option("--aligned-dir", type=click.Path(), default=None)
@click.option("--matched-dir", type=click.Path(), default=None)
@click.option("--out-dir", type=click.Path(), default=None,
              help="Output dir (default: <SRC>/auditions/).")
@click.option("--t0", default=44.0, show_default=True, type=float, help="Excerpt start (s).")
@click.option("--dur", default=12.0, show_default=True, type=float, help="Excerpt length (s).")
@click.option("--gap", default=0.6, show_default=True, type=float, help="A/B gap (s).")
@click.option("--ceil", default=0.95, show_default=True, type=float,
              help="Anti-clip peak ceiling (linear, 0-1) applied after loudness match.")
@click.option("--emit-halves/--no-emit-halves", default=True, show_default=True,
              help="Also write standalone loudness-matched halves for compare-to-reference.")
def audition(src: str, reference: str | None, manifest: str | None, aligned_dir: str | None,
             matched_dir: str | None, out_dir: str | None, t0: float, dur: float, gap: float,
             ceil: float, emit_halves: bool) -> None:
    """Render loudness-matched stereo A/B auditions."""
    def run() -> dict[str, Any]:
        from drum_prep.audition import render_auditions
        from drum_prep.kit import resolve_kit

        kit = resolve_kit(src, manifest, strict=False)
        return render_auditions(kit, reference, aligned_dir=aligned_dir,
                                matched_dir=matched_dir, out_dir=out_dir,
                                t0=t0, dur=dur, gap=gap, ceil=ceil, emit_halves=emit_halves)
    _go(run)


@main.command()
@_SRC
@click.option("--reference", "reference", type=click.Path(exists=True, dir_okay=False),
              required=True, help="Reference audio to match the kit to.")
@_MANIFEST
@click.option("--out-root", type=click.Path(), default=None,
              help="Root for outputs (default: SRC). "
                   "Subdirs phase-aligned/ ref-matched/ auditions/.")
@click.option("--strict/--no-strict", default=True, show_default=True)
@click.option("--max-lag", default=600, show_default=True, type=int)
@click.option("--excerpt-s", default=40.0, show_default=True, type=float)
@click.option("--kick-lowpass", default=180.0, show_default=True, type=float)
@click.option("--strength", default=0.75, show_default=True, type=float)
@click.option("--t0", default=44.0, show_default=True, type=float)
@click.option("--dur", default=12.0, show_default=True, type=float)
@click.option("--gap", default=0.6, show_default=True, type=float)
def chain(src: str, reference: str, manifest: str | None, out_root: str | None, strict: bool,
          max_lag: int, excerpt_s: float, kick_lowpass: float, strength: float,
          t0: float, dur: float, gap: float) -> None:
    """End-to-end: detect -> phase-align -> reference-match -> audition."""
    def run() -> dict[str, Any]:
        from drum_prep.chain import run_chain

        return run_chain(src, reference, manifest_path=manifest, out_root=out_root,
                         strict=strict, max_lag=max_lag, excerpt_s=excerpt_s,
                         kick_lowpass=kick_lowpass, strength=strength, t0=t0, dur=dur, gap=gap)
    _go(run)


if __name__ == "__main__":
    main()
