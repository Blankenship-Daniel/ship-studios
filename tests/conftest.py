"""Shared pytest fixtures: a recording fake session + a fake-hub patch.

The whole package is exercisable with no real subprocess, MCP server, or
audio. Two layers:

* ``FakeSession`` — implements the slice of the MCP ``ClientSession`` surface
  the Hub uses (``initialize``, ``call_tool``, ``list_tools``), records every
  ``call_tool`` invocation, and returns canned results. Use it to assert what
  a pipeline *intended* to call.

* ``fake_hub`` — monkeypatches ``Hub._open_session`` so opening a real Hub
  hands back ``FakeSession`` instances instead of launching ``uv``. The
  Hub's own ``call_tool`` / context-manager logic still runs, so the fake
  exercises the real plumbing end-to-end.

A lighter ``RecordingHub`` is also provided for pipeline tests that only care
about the ordered call log and don't need the Hub's transport at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class RecordedCall:
    """One recorded ``call_tool`` invocation."""

    server: str
    tool: str
    args: dict[str, Any]


class _FakeToolResult:
    """Minimal stand-in for ``mcp.types.CallToolResult``."""

    def __init__(self, structured: Any = None, text: str = "", is_error: bool = False):
        self.structuredContent = structured
        self.isError = is_error
        self.content = [_FakeTextBlock(text)] if text else []


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeListToolsResult:
    def __init__(self, tools: list[Any]) -> None:
        self.tools = tools


@dataclass
class FakeSession:
    """Records calls and returns canned results, per the MCP session surface.

    ``canned`` maps a tool name to the value ``call_tool`` should return for
    that tool (looked up after recording). Unmapped tools return ``{}`` so a
    pipeline that threads a result onward still gets a dict.
    """

    server_key: str
    calls: list[RecordedCall]
    canned: dict[str, Any] = field(default_factory=dict)
    initialized: bool = False

    async def initialize(self) -> None:
        self.initialized = True

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        args = dict(arguments or {})
        self.calls.append(RecordedCall(self.server_key, name, args))
        payload = self.canned.get(name, {})
        return _FakeToolResult(structured=payload)

    async def list_tools(self) -> _FakeListToolsResult:
        names = sorted(self.canned)
        return _FakeListToolsResult([{"name": n} for n in names])


class RecordingHub:
    """A drop-in for the real Hub that records calls without any transport.

    Pipeline tests inject this directly: ``await master_track(hub, ...)``.
    It mirrors :meth:`Hub.call_tool`'s return contract (canned payload or
    ``{}``) so result-threading inside pipelines behaves the same.
    """

    def __init__(self, canned: dict[str, Any] | None = None) -> None:
        self.calls: list[RecordedCall] = []
        self._canned = canned or {}

    async def call_tool(
        self, server_key: str, name: str, args: dict[str, Any] | None = None
    ) -> Any:
        recorded = dict(args or {})
        self.calls.append(RecordedCall(server_key, name, recorded))
        return self._canned.get(name, {})

    # convenience views for assertions -------------------------------------

    @property
    def tool_sequence(self) -> list[str]:
        return [c.tool for c in self.calls]

    @property
    def server_tool_sequence(self) -> list[tuple[str, str]]:
        return [(c.server, c.tool) for c in self.calls]

    def args_for(self, tool: str) -> dict[str, Any]:
        for c in self.calls:
            if c.tool == tool:
                return c.args
        raise AssertionError(f"tool {tool!r} was never called; saw {self.tool_sequence}")


@pytest.fixture
def recording_hub() -> RecordingHub:
    """A transport-free hub that records the ordered call log."""
    return RecordingHub()


@pytest.fixture
def fake_hub(monkeypatch: pytest.MonkeyPatch):
    """Patch ``Hub._open_session`` to yield FakeSessions (no real subprocess).

    Returns a factory: ``hub = fake_hub(canned=...)`` builds a real
    :class:`ship_studios.mcp_client.Hub` whose ``_open_session`` is patched.
    The returned object also exposes ``.sessions`` (per-server FakeSession)
    and ``.calls`` (flat recorded log across both servers) for assertions.
    """
    from ship_studios import mcp_client

    def factory(canned: dict[str, Any] | None = None, server_keys=None):
        calls: list[RecordedCall] = []
        sessions: dict[str, FakeSession] = {}

        async def _open(self: Any, server_key: str) -> FakeSession:  # noqa: ANN401
            sess = FakeSession(server_key=server_key, calls=calls, canned=canned or {})
            await sess.initialize()
            sessions[server_key] = sess
            return sess

        monkeypatch.setattr(mcp_client.Hub, "_open_session", _open, raising=True)

        hub = mcp_client.Hub(server_keys)
        # Attach inspection handles for tests (set before/after entering).
        hub.recorded_calls = calls  # type: ignore[attr-defined]
        hub.fake_sessions = sessions  # type: ignore[attr-defined]
        return hub

    return factory
