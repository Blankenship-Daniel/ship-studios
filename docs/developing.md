# Developing this repo (tests · lint · types) + the headless CLI

Developer reference for working *on* ship-studios. The runtime contract (tool surface, canonical pipelines, rules) lives in [`CLAUDE.md`](../CLAUDE.md); setup/env is in [`setup.md`](setup.md).

## Tests · lint · types

This repo's *own* Python is two `uv`-managed packages — **`ship_studios/`** (the DSP-free MCP-client hub: `cli.py` · `pipelines.py` · `mcp_client.py`) and **`drum_prep/`** (the only DSP). The whole test suite runs **offline** — `tests/conftest.py` provides a `FakeSession` + `fake_hub` that monkeypatches `Hub._open_session`, so no sibling servers, API keys, audio, or network are needed.

```bash
uv sync --extra drum-prep      # dev tools install by default; this adds the DSP test deps

uv run pytest                                   # the full offline suite (asyncio_mode=auto; under tests/)
uv run pytest tests/test_pipelines.py           # one file
uv run pytest -k drum_prep                       # the drum_prep DSP subset (needs --extra drum-prep)

uv run ruff check        # lint (line-length 100; scripts/ + presets/ EXCLUDED by design)
uv run ruff format       # format
uv run mypy              # types — ship_studios + drum_prep only
uv run python scripts/lint_skills.py   # skill-contract lint: [G]-keyless labels, wikilinks, frontmatter (CI-gated)
```

- **The DSP subset SKIPS without `--extra drum-prep`** — those modules `pytest.importorskip` numpy/scipy/soundfile/pyloudnorm; hub tests run on base deps alone.
- **Editing a pipeline = editing `ship_studios/pipelines.py`**; `tests/test_pipelines.py` asserts the *ordered tool-call log* (server, tool, args) against a `RecordingHub`/`FakeSession`, so a reorder/rename fails loudly. Keep the call order in lockstep with **Canonical pipelines** in CLAUDE.md.
- **VST plugin work** (the `[[vst]]` deep-dives): iterate with the harness/probe scripts under `presets/vst/` (`probe_plugin.py` · `dump_params.py` · `apply_vst_preset.py`) + `scripts/mix/*_sweep.py`, run with the sibling loops `vst` venv (`../stemmy-loops-mcp/.venv/bin/python …`). These live outside ruff/mypy coverage on purpose.
- **Skill/doc contract guards** keep the ~102 `SKILL.md` files + CLAUDE.md in lockstep: (1) `scripts/lint_skills.py` — a deterministic CI-gated check (the recurring `[G]`-keyless label bug — `find-sibilance`/`find-resonances`/`check-streaming-targets` are pure DSP — plus wikilink resolution + frontmatter). (2) On-demand agent workflows: `/audit-skill-consistency` and `/audit-pipeline-lockstep`. Author with `/create-skill`; review with `/repo-review` → `/repo-review-fix`; fold session learnings home with `/fold-learnings`.
- **Pre-release / live-contract check.** The offline suite proves only internal consistency (it asserts tool names against a `RecordingHub` that accepts anything). The one guard that opens the **real** sibling servers and asserts every emitted tool name + enum-subset exists is `tests/test_pipelines.py::test_live_tool_names_exist_on_servers` — opt-in (`SHIP_STUDIOS_LIVE_CONTRACT=1` + both siblings synced). Run before a release; CI runs it off the PR path in the additive `live-contract` job (manual + nightly, skips cleanly when siblings are absent).

## Headless alternative — the `ship-studios` CLI

The same pipelines run without an interactive session via the `ship-studios` console script (`ship_studios.cli:main`). It opens both servers over stdio and drives `call_tool` in the verified order:

```bash
ship-studios doctor          # check env vars + sibling repos before first run
ship-studios master          projects/<track>/mix/final.wav --platform spotify
ship-studios batch-master    projects/<album>/mix/*.wav --platform spotify
ship-studios mix-check       projects/<track>/mix/draft.wav
ship-studios reference-match projects/<track>/mix/draft.wav --reference projects/<track>/refs/ref.wav
ship-studios house-curve     projects/<track>/mix/draft.wav --reference refs/a.wav --reference refs/b.wav
ship-studios stem-master     projects/<track>/stems/kick.wav projects/<track>/stems/bass.wav
ship-studios unmask-stems    projects/<track>/stems/kick.wav projects/<track>/stems/bass.wav
ship-studios loops           projects/<track>/stems/drums.wav --bpm 120
ship-studios understand      projects/<track>/refs/ref.wav
```

The nine pipeline subcommands each map to a function in `ship_studios/pipelines.py`, talking to both servers through `ship_studios/mcp_client.py`. `doctor` is a self-contained setup check (env vars + sibling-repo presence; no server launch). `stem-master` drives only the MCP-side per-stem corrective + masking-verify steps — summing (`drum-prep stem-mix`) and mastering the bus (`ship-studios master`) are separate stages by design. Use the CLI for batch/CI; use the skills for interactive work.
