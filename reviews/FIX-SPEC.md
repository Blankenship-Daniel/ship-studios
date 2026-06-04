# Architect-Review Fix Spec

Source of findings: `reviews/ARCHITECT-REVIEW.md`. This spec pins the EXACT changes and the
cross-file CONTRACTS so independent edit agents (each owning a disjoint set of files) stay consistent
without seeing each other's work. **Do only your assigned GROUP. Touch only your owned files.**

## Repo facts (do not violate)
- The hub (`ship_studios/`) is DSP-free; never import numpy/scipy/drum_prep there.
- ruff lint = E4/E7/E9/F/B/I/UP only (line length NOT enforced; do not reflow). Keep ~100 col style.
- `from __future__ import annotations` is at the top of every hub module — keep it first.
- Tests run OFFLINE via `tests/conftest.py` (`RecordingHub`/`FakeSession`/`fake_hub`). New tests must
  not need servers, keys, audio, or network. Use `RecordingHub`/`fake_hub`.
- After your edits, `uv run pytest`, `uv run ruff check`, `uv run mypy`, and
  `uv run python scripts/lint_skills.py` must all stay green (the final gate enforces this; write
  your code to pass them).

---

## SHARED CONTRACTS (every relevant group must follow these EXACTLY)

### C1 — Tool-name registry (Group G2 defines, Group G1b consumes)
In `ship_studios/config.py`, add two `enum.StrEnum` classes named **`LoopsTool`** and **`GeminiTool`**.
Member rule (deterministic, both groups derive identically): **member name = the tool name uppercased
with every `-` replaced by `_`; value = the exact tool-name string.** Examples:
`MEASURE_LOUDNESS = "measure-loudness"`, `APPLY_DYNAMIC_EQ = "apply-dynamic-eq"`,
`ANALYZE_STEM_MASKING = "analyze-stem-masking"`, `MATCH_EQ = "match-eq"`.
Define members for **exactly the tool names currently used in `ship_studios/pipelines.py`** (read the
file and enumerate every literal passed as the 2nd arg to `rec.run(...)` / `hub.call_tool(...)`),
split by server (`LOOPS_SERVER` calls → `LoopsTool`; `GEMINI_SERVER` calls → `GeminiTool`).
Because `StrEnum` IS a `str` subclass, `LoopsTool.MEASURE_LOUDNESS == "measure-loudness"` is True and
it serializes over MCP as the string — so existing string-based test assertions keep passing
unchanged and `call_tool(server, tool: str, ...)` still type-checks.

### C2 — Centralized CLI choice constants (Group G1a defines in pipelines.py, Group G3 imports)
In `ship_studios/pipelines.py`, add three module-level constants (near `PLATFORM_CHOICES`):
```
INTENT_CHOICES: list[str] = ["loud", "dynamic", "warm", "bright", "balanced", "punchy"]
INTENSITY_CHOICES: list[str] = ["subtle", "medium", "strong"]
MATCH_PHASE_CHOICES: list[str] = ["minimum", "linear", "tilt_only"]
```
(These mirror server-side Literals — same single-source-of-truth pattern as `PLATFORM_CHOICES`.)

### C3 — `_master_out` is the single master-path helper
`ship_studios/pipelines._master_out(mix_path, masters_dir)` already exists. Group G3 deletes the
duplicate `cli._default_master_out` and calls `_master_out(mix_path, None)` instead (import it from
`ship_studios.pipelines`). PurePosixPath output is acceptable (POSIX-oriented project).

---

## GROUP G1a — `ship_studios/pipelines.py` + `tests/test_pipelines.py` (behavioral)
Owns those two files. Do NOT do the tool-name enum swap (that is G1b, same file, runs after you).

1. **C2:** add `INTENT_CHOICES` / `INTENSITY_CHOICES` / `MATCH_PHASE_CHOICES` constants.
2. **B1 — `batch_master` partial-failure isolation + album verdict.** Wrap the per-track
   `await master_track(...)` (pipelines.py ~297-321) in `try/except Exception as exc`. On failure,
   append `{"input": mix, "master": out, "error": str(exc), "streaming_compliant": None}` to `tracks`
   and `continue` (do NOT append to `masters`). Add a keyword `continue_on_error: bool = True` to the
   signature; when `False`, re-raise. Run the cross-track album pass over the masters that SUCCEEDED
   (skip it cleanly if none). Add to the return dict an `album` summary:
   `{"ok": <count succeeded>, "failed": <count failed>, "compliant": <count True>,
   "noncompliant": <count False>, "unknown": <count None>}` computed from `tracks`. Keep all existing
   keys.
3. **B2 — observable fallback in `loops_to_deliverables`.** Change `_loop_paths` to return `None` when
   the manifest shape is UNPARSEABLE (not a dict, or no recognizable loops container) and `[]` when it
   parses but finds zero loops. In `loops_to_deliverables`, set `fell_back = False`; if `_loop_paths`
   returns `None` or `[]`, set `loop_paths = [input_path]` and `fell_back = True`. Add
   `"fell_back": fell_back` and `"loop_count": len(loop_paths)` to the returned dict. Update the
   docstring. (Callers that relied on the old `[]`-means-empty behavior: only this function calls it.)
4. **D2 — dedupe the per-stem corrective chain.** `mix_check`'s corrective block and
   `_apply_stem_corrections` apply the SAME ordered chain (apply-eq → de-ess → suppress-resonances →
   apply-dynamic-eq → … ). Factor the shared ordered steps into ONE helper both call (e.g.
   `_run_corrective_chain(rec, path, spec, *, include_excite, include_compress_bool, include_multiband,
   include_shape)` or a small ordered step-table). Preserve EXACT current behavior and call order for
   BOTH callers (mix_check includes excite-loop + a bool `compress` + multiband but NOT shape-bands;
   the stem helper includes shape-bands + bool compress + multiband but NOT excite). The existing
   ordered-call tests must stay green unchanged — they are your correctness oracle.
5. **D3 — document the result contract (light).** Add a "Result contract" paragraph to the module
   docstring: every pipeline returns a dict with at least `"pipeline"` and `"steps"`; most also carry
   `"input"` and an `"output"`/`"outputs"`/`"corrected"`/`"masters"` key (list them per pipeline).
   Define a `Step` TypedDict (`server: str; tool: str; args: dict[str, Any]; result: Any;
   elapsed_s: float; ok: bool`) and annotate `_Recorder.steps: list[Step]`. Do NOT add per-pipeline
   TypedDicts (deferred — too churny for the value).
6. **D5 (minimal/safe):** Leave `PLATFORM_CHOICES` accepting `apple` AND `apple_music` (dropping the
   alias would break existing CLI invocations). No change here — documented deferral.
7. **Tests:** add to `tests/test_pipelines.py`: (a) `batch_master` with a hub whose `master_track`
   path fails on one track (use a small fake/RecordingHub subclass or canned error) still returns a
   result with the other tracks + the `album` summary + the failed track recorded; (b)
   `loops_to_deliverables` with a canned empty/unparseable `find-loops` manifest sets
   `fell_back=True` and falls back to the input; (c) `_loop_paths` returns `None` on a bad shape and
   `[]` on a parseable-but-empty manifest. Keep every existing test passing.

## GROUP G1b — `ship_studios/pipelines.py` (tool-name enum swap; runs AFTER G1a)
Owns `pipelines.py` only (G1a already finished; re-read the file). Per **C1**: replace every bare
tool-name string literal passed as the tool argument to `rec.run(SERVER, "<name>", ...)` /
`hub.call_tool(...)` with the matching `LoopsTool.<MEMBER>` / `GeminiTool.<MEMBER>` (import them:
`from ship_studios.config import GEMINI_SERVER, LOOPS_SERVER, GeminiTool, LoopsTool`). Do not change
call order, args, or behavior. Do NOT touch tests (StrEnum == str keeps them green). Verify with a grep
that no plain tool-name string literal remains as a `rec.run` 2nd positional arg.

## GROUP G2 — `ship_studios/config.py` + `tests/test_config.py`
1. **C1:** add `from enum import StrEnum` (keep import ordering ruff-I clean) and define `LoopsTool` /
   `GeminiTool` per the C1 rule, enumerating members from the tools used in `pipelines.py`. Place them
   in a clearly-commented "Tool-name registry" section. Add a short docstring noting these mirror the
   sibling servers' tool surface (the hub cannot import the real schema).
2. **S1 — harden `_resolve_main_root` against a tampered `commondir`.** Today it only checks the
   resolved path is a dir named `.git`. Strengthen: after computing `cg` (the candidate canonical
   `.git` dir), verify the worktree is actually registered under it — i.e. that
   `cg / "worktrees" / <name>` resolves back to `gitdir` (round-trip), where `<name> = gitdir.name`.
   If the round-trip fails, return `root` (degrade safely). Keep all existing safe-degrade paths and
   the docstring's security note; expand the note to mention the round-trip check.
3. **Tests:** add to `tests/test_config.py`: a test that a tampered `commondir` pointing at a
   decoy tree containing a real `.git/` dir (but NOT registering this worktree) makes
   `_resolve_main_root` fall back to `root` (build the fixture with `tmp_path`; mirror the existing
   worktree-resolution test style). Add a registry sanity test: every `LoopsTool`/`GeminiTool` value
   equals its name lowercased with `_`→`-`, and the value round-trips (`LoopsTool(value) is member`).

## GROUP G3 — `ship_studios/cli.py` + `tests/test_cli.py`
1. **C2 consume:** import `INTENT_CHOICES, INTENSITY_CHOICES, MATCH_PHASE_CHOICES` from
   `ship_studios.pipelines` and use them in the `click.Choice(...)` for `master --intent/--intensity`
   and for `--match-phase` on BOTH `reference-match` and `house-curve` (replace the inline lists).
2. **C3 / D1:** delete `_default_master_out`; in the `master` command, import and call
   `from ship_studios.pipelines import _master_out` → `resolved_out = out_path or _master_out(mix_path, None)`.
3. **D4:** add a `--presets` option to the `master` command (reuse the existing `_parse_presets`
   helper) and thread it into `master_track(..., presets=preset_list)`. (Optional, same pattern for
   `batch-master` if clean.) Keep `--help` working.
4. **Tests:** update any `test_cli.py` reference to `_default_master_out`; add a test that
   `master --presets distribution_44k_16` threads the parsed presets to the pipeline (use the existing
   CLI test pattern that patches/inspects the pipeline call), and that the default master-out path is
   unchanged from before (parity with the old `_default_master_out` for a `mix/` and a flat layout).

## GROUP G4 — `ship_studios/mcp_client.py` + `tests/test_mcp_client.py`
1. **B3 (doc):** expand `Hub.call_tool`'s docstring to state that a CLIENT-SIDE call timeout abandons
   the wait but does NOT send a cancellation to the server — the sibling subprocess keeps running the
   in-flight tool until it is reaped at Hub/stack teardown; therefore set `SHIP_STUDIOS_CALL_TIMEOUT`
   generously for heavy tools (Demucs/Gemini renders). No behavior change.
2. **B4 (tests):** add OFFLINE tests using `fake_hub` (extend `FakeSession` locally in the test if you
   need a slow/raising session — do NOT edit conftest unless additive and safe): (a) after a tool call
   raises `ToolCallError`, a subsequent `call_tool` on the SAME open hub still succeeds (session not
   poisoned); (b) `_open_session` whose `initialize()` is made to exceed `startup_timeout` raises the
   relabelled `TimeoutError` containing the server key (you can monkeypatch `config.startup_timeout_s`
   to a tiny value and make a fake `initialize` sleep, or assert the message-formatting branch
   directly); (c) a session whose `call_tool` raises mid-call still results in the AsyncExitStack being
   closed (assert teardown ran). Keep them fast and deterministic.

## GROUP G5 — `drum_prep/dsp.py` + `tests/test_drum_prep_dsp.py`
**Do NOT change any numerics** (the pinned-signature determinism test must stay green). Documentation
+ comment fixes only:
1. **C1 (doc):** in `zero_phase_eq`'s docstring, add a paragraph: the implementation does an un-padded
   `rfft → ×gain → irfft` at length `n`, i.e. CIRCULAR convolution, so end-of-buffer energy wraps to
   the start. State the safe envelope (modest gains on full-length stems — the production ref-match
   caps at +6/−8 dB where the edge artifact is inaudible) and warn that a large narrow boost or a very
   short buffer would produce audible edge contamination; note zero-padding (mirroring
   `fractional_delay`) is the fix if those cases arise, deliberately NOT applied now to preserve the
   pinned numeric signature.
2. **C2 (comment fix):** `fractional_delay`'s inline comment claims it preserves float32 dtype, but the
   `rfft/irfft` path always returns float64. Correct the comment to say the FFT path returns float64
   (and that production input is float64). Do not change the code.
3. **Tests:** OPTIONAL — add a NON-fragile test documenting that `zero_phase_eq`'s INTERIOR is clean
   (e.g. with a flat 0 dB curve the output equals the input within tight tolerance). Do not assert a
   specific edge-artifact magnitude (fragile). Skip if it risks flakiness.

## GROUP G6 — `.github/workflows/ci.yml` + `CLAUDE.md`
1. **A2 (CI + doc):** add a SEPARATE, additive CI job (e.g. `live-contract`) triggered by
   `workflow_dispatch` (manual) and/or `schedule` (nightly) that, when the sibling repos are reachable
   (via `SHIP_STUDIOS_LOOPS_DIR`/`SHIP_STUDIOS_GEMINI_DIR` or a checkout step you add as best-effort),
   runs `SHIP_STUDIOS_LIVE_CONTRACT=1 uv run pytest tests/test_pipelines.py -k live` and is allowed to
   skip cleanly when siblings are absent. Do NOT make it block the normal PR job. Keep the existing
   `test`/lint jobs intact and valid YAML. In `CLAUDE.md`'s "Developing this repo" section, add a
   "Pre-release / live-contract" note documenting that the live tool-name+enum contract test
   (`SHIP_STUDIOS_LIVE_CONTRACT=1`) must be run against synced siblings before a release, and that the
   normal offline suite proves only internal consistency.
2. **B3 (doc):** in `CLAUDE.md`'s env-vars table row for `SHIP_STUDIOS_CALL_TIMEOUT`, add that a call
   timeout abandons the client wait but does not abort server-side work (set it generously for heavy
   tools) — matching the G4 docstring.
Validate the YAML parses (e.g. `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`).

## GROUP G7 — `.claude/workflows/audit-pipeline-lockstep.js`
**A1b:** update the workflow's default pipeline list (currently 5: master-track, mix-check,
reference-match, loops-to-deliverables, understand-audio) to include all 9 coded pipelines — add
`batch-master`/`batch_master`, `house-curve`/`house_curve`, `stem-master`/`stem_master`,
`unmask-stems`/`unmask_stems` with the same `{name, fn}` shape the existing entries use (match the
field names already in the file). Do not change the workflow logic.

## GROUP G8 — NEW files only (no existing-file edits): `tests/test_pipeline_lockstep.py`,
`tests/test_docs_env_table.py`, `scripts/snapshot_tool_schemas.py`, `tests/test_arg_schemas.py`
Runs after G6 so it sees final `CLAUDE.md`.
1. **A1a — deterministic prose↔code lockstep test** (`tests/test_pipeline_lockstep.py`): parse the
   "Canonical pipelines" section of `CLAUDE.md` (locate `repo_root()/"CLAUDE.md"` via
   `ship_studios.config.repo_root`). For each pipeline whose prose block you can confidently locate by
   its `### <name>` header, extract the ORDERED list of `[L]`/`[G]` + tool-name tokens (regex like
   `\[([LG])\]\s*\`?([a-z0-9-]+)\`?`). Drive the matching pipeline function with a `RecordingHub`
   (canned results as needed so it runs the default path; see existing `test_pipelines.py` canned
   fixtures) and assert the hub's default ordered `(server, tool)` sequence is an ORDERED SUBSEQUENCE
   of the prose tokens (mandatory steps appear in the prose in the same relative order; optional/gated
   steps in prose that don't fire by default are tolerated). Map `[L]`→loops server, `[G]`→gemini
   server. Skip (don't fail) any pipeline whose block can't be parsed, but assert at least
   master-track, mix-check, and reference-match are checked. This catches reorder/rename/missing-step
   drift deterministically and offline.
2. **A5 — env-table ⊇ FORWARDED_ENV test** (`tests/test_docs_env_table.py`): read `CLAUDE.md`, assert
   every var in `ship_studios.config.FORWARDED_ENV` appears in the doc text (closes the
   "keep in sync with CLAUDE.md" manual gap).
3. **A6 — offline arg-schema validation mechanism** (best-effort, skip-if-absent):
   - `scripts/snapshot_tool_schemas.py`: a small script (outside ruff/mypy, like the other scripts)
     that opens the real Hub over both servers, calls `list_tools`, and writes each tool's
     `name → inputSchema` to `tests/fixtures/tool_schemas.json`. Document at the top that it needs
     synced siblings (it's a generator, run manually).
   - `tests/test_arg_schemas.py`: if `tests/fixtures/tool_schemas.json` exists, drive each pipeline
     with a `RecordingHub`, and for every recorded call validate the emitted `args` against that
     tool's `inputSchema` (use a tiny inline validator: required keys present, no unknown keys when
     `additionalProperties is False`, basic type checks — do NOT add a jsonschema dependency).
     `pytest.skip(...)` cleanly when the fixture is absent (the default CI state). This turns the
     "args never validated against the real schema" blind spot into a check that activates once the
     fixture is snapshotted.

---

## Deferred (documented, intentionally NOT changed)
- Full per-pipeline result `TypedDict`s (D3) — light docstring contract + `Step` TypedDict instead.
- Dropping the `apple` `--platform` alias (D5) — would break existing invocations.
- Zero-padding `zero_phase_eq` (C1) — would change the pinned numeric signature; documented instead.
