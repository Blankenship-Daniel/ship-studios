#!/usr/bin/env python3
"""Snapshot the live MCP tool input-schemas into a committed test fixture (A6).

WHY: the offline suite drives pipelines against a ``RecordingHub`` that accepts
ANY args, so it never validates the *values* a pipeline emits against the real
tool ``inputSchema``. This generator captures each server's advertised
``name -> inputSchema`` into ``tests/fixtures/tool_schemas.json``;
``tests/test_arg_schemas.py`` then validates every pipeline's emitted args
against that snapshot — offline, with no live dependency in CI.

THIS IS A MANUAL GENERATOR. It needs the sibling repos synced and launchable
(it opens the real Hub over BOTH servers via ``uv run``); it is NOT run in CI.
Re-run it whenever a sibling tool's schema changes, then commit the updated
fixture. It lives under ``scripts/`` and so is excluded from ruff/mypy by design
(like the other probe/sweep helpers).

Usage::

    uv run python scripts/snapshot_tool_schemas.py
    # or target one server:
    uv run python scripts/snapshot_tool_schemas.py --server stemmy-loops
    # custom output path:
    uv run python scripts/snapshot_tool_schemas.py --out some/where.json

Exit codes: 0 on success, 1 if a server couldn't be reached / yielded no tools.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Make ``import ship_studios`` work when run as a plain script from the repo root
# (``python scripts/snapshot_tool_schemas.py``) without an editable install.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER, repo_root  # noqa: E402
from ship_studios.mcp_client import open_hub  # noqa: E402

_DEFAULT_OUT = repo_root() / "tests" / "fixtures" / "tool_schemas.json"


def _schema_of(tool: Any) -> Any:
    """Best-effort pull of a tool descriptor's input schema (SDK-version safe)."""
    schema = getattr(tool, "inputSchema", None)
    if schema is None:
        schema = getattr(tool, "input_schema", None)
    # Some SDK versions hand back a pydantic model; coerce to a plain dict.
    if schema is not None and hasattr(schema, "model_dump"):
        schema = schema.model_dump()
    return schema


async def _collect(server_keys: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    async with open_hub(server_keys) as hub:
        for key in server_keys:
            tools = await hub.list_tools(key)
            server_map: dict[str, Any] = {}
            for tool in tools:
                name = getattr(tool, "name", None)
                if not isinstance(name, str):
                    continue
                server_map[name] = _schema_of(tool)
            out[key] = server_map
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--server",
        choices=[LOOPS_SERVER, GEMINI_SERVER],
        action="append",
        help="limit to one server (repeatable); default = both",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help=f"output JSON path (default: {_DEFAULT_OUT})",
    )
    args = parser.parse_args(argv)

    server_keys = args.server or [LOOPS_SERVER, GEMINI_SERVER]

    try:
        snapshot = asyncio.run(_collect(server_keys))
    except Exception as exc:  # noqa: BLE001 — a generator: surface any launch failure
        print(f"error: could not snapshot tool schemas: {exc}", file=sys.stderr)
        print(
            "hint: the sibling repos must be synced and launchable "
            "(this is a manual generator, not a CI step).",
            file=sys.stderr,
        )
        return 1

    total = sum(len(m) for m in snapshot.values())
    if total == 0:
        print("error: no tools discovered on any server", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for key, m in snapshot.items():
        print(f"{key}: {len(m)} tool schemas")
    print(f"wrote {total} tool schemas across {len(snapshot)} servers -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
