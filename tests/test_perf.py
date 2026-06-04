"""Stage-1 hub instrumentation: the opt-in perf trace, timing, and error kinds.

All offline — uses the FakeSession/RecordingHub fixtures, no real subprocess,
server, key, or network. Exercises:

* ``ship_studios.perf`` — env gating, JSONL sink, run-id, RSS shape, no-throw.
* ``Hub.call_tool`` — additive timing, JSONL emission, and the timeout vs
  tool_error ``ToolCallError.kind`` split.
* ``_Recorder.run`` — the additive ``elapsed_s``/``ok`` step keys, recorded on
  success AND failure (the step dict stays a superset of the asserted shape).
"""
from __future__ import annotations

import json

import pytest

from ship_studios import perf
from ship_studios.config import LOOPS_SERVER
from ship_studios.mcp_client import ToolCallError

# --- perf module ----------------------------------------------------------


def test_new_run_id_is_unique_and_short() -> None:
    assert perf.new_run_id() != perf.new_run_id()
    assert len(perf.new_run_id()) == 12


def test_perf_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(perf.PERF_LOG_ENV, raising=False)
    assert perf.perf_enabled() is False
    assert perf.perf_log_path() is None
    # Empty string counts as unset (mirrors config._timeout / _passthrough_env).
    monkeypatch.setenv(perf.PERF_LOG_ENV, "")
    assert perf.perf_enabled() is False


def test_perf_record_noop_when_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv(perf.PERF_LOG_ENV, raising=False)
    perf.record({"tool": "x"})  # must neither write nor raise
    assert list(tmp_path.iterdir()) == []


def test_perf_record_writes_jsonl_when_enabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    log = tmp_path / "perf.jsonl"
    monkeypatch.setenv(perf.PERF_LOG_ENV, str(log))
    perf.record({"tool": "measure-loudness", "ok": True})
    rec = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert rec["tool"] == "measure-loudness"
    assert rec["ok"] is True
    assert "at" in rec  # wall-clock stamp added by record()


def test_perf_record_swallows_bad_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(perf.PERF_LOG_ENV, "/no/such/dir/deeply/nested/perf.jsonl")
    perf.record({"tool": "x"})  # best-effort sink must not raise


def test_sample_rss_shape() -> None:
    out = perf.sample_rss()
    assert out is None or set(out) == {"rss_self", "rss_children"}


# --- ToolCallError.kind ---------------------------------------------------


def test_tool_call_error_three_arg_form_defaults_kind() -> None:
    err = ToolCallError("stemmy-loops", "measure-loudness", "boom")
    assert err.kind == "tool_error"
    assert err.server_key == "stemmy-loops"
    assert err.tool == "measure-loudness"
    assert err.detail == "boom"


async def test_call_tool_timeout_sets_kind_timeout(fake_hub, monkeypatch) -> None:
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
    assert exc.value.kind == "timeout"
    assert "within" in exc.value.detail  # message contract preserved


async def test_call_tool_server_error_sets_kind_tool_error(fake_hub, monkeypatch) -> None:
    from tests.conftest import _FakeToolResult

    hub = fake_hub()
    async with hub:
        sess = hub.session(LOOPS_SERVER)

        async def boom(name, arguments=None):
            return _FakeToolResult(text="bad path", is_error=True)

        monkeypatch.setattr(sess, "call_tool", boom, raising=True)
        with pytest.raises(ToolCallError) as exc:
            await hub.call_tool(LOOPS_SERVER, "measure-loudness", {"path": "x"})
    assert exc.value.kind == "tool_error"
    assert "bad path" in exc.value.detail


# --- JSONL emission through the real Hub.call_tool path --------------------


async def test_hub_writes_perf_trace_when_enabled(
    fake_hub, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    log = tmp_path / "perf.jsonl"
    monkeypatch.setenv(perf.PERF_LOG_ENV, str(log))
    hub = fake_hub(canned={"measure-loudness": {"lufs": -14.0}})
    async with hub:
        await hub.call_tool(LOOPS_SERVER, "measure-loudness", {"path": "x"})
    rec = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert rec["server"] == LOOPS_SERVER
    assert rec["tool"] == "measure-loudness"
    assert rec["ok"] is True
    assert rec["elapsed_s"] >= 0
    assert rec["run_id"] == hub.run_id


async def test_hub_no_trace_when_disabled(
    fake_hub, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv(perf.PERF_LOG_ENV, raising=False)
    log = tmp_path / "perf.jsonl"
    hub = fake_hub(canned={"measure-loudness": {}})
    async with hub:
        await hub.call_tool(LOOPS_SERVER, "measure-loudness", {"path": "x"})
    assert not log.exists()


async def test_hub_trace_classifies_non_toolcallerror(
    fake_hub, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # A non-ToolCallError failure must be recorded as kind="exception" (or "timeout"
    # for a bubbled TimeoutError) — never mislabeled "tool_error" — and still propagate.
    log = tmp_path / "perf.jsonl"
    monkeypatch.setenv(perf.PERF_LOG_ENV, str(log))
    hub = fake_hub()
    async with hub:
        sess = hub.session(LOOPS_SERVER)

        async def explode(name, arguments=None):
            raise ValueError("kaboom")

        monkeypatch.setattr(sess, "call_tool", explode, raising=True)
        with pytest.raises(ValueError):
            await hub.call_tool(LOOPS_SERVER, "measure-loudness", {"path": "x"})
    rec = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert rec["ok"] is False
    assert rec["kind"] == "exception"


# --- _Recorder timing + exception capture ---------------------------------


async def test_recorder_records_timing_and_ok(recording_hub) -> None:
    from ship_studios.pipelines import _Recorder

    rec = _Recorder(recording_hub)
    await rec.run(LOOPS_SERVER, "measure-loudness", {"path": "x"})
    step = rec.steps[-1]
    assert {"server", "tool", "args", "result"} <= set(step)  # superset contract
    assert step["ok"] is True
    assert step["elapsed_s"] >= 0


async def test_recorder_records_failed_step_then_reraises() -> None:
    from ship_studios.pipelines import _Recorder

    class _Boom:
        async def call_tool(self, server_key, name, args=None):
            raise ToolCallError(server_key, name, "boom")

    rec = _Recorder(_Boom())
    with pytest.raises(ToolCallError):
        await rec.run(LOOPS_SERVER, "measure-loudness", {"path": "x"})
    step = rec.steps[-1]
    assert step["ok"] is False
    assert step["result"] is None
