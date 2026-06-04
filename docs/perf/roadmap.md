# Performance instrumentation — staged roadmap

**Status:** roadmap (not yet implemented) · **Date:** 2026-06-03 · **Companion to:** [README.md](README.md) (the tool report) · **Scope:** the concrete, ordered steps to take ship-studios from "we can see *what* ran" to "we can see latency, cost, memory, determinism, and regressions."

Each stage is independently shippable and ordered by **value ÷ friction**. Stage 0 is pure config; later stages add code behind opt-in `--extra`s so the **offline test suite stays fast, key-free, and network-free**. Every code change is verifiable against the existing `FakeSession` / `RecordingHub` fixtures (`uv run pytest`) — no live keys or sibling servers needed.

> **Guardrail.** The hub is deliberately **DSP-free** and the base install is dependency-light. Keep it that way: timing uses stdlib (`time.perf_counter`); everything heavier (`psutil`, profilers, eval frameworks) goes in an opt-in extra, matching the repo's existing `--extra` convention.

---

## Stage 0 — zero code (config + docs only)

The biggest win for the least work. Covers surfaces **(g) agent loop, (d) skill cost, (e) workflow cost** and gives a native handshake read for **(a)**.

1. **Turn on Claude Code OTel.** In the dev shell profile / an uncommitted `.env`:
   ```
   CLAUDE_CODE_ENABLE_TELEMETRY=1
   CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1        # adds beta traces (span schema may change)
   OTEL_METRICS_EXPORTER=otlp                   # or =console for a quick look
   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
   ```
   This immediately attributes token/cost/latency by `skill.name` / `mcp_server.name` / `mcp_tool.name` / `query_source`. For traces, point the endpoint at a local Phoenix (Stage 4) — **don't** use the console *trace* exporter under the Agent SDK (it collides with the SDK message channel).
2. **Document `ccusage`** as the retrospective cost read: `npx ccusage@latest session` / `daily` (offline, reads the on-disk transcripts). No dependency added.
3. **Document the MCP Inspector smoke commands** for both siblings:
   `npx @modelcontextprotocol/inspector uv --directory ../stemmy-loops-mcp run <console-script>` (and the gemini sibling).

**Files:** shell profile / `.env` (never committed with keys); a short dev-docs section. Cross-reference CLAUDE.md's "Environment variables" table.

---

## Stage 1 — hub: the `_Recorder` seam

Per-tool-call latency and **error-cause attribution** for both servers, in one place, with stdlib only.

1. **Time each step in `_Recorder.run`** (`ship_studios/pipelines.py` 140–147): wrap the `await self._hub.call_tool(...)` (line 143) in `time.perf_counter()` and add `elapsed_s` to the existing `{server,tool,args,result}` dict. Purely additive — the offline tests keep passing.
2. **Capture the exception path too.** `_Recorder.run` currently only records on **success**; on failure the step is lost. Wrap in `try/finally` so a failed call still records `{...,"ok":false,"error_kind":...,"elapsed_s":...}`.
3. **Split the error cause in `Hub.call_tool`** (`ship_studios/mcp_client.py` 133–162): today a server-flagged error **and** an `asyncio` timeout both raise a single `ToolCallError`. Distinguish `timeout` vs `tool_error` vs (in `_open_session`) `handshake_failure`, so "raise the timeout vs fix a bug" is answerable.
4. **Alarm against the real budgets at runtime:** read `config.startup_timeout_s()` / `call_timeout_s()` (both can be **`None`** when the env var is `0` — don't hardcode 120/600).
5. **Emit a JSONL perf trace** (the plain-log middle ground, before any OTel): one `{ts,server,tool,elapsed_s,ok}` line per call via stdlib `logging` with a JSON formatter (or `structlog`), gated behind an env flag. Queryable with `jq`, no backend.

**Files:** `ship_studios/pipelines.py` (`_Recorder.run`), `ship_studios/mcp_client.py` (`Hub.call_tool`, `Hub._open_session`), `tests/test_pipelines.py` (assert the new keys are present/optional — the **ordered-call assertions must stay green**).

**Optional `metrics` extra** (`psutil`): sample per-subprocess CPU/RSS via `psutil.Process(os.getpid()).children(recursive=True)` (a process-tree scan — the PID is **not** exposed by `stdio_client`; see README correction #4), and the hub's **own** peak RSS via stdlib `tracemalloc` around long pipelines. Remember `cpu_percent()` needs an interval / two reads.

---

## Stage 2 — DSP: regression + determinism

Lock down render **speed** and **output** so a numerics refactor can't silently regress either.

1. **Add `pytest-benchmark`** to the dev dependency group under a dedicated marker. Create `benchmarks/` with `@pytest.mark.benchmark` tests over **deterministic** DSP (`render-mastered`, drum_prep phase-align FFT xcorr, `match-eq` FIR) on a fixed fixture WAV. Wrap async hub coroutines in `asyncio.run()` inside the benchmarked callable. Commit a `.benchmarks/` baseline; gate CI with `--benchmark-compare-fail=mean:5%`. Keep it **out** of the default `uv run pytest` (`--benchmark-disable`) so the offline suite stays fast; needs `--extra drum-prep` for the DSP deps.
2. **Golden-WAV determinism test** — a ~10-line `numpy.testing.assert_allclose` of a render against a committed baseline WAV (drum_prep is seed-free/FFT-based → reproducible). Optionally use **syrupy** / **pytest-regtest** as the snapshot harness. For the **non-deterministic** VST/Pedalboard path, assert `allclose` within a **tolerance window** instead of bit-exact (a drift *alarm*, not equality).
3. **Document on-demand deep profilers** (an opt-in `profiling` extra, never always-on): **Scalene** (`scalene <script>` — Python-vs-native + copy-volume), **py-spy**/**Austin** (attach to a live/hung MCP subprocess — use the venv/Homebrew Python to dodge macOS SIP), **memray** + **pytest-memray** `@limit_memory(...)` (native-allocation + memory-regression), **hyperfine** (standalone binary — end-to-end CLI wall-clock; don't aim it at Gemini-calling pipelines).

**Files:** `pyproject.toml` (`[dependency-groups].dev` + markers; optional `profiling` extra), `benchmarks/` (new), `.benchmarks/` baseline, a golden fixtures dir, CI config.

---

## Stage 3 — Gemini (sibling `stemmy-gemini-mcp`)

The largest blind spot — and it's outside this hub's remit, so it's a sibling-repo change.

1. **Add retry first (the prerequisite):** `tenacity` / `stamina` backoff around the Gemini calls, so transient **429/503** are distinguishable from hard failures.
2. **Log the SDK's `response.usage_metadata`** per call — exact `prompt` / `candidates` / **`thoughts`** (thinking-tier) token counts → direct cost + thinking attribution. Time each call; classify outcomes (ok / 429-quota / timeout / error). Or use **Traceloop OpenLLMetry**'s `google-genai` instrumentor for OTLP spans.
3. **Cross-process correlation:** have the hub inject a **run-id** argument the servers log, so a skill invocation (Claude Code OTel) stitches to its server-side Gemini calls (since `OTEL_*` does **not** cross into the stdio subprocess).

**Files:** `../stemmy-gemini-mcp` (the Gemini call sites + deps); `ship_studios/mcp_client.py` (inject the run-id arg).

---

## Stage 4 — optional: backend + evals

Only if you want dashboards / trace waterfalls / quality gates over time.

1. **Self-host Arize Phoenix** (`pip install arize-phoenix`, no account) as the OTLP sink; point `OTEL_EXPORTER_OTLP_ENDPOINT` at it. Optionally wrap `Hub.call_tool` / `_Recorder` steps as **OpenInference** spans named with the **GenAI semconv** attributes, so hub spans and the agent loop share one pane.
2. **Opt-in `evals` extra** — **MLflow** `agent-eval-skill-invoked` + rule-based graders that call the repo's own DSP meters, run **periodically** (real LLM tokens), **never** in the offline suite. Alternatives: DeepEval (pytest-native), Inspect AI (drives Claude Code + MCP).
3. **Skill-collision audit** — an offline embedding cosine-similarity matrix over the 102 skill `description` fields; no LLM, no tokens; flags the false-fire risk across overlapping skills.

**Files:** `pyproject.toml` (optional `tracing` / `evals` extras), optional span emission in `ship_studios/mcp_client.py` + `pipelines.py`, `evals/` (new, opt-in), a separate periodic CI job.

---

## Sequencing summary

| Stage | Surfaces | Friction | Ships |
|---|---|---|---|
| 0 | g, d, e, (a handshake) | none (env) | telemetry on + cost read + smoke cmds |
| 1 | a, f, hub | low (stdlib + optional psutil) | per-call latency + error split + JSONL trace |
| 2 | b, f | low–medium | speed-regression suite + golden-WAV determinism |
| 3 | c | medium (sibling repo) | Gemini cost/latency/quota + retry + run-id |
| 4 | all | medium (opt-in) | Phoenix dashboards + skill evals + collision audit |

Stages 0–2 are the high-leverage core for a single developer; 3 needs the sibling repo; 4 is for when one laptop's numbers are worth a dashboard.
