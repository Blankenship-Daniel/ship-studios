# Code review — ship-studios

**Date:** 2026-07-31 · **Branch:** `fix/code-review-2026-07` · **Base:** `0ed6d3e`

Whole-repo review across three passes — the MCP hub (`ship_studios/`), the local DSP
(`drum_prep/`), and tests + scripts + packaging. Every finding was verified
empirically against the installed venv and the real sibling servers; the two critical
items were re-confirmed by hand at the source. Findings from the earlier
`REPO-REVIEW` / `ARCHITECT-REVIEW` / `HARMONY-REVIEW` rounds were applied and are
**not** re-reported here — everything below is new.

**Status column:** every finding below was fixed on `fix/code-review-2026-07`, each with
a regression test that fails against the pre-fix code — with ONE exception, L-19, whose
file belongs to another session's uncommitted work and is therefore deliberately left
out of this branch. Gate after the work:
468 passed / 3 skipped, `ruff check` clean, `mypy` clean, `lint_skills` clean.

---

## Summary

| Severity | Count | Headline |
|---|---|---|
| Critical | 2 | Every real Hub teardown raises `RuntimeError`; `phase-align` silently resamples off-rate stems |
| High | 8 | Railed alignment writes wrong audio; relative paths resolve in the sibling repo; two CI gates are defeatable or dormant |
| Medium | 13 | Silent no-ops, output collisions, untested/unlinted `scripts/mix/` |
| Low | 19 | Plumbing gaps, doc drift, vacuous assertions |

The repo is in good shape overall. The offline test contract is real and MCP **error**
paths are genuinely covered (unusual); packaging is correct; and every documented DSP
guardrail is honored in code, not just in docstrings. The two critical bugs both sit in
the same blind spot — behavior that the offline suite structurally cannot observe.

---

## Critical

### C-1 · `ship_studios/mcp_client.py:80` — every real Hub teardown raises `RuntimeError`

`asyncio.gather` wraps each `_open_session` in its own Task. `stdio_client` and
`ClientSession.__aenter__` both enter `anyio.create_task_group()`, so
`stack.enter_async_context(...)` binds anyio's `CancelScope._host_task` to the **gather
child task**. `Hub.__aexit__` then drives `self._stack.__aexit__` from the **parent**
task, and `CancelScope.__exit__` raises:

```
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

Reproduces with a **single** server key — `gather` still creates a Task. The comment at
`:73-79` reasons carefully about `AsyncExitStack` mutation being an atomic list append
and concludes sharing the stack is safe; that premise is correct and irrelevant. The
binding that matters is the *task*, not the stack.

**Failure:** `ship-studios master mix.wav` runs the entire pipeline, produces the
master, then dies at exit with the traceback above and exit code 1 — with the `uv run`
children left un-torn-down.

**Why it shipped:** `tests/conftest.py` patches `Hub._open_session`, and the one test
that stubs `stdio_client` (`tests/test_mcp_client.py:236`) uses a plain
`@asynccontextmanager` with no task group. No test in the suite drives a real
anyio-backed transport. Introduced by `ac7ec48 "perf: apply measured performance fixes"`.

**Status:** fixed — `Hub.__aenter__` now enters both sessions sequentially in its own
task, so every cancel scope is entered and exited by the same task (this also removes
the H-1 rollback race by construction). Cost: two cold `uv run` handshakes sum rather
than overlap, on cold start only. Guarded by
`test_hub_teardown_survives_task_group_backed_transport`, which drives a
task-group-bearing fake transport and reproduces the exact `RuntimeError` against the
old code. Verified live: a real Hub opens both `uv run` subprocesses, calls
`measure-loudness` (−14.41 LUFS on a test tone) and tears down with exit 0 and no
orphaned children.

### C-2 · `drum_prep/phase_align.py:75, 94-95, 126` — off-rate stems are silently resampled

Every stem's sample rate is discarded (`io.read_mono(...)[0]`, `rx, _ = io.read(...)`)
and all writes use the *overhead's* `sr`. `reference_match`, `mix` and `audition` all
call `io.common_samplerate` / `summarize_inputs`; phase-align validates nothing.

**Failure:** a 48 kHz kit with a room mic bounced at 44.1 kHz — the 6.0 s / 264600-frame
room stem is written as a 48 kHz AIFF, i.e. 5.513 s, pitched **+8.8%**, with
`warnings: []`. Because every downstream stage then sees a uniform 48 kHz set, each
passes its own SR check and the corruption is laundered through the rest of the chain.
An off-rate *close* mic is additionally aligned against a time-scaled reference, so the
delay applied to the whole stem is meaningless.

**Status:** fixed — `phase_align` now validates every stem it touches with the existing
`io.common_samplerate` (header-only) and raises before creating any output directory.
Guarded by `test_phase_align_rejects_mixed_sample_rates`.

---

## High

| # | Location | Defect | Status |
|---|---|---|---|
| H-1 | `mcp_client.py:85-91` | Rollback races: `gather(return_exceptions=False)` re-raises without cancelling siblings, so a still-opening session pushes its `stdio_client` CM onto an already-closed stack → orphaned `uv run` subprocess. Verified: `reaped: []`. | fixed |
| H-2 | `cli.py:197` + all `click.Path`; `pipelines.py:1078-1120` | Relative paths reach servers whose cwd is the **sibling repo** (`uv --directory` chdirs the child); every sibling tool schema demands an absolute path. From `~/Music/track/`, `ship-studios master mix/song.wav` makes the loops server resolve against `/…/stemmy-loops-mcp/` — a confusing not-found, or, if a like-named file exists there, the wrong audio processed and the master written **into the sibling repo**. | fixed |
| H-3 | `dsp.py:89-132`, `phase_align.py:85` | A railed `max_lag` returns a plausible bogus lag *and* flips polarity. True lag 880 @ `max_lag=600` → `delay=-541.44, polarity=-1, post_corr=0.437` (vs `-880.0, +1, 1.000` @ 1200). The bad answer is **not** pinned at ±600, so an `abs(d)==max_lag` check would miss it, and `post_corr` is recorded in the result JSON but never thresholded anywhere. The close mic partially cancels the OH. This is the documented ADAT converter-offset gotcha producing wrong audio instead of failing. | fixed |
| H-4 | `mix.py:198`, `stem_mix.py:82` | A stereo file in a non-stereo role keeps only channel 0, but its gain is measured from the mono mean of **both** channels. A stereo `snare top.wav` with L=0.02 and the real signal on R=0.5 reports `gain_db: 0.96, place: center` while sitting ~25 dB low with half the audio discarded. | fixed |
| H-5 | `tune.py:31-36` | The fundamental is a raw Welch bin argmax — no zero-padding, no parabolic interpolation. Measured: 54 Hz kick → 53.33 Hz (−22 c), 52.73 Hz (−41 c); 55 Hz → 56.67 Hz (+52 c). `retune` derives its resample ratio from that, and re-measures with the same coarse method, so the report looks self-consistent while the sample lands ~50 cents off. | fixed |
| H-6 | `phase_align.py:60`, `cli.py:273` | `--out-dir <SRC>` overwrites the original stems in place, contradicting the module docstring's "Non-destructive": a WAV/PCM_16 `snare top.wav` is replaced by AIFF/PCM_24 under the same name. Raw multitracks gone, no prompt. Same shape in `normalize` and `reference-match`. | fixed |
| H-7 | `scripts/lint_skills.py:119` | The CI gate's headline `[G]`-keyless check is suppressed by **any** negation in the ±100-char window, including one belonging to a different tool. Verified against the real predicate: `"This skill requires GEMINI_API_KEY for find-sibilance. Note measure-loudness is pure DSP and needs no key."` → `flagged: []`. That contrast phrasing is idiomatic in this repo, and `lint_skills.py` has **zero** tests. | fixed |
| H-8 | `tests/test_arg_schemas.py:234` | The 323-line arg-schema gate is dormant — it skips unless `tests/fixtures/tool_schemas.json` exists, and that directory does not exist. Nothing anywhere validates the arg *names/types* pipelines emit against real server schemas (`RecordingHub` accepts anything; the live check covers only tool names + four enums). Compounded by `:135` `except Exception: return`, which discards a raising pipeline's calls so the gate stays green even once the fixture lands. | fixed |
| H-9 | `presets/vst/apply_vst_preset.py:65-67` | `set_param` builds `cand` (calling `dist(num(v))`) **before** the `tn is not None` guard → `TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'` on a non-numeric target against numeric `valid_values`. One typo'd or renamed enum label aborts the whole chain render instead of printing the `warn:` line `main():116` promises. Same bug, unguarded, in `scripts/mix/la6176_sweep.py:43`, where it also masks the original `setattr` error. | fixed |
| H-10 | `scripts/mix/warm_bus.py:25`, `tests/test_scripts_mix.py:189-226` | Four tests assert a mirror that never runs in production. `warm_tilt_eq` is imported with `# noqa: F401` and unused; the shipped tilt goes through `apply_eq(phase='zero')` biquads (`:57-60`), a different algorithm from `_core.warm_tilt_eq`'s rFFT magnitude shaping. `test_warm_bus_module_uses_the_core` (`assert wb.warm_tilt_eq is core.warm_tilt_eq`) can only fail if someone deletes the unused import. Flipping `--hs-gain` from `-4.0` to `+4.0` makes the "warm" bus bright with the suite green. | fixed |

---

## Medium

| # | Location | Defect | Status |
|---|---|---|---|
| M-1 | `pipelines.py:373-393` | `batch_master` discards every step of a failed track — `master_track`'s `_Recorder` is local, so when it raises, `res` is never bound and `steps.extend(...)` is skipped. Contradicts the module docstring ("on success AND failure") and `Step`'s ("a failed step is still recorded — it is the one you most want in the trace"). A 3-track batch failing at track 2's `render-mastered` returns track 1 + track 3 + album, and for track 2 only `{"error": str(exc)}` — not its 6 successful measure steps, not the failing one. | fixed |
| M-2 | `pipelines.py:800`, `cli.py:399,447` | An unmatched `--corrections-json` key is a silent, **paid** no-op. Keys are stem names; CLI args are filenames — so `{"kick.wav": {...}}` (the natural mistake) runs zero corrective calls, still fires two `analyze-stem-masking` Gemini calls returning identical maps, and exits 0 with a report implying the unmasking worked. | fixed |
| M-3 | `cli.py:399,447` | `--corrections-json` values are never validated as objects (`_load_json_obj` only checks the top level). `{"kick": ["low cut"]}` → `AttributeError: 'list' object has no attribute 'get'`, raised *after* the Gemini call and the per-stem measures already ran. | fixed |
| M-4 | `pipelines.py:1099-1100` | `_master_out` ignores the source directory, so `--masters-dir out/` collides: `projects/a/mix/intro.wav` and `projects/b/mix/intro.wav` both render to `out/intro.master.wav`. The second silently overwrites the first, `masters` holds the same path twice, and `analyze-album-normalization` measures one file as two tracks. | fixed |
| M-5 | `pipelines.py:930` | `loops_found` is computed *after* the `max_total_loops` slice at `:925`, contradicting its own comment ("captured before the mutation below"). 20 loops with `max_total_loops=5` reports `loops_found: 5`, indistinguishable from a run that found 5. | fixed |
| M-6 | `reference_match.py:66-71` | The coherent sum used to **measure** is truncated to the shortest stem with no truncation note (`mix` and `stem_mix` both emit `io.truncation_note`); the EQ is then applied full-length. 30 s stems plus one 2 s tom → the entire kit's corrective 1/3-octave curve is derived from a 2-second window. `audition.py:52` has the same shape, silently relocating the A/B excerpt. | fixed |
| M-7 | `dsp.py:106` | `max_lag = min(max_lag, nfft - 1)` is the wrong clamp; the alias-free range is `|lag| <= nfft - n`. 64-sample segments with true lag +1 → `estimate()` returns **−127.0** at peak 0.984, identical in magnitude to the correct answer's peak, so nothing distinguishes the ghost. `align_to`'s sign-resolution rescues it, but `phase_align.py:137` calls `dsp.estimate` directly for the ambience polarity decision with no such net. Reachable: `_MIN_OVERLAP=64`. | fixed |
| M-8 | `mix.py:111-121` | A kit with only ONE overhead side falls through the guard (`has_lr` needs both L and R): `has_oh=False, has_lr=False` → no raise → `anchor` falls back to whatever sorts first (e.g. `crash.wav`), so every per-role loudness offset is referenced to a crash mic and the lone OH side is panned dead centre. `resolve_kit` flags it, but the mix CLI uses `strict=False` and `mix_kit` never reads `kit.warnings`. | fixed |
| M-9 | `mix.py:180`, `stem_mix.py:72` | The loudness-match gain is unbounded and unwarned. A room mic 40 dB down gets +40 dB; the single global anti-clip trim then pulls the whole bus down, so the amplified noise floor dominates and every other stem loses headroom. | fixed |
| M-10 | `sub_design.py:37,44-45` | The synthesized sub is free-running (phase 0 at t=0, no phase relationship to the kick's fundamental), so at the default — `sub_hz` on the kick's own fundamental — a near-anti-phase blend **subtracts** low end. `low_60_gain_db` is computed and reported but nothing warns when it is ≤ 0. Separately, `estimate_fundamental` searches [30,120] Hz while `:37` clips to [30,80], so a 100 Hz kick silently gets a detuned 80 Hz beating layer. | fixed |
| M-11 | `presets/vst/probe_plugin.py:110-113` | The "differs from current" fix is inert for enum params — the exact case it was written for. `cur` is `raw_value` (Pedalboard's *normalized float*), compared against `valid_values` **strings**, so `end == current` is never true and `extreme()` always returns `vv[0]` — the default for an enum-default-at-index-0 plugin. Probing default-vs-default yields Δ0 and a false `PASSTHROUGH ✗`. This backstops the entire `vst-*` skill suite and `demo/headless-safe-titles.txt`. | fixed |
| M-12 | `scripts/mix/warm_bus.py:56,61,72` | Intermediates (`src + ".w1.wav"`, `".w2.wav"`) are written next to the user's source and removed only on the happy path, after the plugin load and render. Any failure litters `projects/<t>/mix/` with files the next glob-based stem scan will pick up; two concurrent runs on one source clobber each other. | fixed |
| M-13 | `scripts/snapshot_tool_schemas.py:90,107` | `--out` defaults to the shared fixture regardless of `--server`, and the file is written wholesale — so refreshing one server **deletes** the other's schemas. `test_arg_schemas.py:246` then hits `if not isinstance(server_schemas, dict): continue` and silently validates zero calls for it while `validated > 0` still passes on the other. The gate half-disables itself with no signal. | fixed |
| M-14 | `scripts/mix/*.py` (12+ files) | Hardcoded `/Users/ship/Documents/code/ship-studios` in `voxbox_stems.py:15`, `bb_a5_eq_stems.py:15`, `demucs_debleed.py:25`, `extract_drum_key.py:19`, `gap_mute.py:22`, `vcme_stems.py:17`, and the `*_sweep.py` family; plus `PY = ROOT.parent / "stemmy-loops-mcp/.venv/bin/python"`, which breaks under a git worktree — the very failure `scripts/mcp_launch.py` exists to solve. On any other checkout these fail with a bare `FileNotFoundError` at spawn. | fixed |
| M-15 | `scripts/mix/` | ~3,000 lines with essentially no coverage — `tests/test_scripts_mix.py` covers `_core.py` (127 lines) plus two `is`-identity assertions. All ten famous-drum bus recipes are untested, unlinted (`extend-exclude`) and untyped, and every one is reachable from a shipped SKILL.md. | fixed |

---

## Low

| # | Location | Defect | Status |
|---|---|---|---|
| L-1 | `pipelines.py:119-126` | `_streaming_compliant` drops malformed platform entries, so `[{spotify: true}, {tidal: null}]` → `flags == [True]` → reports full compliance while tidal's verdict is unknown. Should return `None`. | fixed |
| L-2 | `pipelines.py:711-713` | `house_curve` exits 0 with `output == input` when `match-to-profile` returns text instead of `structuredContent`. `matched: false` is present but there is no non-zero exit or warning; a scripted EP loop would "match" every mix to nothing. | fixed |
| L-3 | `cli.py:318` | `_expand_mix_paths` globs `*.wav` only — case-sensitive on macOS, no `.WAV`/`.aiff`/`.flac`. A folder of `.WAV` masters errors with the misleading `no .wav files in <dir>`. | fixed |
| L-4 | `cli.py:339` | `batch-master` cannot reach `--presets`, `--high-pass-hz`, `--transient-shape` or `--assistant`, all of which `master` exposes and `batch_master` forwards. An EP therefore cannot use a non-default export matrix. | fixed |
| L-5 | `config.py:219` | `return None if val <= 0 else val` makes a **negative** timeout mean "wait forever" while the docstring says `0` disables it. `SHIP_STUDIOS_CALL_TIMEOUT=-1` silently removes the timeout instead of erroring. | fixed |
| L-6 | `mcp_client.py:52` | Duplicate server keys aren't rejected: `Hub(["stemmy-loops", "stemmy-loops"])` spawns two subprocesses while `_sessions` keeps only the last — one redundant `uv run` held for the Hub's lifetime. | fixed |
| L-7 | `cli.py:374-456` | `unmask_stems_cmd` and `stem_master_cmd` duplicate ~25 lines (arity check, stem-name dict with dup detection, corrections load). One `_stems_from_paths` helper removes the drift risk. | fixed |
| L-8 | `perf.py:108-112` | `sample_rss` imports `psutil` before checking `SHIP_STUDIOS_PERF_RSS=0`, so the documented opt-out doesn't avoid the import cost. Swap the guards. | fixed |
| L-9 | `dsp.py:186-193` | `band_power` returns `1e-20` (−200 dB) for a band containing no FFT bins, indistinguishable from a genuinely empty band. At a 0.05 s reference the 25/31.5 Hz bands read −197 dB and `tilt()` reports **9.84 dB/oct** vs a true ~3.0. Also feeds `delta`, so those bands take the full `cut_cap` on every stem. | fixed |
| L-10 | `audition.py:74-83`, `cli.py:31-32` | A silent half skips the loudness match (`-inf` LUFS) and `_json_safe` maps `-inf` → `null`, so the operator sees `"lufs_before": null, "gain_db_on_after": null` beside a file that claims to be a loudness-matched A/B. No warning, no non-zero exit. | fixed |
| L-11 | `normalize.py:44-46,60` | `--include` files are written to `out_dir` by basename only, so a basename collision with a `src_dir` file silently overwrites it. Also: `_peak` reads every file in full, then the main loop reads them all again — 2× I/O on a full multitrack. | fixed |
| L-12 | `reference_match.py:112-114` | `--out-dir` may equal `--aligned-dir`. It "works" because all data is in `raw` before any write, but a second run compounds EQ onto already-matched stems with no guard or note. | fixed |
| L-13 | `drum_prep/cli.py` | Plumbing gaps: `chain` exposes no `--boost-cap/--cut-cap/--owner-thresh/--low-zero/--ceil-dbfs` (and `run_chain` doesn't accept them), locking the end-to-end path to ref-match defaults; `mix` exposes neither `--ceil-dbfs` nor `--out-name` despite `mix_kit` taking both; `stereo-merge` and `overheads` expose no `--max-lag` and their defaults disagree (600 vs 200) for the same `align_to` operation. | fixed |
| L-14 | `tests/test_pipeline_lockstep.py:23-24` | The docstring claims a "dropped mandatory step" breaks the gate; it doesn't — a shorter `code_seq` remains an ordered subsequence of the prose. `test_pipelines.py`'s exact-equality does cover drops, so this is doc drift that invites trusting the wrong gate. | fixed |
| L-15 | `benchmarks/test_dsp_bench.py:14-19` | The documented `--benchmark-compare-fail=mean:5%` regression gate is wired into no CI job; `.github/workflows/ci.yml` has no `bench` step and the `bench` extra is never synced. A 3× DSP regression ships silently. | fixed |
| L-16 | `tests/test_scripts_mix.py:35,39` | `_load` permanently mutates global state — `sys.path.insert(0, …)` never popped, and bare top-level names (`_core`, `process_stems`, `warm_bus`) registered in `sys.modules`. Any later `import <name>` matching a `scripts/mix/*.py` filename resolves there for the rest of the session, making `-n auto` differ from serial. | fixed |
| L-17 | `tests/test_perf.py:39-42,63-65` | Two vacuous assertions: `tmp_path` is never wired to `perf`, so the test would pass even if `record()` wrote to a hardcoded path; and `out is None or set(out) == {...}` is trivially true on the base-deps CI leg where `psutil` is absent. | fixed |
| L-18 | `pyproject.toml:63`, `presets/vst/apply_vst_preset.py:32` | `line-length = 100` is a no-op (E501 unselected, `ruff format` unused) but CLAUDE.md:360 presented it as enforced; `_FAITHFUL` is dead in production (`main():130` uses `R.get(..., -1.0)`, so the sentinel could only ever be reached from its own test). | fixed |
| L-19 | `presets/vst/tight-70s-vintage-mix.json:56` | The embedded "Apply:" line points at `tight-70s.json`, not itself — following it applies the wrong preset. | **fix applied locally, NOT committed** — that preset is an untracked file authored by another session, so committing it here would have swept in work this review did not author. The one-line correction is in the working tree; land it with that session's own change. |

---

## Worth preserving

Do not "simplify" these — each is load-bearing and correct:

- **`config.py:243-302` `_resolve_main_root`** — the `.git`-name check *plus* the
  `worktrees/<name>` round-trip containment check is real hardening against a tampered
  `commondir` redirecting `uv --directory`. Rare to see done properly.
- **The `LoopsTool`/`GeminiTool` `StrEnum` registry** — a typo'd or renamed tool becomes
  an import/type-check failure while staying wire-compatible. Spot-checked `match-eq`'s
  bare-`delta_db_curve` mode, `analyze-album-normalization`'s `ceiling_dbtp` and
  `master-assistant`'s `target_platform` against the real sibling sources: all correct,
  and `[L]`/`[G]` routing is right in every pipeline traced.
- **`_run_corrective_chain` injecting `path`/`out_path` last** — a real injection guard,
  correctly ordered, so a user-supplied spec dict can't hijack the chain.
- **`Hub.__aexit__` forwarding `(exc_type, exc, tb)`** into the nested CMs rather than
  `aclose()`, and the timeout relabelling that names *which* sibling stalled.
- **`test_pipeline_lockstep.py`** — a genuinely novel deterministic prose↔code gate, with
  a self-test of its own subsequence helper and a parser-still-works guard.
- **Every documented DSP guardrail is honored in code** (verified, not assumed):
  time-domain coherent sum, `zero_phase_eq` length-preserving to 1e-15 for odd *and*
  even `n`, `trim = min(1.0, ceil/gpeak)` attenuate-only, `align_to`'s three-stage
  envelope→refine→sign design (which recovered the correct lag even where `estimate`
  alone returned an aliased ghost), full-band delay application.
- **`qc.py`** — RIFF `LIST`/`INFO` form-type discrimination, the FLAC block walk, and
  past-EOF guards in all three parsers.
- **`merge_pair`'s read-back verification**, `mix_kit`'s refusal on a raw L/R pair, the
  FX-return dedupe by `realpath`, and measuring the anchor the same way (`to_stereo`)
  as the stems it's compared against — that ~3 dB trap is easy to miss.
- **MCP error-path coverage** in `tests/test_mcp_client.py`: `isError` → `ToolCallError`,
  timeout → `kind="timeout"`, session-not-poisoned-after-error, partial-open rollback,
  mid-call-raise teardown. `FakeSession.list_tools` deliberately returns a shape the
  real SDK returns so a test can't pass against a fiction.
- **Packaging**: the wheel correctly excludes `scripts/`, `presets/`, `projects/`,
  `tests/`; both console scripts resolve; `drum_prep.cli` imports only `click` at module
  level so `drum-prep --help` works on a base sync; the `base-deps` CI job guards
  against the drum-prep leg masking a base-install break.
- **Security posture**: no `shell=True`, argv as lists, no hardcoded keys, an explicit
  `_SERVER_ENV_KEYS` allow-list with truthy-only forwarding.

---

## Systemic note

Both critical bugs live in the same blind spot: **behavior the offline suite
structurally cannot observe.** `conftest.py` patches `_open_session`, so no test drives
a real anyio transport; and no drum_prep test builds a mixed-sample-rate kit. The
highest-leverage durable fix is not any individual patch but closing those two seams —
a task-group-bearing fake transport, and a mixed-rate kit fixture — so this class of
defect fails loudly next time.

Secondary: two CI gates are currently worth less than they appear. `test_arg_schemas.py`
is dormant for want of a committed fixture (H-8), and `lint_skills.py`'s headline check
is defeated by idiomatic repo phrasing and has no tests of its own (H-7).

---

## Behavior changes worth knowing

Most fixes are invisible. These are not:

- **`phase-align` now RAISES on a mixed-sample-rate kit** (C-2) instead of silently
  resampling. Convert upstream, then re-run. It also **skips** (rather than
  mis-aligns) a mic whose true delay lies outside `--max-lag`, naming the value to
  re-run with (H-3) — the ADAT converter-offset case.
- **`phase-align` / `normalize` / `reference-match` refuse `--out-dir` == the source
  directory** (H-6). They were documented non-destructive but would overwrite the raw
  multitrack in place.
- **Every CLI path is resolved to absolute** (H-2). Relative paths previously resolved
  against the *sibling repo*, because `uv --directory` chdirs the server.
- **`mix` / `stem-mix` fold a stereo file in a mono role to mono** rather than keeping
  channel 0 only (H-4), and **cap a loudness-match gain at +24 dB** with a note
  (M-9). Both appear in a new `notes` field.
- **`drum-prep tune`** is now accurate to a few cents rather than ±50 (H-5), so a
  retuned sample lands where you asked.
- **`sub-design`** phase-locks the sub to the kick (M-10). It previously depended on
  the kick's arbitrary starting phase: measured +4.6 dB of low end at one phase and
  **−10.0 dB** (cancellation) at anti-phase.
- **New CLI flags**: `batch-master` gains `--presets`, `--high-pass-hz`,
  `--transient-shape`, `--assistant`/`--intent`/`--intensity`/`--style` (L-4);
  `drum-prep chain` gains the reference-match caps, `mix` gains `--ceil-dbfs` /
  `--out-name`, `overheads` / `stereo-merge` gain `--max-lag` (L-13).
- **A colliding `--masters-dir` basename is disambiguated** rather than overwritten
  (M-4), so `a/mix/intro.wav` and `b/mix/intro.wav` no longer render to one file.
- **`scripts/mix/` and `presets/vst/` are now linted** (M-15) and no longer contain
  hardcoded `/Users/ship/...` paths (M-14) — they work from any checkout, including a
  worktree, via `_core.repo_root()` / `_core.sibling_python()`.
- **`tests/fixtures/tool_schemas.json` is now committed** (H-8), which activates the
  arg-schema gate. Refresh it with `scripts/snapshot_tool_schemas.py`, which now
  MERGES per-server instead of truncating the file (M-13).
