# Performance & efficiency measurement — tooling reference

**Status:** reference + roadmap; **Stages 0–2 + hub `run_id` now wired in** (see [Status](#status--whats-wired-in)) · **Date:** 2026-06-03 · **Last verified:** 2026-06-03 against the live repo (mcp SDK **1.27.2**) and each tool's official docs · **Scope:** the best tools to measure **efficiency & performance** across every ship-studios surface — MCP servers, DSP renders, the Gemini API, skills, workflows, the hub, and the Claude Code agent loop.

This folder answers *"what should we use to measure how fast / how expensive / how reliable ship-studios is?"* It is a **research report** (ranked tool picks per surface, with trade-offs) plus a **[staged instrumentation roadmap](roadmap.md)**. The high-leverage core is now **wired in** — see [Status](#status--whats-wired-in); the rest stays a documented map.

> **How this was built.** A 7-agent research workflow surveyed five categories (MCP-native, LLM observability, eval frameworks, Python profiling, infra/Claude-native telemetry), then an adversarial completeness-critic re-checked the synthesis. Every load-bearing fact here was re-verified against the repo at the versions installed today. Re-verify a number before betting a build on it; the landscape moves fast and several tools changed ownership in early 2026.

---

## The one finding that shapes everything

> ship-studios is a **local, single-developer, `uv`-managed macOS** tool — short-lived CLI/agent runs on one laptop, **not** a hosted multi-tenant service.

That single fact decides almost every pick below. It means: **lean on what's already in the box** (Claude Code's native telemetry, the existing `_Recorder`, the existing pytest stack), prefer **OSS / self-hostable / zero-service** tools, and **skip the hosted observability stacks** (Datadog-style SaaS, Prometheus+Grafana, gateways) that assume a long-lived scrapeable server and a team. A pull-based metrics server or a 5-container LGTM stack is *more* operational burden than the thing it measures.

---

## Status — what's wired in

Implemented in the hub (Stages 0–2 of the [roadmap](roadmap.md), plus the hub `run_id`):

- **Opt-in JSONL perf trace** — set `SHIP_STUDIOS_PERF_LOG=<file>` and every MCP tool call **and** the handshake append one line `{run_id, server, tool, elapsed_s, ok, kind?, rss_self?, rss_children?, at}` (`ship_studios/perf.py`, emitted from `Hub.call_tool` / `Hub._open_session`). Off by default → the offline suite and normal runs are unaffected. Best-effort: a sink error never breaks a pipeline.
- **Always-on per-step timing** — `_Recorder.run` now stamps every pipeline step with `elapsed_s` + `ok` (additive; the step stays a superset of `{server,tool,args,result}`), recorded on success **and** failure.
- **Error-cause split** — `ToolCallError.kind` distinguishes `"timeout"` from `"tool_error"` (keyword-only, defaulted → the 3-arg form is unchanged), surfaced in the trace.
- **Hub `run_id`** — a per-`Hub` correlation id on every traced event. *Not* injected into tool-call `args` (the sibling servers validate strict input schemas and would reject an unknown property) — correlation is hub-side.
- **Per-subprocess RSS** — `metrics` extra (`psutil`): `perf.sample_rss()` sums the hub process + its children via an OS process-tree scan (the child PID is never exposed by `stdio_client`). Omitted when `psutil` isn't installed.
- **DSP regression + determinism** — `pytest-benchmark` suite under `benchmarks/` (opt-in `bench` extra, outside `testpaths`) + a golden-signature determinism test (`tests/test_drum_prep_determinism.py`): bit-exact reproducibility **and** a tolerance-pinned numeric fingerprint (no committed WAV — `*.wav` is gitignored).
- **Extras** — `uv sync --extra metrics` (psutil) · `--extra bench` (pytest-benchmark) · `--extra profiling` (scalene/py-spy/memray, on-demand CLI profilers).

**Enable the trace + a quick read:**
```bash
SHIP_STUDIOS_PERF_LOG=artifacts/perf.jsonl ship-studios master projects/<t>/mix/x.wav
jq -s 'group_by(.tool)[] | {tool: .[0].tool, n: length, p50: (sort_by(.elapsed_s)[length/2|floor].elapsed_s)}' artifacts/perf.jsonl
```

**Stage 3 (Gemini sibling) — already done upstream, intentionally untouched here.** `../stemmy-gemini-mcp` already implements the Stage-3 intent: native `genai.Client(retry_options=HttpRetryOptions())` retry/backoff (408/429/5xx + jitter), a concurrency semaphore, and `usage_metadata` logging (`prompt/candidates/thoughts/total` + cache details). It also has active uncommitted work on a feature branch, so this change does **not** modify it. The hub-side half (the `run_id` correlation key) is wired in here.

What remains optional (Stage 4): a self-hosted Phoenix backend + an `evals` extra (MLflow skill-trigger + DSP-meter graders) + the skill-collision embedding audit. See [roadmap.md](roadmap.md).

---

## The seven surfaces, and what to measure

| # | Surface | The metric that matters | Captured today? |
|---|---|---|---|
| a | **MCP servers** (`stemmy-loops`, `stemmy-gemini`) | per-tool-call latency, handshake/cold-start, **error vs timeout** split, subprocess CPU/RSS | ❌ |
| b | **DSP renders** (numpy/scipy/soundfile/Pedalboard) | render wall-clock, peak RSS / native allocations, **output determinism** | ❌ |
| c | **Gemini API** (the `[G]` listen tools) | per-call latency, token / thinking-tier $cost, **429/quota rate** | ❌ |
| d | **Skills** (102) | trigger precision / collision, $/skill, output quality | ❌ |
| e | **Workflows** (15) | fan-out wall-clock, token budget actual vs target, per-agent success | ⚠️ partial¹ |
| f | **Hub + drum_prep code** | function/line CPU+memory, regression benchmarks | ❌ |
| g | **Agent loop** (the Claude Code session) | tokens, $cost, tool-call counts, latency | ❌ |

¹ Only `repo-review.js` uses a `budget` object — and only `.remaining()`/`.total`, **never `.spent()`**. The other 14 workflows have no budget instrumentation. See [correction #3](#corrections-verified-against-the-repo).

**Current state in one line:** the hub is transparent about *what* ran (`pipelines.py` records an ordered `{server,tool,args,result}` step list; the hub raises structured `ToolCallError`/`TimeoutError`) but **opaque about *how much it cost*** — no timing, no token/$ tracking, no profiling deps, no determinism regression, no retry/429 handling, no telemetry export.

---

## The backbone — adopt these first (near-zero friction)

These four cover surfaces (g), most of (d)/(e), and the standards layer — for almost no work.

| Tool | What it gives you | License / self-host |
|---|---|---|
| **Claude Code native OpenTelemetry**<br>(`CLAUDE_CODE_ENABLE_TELEMETRY=1`) | THE answer for the agent loop, and free skill/workflow attribution: per-API-request tokens, USD cost, tool-call counts, latency — **sliced by `skill.name` / `mcp_server.name` / `mcp_tool.name` / `query_source(main\|subagent)`**. Subagent (Task) spans nest under the parent → a fan-out workflow renders as **one** trace. `mcp_server_connection.duration_ms` is the native read on the stdio handshake. | Built-in (no dep); emits vendor-neutral OTLP |
| **ccusage** | Zero-setup retrospective **$/token per session / day / billing-block**, computed **fully offline** from the `~/.claude/projects/*.jsonl` transcripts already on disk (the same ones `studio:copy-transcript` knows). `npx ccusage@latest session`. | MIT, offline |
| **OpenTelemetry GenAI semantic conventions** | Not a product — the **attribute schema** (`gen_ai.usage.input_tokens`, `gen_ai.request.model`, agent/tool spans) to name any custom spans you emit, so you can swap backends freely. Anti-lock-in insurance. | Apache-2.0 standard |
| **Arize Phoenix** *(optional backend)* | `pip install arize-phoenix`, **no account, data stays local** — an OTLP sink with trace waterfalls + an eval harness. Ingests Claude Code's native telemetry *and* any custom hub spans. The **lightest** self-hosted backend (vs Langfuse's Postgres+ClickHouse+Redis stack or the docker-otel-lgtm 5-service bundle — both overkill for one dev). | Elastic License 2.0 (free to self-host) |

> **Two env-var caveats worth knowing up front.** (1) Claude Code does **NOT** pass `OTEL_*` env into MCP subprocesses, Bash, or hooks — so the sibling stdio servers **do not inherit** this telemetry; their *internal* latency/cost must be measured inside those repos or by the hub. (2) Under the Agent SDK, the OTel **console trace** exporter collides with the SDK's stdout message channel — use an OTLP endpoint (e.g. a local Phoenix) locally, or the **metrics** console exporter for a quick look.

---

## Per-surface recommendations

### (a) MCP servers — latency, handshake, error/timeout, subprocess resource

- **Top pick — MCP Inspector** *(MIT, Anthropic-maintained)* for protocol/schema/handshake conformance:
  `npx @modelcontextprotocol/inspector uv --directory ../stemmy-loops-mcp run <console-script>` drives the **exact stdio launch shape** the hub uses, on either sibling, untouched. CLI mode gives JSON + exit codes for a CI smoke gate. **It's a debugger, not a profiler** — get latency from the hub, not Inspector.
- **For latency + error attribution — extend the hub's own `_Recorder`** (see [roadmap Stage 1](roadmap.md#stage-1--hub-the-_recorder-seam)). It already records every step; adding `time.perf_counter()` is a few lines and covers *both* servers in one place.
- **For subprocess CPU/RSS — `psutil`** *(BSD-3)*, **but** not via a clean handle: mcp 1.27.2's `stdio_client` yields only the read/write streams, so sample the children with `psutil.Process(os.getpid()).children(recursive=True)` (a process-tree scan). This is the one resource read Claude Code's OTel **cannot** reach.
- **Alternatives:** **promptfoo** MCP provider (MIT) — an LLM-free declarative YAML matrix of `{tool,args}` → expected output, a CI-friendly *correctness* gate (no latency); **mcp-tester** (Rust) for stricter conformance + the only real MCP load-tester found — though stdio is single-client, so load-testing has little meaning here.

### (b) DSP renders — speed, memory, and output determinism

- **Top pick — Scalene** *(Apache-2.0)*: one command, **separates Python time from native/C** (BLAS/FFT/Pedalboard) and reports **copy-volume** — exactly what catches the inadvertent large-audio-buffer copies. Runs on Apple Silicon, no code edits.
- **Companions:** **py-spy** *(MIT)* to attach to a live/hung process with no code change — *on macOS prefer a `uv`/Homebrew Python to dodge the SIP+sudo wall, or let py-spy spawn the process*; **Austin** *(MIT)* is the py-spy alternative that sidesteps that macOS friction. **memray** + **pytest-memray** `@limit_memory(...)` *(Apache-2.0)* for exact native-allocation attribution and a **memory-regression** guard. **viztracer** *(Apache-2.0)* for the **asyncio** tool-call timeline (the hub awaiting two stdio children). **line_profiler** once a hotspot is localized.
- **Speed regression — pytest-benchmark** *(BSD-2)*: drops into the existing pytest stack; `--benchmark-compare-fail=mean:5%` fails CI on a render slowdown. Keep it behind a marker / `--benchmark-disable` so the offline suite stays fast; wrap async hub calls in `asyncio.run()`; benchmark **only deterministic local DSP** (never the Gemini or non-deterministic VST paths). **hyperfine** *(MIT/Apache)* — a standalone binary — for end-to-end **CLI wall-clock** of the `ship-studios` / `drum-prep` console scripts. **asv** (optional) if you want a historical trend DB.
- **Determinism — the real gap, and it's cheap.** `drum_prep` is **seed-free + FFT-based**, so renders should be bit-reproducible: a **~10-line golden-WAV `numpy.testing.assert_allclose`** snapshot is the correct and sufficient guard (pytest-benchmark measures *speed*, not *output equality*). Use **syrupy** or **pytest-regtest** if you want a snapshot harness; for the **non-deterministic VST/Pedalboard** path, a **tolerance-based drift alarm** (allclose within a window) instead of bit-exact. **tracemalloc** *(stdlib)* covers the *hub's own* peak RSS on long pipelines (`loops_to_deliverables` runs a 5-tool chain **per loop** over an unbounded set).

### (c) Gemini API — the flagged blind spot (lives in the sibling repo)

This is the **largest measurement gap**: Gemini is the network-bound, paid, rate-limited surface that dominates real pipeline wall-clock, and **the hub has no retry/429 handling at all** (verified — nothing in `ship_studios/`).

- **Instrument inside `stemmy-gemini-mcp`** (out of this hub's DSP-free remit, but where the calls live): log the **google-genai SDK's `response.usage_metadata`** — it already returns exact `prompt` / `candidates` / **`thoughts`** token counts per call, so per-call **cost + thinking-tier** is a direct read, lower-friction and more accurate than wrapping. Time each call there too. Or drop in **Traceloop OpenLLMetry**'s `google-genai` instrumentor for OTLP spans (Apache-2.0).
- **Prerequisite — add `tenacity` / `stamina` retry/backoff.** Without retries you cannot separate a transient **429/503** from a hard error, so "quota-exhaustion rate" is literally unmeasurable. Retry is an *instrumentation prerequisite* here, not just resilience.
- **Hub side (done):** `ToolCallError.kind` splits **timeout vs tool_error**, and a per-`Hub` **`run_id`** tags every traced call. Injecting the `run_id` into tool-call `args` for true cross-process stitching was deliberately **rejected** — the sibling servers validate strict input schemas and reject unknown properties — so hub correlation is within one session/trace; cross-process stitch to the sibling's `usage_metadata` stays open (see [Status](#status--whats-wired-in)).

### (d)/(g) Skills + agent loop — triggering, cost, quality

- **Cost + "did it fire" — Claude Code native OTel** (`skill.name` token/cost slicing; `tool_decision` with `skill_name`) + **ccusage** for the retrospective dollar figure. This is the zero-code answer.
- **Triggering + output quality (opt-in `evals` extra, periodic, real tokens, never in the offline suite):** **MLflow**'s `agent-eval-skill-invoked` judge is the most on-target ("did the *right* skill load and get followed?"), and it **ingests Claude Code OTel traces** so it doubles as the agent-loop sink. Alternatives: **DeepEval** (pytest-native G-Eval, fits the existing test stack), **Inspect AI** (drives Claude Code itself as the system under test, first-class MCP tools), **promptfoo** (`llm-rubric` to regression-test skill *descriptions*). Whichever you pick, write **rule-based graders that call the repo's own DSP meters** (LUFS / true-peak / tilt) for deterministic audio-correctness, reserving LLM-as-judge for perceptual "right move" grading.
- **The collision check MLflow can't do — an offline, deterministic skill-description embedding-similarity audit.** With **102** skills carrying dense, overlapping descriptions (`drum-mix` vs `song-mix` vs `mix-balance`; the 15+ `vst-*` skills), the real risk is the **wrong** skill firing or two firing. An embedding cosine-similarity matrix over the frontmatter `description` fields flags collisions cheaply, with no LLM and no tokens — it measures the *false-fire* risk that "did the target fire" can't.

### (e)/(f) Workflows + hub code

- **Workflows:** there is **no usable in-script budget surface** to read (correction #3) — measure fan-out cost via **Claude Code OTel `query_source=subagent`** (each agent's tokens nest under the parent trace). The metric that matters is **parallelism gain** (parent span duration vs sum of child spans) and **per-agent success** — including the documented **UADx render non-determinism under concurrency** (parallel agents hammering the same VST plugin produce inconsistent renders; the tuning workflows already warn to re-render the winner serially).
- **Hub:** **extend `_Recorder.run`** with timing (the single highest-leverage hub change); **viztracer** for the asyncio waterfall; promote to the **OpenTelemetry Python SDK** only if you want hub spans correlated with the agent loop in Phoenix.

---

## What to skip (and why), for a local single dev

| Skip | Why |
|---|---|
| **Helicone** | Maintenance mode (acquired Mar 2026); proxy model doesn't fit scattered model calls. |
| **Braintrust, LangSmith** | Closed SaaS; self-host is enterprise-only. (Both *ingest* OTLP, so no lock-in if you ever go hosted.) |
| **Pydantic Logfire (backend)** | SDK is MIT, but self-hosting the backend is enterprise-only — fails the self-host bias. Use the SDK→Phoenix only if you love its DX. |
| **Ragas** | RAG-specific metrics; ship-studios has no retrieval surface. |
| **OpenAI Evals** | Being deprecated in 2026. |
| **Prometheus client, docker-otel-lgtm, IBM ContextForge** | Assume a long-lived scrapeable target / a gateway hop / a 5-service stack — operational overkill for short-lived local runs. Revisit only if ship-studios ever becomes a hosted service. |
| **pytest-codspeed** | Its deterministic mode needs Valgrind (Linux-only); on macOS you'd get only walltime, where pytest-benchmark already suffices. |

---

## Corrections (verified against the repo)

The research synthesis contained several factual errors; these are corrected here and were re-confirmed on 2026-06-03:

1. **The seam is `_Recorder.run`** (`ship_studios/pipelines.py:141`) — there is no `__call__` method.
2. **Counts:** **102** skills (`ls -1d .claude/skills/*/ | wc -l`); **≈240–330** test functions depending on count method (`grep -rE '^\s*def test_' tests/` → 239) — the **"~190 tests" / "~97 skills"** figures in CLAUDE.md prose are **stale**.
3. **No real workflow budget surface:** only `repo-review.js` references `budget`, and only `.remaining()` / `.total` — **never `.spent()`**. Workflow token/cost must come from Claude Code OTel `query_source=subagent`, not from the workflows.
4. **`psutil` on subprocesses needs a process-tree scan:** mcp **1.27.2** `stdio_client` is an `@asynccontextmanager` that `yield`s only the read/write streams — the child process handle is held *inside* the CM and never exposed. There is no supported PID to read in `Hub._open_session`.
5. **`RecordingHub` is a test double:** production timing belongs in `_Recorder.run` / `Hub.call_tool`, not the conftest fakes (extending the fake adds nothing to production telemetry).
6. **Determinism = golden-WAV `np.allclose`**, not an eval framework — drum_prep is seed-free/FFT-based, so a snapshot test is correct and sufficient.
7. **No retry/429 handling exists** anywhere in the hub → it's a *prerequisite* for measuring Gemini quota/error rate, not just resilience.
8. **Timeouts can be `None`:** `config.startup_timeout_s()` (default 120s) and `call_timeout_s()` (default 600s) return `None` when the env var is `0`, which **skips** the `asyncio.wait_for` guard entirely — any latency-vs-budget alarm must read them at runtime, not assume 120/600.

---

## Where the seams are

| File | Seam | Use for |
|---|---|---|
| `ship_studios/mcp_client.py` | `Hub.call_tool` (`def` @156) — the single chokepoint every MCP call flows through | per-call latency, error/timeout split |
| `ship_studios/mcp_client.py` | `Hub._open_session` (`def` @89); `initialize()` timed | handshake / cold-start time + RSS |
| `ship_studios/pipelines.py` | `_Recorder.run` (`def` @141) | per-step pipeline timing (additive) |
| `ship_studios/config.py` | `startup_timeout_s()` / `call_timeout_s()` (can be `None`) | the latency budgets to alarm against |
| `ship_studios/cli.py` | `_run` (54–86) | per-run summary in the emitted JSON |
| `tests/conftest.py` | `FakeSession` / `RecordingHub` | offline-test the additive timing; `tests/test_pipelines.py` ordered-call asserts must stay green |
| `pyproject.toml` | dev group + the `--extra` convention | opt-in `metrics` / `profiling` / `evals` extras |

---

## Next

- The concrete, ordered wiring is in **[roadmap.md](roadmap.md)** (Stages 0–4: zero-code → hub → DSP → Gemini sibling → backend + evals).
- Re-verify the counts/seams (the commands in the corrections section) before publishing or building.
