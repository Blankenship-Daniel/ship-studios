# ship-studios — Software Architect's Review

*Method: 9 architect-lens review agents fanned out by dimension, each finding then adversarially
verified against the source (43 agents total). Severities below are the **post-verification**
verdicts. Author cross-checked the hub (`config`/`mcp_client`/`perf`/`pipelines`/`cli`), the
`drum_prep` DSP core, the test seam, and the launch/security surface directly.*

## Verdict

This is a **well-architected, mature codebase** — unusually so for a thin orchestration layer. The
central design bet (a deliberately **DSP-free MCP-client hub** that *mirrors* two server schemas it
cannot import, with CLAUDE.md as the binding contract and a fully **offline** test seam) is sound
and consistently executed. After adversarial verification, **no CRITICAL or HIGH issue survived** —
5 findings were dismissed as invalid/by-design, and the rest are robustness, enforcement, and
DRY/polish items.

The one architectural risk worth real attention is not a bug but an **enforcement gap**: the repo's
defining "everything stays in lockstep" contract is, in CI, enforced only *internally* (code↔test).
The half that guards the hub's actual reason-for-being — that its mirrored tool names/enums match the
real servers — is dormant. Everything else is incremental hardening.

| Severity (verified) | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 4 |
| LOW | 25 |
| INVALID (dismissed on verification) | 5 |

## Architectural strengths (verified, not assumed)

- **Strictly acyclic, leaf-stable layering.** `cli → pipelines → mcp_client/Hub → config`, with
  `config` and `perf` as true leaves (neither imports another `ship_studios` module). This is the
  property that makes the offline test strategy possible.
- **The DSP-free boundary is real and enforced at the packaging layer**, not just by discipline:
  base hub deps are only `mcp` + `click` (`pyproject.toml:9-20`); numpy/scipy/soundfile/pyloudnorm
  are quarantined behind the `drum-prep` extra. Zero DSP imports and zero `import drum_prep` anywhere
  in `ship_studios/`; `drum_prep` has no reverse coupling either.
- **Clean abstraction seam.** `SupportsCallTool` (`pipelines.py:126`) is a structural Protocol the
  real `Hub`, `RecordingHub`, and `FakeSession` all satisfy with no inheritance.
- **Coherent error taxonomy.** `ToolCallError` carries a `kind` discriminator (`tool_error` vs
  `timeout`); `call_tool`/`_open_session` guard *only* the `wait_for` branch so a `TimeoutError`
  bubbling from the tool on the no-timeout path is never relabelled (`mcp_client.py:175-205`). The
  `ExceptionGroup`/`BaseExceptionGroup` peeling in `_run` (`cli.py:39-85`) is correct *and* complete.
- **Leak-proof async lifecycle.** A single `AsyncExitStack` owns transport + session; partial-open
  rolls back and nulls the stack (`mcp_client.py:74-80`); re-entry is guarded. The
  `asyncio.wait_for` × anyio interaction is actually correct (no cross-task cancel-scope error; a
  call-timeout does not poison the session).
- **DSP invariants are each pinned by a targeted regression test** (not smoke tests): coherent vs
  power-sum (~+6 dB on correlated lows), zero-phase EQ preserving prior alignment lag under sloped
  curves, cuts-to-all/boosts-to-owners routing per-band, trim-invariant balance, and a
  pinned-signature determinism test that tolerates BLAS/FFT float noise.
- **Validation-at-the-edge in the CLI.** Every free-form input becomes a clean `click.BadParameter`
  before it can reach a server (`_parse_bars`/`_parse_presets`/`_load_eq_bands`/`_load_json_obj` +
  liberal `Choice`/`FloatRange`/`IntRange`).
- **The dual-server platform vocabulary split is a genuinely sound abstraction**, not a workaround:
  one `--platform` arg → two disjoint server vocabularies via `_feedback_mood`/`_streaming_service`,
  centralized and exhaustively test-parametrized over every `PLATFORM_CHOICES` value.

---

## Theme A — The lockstep "contract" is not actually enforced in CI *(highest leverage)*

The repo's identity is "the hub mirrors a schema it can't import; CLAUDE.md + tests keep everything
in lockstep." The mirror is managed unusually well in places (centralized `PLATFORM_CHOICES`/
`SEVERITY_CHOICES`/`DEFAULT_PRESETS`; a self-collecting live-contract test). But the **enforcement**
of the contract has holes that all point the same way: CI proves the hub is *internally* consistent,
never that it matches the *real servers*.

- **[MEDIUM] The one test that validates tool names + enum subsets against the real servers is
  opt-in and never runs in CI.** `test_live_tool_names_exist_on_servers` is gated on
  `SHIP_STUDIOS_LIVE_CONTRACT` (`test_pipelines.py:1258`), which is set nowhere in `.github/`; CI
  also never syncs the siblings (`ci.yml:28` only `--extra drum-prep`). So a sibling-server tool
  rename or removed enum value passes CI green and fails only at runtime. This is the single
  automated guard against the hub's defining risk — and it is dormant.
  → Add a dedicated/nightly CI job that syncs the siblings and sets the flag; at minimum document it
  as a required pre-release check. (The test already skips cleanly when siblings are absent.)

- **[MEDIUM] The prose↔code half of the three-way lockstep has no deterministic gate.** CLAUDE.md's
  "Canonical pipelines" is verified only by the on-demand `audit-pipeline-lockstep` agent workflow,
  whose **default pipeline list is stale — 5 of 9** (`batch_master`, `house_curve`, `stem_master`,
  `unmask_stems` are absent). `tests/test_pipelines.py` pins code↔test but cannot see the prose.
  → Either update the audit default to all 9 *and* make it a required step, or add a tiny
  deterministic CI check that extracts the `[L]/[G]`+tool sequence from each prose block and asserts
  it equals the `RecordingHub` sequence for the matching function (the collection helper already
  exists at `test_pipelines.py:1158-1246`).

- **[LOW] Tool names are bare string literals scattered across every orchestrator** (`pipelines.py`).
  This is by-design (the hub can't import the schema) and acceptable, but it is the largest latent
  change-amplification cost. → Promote names to a typed `StrEnum` registry in `config.py`
  (`LoopsTool`/`GeminiTool`) imported by both pipelines and the live test. A rename becomes one edit +
  a type error instead of a runtime/audit-only failure — this *strengthens* the verified-surface
  contract, shrinking the lockstep surface from 3 places to 2.

- **[LOW] Two enum allow-lists escaped centralization** — `master-assistant` intent/intensity and
  `match-phase` are inline in `cli.py` with no test or doc guard. → Promote to module constants and
  add them to the live-contract enum-subset checks (`test_pipelines.py:1337-1346`).

- **[LOW] CLAUDE.md's env-var table is a manual mirror of `FORWARDED_ENV`** (the code even says "keep
  in sync"). → A one-line test asserting the documented table ⊇ `FORWARDED_ENV` closes the last
  manual-sync gap.

- **[LOW, by-design] Offline tests never validate arg *values* against a real input schema** — they
  assert keys/order against a `RecordingHub` that accepts anything. → Snapshot live `inputSchema`s
  into a committed fixture and validate emitted args offline (gets schema enforcement without a live
  dependency in CI).

---

## Theme B — Failure-mode design at the batch / long-job boundary

The hub's documented primary use is "batch/CI runs." The serial happy path is clean; the
long-running, many-Gemini-call paths have a few rough failure modes.

- **[MEDIUM] `batch_master` is all-or-nothing.** The per-track loop (`pipelines.py:297-321`) calls
  `await master_track(...)` with no `try/except`; one bad mix / one Gemini 429 / one render failure
  aborts the whole album, the function never returns, and the **cross-track consistency table — the
  documented headline output — never runs**. (Rendered masters do persist to disk, so the operator
  isn't empty-handed, but the in-memory result + album pass are forfeited, and this contradicts the
  `/batch-master` *workflow* sibling, which isolates per-track agents.) → Wrap the per-track call,
  record `{input, master, error}`, `continue`, and run the album pass over survivors — or add an
  explicit `continue_on_error` kwarg. Add a test that one failing track still yields a result.

- **[LOW] `loops_to_deliverables` silently masters the raw input when `find-loops` returns an
  empty/unparseable manifest** (`pipelines.py:806-810`). A genuinely failed extraction is reported as
  a degraded-but-"successful" run. → Distinguish "unparseable shape" from "zero loops" and surface a
  `fell_back: bool` / `loop_count` field so CI can detect it.

- **[LOW] `batch_master` forwards per-track `streaming_compliant` but never aggregates an album
  verdict** — the consistency headline is left for the caller to recompute. → Add an album-level
  summary (compliant/non-compliant/unknown counts + outliers vs median) to the return dict.

- **[LOW] A call-timeout cancels the client wait but sends no `notifications/cancelled`** — the
  sibling subprocess keeps grinding the in-flight tool (a 10-min Demucs/Gemini render) until reaped at
  teardown. Defensible for a one-shot CLI. → Document it in `call_tool`'s docstring + CLAUDE.md's
  timeout note ("set `CALL_TIMEOUT` generously; a timeout abandons but does not abort server work").

- **[LOW] Timeout/cancellation/teardown paths are under-tested** relative to their subtlety. → Add
  offline `fake_hub` tests: post-timeout the same hub still serves a call; a handshake exceeding
  `startup_timeout` raises the relabelled error with the server key; a mid-call raise still triggers
  stack teardown.

---

## Theme C — DSP primitive robustness (latent, benign today)

- **[MEDIUM → leans LOW] `zero_phase_eq` uses un-padded (circular) convolution** (`dsp.py:245`:
  `irfft(rfft(x) * glin, n=n)` with no zero-pad). Empirically confirmed: end-of-buffer energy wraps
  onto the start. It is benign at today's capped ref-match gains (+6/−8 dB) on full-length stems, but
  the safety margin is an **undocumented, untested invariant**, and `fractional_delay` in the *same
  module* (`dsp.py:77`) *does* zero-pad — so this is an inconsistency, not a stated tradeoff. A future
  caller raising `boost_cap` or reusing it on a short loop gets audible edge contamination with no
  failing test. → Document the tradeoff in the docstring, or zero-pad to `n + tail` and crop (mirror
  `fractional_delay`); add an edge-content regression test. The `dsp.py` "do-not-drift" doctrine makes
  the docstring half the cheap, zero-risk fix.

- **[LOW] `fractional_delay`'s dtype-preservation comment is false** — the `rfft/irfft` path always
  returns float64 (`dsp.py:72-83`). Harmless (production is float64-only) but actively misleading in a
  module whose whole premise is verified numerics. → Fix the comment (or cast back to `x.dtype`).

---

## Theme D — Consistency, DRY, and surface polish (LOW)

- **Pipeline result-dicts are an informal, per-pipeline-varying contract** with no typed model — keys
  diverge (`output` vs `masters` vs `corrected`). → A per-pipeline `TypedDict` (or a shared base
  guaranteeing `pipeline`/`steps`/`input`) makes the contract checkable for both CLI and workflow
  callers.
- **Master output-path defaulting is implemented twice with divergent `Path` semantics** —
  `cli._default_master_out` (`pathlib.Path`) vs `pipelines._master_out` (`PurePosixPath`). →
  Consolidate on the `pipelines.py` one.
- **The per-stem corrective chain is duplicated near-verbatim** between `mix_check` and
  `_apply_stem_corrections`. → Factor one ordered chain-spec both consume (tests already pin both
  orders, so the refactor is verifiable).
- **`ship-studios master` silently omits `--presets` / `--max-total-loops`** that its pipeline
  function accepts — a CLI↔pipeline parity gap. → Add them (reuse `_parse_presets`) or document the
  intent.
- **`--platform` overloads two disjoint vocabularies in one Choice** (service vs critique mood).
  Intentional and well-tested, but an ergonomic seam; the `apple`/`apple_music` aliases also both show
  in the visible Choice. → Optional `--service` / `--critique-mood` split, or at least dedupe aliases.
- **`config.py` carries a thin env-passthrough *policy* in an otherwise pure data/leaf module**
  (`_passthrough_env`, `_SERVER_ENV_KEYS`). Verified as **by-design and well-documented** — noted only
  as a boundary to watch, not a defect.

---

## Security posture (verified)

- **`SHIP_STUDIOS_LOOPS_DIR`/`GEMINI_DIR` are an env-var → code-execution surface** (`uv --directory
  <path> run`). This is **documented and accepted** for trusted local/CI use; `checked_server_dir`
  guards misconfiguration, not a deliberately planted `pyproject.toml`, and the code says so. Sound.
- **[LOW] The tampered-`commondir` worktree guard is shallow and untested.** `_resolve_main_root`
  only trusts a resolved path if it's a dir named `.git` (`config.py:209`); a crafted `commondir`
  pointing at an attacker-controlled tree containing a real `.git/` could still redirect sibling
  resolution. Low risk (requires write access to the worktree's git dir), but → add a round-trip
  ownership check or document it as defense-in-depth, plus a regression test feeding a redirecting
  `commondir`.
- **No secret-leak path found.** Keys flow only through `StdioServerParameters.env`, never argv; the
  perf trace records timings/RSS/tool names, never args or env.

---

## Verified and dismissed (so the report is honest about what isn't a problem)

Five findings were rejected on adversarial verification, e.g.: the package `__all__` "under-exports"
the API (false premise — workflows call MCP tools, not these Python functions); `estimate()`
parabolic interp "biases the peak under inversion+noise" (correct-by-design, abs() for magnitude +
signed peak for polarity, test-covered); the tool-name duplication being framed as a *defect* (it's
the deliberate lockstep contract). Several "findings" were really **strength confirmations** (clean
layering; DSP-free boundary; Protocol seam; lazy-import discipline) and are folded into *Strengths*
above.

## Recommended sequence

1. **Wire the live-contract test into CI** (nightly or a dedicated sibling-syncing job) — closes the
   single dormant guard against the hub's defining risk. *(Theme A, MEDIUM)*
2. **Make the prose↔code lockstep deterministic** — extend the audit default to all 9 *and/or* add
   the tiny prose-vs-`RecordingHub` sequence assertion. *(Theme A, MEDIUM)*
3. **Give `batch_master` partial-failure isolation** + an aggregated album verdict. *(Theme B)*
4. **Promote tool names + the stray enums to a typed registry** in `config.py`. *(Theme A, LOW but
   high ROI — shrinks the whole lockstep surface)*
5. **Document/pad `zero_phase_eq`'s circular convolution + fix the `fractional_delay` comment.**
   *(Theme C)*
6. Polish: unify the two `_master_out` helpers, dedupe the per-stem chain, type the result-dicts, add
   the timeout/teardown tests, surface the `loops_to_deliverables` fallback. *(Theme D)*

Items 1–2 are the ones that actually move the architecture; the rest is hardening a structure that is
already in good shape.
