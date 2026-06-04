"""Opt-in performance tracing for the hub (Stage 1 of docs/perf/roadmap.md).

Two layers, both cheap and additive:

* **Always-on timing** — :func:`now` (a monotonic ``perf_counter``) is used by
  the pipeline ``_Recorder`` and the :class:`~ship_studios.mcp_client.Hub` to
  stamp every MCP tool call with an ``elapsed_s``. This is stdlib-only and
  negligible, so it runs unconditionally; the duration just rides along in the
  recorded step dict / returned result.

* **Opt-in JSONL sink** — set ``SHIP_STUDIOS_PERF_LOG`` to a file path and each
  tool call (and the MCP handshake) also appends one JSON line
  ``{run_id, server, tool, elapsed_s, ok, kind?, rss_self?, rss_children?, at}``.
  Disabled by default, so the offline test suite and normal runs are unaffected.

The ``run_id`` correlates every call made through one :class:`Hub` instance —
the cross-process correlation key the roadmap calls for. (It is recorded in the
hub's own trace; it is deliberately NOT injected into tool-call ``args``, since
the sibling servers validate against strict input schemas and would reject an
unknown property.)

Per-subprocess RSS is best-effort: the optional ``psutil`` dependency (the
``metrics`` extra) is used to sample the hub process and its children, because
the MCP ``stdio_client`` transport never exposes the spawned child PID — so the
only handle on the ``uv --directory … run`` subprocesses is an OS process-tree
scan from the hub's own PID. Without ``psutil`` installed, RSS is simply omitted.

A telemetry sink must never break the pipeline it observes, so every IO path
here swallows its own errors and degrades to a no-op.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

#: File path to append the JSONL perf trace to; unset/empty disables the sink.
PERF_LOG_ENV = "SHIP_STUDIOS_PERF_LOG"


def perf_log_path() -> str | None:
    """The configured perf-trace file path, or ``None`` when tracing is off."""
    raw = os.environ.get(PERF_LOG_ENV)
    # Treat an empty string as unset, mirroring config._timeout / _passthrough_env.
    return raw or None


def perf_enabled() -> bool:
    """True when the opt-in JSONL perf sink is configured."""
    return perf_log_path() is not None


def new_run_id() -> str:
    """A short, unique id correlating every call made through one Hub session."""
    return uuid.uuid4().hex[:12]


def now() -> float:
    """Monotonic high-resolution clock for measuring durations (seconds)."""
    return time.perf_counter()


def _load_psutil() -> Any:
    """Return the ``psutil`` module if the ``metrics`` extra is installed, else None."""
    try:
        import psutil

        return psutil
    except ImportError:
        return None


#: Resolved once at import; ``Any`` so attribute access type-checks whether or
#: not the optional dependency is present (mypy treats a missing import as Any).
_PSUTIL: Any = _load_psutil()


def sample_rss() -> dict[str, int] | None:
    """Best-effort RSS (bytes) of the hub process and its children.

    Returns ``{"rss_self", "rss_children"}`` when ``psutil`` is available, else
    ``None``. The children sum captures the ``uv … run`` stdio MCP subprocesses
    (and any DSP/Demucs/Pedalboard workers they spawn) — the per-subprocess cost
    Claude Code's native telemetry cannot see. Never raises.
    """
    if _PSUTIL is None:
        return None
    try:
        proc = _PSUTIL.Process()
        own = int(proc.memory_info().rss)
        children = sum(int(c.memory_info().rss) for c in proc.children(recursive=True))
        return {"rss_self": own, "rss_children": children}
    except Exception:
        # Best-effort sampling — a dead child / permission error must not surface.
        return None


def record(event: dict[str, Any]) -> None:
    """Append one event as a JSON line to the perf log; no-op when disabled.

    Adds a wall-clock ``at`` timestamp for human-readable ordering. Any IO or
    serialization failure is swallowed: perf tracing is best-effort and must
    never turn a logging problem into a pipeline error.
    """
    path = perf_log_path()
    if path is None:
        return
    try:
        # Best-effort: create the parent dir so a nested path (e.g. the documented
        # artifacts/perf.jsonl on a fresh checkout) writes instead of silently no-opping.
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = {"at": time.time(), **event}
        line = json.dumps(payload, default=str)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        # Intentional broad catch (documented in the module docstring): a telemetry
        # sink must degrade to a no-op rather than break the observed pipeline.
        return
