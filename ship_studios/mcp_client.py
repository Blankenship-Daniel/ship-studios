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

import asyncio
import contextlib
from types import TracebackType
from typing import TYPE_CHECKING, Any

from ship_studios import config, perf

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mcp import ClientSession


class Hub:
    """Holds an initialized MCP ``ClientSession`` per server key.

    Construct with the server keys to open (defaults to both). Use as an
    async context manager — sessions are created in ``__aenter__`` and torn
    down in ``__aexit__``.
    """

    def __init__(self, server_keys: list[str] | None = None) -> None:
        keys = list(server_keys if server_keys is not None else config.SERVER_KEYS)
        # Validate at construction so a typo'd key fails here with a clear message
        # rather than deep in __aenter__/_open_session as a bare KeyError.
        unknown = [k for k in keys if k not in config.SERVER_KEYS]
        if unknown:
            raise ValueError(
                f"unknown server key(s): {unknown}; "
                f"valid keys are {list(config.SERVER_KEYS)}"
            )
        # A repeated key spawned a second `uv run` subprocess while _sessions kept
        # only the last one — a redundant child held for the Hub's whole lifetime,
        # with no way to reach it.
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        if dupes:
            raise ValueError(f"duplicate server key(s): {dupes}")
        self.server_keys: list[str] = keys
        self._sessions: dict[str, ClientSession] = {}
        self._stack: contextlib.AsyncExitStack | None = None
        # Correlates every call/handshake made through this Hub in the perf trace
        # (see ship_studios.perf). Cheap to generate; only surfaced when
        # SHIP_STUDIOS_PERF_LOG is set.
        self.run_id: str = perf.new_run_id()

    async def __aenter__(self) -> Hub:
        if self._stack is not None:
            # Re-entering an open Hub would orphan the first AsyncExitStack (and the
            # subprocesses it holds). Open one `async with`/open_hub() per instance.
            raise RuntimeError("Hub is already open; use a fresh Hub per context")
        self._stack = contextlib.AsyncExitStack()
        try:
            # Open the servers SEQUENTIALLY, in this task. Do NOT reintroduce
            # asyncio.gather here: `stdio_client` and `ClientSession.__aenter__` each
            # enter an `anyio.create_task_group()`, and anyio binds a cancel scope's
            # `_host_task` to whichever task ENTERED it. gather runs every coroutine in
            # its own child Task, so the scopes would be entered there while __aexit__
            # unwinds self._stack from THIS task — and anyio raises "Attempted to exit
            # cancel scope in a different task than it was entered in" on every
            # teardown (including with a single key: gather still spawns a Task).
            # Entering here keeps enter and exit in the same task by construction, and
            # removes the rollback race below: no sibling open can still be in flight
            # pushing onto a stack the `except` has already closed. The cost is that
            # two cold `uv run` handshakes sum rather than overlap, on cold start only.
            for key in self.server_keys:
                self._sessions[key] = await self._open_session(key)
        except BaseException:
            # Roll back any partially-opened sessions so a failure on one
            # server doesn't leak another server's subprocess.
            await self._stack.aclose()
            self._stack = None
            self._sessions.clear()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._stack is not None:
            # Forward the active exception into the nested CM teardown (not aclose(),
            # which passes (None, None, None)) — so the SDK context managers see the
            # body's exception, and a teardown error chains onto it instead of
            # masking it.
            await self._stack.__aexit__(exc_type, exc, tb)
            self._stack = None
        self._sessions.clear()

    async def _open_session(self, server_key: str) -> ClientSession:
        """Spawn the server subprocess and return an initialized session.

        Isolated as its own method so tests can monkeypatch it to hand back
        a fake session without ever launching ``uv``.
        """
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        assert self._stack is not None  # set by __aenter__ before this runs
        # Validate the sibling dir at the launch boundary (server_parameters stays
        # side-effect-free), so a missing/un-synced or mis-pointed repo fails with
        # a clear message instead of an opaque `uv --directory` spawn error.
        config.checked_server_dir(server_key)
        params = config.server_parameters(server_key)
        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        timeout = config.startup_timeout_s()
        # Guard ONLY the wait_for branch (see call_tool): the no-timeout path must
        # let a bubbling TimeoutError through unrelabelled, and `f"{timeout:g}"`
        # would crash with timeout=None.
        start = perf.now()
        handshake_ok = False
        try:
            if timeout is None:
                await session.initialize()
            else:
                try:
                    await asyncio.wait_for(session.initialize(), timeout)
                except TimeoutError as exc:
                    # Keep the asyncio cause chained (`from exc`): the original
                    # traceback shows the handshake stalled inside wait_for/initialize,
                    # which is exactly what an operator debugging a hang wants to see.
                    raise TimeoutError(
                        f"server {server_key!r} did not complete the MCP handshake "
                        f"within {timeout:g}s — is the sibling repo synced and runnable? "
                        f"(uv --directory {config.server_dir(server_key)} run …). "
                        f"Set {config.STARTUP_TIMEOUT_ENV}=0 to wait indefinitely."
                    ) from exc
            handshake_ok = True
        finally:
            if perf.perf_enabled():
                # Cold-start is the most informative subprocess-RSS moment — the uv-run
                # child has just spawned — so sample it here too (not only mid-pipeline).
                event: dict[str, Any] = {
                    "run_id": self.run_id,
                    "server": server_key,
                    "tool": "<handshake>",
                    "elapsed_s": round(perf.now() - start, 6),
                    "ok": handshake_ok,
                }
                rss = perf.sample_rss()
                if rss is not None:
                    event.update(rss)
                perf.record(event)
        return session

    def session(self, server_key: str) -> ClientSession:
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

        Timeout semantics (important): the client-side call timeout
        (``SHIP_STUDIOS_CALL_TIMEOUT``) only abandons the local wait — it
        does NOT send a cancellation (``notifications/cancelled``) to the
        server. When the wait elapses this raises ``ToolCallError(kind=
        "timeout")``, but the sibling subprocess keeps grinding the in-flight
        tool (e.g. a 10-minute Demucs separation or a Gemini render) until it
        is reaped at Hub/stack teardown — the work is abandoned, not aborted.
        So set ``SHIP_STUDIOS_CALL_TIMEOUT`` GENEROUSLY for heavy tools, or to
        ``0`` to disable it; a too-short timeout wastes the server's compute
        without freeing it. Passing ``args=None`` is treated as ``{}``.
        """
        session = self.session(server_key)
        timeout = config.call_timeout_s()
        # Always stamp the call with a duration; only write the JSONL sink + sample
        # RSS when SHIP_STUDIOS_PERF_LOG is set (the finally guards on perf_enabled).
        start = perf.now()
        ok = False
        kind: str | None = None
        try:
            # Guard ONLY the wait_for branch: a TimeoutError bubbling out of the tool
            # itself on the no-timeout path must not be relabelled (and would crash
            # `f"{timeout:g}"` with timeout=None).
            if timeout is None:
                result = await session.call_tool(name, args or {})
            else:
                try:
                    result = await asyncio.wait_for(session.call_tool(name, args or {}), timeout)
                except TimeoutError:
                    raise ToolCallError(
                        server_key, name,
                        f"no response within {timeout:g}s "
                        f"(set {config.CALL_TIMEOUT_ENV}=0 to disable the call timeout)",
                        kind="timeout",
                    ) from None
            if getattr(result, "isError", False):
                raise ToolCallError(server_key, name, _result_text(result))
            parsed = _parse_result(result)
            ok = True
            return parsed
        except ToolCallError as exc:
            # Carry the cause class (timeout vs server-flagged tool_error) into the
            # trace so an operator can tell "raise the timeout" from "fix a bug".
            kind = exc.kind
            raise
        except Exception as exc:
            # A non-ToolCallError failure (transport/decode error, or a TimeoutError
            # bubbling from the tool on the no-timeout path): classify it for the
            # trace only — never label it "tool_error" — then propagate unchanged.
            kind = "timeout" if isinstance(exc, TimeoutError) else "exception"
            raise
        finally:
            if perf.perf_enabled():
                event: dict[str, Any] = {
                    "run_id": self.run_id,
                    "server": server_key,
                    "tool": name,
                    "elapsed_s": round(perf.now() - start, 6),
                    "ok": ok,
                }
                if not ok and kind is not None:
                    event["kind"] = kind
                # sample_rss() walks the process tree — only on the opt-in trace path,
                # so the default run pays nothing; accept the per-call cost when on.
                rss = perf.sample_rss()
                if rss is not None:
                    event.update(rss)
                perf.record(event)

    async def list_tools(self, server_key: str) -> list[Any]:
        """Return the tool descriptors advertised by ``server_key``."""
        session = self.session(server_key)
        result = await session.list_tools()
        return list(result.tools)


class ToolCallError(RuntimeError):
    """Raised when an MCP tool returns an error result.

    ``kind`` distinguishes a server-flagged error result (``"tool_error"``) from a
    client-side call timeout (``"timeout"``) so the failure cause is visible in the
    perf trace. It is keyword-only with a default, so the historical
    ``ToolCallError(server, tool, detail)`` call sites stay valid.
    """

    def __init__(
        self, server_key: str, tool: str, detail: str, *, kind: str = "tool_error"
    ) -> None:
        self.server_key = server_key
        self.tool = tool
        self.detail = detail
        self.kind = kind
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
