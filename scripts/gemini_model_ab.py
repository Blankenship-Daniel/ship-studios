#!/usr/bin/env python3
"""Gemini model A/B harness for the perceptual critique tools.

Runs the stemmy-gemini perceptual critique tools across THREE Gemini models on
ONE audio file and tabulates the structured outputs side by side so a human can
judge which model reads the audio best. **This script decides nothing.** The
model-currency call is *ear-gated*: a 2026-06-02 report flags that the whole
Gemini 3 series may have regressed on audio/ASR versus the 2.5 line, so a model
bump is not a safe drop-in — the default (``STEMMY_MCP_MODEL``) stays put until a
human compares candidates on real material and decides by ear.

Models compared (override with ``--models a,b,c``):
  * ``gemini-3.1-pro-preview``  — current repo default (preview)
  * ``gemini-3.5-flash``        — GA (2026-05-19), audio-capable flash alternative
  * ``gemini-2.5-pro``          — GA, conservative audio fallback

Tools run (all need ``GEMINI_API_KEY``):
  * ``mastering-feedback``   — master-bus critique + release-ready bool
  * ``detect-mix-issues``    — audible problems w/ severity + timestamps
  * ``compare-to-reference`` — only when ``--reference`` is given (perceptual A/B)

How it drives the models: each tool runs in the real stemmy-gemini MCP server,
launched over stdio by ``ship_studios.mcp_client.Hub`` (the same client the
``ship-studios`` CLI uses). The gemini server reads its model from the
``STEMMY_MCP_MODEL`` env var, and ``config._passthrough_env`` forwards that var
into the subprocess. So to switch models we set ``os.environ["STEMMY_MCP_MODEL"]``
and open a *fresh* hub per model (a new subprocess that reads the new value) —
there is no per-call ``model=`` argument on the tools, so a new subprocess per
model is the clean seam. ``--model-env`` lets you point at a different var name
if the server's convention ever changes.

REQUIRES: ``GEMINI_API_KEY`` set in the environment, the ``stemmy-gemini-mcp``
sibling repo synced (``uv sync`` in it), and the MCP SDK installed for this repo.
This script makes real, billed Gemini calls (audio is metered at 32 tok/s).

Usage:
    export GEMINI_API_KEY=...
    python scripts/gemini_model_ab.py projects/<track>/mix/draft.wav
    python scripts/gemini_model_ab.py mix.wav --reference refs/ref.wav
    python scripts/gemini_model_ab.py mix.wav --models gemini-2.5-pro,gemini-3.5-flash
    python scripts/gemini_model_ab.py mix.wav --json results.json   # also dump raw

It is intentionally read-only — it never renders or writes audio. The default
``STEMMY_MCP_MODEL`` is restored on exit, so running the harness does not change
your environment for later tools.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Make ``import ship_studios`` work when run as a plain script from the repo root
# (``python scripts/gemini_model_ab.py …``) without an editable install.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ship_studios.config import GEMINI_SERVER  # noqa: E402
from ship_studios.mcp_client import ToolCallError, open_hub  # noqa: E402

#: The env var the stemmy-gemini server reads its model from (see CLAUDE.md /
#: config.GEMINI_OVERRIDE_ENV). Overridable via --model-env for forward-compat.
DEFAULT_MODEL_ENV = "STEMMY_MCP_MODEL"

#: The three models the human is choosing between. Order = display order.
DEFAULT_MODELS: list[str] = [
    "gemini-3.1-pro-preview",  # current repo default (preview)
    "gemini-3.5-flash",        # GA 2026-05-19, audio-capable flash alternative
    "gemini-2.5-pro",          # GA, conservative audio fallback
]


async def _run_one_model(
    model: str, audio_path: str, reference_path: str | None, model_env: str
) -> dict[str, Any]:
    """Run every critique tool once under ``model`` and return its raw outputs.

    Sets ``model_env`` to ``model`` in this process's env, then opens a fresh
    gemini-only hub so the spawned subprocess picks up the model (the server
    reads the var at startup). One subprocess per model is deliberate — the
    tools take no per-call ``model=`` argument. Tool failures are captured per
    tool as ``{"error": ...}`` so one model erroring out doesn't sink the table.
    """
    os.environ[model_env] = model
    out: dict[str, Any] = {"model": model, "tools": {}}

    async with open_hub([GEMINI_SERVER]) as hub:
        async def _call(tool: str, args: dict[str, Any]) -> None:
            try:
                out["tools"][tool] = await hub.call_tool(GEMINI_SERVER, tool, args)
            except ToolCallError as exc:  # tool ran but returned an error result
                out["tools"][tool] = {"error": exc.detail}
            except Exception as exc:  # transport / timeout / unexpected
                out["tools"][tool] = {"error": f"{type(exc).__name__}: {exc}"}

        await _call("mastering-feedback", {"path": audio_path})
        await _call("detect-mix-issues", {"path": audio_path})
        if reference_path is not None:
            await _call(
                "compare-to-reference",
                {
                    "mix_path": audio_path,
                    "reference_path": reference_path,
                    "goal": "compare the mix to the reference",
                },
            )

    return out


def _short(value: Any, width: int = 60) -> str:
    """One-line, width-capped repr of a structured value for the table."""
    if isinstance(value, dict) and "error" in value and len(value) == 1:
        text = f"ERROR: {value['error']}"
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    text = " ".join(text.split())  # collapse whitespace/newlines
    return text if len(text) <= width else text[: width - 1] + "…"


def _print_table(results: list[dict[str, Any]]) -> None:
    """Print a tool×model grid of one-line summaries, then per-tool detail.

    The grid is the at-a-glance "do these even agree?" view; the detail blocks
    below give the human the full structured output to actually judge by.
    """
    models = [r["model"] for r in results]
    tools: list[str] = []
    for r in results:
        for t in r["tools"]:
            if t not in tools:
                tools.append(t)

    col_w = 62
    name_w = max((len(t) for t in tools), default=10) + 2

    print("\n=== SIDE-BY-SIDE SUMMARY (one line per tool×model) ===\n")
    header = "tool".ljust(name_w) + "".join(m.ljust(col_w) for m in models)
    print(header)
    print("-" * len(header))
    for tool in tools:
        row = tool.ljust(name_w)
        for r in results:
            row += _short(r["tools"].get(tool, "—"), col_w - 2).ljust(col_w)
        print(row)

    print("\n=== PER-TOOL DETAIL (full structured output) ===")
    for tool in tools:
        print(f"\n--- {tool} ---")
        for r in results:
            print(f"\n[{r['model']}]")
            value = r["tools"].get(tool, "(not run)")
            print(json.dumps(value, ensure_ascii=False, indent=2, default=str))

    print(
        "\nThe model-currency decision is yours to make BY EAR — a 2026-06-02 report\n"
        "flags a possible Gemini-3 audio/ASR regression, so do NOT auto-upgrade the\n"
        "default. Keep gemini-2.5-pro as the conservative fallback.\n"
    )


async def _amain(args: argparse.Namespace) -> int:
    audio_path = str(Path(args.audio).expanduser())
    reference_path = (
        str(Path(args.reference).expanduser()) if args.reference else None
    )
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    if not os.environ.get("GEMINI_API_KEY"):
        print("error: GEMINI_API_KEY is not set — this harness makes real Gemini "
              "calls.", file=sys.stderr)
        return 2
    if not Path(audio_path).is_file():
        print(f"error: audio file not found: {audio_path}", file=sys.stderr)
        return 2
    if reference_path is not None and not Path(reference_path).is_file():
        print(f"error: reference file not found: {reference_path}", file=sys.stderr)
        return 2

    # Restore whatever the default was so the harness doesn't leak a model choice
    # into the rest of the shell session.
    saved = os.environ.get(args.model_env)
    results: list[dict[str, Any]] = []
    try:
        for model in models:
            print(f"\n>>> running critique tools under {model} …", file=sys.stderr)
            results.append(
                await _run_one_model(model, audio_path, reference_path, args.model_env)
            )
    finally:
        if saved is None:
            os.environ.pop(args.model_env, None)
        else:
            os.environ[args.model_env] = saved

    _print_table(results)

    if args.json:
        Path(args.json).write_text(
            json.dumps({"audio": audio_path, "reference": reference_path,
                        "results": results}, ensure_ascii=False, indent=2, default=str)
        )
        print(f"raw results written to {args.json}", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="A/B the Gemini perceptual critique tools across models "
                    "(human/ears-gated; changes nothing).",
    )
    parser.add_argument("audio", help="path to the audio file to critique")
    parser.add_argument(
        "--reference", "-r", default=None,
        help="optional reference WAV → also runs compare-to-reference",
    )
    parser.add_argument(
        "--models", "-m", default=",".join(DEFAULT_MODELS),
        help="comma-separated model IDs to compare "
             f"(default: {','.join(DEFAULT_MODELS)})",
    )
    parser.add_argument(
        "--model-env", default=DEFAULT_MODEL_ENV,
        help=f"env var the gemini server reads its model from "
             f"(default: {DEFAULT_MODEL_ENV})",
    )
    parser.add_argument(
        "--json", default=None,
        help="also write the full raw results to this JSON path",
    )
    args = parser.parse_args(argv)
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
