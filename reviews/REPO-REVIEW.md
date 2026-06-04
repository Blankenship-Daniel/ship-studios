# ship-studios — Repo Code + Documentation Review

**Date:** 2026-06-03 · **Scope:** all (code + docs) · **Branch:** main (worktree `cheerful-noodling-flame`)

## Executive summary

This review fanned out read-only review agents across the ship-studios hub (`ship_studios/`), the local DSP package (`drum_prep/`), the test suite, and the documentation surface (CLAUDE.md, README.md, `docs/gemini-audio/`, `docs/vst/`, and the skill suite), then adversarially verified every candidate finding. The codebase is healthy — **no critical findings, and all executable code and test files are covered** — but there is a recurring theme of **documentation drift in pipeline/flow counts and per-plugin metadata** (README says "Six pipelines" while the code ships nine; CLAUDE.md over-claims that every drum-prep flow has a skill) and a cluster of **`drum_prep` correctness bugs** (a boolean lost on `kit.json` round-trip, audition LUFS values reported pre-trim, and a `log2(0)` crash guard gap). The single most consequential code issue is a **trust-boundary/config-passthrough gap**: `.mcp.json` does not forward the documented `STEMMY_MCP_ALLOWED_ROOTS` filesystem allow-list (or any other override env var) to the MCP servers when launched interactively from Claude Code, so security/behavioral overrides that work via the CLI are silently dropped. Two findings remain genuinely **disputed** (pipeline-count semantics; the severity of a best-effort bare-except) and are flagged for human judgment.

### Severity totals

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 7 |
| Medium | 9 |
| Low | 10 |
| Nit | 1 |
| **Disputed (subset, needs human judgment)** | 2 |

---

## Code Review

### [HIGH] `.mcp.json` does not forward documented MCP-server override env vars

**File:** `.mcp.json` (env sections: lines 12–15 stemmy-loops, 26–28 stemmy-gemini)

```jsonc
"env": { "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}", "GEMINI_API_KEY": "${GEMINI_API_KEY}" }
```

**Why:** `ship_studios/config.py` documents (lines 68–93, 100–103) that the MCP stdio transport spawns each server with only a minimal safe allow-list (HOME/PATH/…) merged with whatever `StdioServerParameters.env` carries — *"anything we don't forward here is silently dropped"* (config.py:71). The CLI path (`config.server_parameters()` → `_passthrough_env()`) correctly includes the four `GEMINI_OVERRIDE_ENV` vars (`STEMMY_MCP_MODEL`, `STEMMY_MCP_THINKING_LEVEL`, `STEMMY_MCP_THINKING_BUDGET`, `STEMMY_MCP_ALLOWED_ROOTS`) and the five `LOOPS_OVERRIDE_ENV` vars (`STEMMY_LLM_MODEL`, `STEMMY_LLM_CAPTION_MODEL`, `STEMMY_LISTEN_MODEL`, `STEMMY_CACHE_DIR`, `STEMMY_NO_CACHE`). But `.mcp.json` only lists the two API keys, so when Claude Code launches the servers interactively, these documented overrides never reach the subprocess. Most consequentially, `STEMMY_MCP_ALLOWED_ROOTS` is a **filesystem allow-list / security boundary** (CLAUDE.md), and `STEMMY_LLM_MODEL` / `STEMMY_CACHE_DIR` are functional controls — users who set them in their shell get no effect interactively, an asymmetry with the CLI that can cause security/behavioral surprises. (Verifiers split high/medium; kept at high per totals — it crosses a trust boundary and breaks documented behavior.)

**Fix:** Add the documented override vars to both server `env` blocks in `.mcp.json` using the existing `${VAR}` expansion pattern — e.g. for stemmy-gemini add `"STEMMY_MCP_ALLOWED_ROOTS": "${STEMMY_MCP_ALLOWED_ROOTS}"`, `"STEMMY_MCP_MODEL": "${STEMMY_MCP_MODEL}"`, `"STEMMY_MCP_THINKING_LEVEL"`, `"STEMMY_MCP_THINKING_BUDGET"`; for stemmy-loops add `"STEMMY_LLM_MODEL"`, `"STEMMY_LLM_CAPTION_MODEL"`, `"STEMMY_LISTEN_MODEL"`, `"STEMMY_CACHE_DIR"`, `"STEMMY_NO_CACHE"`.

---

### [HIGH] `ambience=false` is lost on `kit.json` serialization

**File:** `drum_prep/kit.py:69` (filter at line 71; reload at lines 204–205)

```python
"ambience": s.ambience or None,
...
# line 71 filter drops keys whose value is None
if v is not None
```

**Why:** When `s.ambience` is `False`, `False or None` evaluates to `None`, and the line-71 filter then drops the `ambience` key entirely from the serialized dict. This breaks round-trip serialization: a kit with an explicit `"ambience": false` loses that setting on save → reload (the reload `setattr` at line 205 never runs because the field is absent from the JSON entry). A user who sets `ambience` on a stem and saves via `drum-prep detect --write-manifest` silently loses it. (Confirmed 2/2, including a reproduction.)

**Fix:** Preserve the not-set (`None`) vs explicitly-false (`False`) distinction — e.g. serialize `ambience` only when truthy *or* special-case bools in the filter (`if v is not None or isinstance(v, bool)`), rather than collapsing `False` to `None`.

---

### [HIGH] `estimate()` crashes on empty arrays via `log2(0)`

**File:** `drum_prep/dsp.py:91`

```python
nfft = 1 << int(np.ceil(np.log2(2 * n)))
```

**Why:** When `n == 0` (both input arrays empty), `np.log2(0)` returns `-inf`, `np.ceil(-inf)` stays `-inf`, and `int(-inf)` raises `OverflowError: cannot convert float infinity to integer` (reproduced directly). Production call sites in `phase_align.py` (lines ~78–84, 98–99, 131–136) guard against empty excerpts via `_excerpt_overlap()` returning `ok=False`, so this is largely unreachable in the main flows; `stereo_merge.py:139` and `overheads.py:41` call `align_to()` without explicit guards but are protected in practice (files read from disk are non-empty). It remains a defensive-programming gap in a core numerical primitive. (Verifiers leaned "medium in practice"; kept at high per totals — it is an unguarded crash in shared DSP.)

**Fix:** Add an early guard before the `nfft` computation (and before the line 88–89 mean ops to avoid NaN warnings): `if n == 0: return 0.0, 0.0`.

---

### [HIGH] `Hub` async context manager allows reentry → subprocess/resource leak

**File:** `ship_studios/mcp_client.py:62` (`__aenter__` lines 61–73; `__aexit__` 75–79)

```python
self._stack = contextlib.AsyncExitStack()
```

**Why:** If `__aenter__` is called on an already-entered `Hub` instance, this line unconditionally overwrites `self._stack` without closing the previous one — losing the reference to already-opened sessions and leaking the stdio subprocesses they hold. There is no reentry guard, and no test exercises reentry (`tests/test_mcp_client.py` only tests single entry). Standard `async with` usage (and `open_hub()`, which creates fresh instances) is safe; the leak only occurs on deliberate instance reuse in nested contexts. (Confirmed 2/2, with a reproduction; verifiers noted low practical risk but the fix is sound.)

**Fix:** Guard at the top of `__aenter__`: `if self._stack is not None: raise RuntimeError("Hub is already open")` (or implement refcounting if nesting is intended).

---

### [MEDIUM] `audition.py` reports pre-trim LUFS for the before/after pair (files are post-trim)

**File:** `drum_prep/audition.py:135` (measure/trim in `_prep_pair`, lines ~70–74)

```python
auditions.append({"name": "before-vs-after", "path": path_a, "seconds": round(dur_a, 1),
                  "lufs_before": round(lb, 2), "lufs_after": round(la, 2),
                  "gain_db_on_after": round(lb - la, 2)})
```

**Why:** `_prep_pair()` measures integrated loudness (`lb`, `la`) **before** applying the anti-clip trim, but the arrays written to disk (`bA`, `aA`) are **post-trim**. When the trim fires (peak > ceiling, e.g. matching a quiet half up to a loud one, 1–2+ dB), the reported `lufs_before` / `lufs_after` no longer match the actual files. The existing test only checks inter-half matching consistency, not absolute accuracy vs the reported numbers.

**Fix:** Apply the trim offset to the reported values: if `trim != 1.0`, `trim_db = 20*log10(trim)`, and report the measured loudness `+ trim_db`.

---

### [MEDIUM] Gemini compare halves report pre-trim loudness

**File:** `drum_prep/audition.py:154`

```python
halves = {"reference": ref_h, "after": aft_h, "lufs": round(lr, 2),
          "note": "loudness-matched; feed to compare-to-reference ..."}
```

**Why:** Same root cause as above — the reported `lr` is the pre-trim reference loudness, but the `cmp_reference.wav` / `cmp_after.wav` arrays written at lines 152–153 are post-trim. Feeding these to `compare-to-reference`, the actual loudness differs from the reported value by the trim amount (~`20*log10(f)` dB).

**Fix:** Include the trim offset in the reported LUFS: report `lr + trim_db` when a trim was applied.

---

## Documentation Review

### [HIGH] README says "Six pipelines" but the code implements nine

**File:** `README.md:148` (and the contradicting claim at `README.md:217`)

```text
"Six pipelines, each available as a Claude Code skill/command and (where it processes audio) as a CLI subcommand."
```

**Why:** `ship_studios/pipelines.py` implements nine `async def` pipelines (`master_track`, `batch_master`, `mix_check`, `reference_match`, `house_curve`, `stem_master`, `unmask_stems`, `loops_to_deliverables`, `understand_audio`), and CLAUDE.md:410 correctly says "nine pipeline subcommands". The README's `## Pipelines` section documents only six (master-track, mix-check, reference-match, loops-to-deliverables, understand-audio, new-track), omitting `batch-master`, `house-curve`, `stem-master`, and `unmask-stems` — a user-facing understatement of the capability surface. (Confirmed 2/2.)

**Fix:** Change README:148 "Six pipelines" → "Nine pipelines"; add sections for `batch-master`, `house-curve`, `stem-master`, and `unmask-stems`; and update README:217 "Unlike the six pipelines above" → "nine".

---

### [HIGH] CLAUDE.md claims `kit.json` file fields "need the `.wav` extension" — contradicted by code and example

**File:** `CLAUDE.md:261`

```text
`kit.json` file fields need the `.wav` extension
```

**Why:** The code accepts four extensions — `drum_prep/kit.py:17` defines `AUDIO_EXTS = (".wav", ".aif", ".aiff", ".flac")`, lines 80–85 filter by that set, and lines 170–171 validate against on-disk existence, not a `.wav` requirement. The shipped example `drum_prep/examples/kit.json` uses **only `.aif`** files. The doc statement is false and will mislead developers into an unnecessary restriction. (Confirmed 2/2.)

**Fix:** Replace with "`kit.json` file fields must match actual audio files in the directory (supports `.wav`, `.aif`, `.aiff`, `.flac`)", or drop the prescriptive sentence since the code validates against files on disk.

---

### [HIGH] Broken SECURITY.md link points to bare `https://github.com/`

**File:** `docs/gemini-audio/README.md:72`

```text
writes audio ([SECURITY.md](https://github.com/) of that repo)
```

**Why:** The link target is `https://github.com/` with no repository path — unclickable and misleading. The intent is the SECURITY.md of the sibling `stemmy-gemini-mcp` repo (which documents the read-only invariant). The parallel reference in `speech-generation.md:79` handles this correctly with a bare `[SECURITY.md]` reference instead of a broken URL. (Confirmed 2/2; one verifier suggested medium since it is reference docs, but kept at high per totals.)

**Fix:** Point to the real location — `[SECURITY.md](../../stemmy-gemini-mcp/SECURITY.md)` for the sibling layout, or a full GitHub URL such as `https://github.com/ship-studios/stemmy-gemini-mcp/blob/main/SECURITY.md`.

---

### [HIGH] `manley-massive-passive` skill description is bare/incomplete in the skill index

**File:** `(skill system reminder)` — also affects sibling `manley-variable-mu`, `manley-voxbox`

```text
manley-massive-passive   (appears as a bare name, no descriptive text)
```

**Why:** The three Manley skills surface with **no description text** in the skill index, unlike the 80+ other skills that each carry a "measured deep-dive of [[vst-…]] … grounded in docs/vst/<plugin>.md" blurb. (The `SKILL.md` files themselves — e.g. `.claude/skills/manley-massive-passive/SKILL.md:3` — contain complete descriptions, so the drift is between the SKILL.md frontmatter and what the index shows.) An agent relying on the index can't tell what these skills do or when to reach for them. (Confirmed; the verifier noted the quoted "truncated" evidence text differs from reality — the entries are fully bare, not truncated — but the underconfirmed-description issue is real.)

**Fix:** Ensure the three Manley skills' descriptions match the suite pattern, e.g. for massive-passive: "The measured, plugin-specific deep-dive of [[vst-eq]] / [[vst-master]] — grounded in the real 51-param Pedalboard surface + gain/bw/freq isolation / shelf-overshoot / parallel-non-additivity measurements in docs/vst/manley-massive-passive.md. Stemmy MCP, the `vst` extra. UADx native (no iLok)."

---

### [MEDIUM] `unmask-stems` pipeline has no dedicated Canonical-pipelines section

**File:** `CLAUDE.md:180`

```text
unmask-stems is the masking-only subset (steps 2 + 4 + re-score), when you don't need the sum or master.
```

**Why:** `unmask-stems` is a real, tested, CLI-exposed pipeline (`pipelines.py:688`, `cli.py:354`, `test_unmask_stems_sequence`) but appears in CLAUDE.md only as an inline note inside `stem-master`, while every other pipeline gets its own `###` section with an ordered tool-call recipe. Readers won't discover it via the Canonical-pipelines block.

**Fix:** Add a dedicated `### unmask-stems — masking-only subset of stem-master` section after stem-master with the ordered recipe: `analyze-stem-masking` (initial map) → optional `detect-masking` cross-check → per-losing-stem `apply-eq` / `apply-dynamic-eq` → `analyze-stem-masking` (re-score); note it skips per-stem baseline, tone shaping, summing, and mastering.

---

### [MEDIUM] CLAUDE.md drum-prep "Flows" header over-claims that every flow has a skill

**File:** `CLAUDE.md:422`

```text
### Flows (each a `/drum-*` skill + `drum-prep` subcommand)
```

**Why:** Only 8 of the 14 listed flows have a `/drum-*` skill (audition, mix, normalize, phase-align, prep/chain, reference-match, stereo-merge, tune). Six are CLI-only with no skill: detect (1), overheads (3), analyze (6), stem-mix (11), sub-design (12), verify-tags (14). README:237–238 correctly qualifies this; CLAUDE.md's blanket header does not.

**Fix:** Change the header to "### Flows (each a `drum-prep` subcommand; selected flows also have `/drum-*` skills)" or enumerate which flows have skills.

---

### [MEDIUM] gemini-audio README lists 11 perceptual tools; the authoritative table has 12

**File:** `docs/gemini-audio/README.md:68` (authoritative table: `docs/gemini-audio/audio-understanding.md:24`)

```text
11 Gemini perceptual tools
(transcribe, describe-region, compare, classify, extract-events, summarize-long, audio-to-json,
analyze-mix-balance, detect-mix-issues, compare-to-reference, mastering-feedback)
```

**Why:** The `audio-understanding.md` table's "Perceptual mix/master critique" row includes `recommend-mastering-chain`, which the README's count and parenthetical omit — a factual inconsistency with the authoritative source.

**Fix:** Change "11" → "12" and add `recommend-mastering-chain` to the list, or clarify the README is showing "11 core tools" and note `recommend-mastering-chain` separately (option 1 preferred for consistency).

---

### [MEDIUM] API Vision Channel Strip guide omits the param count its shard siblings all state

**File:** `docs/vst/api-vision-channel-strip.md:38`

```text
### The real parameter surface (Pedalboard-exposed — authoritative)

Six API modules in series.
```

**Why:** Every other plugin guide in the shard states an explicit total param count in the TL;DR or the param-surface heading (e.g. fabfilter-pro-l-2: 37; fabfilter-saturn-2: 956; hitsville-eq-mastering: 53; ssl-native-channel-strip-2: 51; vibe-analog-machines: 6). API Vision enumerates ~43–52 params but never states the total, breaking the shard's pattern.

**Fix:** Add the count to the heading, e.g. "### The real parameter surface (Pedalboard-exposed — authoritative; 30+ params)".

---

## Disputed (needs human judgment)

### [DISPUTED → HIGH claim] CLI documents nine pipelines; Canonical section documents only seven MCP pipelines

**File:** `CLAUDE.md:410` · confirmed 1 / refuted 1

```text
The nine pipeline subcommands (`master`, `batch-master`, `mix-check`, `reference-match`, `house-curve`,
`stem-master`, `unmask-stems`, `loops`, `understand`) each map to the matching function in `ship_studios/pipelines.py`
```

**The dispute:** Line 410's claim is **factually correct** — all nine CLI subcommands exist and map to real `pipelines.py` functions. One verifier therefore refutes the finding: there is no factual error at line 410. The other reads it as a documentation-coverage issue: the "Canonical pipelines" section (lines 136–232) gives dedicated `###` subsections to only seven MCP pipelines, with `house-curve` and `unmask-stems` documented only inline (variants of reference-match / stem-master). This is the same coverage gap captured by the two "missing dedicated section" findings below — whether it also constitutes a "drift" at line 410 is the judgment call. **Recommendation:** treat as a documentation-organization issue (add the two missing subsections), not a factual error at line 410.

### [DISPUTED → HIGH claim] Bare `except Exception` swallows audio-read errors in `_try_samplerate`

**File:** `drum_prep/kit.py:95` · confirmed 1 / refuted 1

```python
        except Exception:
            continue  # try the next stem rather than giving up on the first failure
    return None
```

**The dispute:** The bare `except Exception` does swallow `soundfile.info()` errors (missing/corrupt/permission) and returns `None` with no warning — poor observability and an over-broad catch. But verifiers found `Kit.sr` is **dead metadata**: assigned at kit.py:146, never serialized in `to_dict()`, never tested, and never read by any downstream flow (real sample-rate errors surface later via `io.common_samplerate()` / `resolve_overhead()`, which do propagate). One verifier downgrades to "nit" on that basis; the other keeps it medium for the missing-warning observability gap; the function is explicitly documented as best-effort graceful degradation. **Recommendation:** narrow the catch to `(OSError, soundfile.LibsndfileError)` and log a warning when all stems fail; severity is medium-at-most given the field is currently unused.

---

## Minor / unverified

- **[LOW] `house-curve` missing dedicated Canonical-pipelines section** — `CLAUDE.md:207`; documented only inline within reference-match. It is discoverable (CLI examples, `[[house-curve]]` link, the 9-subcommand list); add a `### house-curve` section for parity (`build-target-profile` → `match-to-profile` → `match-eq`). *(Confirmed; downgraded to low — content exists, only organization.)*
- **[LOW] Hitsville EQ Mastering: speed-switch inertness wording reads as surprising** — `docs/vst/hitsville-eq-mastering.md:34`; the "did (→ 414 Hz)" example is correct (414 Hz is the half-speed center of the 400 Hz set) but ambiguous because the table only shows Normal-speed centers; clarify the phrasing. *(Confirmed; clarity only.)*
- **[LOW] Vibe Analog Machines: TONE/WARBLE second-knob split not emphasized in TL;DR** — `docs/vst/vibe-analog-machines.md:43`; the split *is* stated at TL;DR point 3 and in Footgun 1, so info is present; finding is an emphasis suggestion. *(Confirmed; minor.)*
- **[LOW] README lists 5 "core" drum-prep flows vs CLAUDE.md's 14** — `README.md:236`; intentional ("run `drum-prep --help`"), but a README-only reader misses detect/stereo-merge/normalize/analyze/mix/stem-mix/sub-design/tune/verify-tags; consider a one-line pointer to the full list. *(Unverified.)*
- **[LOW] `batch-master` SKILL.md "six lifecycle stages" reference** — `.claude/skills/batch-master/SKILL.md`; ground truth says 6-stages-vs-5-pipelines is *not* drift; the skill correctly loops `master_track` per track. No fix needed. *(Unverified.)*
- **[LOW] `drum-stems-warm-loops` Gemini-mono phrasing** — `.claude/skills/drum-stems-warm-loops/SKILL.md:61`; "Gemini hears ~16 kbps MONO" is sound guidance; consider "hears mono at ~16 kbps compression" for clarity. *(Unverified.)*
- **[LOW] `fabfilter-pro-mb` skill doesn't restate the "156 params" count** — `docs/vst/fabfilter-pro-mb.md:34`; doc is internally consistent (6×21 + 30 = 156); skill says "real param surface" without the number. Optional. *(Unverified.)*
- **[LOW] `pultec-meq-5` skill param count** — `docs/vst/pultec-meq-5.md`; skill *does* say "10 params" inline; consistent, **no issue found**. *(Unverified.)*
- **[LOW] `studer-a800` date-stamped inline fact-check note** — `docs/vst/studer-a800.md:25`; not an error, but a "Verified 2026-06-03" research-note style claim that could read as stale later; consider moving into a Sources/Verification block. *(Unverified.)*
- **[LOW] `test_loops_to_deliverables_processes_every_loop` checks counts, not per-loop args** — `tests/test_pipelines.py:643`; verifies call counts and the result list but not that each `clean-loop`/`render-mastered` got the correct per-loop path; a future bug processing one loop 3× would still pass. Add a per-call-arg assertion. *(Unverified.)*
- **[NIT] `dbx-160` "8 knobs" vs 12-param assertion** — `docs/vst/dbx-160.md:1`; on inspection the doc and skill correctly state 8 params; **no discrepancy** (the 12 was an initial-assessment error). *(Unverified.)*

---

## Coverage & gaps

**Files covered:** All 25 code files (19 `drum_prep/` + 5 `ship_studios/` + `ship_studios/__init__.py`) and all 24 test files were reviewed. No gaps remain in executable code or test coverage.

**Intentionally out of scope (9 files):** `.claude/commands/{loops,master,understand}.md` (command config), `demo/installed-plugins*.md` (reference artifacts), `presets/vst/README.md` (preset data), `projects/{ship-studios-drums,watercolors}/track.md` (project examples), and `reviews/REPO-REVIEW.md` (this report).

**Dimension gaps (require specialized passes beyond the unit structure):**
- **Integration testing** — no dedicated unit for cross-module interaction.
- **Error-path edge cases** — only partial; signal handling and cleanup paths not explicitly audited.
- **Performance / scalability** — no review of DSP complexity, memory on large files, or throughput.
- **Deployment / DevOps** — no CI/CD-readiness, `.mcp.json` validation, or environment-setup audit (note: the top `.mcp.json` finding touches this area).
- **CLI UX** — help text and user-facing messaging not thoroughly reviewed.
- **Type completeness** — no mypy/pyright pass; return-type consistency not exhaustively checked.

---

## Method

This review was produced by the **repo-review workflow**, which fans out read-only review agents by dimension — code: DSP numerics (`drum_prep/dsp.py`), async safety (`ship_studios/mcp_client.py`), silent failures, security/trust boundaries, test coverage; docs: CLAUDE.md contract drift, wikilink/twin integrity, pipeline-order lockstep, and `vst`/`gemini-audio`/skill consistency.

Each candidate finding was **adversarially verified** by independent confirm/refute passes against the actual files (with reproductions for the code bugs), and severities were adjusted from the verifier consensus. Findings that one verifier refuted are surfaced explicitly in **Disputed**; findings collected but not independently re-verified are condensed into **Minor / unverified**. Counts above reflect the verified, de-duplicated finding set.

**Environment caveat:** This worktree (`.claude/worktrees/cheerful-noodling-flame`) intentionally does **not** contain the sibling MCP servers (`../stemmy-loops-mcp`, `../stemmy-gemini-mcp`) — they are absent here by design. Findings that reference server behavior (e.g. env-var forwarding, the `SECURITY.md` of stemmy-gemini, tool-surface claims) were verified against this repo's own contracts (CLAUDE.md, `ship_studios/config.py`, `.mcp.json`, tests) rather than the live servers; the servers themselves were not run.
