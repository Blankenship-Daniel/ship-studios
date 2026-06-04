# ship-studios — Integration (Harmony) Review

**Date:** 2026-06-04 · **Branch:** `main` · **Scope:** merge window `13794c3..0d485d9` (last 8 merges)

## Executive summary

This is an integration review of the most recent merge window on `main` — eight merged PRs (#53–#60) covering a new ff-stems FabFilter chain recipe, the `kick_beater` robustness change to the VOXBOX stem driver, three new `.claude/` skills (`/deploy`, `/fold-learnings`, `/harmony`) with two companion workflows, a `.claude/` config hardening pass, and a docs fold of session hiss/hum/transient learnings into three skills. The **merged-tip gate is green** — pytest (413 passed, 3 skipped), ruff, mypy, and `lint_skills.py` (107 skills clean) all pass on tip `0d485d9`, and there is **no union-breakage**: nothing that passed in isolation broke once the PRs were merged together. No cross-PR interaction defects were found; all three confirmed findings are single-PR documentation drift at **low** severity (one skill argument-hint drift, two pipeline prose-vs-code abbreviations). No criticals, highs, mediums, disputes, or cross-PR findings.

### Severity totals

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 3 |
| Nit | 0 |
| Disputed | 0 |
| Cross-PR | 0 |

### Window header

- **Range:** `13794c3..0d485d9` (window strategy: last 8 merges to `main`)
- **In-window PRs (sha — title):**
  - `0d485d9` — Merge pull request #60 from Blankenship-Daniel/docs/fold-hiss-hum-learnings
  - `c8d6f09` — Merge pull request #59 from Blankenship-Daniel/claude/focused-maxwell-9fMVX
  - `9b8929e` — Merge pull request #58 from Blankenship-Daniel/feat/harmony-skill
  - `6e7293f` — Merge pull request #57 from Blankenship-Daniel/worktree-noble-moseying-kurzweil
  - `f556967` — Merge pull request #56 from Blankenship-Daniel/feat/fold-learnings-skill
  - `e5ee80d` — Merge pull request #55 from Blankenship-Daniel/worktree-noble-moseying-kurzweil
  - `c4b86b0` — Merge pull request #54 from Blankenship-Daniel/manley-drums-kick-beater-robustness
  - `b24f80e` — Merge pull request #53 from Blankenship-Daniel/worktree-luminous-dreaming-elephant
- **GATE verdict:** **PASS** — union-breakage count: **0**

---

## Union-breakage (merged-tip gate)

**Gate PASSED on the merged tip `0d485d9`, with zero union-breakage.** No cross-PR / gate-union-break findings. Nothing that was green in its own PR went red once the eight PRs were composed on `main`.

The deterministic gate was re-run inline on the merged tip (`uv sync --extra drum-prep`, then `uv run pytest -q` / `ruff check` / `mypy` / `python scripts/lint_skills.py`) — all exited 0:

```text
pytest      : 413 passed, 3 skipped, 1 warning in 8.56s — no FAILED node ids
              (the 1 warning is the expected test_perf read-only-FS perf-disable assertion)
ruff        : All checks passed!
mypy        : Success: no issues found in 25 source files
lint_skills : OK — 107 skills clean (frontmatter, wikilinks, [G]-keyless labels)
live        : not run (live-contract not requested; siblings present but unverified)
```

---

## Cross-PR interaction findings

**None.** No `crossPR:true` findings at any severity. The window's parallel PRs do not break each other: the new skills/workflows (#56, #58, #59) introduce no name/slug collisions with existing skills, the `voxbox_stems.py` `kick_beater` change (#54) is a standalone utility script with no integration into `ship_studios/pipelines.py`, and the docs fold (#60) edits skill bodies that no other in-window PR touches.

---

## Single-PR findings surfaced in-window

These are `crossPR:false` findings — real but single-PR drift surfaced during the window scan. Condensed (`file:line — [SEV] … FIX: …`), consumable by `/repo-review-fix`:

- `.claude/skills/manley-drums/SKILL.md:0 — [LOW] skill drift: argument-hint advertises an optional `[--ref ref.wav]` flag, but `--ref` (and any reference-file plumbing) appears nowhere in the skill body or its driver `scripts/mix/voxbox_stems.py` (which takes only two positional args `<de-bled-stems-dir> <voxbox-out-dir>`); the only reference use is the optional `[G] compare-to-reference` A/B in Stage 4, not wired to a flag. FIX: drop `[--ref ref.wav]` from the YAML argument-hint, or document in the body how `--ref` is consumed.
- `ship_studios/pipelines.py:0 — [LOW] pipeline lockstep drift: batch-master per-track baseline (step 1) — the batch-master PROSE lists only 3 measures before mastering-feedback (measure-loudness + measure-spectrum + check-clipping), but the CODE delegates per track to `master_track` (pipelines.py:359) which runs FIVE (adds measure-stereo + measure-distortion), and the TEST (`test_master_track_sequence`, tests/test_pipelines.py:26-36) pins all five. FIX: reconcile the CLAUDE.md batch-master subsection prose to the five-measure baseline already in code + test (the standalone master-track prose section already lists all five; only the batch-master subsection abbreviates).
- `ship_studios/pipelines.py:0 — [LOW] pipeline lockstep drift: stem-master step-count differs by SCOPE, not drift — PROSE shows 8 numbered steps but steps 6 (drum-prep stem-mix sum) and 8 (master-track hand-off) are explicitly non-MCP downstream stages, so the MCP-call steps are 1-5 + 7; CODE makes 4 unconditional MCP calls and up to 12 with `cross_check`/`corrections` opt-in paths; the ORDERED required sequence matches across prose/code/test. FIX: optional clarity-only — annotate the prose so the opt-in (cross-check / corrective-chain) calls and the non-MCP steps are visibly distinguished from the unconditional core; no behavioral reconciliation needed.

---

## Disputed (needs human judgment)

**None.** No findings carry `status=disputed`.

---

## Minor / unverified

All three confirmed findings above are **low** severity and were marked `verified:false` by the delegated agents (i.e. flagged from reading the sources, not re-executed by an independent verifier in this pass) but `status:confirmed`. They are low-blast-radius documentation/prose drift with no runtime or integration impact — safe to defer or batch into the next `/repo-review-fix`. No nit-level findings. No separate unverified-but-material items.

---

## Coverage & gaps

**Changed files: 20.** Covered: 11 of the 12 logic/doc files; 8 generated artifacts intentionally excluded; 1 utility script covered for conflicts.

- **Covered (skills / workflows / CLAUDE.md / config / .gitignore):** the `skill-doc-semantic-conflict` dimension validated the 7 changed/added `SKILL.md` files (deploy, drum-punch, ff-stems, fold-learnings, harmony, manley-drums) for wikilinks + frontmatter + slugs; `cross-pr-logic-conflict` + `rename-vs-references` checked the 2 new workflows (`fold-learnings.js`, `harmony.js`) and the script-side `voxbox_stems.py` change; `pipeline-lockstep-drift` scope included the CLAUDE.md updates.
- **Single source-code change — `scripts/mix/voxbox_stems.py`** (adds `kick_beater` stem handling + skip-missing robustness, #54): a standalone utility script with no integration into the core `pipelines.py` system, so it falls outside `pipeline-lockstep-drift` scope but was covered by `cross-pr-logic-conflict` (no conflicts with parallel changes).
- **Intentionally uncovered (low-risk, generated artifacts):** 8 VST chain-preset JSONs under `projects/drums-ffchain/chains/` — `drum_overheads.json`, `drum_room.json`, `kick_beater.json`, `kick_in.json`, `plans.json`, `snare_bottom.json`, `snare_top.json`, `unmask.json`. These are committed recipe documentation for the ff-stems workflow (like committed reference audio / preset bundles), not logic code or docs; no cross-file logic implications, no API/interface surface.
- **Dimensions that did not run (not applicable):**
  - `dep-lockfile-coherence` — no lockfiles (e.g. `uv.lock`) changed in the window, so no coherence checks were needed.
  - `gate-failure-triage` — the gate passed, so there were no failures to triage.

---

## Method

- **Window strategy:** last-N-merges — the review scoped to the most recent 8 merges to `main` (`git log 13794c3..0d485d9`), enumerating the in-window PRs (#53–#60) and the union of changed files.
- **Merged-tip gate re-run:** the deterministic gate was re-executed **inline on the merged tip `0d485d9`** (not on each PR branch in isolation) — `uv sync --extra drum-prep`, then `uv run pytest -q`, `ruff check`, `mypy`, and `python scripts/lint_skills.py`. This is the union-breakage catch: CI green on each PR independently does not prove the composed tip is green. All four steps exited 0 (413 passed / 3 skipped; one expected read-only-FS perf-disable warning).
- **Per-dimension fan-out + adversarial verification:** one read-only agent per integration dimension (gate-failure-triage, pipeline-lockstep-drift, skill-doc-semantic-conflict, rename-vs-references, name-slug-collision, dep-lockfile-coherence, cross-pr-logic-conflict), scoped to the changed-file subset + in-window commits, composing the mechanical `/audit-pipeline-lockstep` and `/audit-skill-consistency` drift checks; each candidate finding was then challenged/deduped before inclusion (3 findings survived dedup, dupes folded).
- **Sibling MCP servers:** the sibling `../stemmy-*-mcp` servers were present locally but the live-contract test was **not requested/run** in this worktree, so tool-name/enum existence on the real servers was not asserted this pass; the gate's pipeline↔test lockstep was asserted against the offline `RecordingHub`/`FakeSession` only.

---

**Verdict:** integration-healthy

---

## Auto-fixes applied

Safe, mechanical fixes applied from this review (read-first, minimal edit, re-verified). Judgment / DSP-behavior / tool-call-order / frontmatter-`description` items were left for human review.

- **`.claude/skills/manley-drums/SKILL.md`** (`skill-doc-semantic-conflict#0`, [LOW]) — dropped the unsupported `[--ref ref.wav]` token from the YAML `argument-hint`. The driver `scripts/mix/voxbox_stems.py` takes only two positional args (`<de-bled-stems-dir> <voxbox-out-dir>`) and no `--ref` plumbing exists anywhere in the skill body or CLI; the only reference use is the optional `[G] compare-to-reference` perceptual A/B in Stage 4, which is not wired to a flag. New hint: `argument-hint: <stems-dir> [--platform spotify|apple|youtube]`. Verified: YAML still parses and `scripts/lint_skills.py` reports OK — 107 skills clean.
