"""Hub plumbing: real session lifecycle + result parsing, no subprocess.

Uses the ``fake_hub`` fixture, which patches only ``Hub._open_session`` — the
Hub's own context-manager, ``call_tool`` parsing, and error handling all run
for real against :class:`tests.conftest.FakeSession`.
"""
from __future__ import annotations

import pytest

from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER
from ship_studios.mcp_client import Hub, ToolCallError


def test_hub_rejects_unknown_server_key() -> None:
    # A typo'd key must fail at construction with a clear message, not later in
    # __aenter__/_open_session as a bare KeyError far from the cause.
    with pytest.raises(ValueError, match="unknown server key"):
        Hub([LOOPS_SERVER, "not-a-server"])


def test_hub_accepts_known_server_keys() -> None:
    hub = Hub([LOOPS_SERVER, GEMINI_SERVER])
    assert hub.server_keys == [LOOPS_SERVER, GEMINI_SERVER]


async def test_hub_opens_both_sessions_and_initializes(fake_hub) -> None:
    hub = fake_hub()
    async with hub:
        assert set(hub.fake_sessions) == {LOOPS_SERVER, GEMINI_SERVER}
        for sess in hub.fake_sessions.values():
            assert sess.initialized is True


async def test_hub_call_tool_records_and_returns_structured(fake_hub) -> None:
    hub = fake_hub(canned={"measure-loudness": {"lufs_i": -14.2}})
    async with hub:
        result = await hub.call_tool(
            LOOPS_SERVER, "measure-loudness", {"path": "x.wav"}
        )
    assert result == {"lufs_i": -14.2}
    assert hub.recorded_calls[0].server == LOOPS_SERVER
    assert hub.recorded_calls[0].tool == "measure-loudness"
    assert hub.recorded_calls[0].args == {"path": "x.wav"}


async def test_hub_call_tool_unknown_tool_returns_empty_dict(fake_hub) -> None:
    hub = fake_hub()
    async with hub:
        result = await hub.call_tool(GEMINI_SERVER, "transcribe-audio", {"path": "a"})
    assert result == {}


async def test_hub_only_opens_requested_servers(fake_hub) -> None:
    hub = fake_hub(server_keys=[GEMINI_SERVER])
    async with hub:
        assert set(hub.fake_sessions) == {GEMINI_SERVER}
        with pytest.raises(KeyError):
            hub.session(LOOPS_SERVER)


async def test_hub_rejects_reentry(fake_hub) -> None:
    # Re-entering an already-open Hub would overwrite the live AsyncExitStack and
    # orphan the first set of sessions/subprocesses. The second __aenter__ must
    # fail loud rather than leak.
    hub = fake_hub()
    async with hub:
        with pytest.raises(RuntimeError, match="already open"):
            await hub.__aenter__()


async def test_hub_list_tools(fake_hub) -> None:
    hub = fake_hub(canned={"find-loops": {}, "measure-loudness": {}})
    async with hub:
        tools = await hub.list_tools(LOOPS_SERVER)
    # real MCP Tool descriptors expose .name as an attribute
    names = {t.name for t in tools}
    assert names == {"find-loops", "measure-loudness"}


async def test_hub_session_raises_after_close(fake_hub) -> None:
    hub = fake_hub()
    async with hub:
        pass
    with pytest.raises(KeyError):
        hub.session(LOOPS_SERVER)


async def test_call_tool_raises_on_error_result(fake_hub, monkeypatch) -> None:
    hub = fake_hub()
    async with hub:
        sess = hub.session(LOOPS_SERVER)

        from tests.conftest import _FakeToolResult

        async def boom(name, arguments=None):
            return _FakeToolResult(text="bad path", is_error=True)

        monkeypatch.setattr(sess, "call_tool", boom, raising=True)
        with pytest.raises(ToolCallError) as exc:
            await hub.call_tool(LOOPS_SERVER, "measure-loudness", {"path": "no"})
    assert exc.value.tool == "measure-loudness"
    assert "bad path" in exc.value.detail


async def test_hub_rolls_back_first_session_when_second_fails(monkeypatch) -> None:
    """If the 2nd server fails to open, the 1st server's context must be torn
    down (no leaked subprocess) and the error re-raised."""
    from ship_studios import mcp_client

    closed: list[bool] = []

    class _Sentinel:  # stand-in for the first server's stdio/session context
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            closed.append(True)

    opened: list[str] = []

    async def _open(self, server_key):
        opened.append(server_key)
        if len(opened) == 1:
            await self._stack.enter_async_context(_Sentinel())
            return object()  # a "session" for the first server
        raise RuntimeError("second server failed to start")

    monkeypatch.setattr(mcp_client.Hub, "_open_session", _open, raising=True)

    hub = mcp_client.Hub()
    with pytest.raises(RuntimeError, match="second server"):
        async with hub:
            pass

    assert closed == [True]        # first server's context was rolled back
    assert hub._sessions == {}     # no leaked session left behind
    assert hub._stack is None      # exit stack released


async def test_result_text_fallback_when_no_structured(fake_hub, monkeypatch) -> None:
    hub = fake_hub()
    async with hub:
        sess = hub.session(GEMINI_SERVER)

        from tests.conftest import _FakeToolResult

        async def text_only(name, arguments=None):
            return _FakeToolResult(structured=None, text="plain answer")

        monkeypatch.setattr(sess, "call_tool", text_only, raising=True)
        result = await hub.call_tool(GEMINI_SERVER, "transcribe-audio", {"path": "a"})
    assert result == "plain answer"


async def test_call_tool_times_out_into_tool_call_error(fake_hub, monkeypatch) -> None:
    """A hung tool call must surface as a clean ToolCallError, not block forever."""
    import asyncio

    from ship_studios import config

    monkeypatch.setattr(config, "call_timeout_s", lambda: 0.01)
    hub = fake_hub()
    async with hub:
        sess = hub.session(LOOPS_SERVER)

        async def slow(name, arguments=None):
            await asyncio.sleep(1.0)

        monkeypatch.setattr(sess, "call_tool", slow, raising=True)
        with pytest.raises(ToolCallError) as exc:
            await hub.call_tool(LOOPS_SERVER, "measure-loudness", {"path": "x"})
    assert "within" in exc.value.detail


async def test_call_tool_no_timeout_when_disabled(fake_hub, monkeypatch) -> None:
    from ship_studios import config

    monkeypatch.setattr(config, "call_timeout_s", lambda: None)
    hub = fake_hub(canned={"measure-loudness": {"lufs_i": -14.0}})
    async with hub:
        result = await hub.call_tool(LOOPS_SERVER, "measure-loudness", {"path": "x"})
    assert result == {"lufs_i": -14.0}
