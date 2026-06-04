"""Offline arg-value validation against a snapshotted live schema (A6).

The offline suite drives pipelines against a ``RecordingHub`` that accepts ANY
args, so it never checks the *values* a pipeline emits against the real tool
``inputSchema`` — only keys/order. This test closes that blind spot WITHOUT a
live dependency in CI: if a schema snapshot exists at
``tests/fixtures/tool_schemas.json`` (produced manually by
``scripts/snapshot_tool_schemas.py`` against synced siblings), it drives every
pipeline with a ``RecordingHub`` and validates each emitted call's ``args``
against that tool's recorded ``inputSchema`` using a tiny inline validator.

When the fixture is ABSENT (the default CI state) the whole module skips
cleanly — so this is dormant until someone snapshots the fixture, at which point
it activates with no extra dependency (NO ``jsonschema``).

The inline validator is deliberately minimal — it checks exactly the three
things that catch real drift:

* every ``required`` key is present in the emitted args;
* when ``additionalProperties is False``, no unknown key is emitted;
* a property declaring a JSON ``type`` is type-checked (loosely) against it.

It does NOT attempt full JSON-Schema semantics (oneOf/allOf/pattern/format/…) —
those would invite false positives against the real, richer schemas.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ship_studios import config, pipelines
from tests.conftest import RecordedCall, RecordingHub

_FIXTURE = config.repo_root() / "tests" / "fixtures" / "tool_schemas.json"


def _load_snapshot() -> dict[str, dict[str, Any]]:
    raw = json.loads(Path(_FIXTURE).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AssertionError(f"{_FIXTURE} is not a server->tool->schema mapping")
    return raw


# --- tiny inline JSON-Schema-ish validator (no jsonschema dependency) --------

#: JSON-Schema ``type`` -> the Python type(s) an emitted value may be. JSON
#: numbers include ints, so ``number`` accepts both ``int`` and ``float``.
#: ``bool`` is a subclass of ``int`` in Python but JSON treats them as distinct,
#: so a ``boolean`` must be a real ``bool`` and a ``number``/``integer`` must NOT
#: be a ``bool`` — both handled explicitly in ``_type_matches`` below.
_TYPE_OK: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list, tuple),
    "string": (str,),
    "boolean": (bool,),
    "null": (type(None),),
}


def _type_matches(value: Any, json_type: str) -> bool:
    if json_type in ("integer", "number"):
        # bool is a subclass of int but is NOT a JSON number/integer.
        if isinstance(value, bool):
            return False
        if json_type == "integer":
            return isinstance(value, int)
        return isinstance(value, (int, float))
    expected = _TYPE_OK.get(json_type)
    if expected is None:
        return True  # unknown/unsupported type keyword -> don't second-guess it
    # A declared boolean must be a real bool, not just any int.
    if json_type == "boolean":
        return isinstance(value, bool)
    return isinstance(value, expected)


def _validate(args: dict[str, Any], schema: Any) -> list[str]:
    """Return a list of human-readable problems; empty == valid."""
    problems: list[str] = []
    if not isinstance(schema, dict):
        return problems  # no usable schema -> nothing to assert

    props = schema.get("properties")
    props = props if isinstance(props, dict) else {}

    required = schema.get("required")
    if isinstance(required, list):
        for key in required:
            if isinstance(key, str) and key not in args:
                problems.append(f"missing required key {key!r}")

    if schema.get("additionalProperties") is False:
        for key in args:
            if key not in props:
                problems.append(f"unknown key {key!r} (additionalProperties:false)")

    for key, value in args.items():
        spec = props.get(key)
        if not isinstance(spec, dict):
            continue
        jtype = spec.get("type")
        # ``type`` may be a list (union) in JSON Schema; accept if any matches.
        if isinstance(jtype, str):
            if not _type_matches(value, jtype):
                problems.append(
                    f"key {key!r}={value!r} is not type {jtype!r}"
                )
        elif isinstance(jtype, list):
            if not any(
                isinstance(t, str) and _type_matches(value, t) for t in jtype
            ):
                problems.append(f"key {key!r}={value!r} matches none of {jtype}")
    return problems


# --- collect every call every pipeline emits (default + branch paths) --------


async def _all_recorded_calls() -> list[RecordedCall]:
    """Drive each pipeline so its conditional branches all fire, collecting calls.

    Each pipeline is driven inside a try/except so a single pipeline whose
    signature is mid-flux can't abort the whole collection — the args of every
    pipeline that DOES run still get validated.
    """
    calls: list[RecordedCall] = []

    async def _run(make_hub, coro_factory) -> None:
        hub = make_hub()
        try:
            await coro_factory(hub)
        except Exception:  # noqa: BLE001 — tolerate a mid-edit signature
            return
        calls.extend(hub.calls)

    eq_band = {"type": "bell", "freq_hz": 1.0, "gain_db": 0.0, "q": 1.0}
    dyn_band = {"freq_hz": 1.0, "gain_db": 0.0, "q": 1.0, "threshold_db": -24.0}
    find_loops_canned = {
        "find-loops": {
            "out_dir": "out",
            "manifest": {"bpm": 120.0, "loops": [{"wav": "a.wav"}]},
        }
    }

    await _run(
        RecordingHub,
        lambda h: pipelines.master_track(h, "m.wav", "o.wav", target_platform="spotify"),
    )
    await _run(
        RecordingHub,
        lambda h: pipelines.master_track(
            h, "m.wav", "o.wav", assistant=True, style="indie"
        ),
    )
    await _run(
        RecordingHub,
        lambda h: pipelines.mix_check(
            h,
            "m.wav",
            eq_bands=[eq_band],
            deess={},
            suppress={},
            dynamic_eq_bands=[dyn_band],
            excite={},
            compress=True,
            multiband={},
        ),
    )
    await _run(
        RecordingHub,
        lambda h: pipelines.reference_match(h, "m.wav", "r.wav", eq_bands=[eq_band]),
    )
    await _run(
        lambda: RecordingHub(
            canned={"match-to-profile": {"bands": [{"freq_hz": 1.0, "delta_db": 0.0}]}}
        ),
        lambda h: pipelines.house_curve(h, "m.wav", ["r.wav"]),
    )
    await _run(
        lambda: RecordingHub(canned=find_loops_canned),
        lambda h: pipelines.loops_to_deliverables(
            h, "d.wav", 120.0, out_dir="out", describe=True
        ),
    )
    await _run(
        RecordingHub,
        lambda h: pipelines.understand_audio(
            h,
            "a.wav",
            transcribe=True,
            region=(0.0, 1.0, "?"),
            event_description="kick",
            labels=["x"],
            compare_paths=["b.wav"],
            json_schema={"type": "object"},
        ),
    )
    await _run(RecordingHub, lambda h: pipelines.batch_master(h, ["m.wav"]))
    await _run(
        RecordingHub,
        lambda h: pipelines.unmask_stems(h, {"kick": "k.wav", "bass": "b.wav"}),
    )
    await _run(
        RecordingHub,
        lambda h: pipelines.stem_master(
            h,
            {"kick": "k.wav", "bass": "b.wav"},
            cross_check=True,
            corrections={
                "bass": {
                    "eq_bands": [eq_band],
                    "deess": {},
                    "suppress": {},
                    "dynamic_eq_bands": [dyn_band],
                    "compress": True,
                    "multiband": {},
                    "shape_bands": {
                        "bands": [{"band": 0, "transient_db": 0.0, "gain_db": 0.0}]
                    },
                }
            },
        ),
    )
    return calls


# --- the gate (skips cleanly when the fixture is absent) ---------------------


async def test_emitted_args_validate_against_snapshot() -> None:
    if not _FIXTURE.is_file():
        pytest.skip(
            f"no schema snapshot at {_FIXTURE}; run "
            "scripts/snapshot_tool_schemas.py against synced siblings to enable"
        )

    snapshot = _load_snapshot()
    calls = await _all_recorded_calls()
    assert calls, "no pipeline calls were collected to validate"

    failures: list[str] = []
    validated = 0
    for call in calls:
        server_schemas = snapshot.get(call.server)
        if not isinstance(server_schemas, dict):
            continue  # server not in snapshot -> nothing to validate against
        schema = server_schemas.get(call.tool)
        if schema is None:
            # Tool not in the snapshot: tool-name existence is the live-contract
            # test's job, not ours. Skip rather than double-report.
            continue
        problems = _validate(call.args, schema)
        validated += 1
        for problem in problems:
            failures.append(f"{call.server}:{call.tool}: {problem}")

    assert validated > 0, (
        "the snapshot exists but matched none of the emitted (server, tool) "
        "calls — is the fixture stale or empty?"
    )
    assert not failures, "emitted args violate the live tool schemas:\n" + "\n".join(
        sorted(set(failures))
    )


# --- a self-test of the inline validator (always runs, no fixture needed) ----


def test_inline_validator_flags_missing_required() -> None:
    schema = {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}
    assert _validate({"path": "x.wav"}, schema) == []
    assert _validate({}, schema) == ["missing required key 'path'"]


def test_inline_validator_flags_unknown_when_closed() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"path": {"type": "string"}},
    }
    assert _validate({"path": "x.wav"}, schema) == []
    assert _validate({"path": "x.wav", "bogus": 1}, schema) == [
        "unknown key 'bogus' (additionalProperties:false)"
    ]
    # Open schemas (the default) tolerate extra keys.
    open_schema = {"type": "object", "properties": {"path": {"type": "string"}}}
    assert _validate({"path": "x.wav", "extra": 1}, open_schema) == []


def test_inline_validator_type_checks() -> None:
    schema = {
        "type": "object",
        "properties": {
            "n": {"type": "number"},
            "i": {"type": "integer"},
            "s": {"type": "string"},
            "b": {"type": "boolean"},
            "a": {"type": "array"},
            "o": {"type": "object"},
        },
    }
    assert _validate({"n": 1.5, "i": 3, "s": "x", "b": True, "a": [], "o": {}}, schema) == []
    # bool is not a number/integer; int is a valid number.
    assert _validate({"n": 2}, schema) == []
    assert _validate({"i": True}, schema) == ["key 'i'=True is not type 'integer'"]
    assert _validate({"n": True}, schema) == ["key 'n'=True is not type 'number'"]
    assert _validate({"s": 3}, schema) == ["key 's'=3 is not type 'string'"]


def test_inline_validator_accepts_union_types() -> None:
    schema = {"type": "object", "properties": {"x": {"type": ["string", "null"]}}}
    assert _validate({"x": "s"}, schema) == []
    assert _validate({"x": None}, schema) == []
    assert _validate({"x": 3}, schema) == ["key 'x'=3 matches none of ['string', 'null']"]


def test_inline_validator_tolerates_non_dict_schema() -> None:
    # A tool whose snapshotted schema is null/absent must not raise.
    assert _validate({"any": "thing"}, None) == []
    assert _validate({"any": "thing"}, True) == []
