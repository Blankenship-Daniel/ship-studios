---
name: harmony
description: "Use after several PARALLEL agent-worktree PRs merged to main and you want to catch cross-PR INTEGRATION problems no single-PR review sees — 'do a harmony review', 'check the recent merges play nicely together', 'review the merge window on main', 'did these parallel PRs break each other', 'integration-review the last N merges', 'are the recent commits coherent'. Scopes to the recent commit window, hunts cross-PR interaction effects (renames vs stale references, name/slug collisions, dep clashes, pipeline/test/doc drift, contradictory prose), and re-runs the deterministic gate on the merged tip to catch union-breakage CI missed. Distinct from the whole-repo /repo-review and the single-dimension audits."
argument-hint: "[--since <ref>] [--window <N>] [--no-gate] [--live] [--fix]"
---

# harmony — integration review of the recent merge window

Goal: confirm the recently-merged changes on `main` **play nicely together**. Many parallel agent
worktrees each open a PR and merge; every PR is green **alone**, but the merged union can still
break — a rename in PR-A leaves a dangling reference added by PR-B, two PRs add the same skill
name, a dep bump breaks new code, one PR reorders a pipeline while another asserts the old order,
or two CLAUDE.md edits land contradictory prose (textually merge-clean). `harmony` scopes to the
recent commit window, **re-runs the deterministic gate on the merged tip** (the union-breakage
check CI can't do per-PR), fans out one read-only agent per integration dimension, adversarially
verifies each finding, and writes a prioritized report.

This is **dev tooling — git + `uv` only, NO audio MCP tools, no API keys.** It is the
window-scoped, cross-PR-interaction sibling of the whole-repo `/repo-review`; hand its report to
`/repo-review-fix` to apply.

## Prerequisites

- Run from the **repo root** with the in-window merges present in `git log` (this is `main`, not a
  feature branch).
- `uv` for the gate — `uv sync --extra drum-prep` so the full offline suite runs. **The gate costs
  a few minutes**; pass `--no-gate` to skip it (you then lose the union-breakage headline).
- Sibling `../stemmy-*-mcp` servers absent is fine — only `--live` touches them and it self-skips.

## Recipe (ordered)

1. **Determine the window** (git). Default = the last `--window 8` merges; or `--since <ref>` (a
   sha / tag / date like `"3 days ago"`). Resolve it to a range:
   `git log --merges -n <N> --format=%H` → oldest in-window sha `S` → `SINCE = S^1` →
   `RANGE = SINCE..HEAD`. (You may run this inline and pass `changedFiles`/`commits`/`prs` into the
   workflow, or let the workflow's Window agent do it — both are supported.)
2. **Run the gate on the merged tip** (unless `--no-gate`): `uv run pytest -q`, `uv run ruff check`,
   `uv run mypy`, `uv run python scripts/lint_skills.py` (+ `SHIP_STUDIOS_LIVE_CONTRACT=1 uv run
   pytest tests/test_pipelines.py -k live` only with `--live`). Capture pass/fail. (Inline, or let
   the workflow's Gate agent do it.)
3. **Invoke the `harmony` workflow** with the scope:
   `Workflow harmony { since, head, window, changedFiles, commits, prs, gateResults, gate, live, fix, out }`
   (omit the pre-supplied fields to let the workflow's own Window/Gate agents produce them). It
   filters the active dimensions against the changed files, composes `/audit-pipeline-lockstep` +
   `/audit-skill-consistency` for the changed pipelines/skills, fans out the semantic dimensions,
   adversarially verifies, and the report-writer agent writes the report.
4. **Confirm `reviews/HARMONY-REVIEW.md`** was written (the workflow's report-writer agent writes
   it — workflow scripts can't touch the filesystem).
5. **Report the verdict** to the user (below).

## Outputs

- `reviews/HARMONY-REVIEW.md` — window header (range + PR list + gate verdict), union-breakage,
  cross-PR interaction findings, single-PR findings, disputed, coverage gaps, method.
- Review-only unless `--fix` (then safe mechanical fixes are applied + an "## Auto-fixes applied"
  section appended).

## Reporting to the user

Lead with the **window header** (range + the in-window PRs) and the **gate / union-breakage
verdict** — that's the headline. Then the cross-PR interaction findings (naming which PRs interact),
then single-PR findings surfaced in-window. End with one line: **integration-healthy** (gate green
+ no confirmed cross-PR criticals/highs) or **integration-broken**, and point at `/repo-review-fix`
(or `--fix`) for the actionable ones.

## Pitfalls

- **Window-scoped, not whole-repo.** harmony reviews only the recent merge window; a pre-existing
  issue untouched by an in-window commit is out of scope — use `/repo-review` for a full sweep.
- **Green per-PR CI ≠ green union.** The whole point is union-breakage; that's why the gate re-runs
  on the merged tip. `--no-gate` is faster but drops the headline check.
- **Rebased / force-pushed history blurs the window.** When merge history is messy, pin the start
  explicitly with `--since <sha/tag>` instead of trusting the last-N-merges heuristic.
- **The delegated audits scan the WHOLE surface.** `/audit-pipeline-lockstep` audits all pipelines
  and `/audit-skill-consistency` is passed only the changed skill dirs; harmony narrows lockstep
  output to the window, so cross-check that a flagged drift is genuinely in-window.
- **The gate is serial by design.** It runs as ONE agent in one env — don't parallelize it (concurrent
  `uv` runs race the venv); the per-dimension review is where the parallelism lives.

## Fan-out

The **per-dimension review is the parallel win**: each integration dimension's analysis over the
changed-file subset is independent → the `harmony` workflow runs one agent per dimension, then
tiered adversarial refuters per finding (exactly like `/repo-review`). The **Gate phase is
intentionally ONE serial agent** (mirrors `/measure-performance`'s honest serial ground-truth
pass) — concurrent gate runs would race the env. The **Window enumeration** is one agent. Two
dimensions delegate to `/audit-pipeline-lockstep` and `/audit-skill-consistency` via the workflow
hook (one nesting level), scoped to the changed pipelines/skills.

## Related

- `/repo-review` (workflow) — the whole-repo code+doc review; harmony is its window-scoped,
  cross-PR-interaction-focused sibling. Feed harmony's report to `/repo-review-fix` to apply findings.
- `/audit-pipeline-lockstep` · `/audit-skill-consistency` (workflows) — the single-dimension drift
  detectors harmony composes, scoped to the merge window.
- `/measure-performance` (workflow) — the serial-ground-truth idiom harmony's Gate phase mirrors.
- [[deploy]] — the git/gh ship skill whose parallel merges produce the window harmony reviews.
- [[delivery-qc]] — the audio-deliverable ship gate; the audio-domain cousin of this dev-integration gate.
- [[batch-master]] / [[stem-process]] — the skill-drives-same-named-workflow twin pattern harmony follows.
