"""Async stdio-client wrapper over the official MCP SDK.

``Hub`` is a thin async context manager that owns one ``ClientSession`` per
server, opened over a ``stdio_client`` subprocess transport and driven
through the ``initialize()`` handshake. Pipelines talk to it through a single
verb:

    async with open_hub() as hub:
        result = await hub.call_tool("stemmy-loops", "measure-loudness", {"path": wav})

The two SDK objects this leans on:

* ``mcp.client.stdio.stdio_client(params)`` — an async-context that spawns the
  server subprocess and yields ``(read, write)`` streams.
* ``mcp.ClientSession(read, write)`` — the JSON-RPC session; ``initialize()``
  negotiates protocol version before any tool call.

Both are managed through a single ``contextlib.AsyncExitStack`` so closing the
Hub tears every session and subprocess down in reverse order, even on error.

The SDK import is deferred to ``__aenter__`` so ``import
ship_studios.mcp_client`` stays cheap — ``ship-studios doctor`` can import the
package and report setup problems without the SDK installed. Tests
monkeypatch ``Hub._open_session`` to inject a fake session, so the whole
package is exercisable with no real subprocess, server, or audio.
"""
from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from ship_studios import config

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mcp import ClientSession


class Hub:
    """Holds an initialized MCP ``ClientSession`` per server key.

    Construct with the server keys to open (defaults to both). Use as an
    async context manager — sessions are created in ``__aenter__`` and torn
    down in ``__aexit__``.
    """

    def __init__(self, server_keys: list[str] | None = None) -> None:
        self.server_keys: list[str] = list(
            server_keys
            if server_keys is not None
            else (config.LOOPS_SERVER, config.GEMINI_SERVER)
        )
        self._sessions: dict[str, "ClientSession"] = {}
        self._stack: contextlib.AsyncExitStack | None = None

    async def __aenter__(self) -> "Hub":
        self._stack = contextlib.AsyncExitStack()
        try:
            for key in self.server_keys:
                self._sessions[key] = await self._open_session(key)
        except BaseException:
            # Roll back any partially-opened sessions so a failure on the
            # second server doesn't leak the first server's subprocess.
            await self._stack.aclose()
            self._stack = None
            self._sessions.clear()
            raise
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
        self._sessions.clear()

    async def _open_session(self, server_key: str) -> "ClientSession":
        """Spawn the server subprocess and return an initialized session.

        Isolated as its own method so tests can monkeypatch it to hand back
        a fake session without ever launching ``uv``.
        """
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        assert self._stack is not None  # set by __aenter__ before this runs
        params = config.server_parameters(server_key)
        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        return session

    def session(self, server_key: str) -> "ClientSession":
        """Return the live session for ``server_key`` (must be open)."""
        try:
            return self._sessions[server_key]
        except KeyError:
            raise KeyError(
                f"no open session for {server_key!r}; "
                f"opened servers: {sorted(self._sessions)}"
            ) from None

    async def call_tool(
        self, server_key: str, name: str, args: dict[str, Any] | None = None
    ) -> Any:
        """Call ``name`` on ``server_key`` with ``args`` and return parsed output.

        Returns ``structuredContent`` when the tool provides it (the common
        case for these JSON-returning tools), else the joined text of the
        result's text content blocks. Raises ``ToolCallError`` when the
        server flags the result as an error so a broken step fails the
        pipeline loudly rather than feeding garbage to the next tool.
        """
        session = self.session(server_key)
        result = await session.call_tool(name, args or {})
        if getattr(result, "isError", False):
            raise ToolCallError(server_key, name, _result_text(result))
        return _parse_result(result)

    async def list_tools(self, server_key: str) -> list[Any]:
        """Return the tool descriptors advertised by ``server_key``."""
        session = self.session(server_key)
        result = await session.list_tools()
        return list(result.tools)


class ToolCallError(RuntimeError):
    """Raised when an MCP tool returns an error result."""

    def __init__(self, server_key: str, tool: str, detail: str) -> None:
        self.server_key = server_key
        self.tool = tool
        self.detail = detail
        super().__init__(f"{server_key}:{tool} failed: {detail}")


def _result_text(result: Any) -> str:
    """Join the ``.text`` of every text content block on a result."""
    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


def _parse_result(result: Any) -> Any:
    """Pull the useful payload out of a CallToolResult.

    Prefers ``structuredContent`` (the tool's typed JSON return), falling
    back to the concatenated text blocks. Returning the raw text rather than
    forcing a JSON parse keeps the Hub agnostic about each tool's exact
    shape — pipelines just thread the value through.
    """
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    return _result_text(result)


@contextlib.asynccontextmanager
async def open_hub(server_keys: list[str] | None = None):
    """Open a :class:`Hub` over the given servers (both by default).

    Sugar over ``async with Hub(...) as hub`` so pipelines read cleanly:

        async with open_hub() as hub:
            ...
    """
    async with Hub(server_keys) as hub:
        yield hub
