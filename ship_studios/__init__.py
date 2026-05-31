"""ship-studios — headless hub over the stemmy-loops + stemmy-gemini MCP servers.

This package is a *client*: it launches the two sibling MCP servers as stdio
subprocesses and sequences their verified tools into the fixed create -> mix
-> master -> deliver pipelines (master-track, mix-check, reference-match,
loops-to-deliverables, understand-audio).

Imports stay cheap on purpose. The MCP SDK and the async pipeline code are
pulled lazily so `ship-studios doctor` (env + sibling-dir checks) runs even
when the servers aren't installed or reachable yet.
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
