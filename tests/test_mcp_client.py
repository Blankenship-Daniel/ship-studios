"""Hub plumbing: real session lifecycle + result parsing, no subprocess.

Uses the ``fake_hub`` fixture, which patches only ``Hub._open_session`` — the
Hub's own context-manager, ``call_tool`` parsing, and error handling all run
for real against :class:`tests.conftest.FakeSession`.
"""
from __future__ import annotations

import pytest

from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER
from ship_studios.mcp_client import ToolCallError


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


async def test_hub_list_tools(fake_hub) -> None:
    hub = fake_hub(canned={"find-loops": {}, "measure-loudness": {}})
    async with hub:
        tools = await hub.list_tools(LOOPS_SERVER)
    names = {t["name"] for t in tools}
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
