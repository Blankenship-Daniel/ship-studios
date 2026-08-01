"""Deterministic prose <-> code lockstep gate for the canonical pipelines (A1a).

The repo's defining contract is "CLAUDE.md + the code + the tests stay in
lockstep." ``tests/test_pipelines.py`` already pins code<->test (the ordered
``(server, tool)`` log against a ``RecordingHub``); the on-demand
``audit-pipeline-lockstep`` agent workflow is the only thing that watches the
PROSE half — and only on demand. This module closes that gap with a tiny,
offline, deterministic check.

For each pipeline whose ``### <name>`` prose block under the "Canonical
pipelines" section we can confidently parse, we extract the ORDERED list of
``[L]``/``[G]`` + tool-name tokens, then drive the matching pipeline function
with a :class:`RecordingHub` on its DEFAULT path and assert the emitted
``(server, tool)`` sequence is an ORDERED SUBSEQUENCE of the prose tokens.

Subsequence (not equality) is deliberate:

* The prose blocks mention optional / gated steps (``apply-eq`` residuals,
  ``master-assistant`` alternative, the corrective chain in ``mix-check``) and
  even purely descriptive ``[L]``/``[G]`` references ("``[L] compare-tonality``
  again"). Those are extra prose tokens the default code path skips.
* What this enforces is the strong half: every tool the default path actually
  calls appears in the prose, in the same relative order. A reorder or a rename
  breaks the subsequence and fails here.

  A DROPPED step does NOT fail this gate — removing a call only shortens
  ``code_seq``, which remains an ordered subsequence of the prose. Drops are
  covered by ``test_pipelines.py``, whose per-pipeline assertions compare the
  emitted sequence for EQUALITY. Don't reach for this gate to catch a deletion.

Unparseable blocks are skipped (not failed), but ``master-track``,
``mix-check`` and ``reference-match`` MUST be parsed and checked — they are the
load-bearing pipelines, so a regression there is a hard failure.

Fully offline: ``RecordingHub`` needs no servers, keys, audio, or network.
"""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

import pytest

from ship_studios import config, pipelines
from tests.conftest import RecordingHub

# --- prose extraction --------------------------------------------------------

#: ``[L]``/``[G]`` followed by an (optionally back-ticked) hyphenated tool name.
#: Greedy on the tool slug; tolerant of an optional space and surrounding
#: backticks (``[L] `measure-loudness```/``[G] mastering-feedback``).
_TOKEN_RE = re.compile(r"\[([LG])\]\s*`?([a-z0-9]+(?:-[a-z0-9]+)+)`?")

#: ``### <name> — ...`` headers inside the Canonical pipelines section.
_HEADER_RE = re.compile(r"^###\s+([a-z0-9-]+)\b")

_SERVER_FOR_TAG = {"L": config.LOOPS_SERVER, "G": config.GEMINI_SERVER}


def _canonical_section(text: str) -> str:
    """Slice CLAUDE.md down to the body of the "Canonical pipelines" section.

    Returns the text between the ``## Canonical pipelines`` header and the next
    top-level (``## ``) header, or ``""`` if the section is absent (the parser
    then yields no blocks and every pipeline is treated as unparseable — the
    mandatory-coverage assertion would catch that as a failure).
    """
    start = re.search(r"^##\s+Canonical pipelines\b", text, flags=re.MULTILINE)
    if start is None:
        return ""
    rest = text[start.end() :]
    nxt = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest if nxt is None else rest[: nxt.start()]


def _prose_blocks(text: str) -> dict[str, list[tuple[str, str]]]:
    """Map each ``### <name>`` pipeline block to its ordered prose tokens.

    A token is ``(server_key, tool_name)``; ``[L]``->loops, ``[G]``->gemini.
    Only blocks inside the Canonical pipelines section are considered.
    """
    section = _canonical_section(text)
    blocks: dict[str, list[tuple[str, str]]] = {}
    current: str | None = None
    buf: list[str] = []

    def _flush() -> None:
        if current is None:
            return
        body = "\n".join(buf)
        tokens = [
            (_SERVER_FOR_TAG[tag], tool) for tag, tool in _TOKEN_RE.findall(body)
        ]
        blocks[current] = tokens

    for line in section.splitlines():
        m = _HEADER_RE.match(line)
        if m is not None:
            _flush()
            current = m.group(1)
            buf = []
        elif current is not None:
            buf.append(line)
    _flush()
    return blocks


def _is_ordered_subsequence(
    needle: list[tuple[str, str]], haystack: list[tuple[str, str]]
) -> bool:
    """True if every element of ``needle`` appears in ``haystack`` in order."""
    it = iter(haystack)
    return all(item in it for item in needle)


# --- per-pipeline default-path drivers --------------------------------------
#
# Each driver runs the pipeline's DEFAULT path against a fresh RecordingHub and
# returns the recorded (server, tool) sequence. Canned results are supplied only
# where a default path threads a previous result onward (find-loops manifest,
# match-to-profile delta) so the pipeline runs to completion. Keep these
# argument-minimal: optional corrective branches must NOT be triggered, so the
# code sequence stays a clean subsequence of the prose.


async def _seq_master_track() -> list[tuple[str, str]]:
    hub = RecordingHub()
    await pipelines.master_track(hub, "m.wav", "o.wav", target_platform="spotify")
    return hub.server_tool_sequence


async def _seq_mix_check() -> list[tuple[str, str]]:
    hub = RecordingHub()
    await pipelines.mix_check(hub, "m.wav")
    return hub.server_tool_sequence


async def _seq_reference_match() -> list[tuple[str, str]]:
    hub = RecordingHub()
    await pipelines.reference_match(hub, "m.wav", "r.wav")
    return hub.server_tool_sequence


async def _seq_house_curve() -> list[tuple[str, str]]:
    hub = RecordingHub(
        canned={"match-to-profile": {"bands": [{"freq_hz": 1.0, "delta_db": 0.0}]}}
    )
    await pipelines.house_curve(hub, "m.wav", ["r.wav"])
    return hub.server_tool_sequence


async def _seq_loops_to_deliverables() -> list[tuple[str, str]]:
    hub = RecordingHub(
        canned={
            "find-loops": {
                "out_dir": "out",
                "manifest": {"bpm": 120.0, "loops": [{"wav": "a.wav"}]},
            }
        }
    )
    await pipelines.loops_to_deliverables(hub, "d.wav", 120.0, out_dir="out")
    return hub.server_tool_sequence


#: Prose ``### <name>`` header -> a coroutine that yields the default-path
#: (server, tool) sequence. Two classes of pipeline are intentionally ABSENT:
#:
#: * No-default-call recipes (``understand-audio`` fires nothing until an
#:   analysis flag is set; ``new-track`` / ``raw-intake`` are local-DSP-only) —
#:   nothing to lock against.
#: * Per-ITEM loop pipelines (``stem-master`` / ``unmask-stems`` /
#:   ``batch-master``) — their prose mentions each per-stem step ONCE to describe
#:   a loop, but the code emits one call PER stem, so a subsequence over
#:   single-mention prose can't match the duplicate code calls cleanly. These are
#:   left to the code<->test ordered-log assertions in ``test_pipelines.py``.
_DRIVERS: dict[str, Callable[[], Awaitable[list[tuple[str, str]]]]] = {
    "master-track": _seq_master_track,
    "mix-check": _seq_mix_check,
    "reference-match": _seq_reference_match,
    "house-curve": _seq_house_curve,
    "loops-to-deliverables": _seq_loops_to_deliverables,
}

#: Pipelines whose lockstep MUST be verifiable — a regression here is a hard
#: failure, never a silent skip.
_MANDATORY = ("master-track", "mix-check", "reference-match")


def _claude_md_text() -> str:
    path = config.repo_root() / "CLAUDE.md"
    return path.read_text(encoding="utf-8")


# --- the gate ----------------------------------------------------------------


async def _check_one(name: str, prose_tokens: list[tuple[str, str]]) -> None:
    """Assert the pipeline's default code sequence ⊆ its prose tokens (in order)."""
    code_seq = await _DRIVERS[name]()
    assert code_seq, f"{name}: default path emitted no tool calls to lock against"
    assert _is_ordered_subsequence(code_seq, prose_tokens), (
        f"{name}: code's ordered (server, tool) sequence is NOT an ordered "
        f"subsequence of the CLAUDE.md prose.\n"
        f"  code:  {code_seq}\n"
        f"  prose: {prose_tokens}\n"
        f"Update CLAUDE.md's '### {name}' block or the pipeline to re-align."
    )


async def test_mandatory_pipelines_are_parsed_and_checked() -> None:
    """master-track / mix-check / reference-match must parse AND pass."""
    blocks = _prose_blocks(_claude_md_text())
    for name in _MANDATORY:
        assert name in blocks and blocks[name], (
            f"required pipeline '### {name}' block not found/parseable in "
            f"CLAUDE.md's Canonical pipelines section"
        )
        await _check_one(name, blocks[name])


async def test_all_parseable_pipelines_lockstep() -> None:
    """Every prose block we have a driver for must lockstep with its code path.

    Blocks without a driver (no default MCP calls, or a local-DSP-only recipe
    like new-track) are skipped; a block we can't parse at all simply won't be
    in ``blocks`` and is likewise tolerated — the mandatory-coverage test above
    is the backstop that the parser still works on the load-bearing pipelines.
    """
    blocks = _prose_blocks(_claude_md_text())
    checked = 0
    for name, tokens in blocks.items():
        if name not in _DRIVERS or not tokens:
            continue
        await _check_one(name, tokens)
        checked += 1
    # At minimum the three mandatory ones are driver-backed and parseable.
    assert checked >= len(_MANDATORY), (
        f"expected to lockstep-check at least {len(_MANDATORY)} pipelines, "
        f"checked {checked}"
    )


def test_prose_parser_finds_the_canonical_section() -> None:
    """Guard the parser itself: the section exists and yields the big pipelines."""
    blocks = _prose_blocks(_claude_md_text())
    for name in _MANDATORY:
        assert name in blocks, f"parser failed to locate '### {name}'"


@pytest.mark.parametrize(
    ("needle", "haystack", "expected"),
    [
        ([("a", "x")], [("a", "x")], True),
        ([("a", "x"), ("a", "z")], [("a", "x"), ("a", "y"), ("a", "z")], True),
        ([("a", "z"), ("a", "x")], [("a", "x"), ("a", "z")], False),  # order
        ([("a", "x"), ("a", "q")], [("a", "x"), ("a", "z")], False),  # missing
        ([], [("a", "x")], True),  # empty needle is trivially a subsequence
    ],
)
def test_ordered_subsequence_helper(
    needle: list[tuple[str, str]],
    haystack: list[tuple[str, str]],
    expected: bool,
) -> None:
    assert _is_ordered_subsequence(needle, haystack) is expected
