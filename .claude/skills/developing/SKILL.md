---
name: developing
description: Use when working ON the ship-studios repo — running tests / lint / types, editing a pipeline, the skill/doc contract guards, the headless ship-studios CLI, or the pre-release live-contract check — "run the tests", "how do I lint / typecheck", "uv run pytest", "edit a pipeline", "the ship-studios CLI", "audit-skill-consistency", "live-contract", "develop / contribute to this repo". The index to the developer reference (docs/developing.md); points at the docs, runs no audio tools. Reference, not a pipeline.
argument-hint: [topic, e.g. "tests" | "pipeline" | "cli"]
---

# developing — tests · lint · types + the headless CLI (index)

Goal: answer "how do I develop, test, and ship changes to *this* repo" by routing to
[`docs/developing.md`](../../../docs/developing.md). This is a **documentation index** for repo
maintenance, not an audio pipeline — it runs no `stemmy-*` tools. CLAUDE.md keeps a brief
"Developing this repo" stub; the full detail lives in the doc.

## Where to look

| The user is asking about… | Where |
|---|---|
| **Run tests / lint / types** (`uv run pytest` / `ruff` / `mypy` / `lint_skills.py`) | [docs/developing.md](../../../docs/developing.md) |
| **Edit a pipeline** (keep `pipelines.py` ↔ tests ↔ CLAUDE.md in lockstep) | [docs/developing.md](../../../docs/developing.md) |
| The **headless `ship-studios` CLI** (nine pipeline subcommands + `doctor`) | [docs/developing.md](../../../docs/developing.md) |
| **Contract guards** (`/audit-skill-consistency`, `/audit-pipeline-lockstep`, `/create-skill`, `/repo-review`, `/fold-learnings`) | [docs/developing.md](../../../docs/developing.md) |
| The opt-in **live-contract** pre-release check | [docs/developing.md](../../../docs/developing.md) |

## At a glance

- The repo's own Python is two `uv` packages — `ship_studios/` (the DSP-free MCP-client hub) and
  `drum_prep/` (the only DSP). The whole suite runs **offline** (`tests/conftest.py` monkeypatches
  `Hub._open_session` with a `FakeSession` — no siblings, keys, audio, or network).
- One command: `uv sync --extra drum-prep` then `uv run pytest`. The DSP subset SKIPS without that
  extra; hub tests run on base deps alone.
- **Editing a pipeline = editing `ship_studios/pipelines.py`** — `tests/test_pipelines.py` asserts the
  *ordered* tool-call log, so a reorder/rename fails loudly. Keep it in lockstep with CLAUDE.md's
  "Canonical pipelines" section.
- Setup / install / env vars are the sibling concern → `[[setup]]`.

## How to use this skill

Identify the dev task and quote the matching command or rule from
[`docs/developing.md`](../../../docs/developing.md). For shipping a change end-to-end (commit →
push → PR → CI-green → merge) use the `deploy` skill, not this reference.

## Pitfalls

- **Don't run audio tools here.** This is repo maintenance; for actual mix/master work use the
  pipeline skills (`[[master-track]]`, `[[mix-check]]`, …).
- **Remote CI is authoritative**, but a fast local pre-flight (`ruff check && mypy && lint_skills.py
  && pytest -q`) catches most failures before a push.

## Related

- `[[setup]]` — install / sync / env vars (the setup counterpart)
- `[[vst]]` — the VST harness/probe scripts under `presets/vst/`
- `[[master-track]]` · `[[mix-check]]` — the actual audio pipelines this hub drives
