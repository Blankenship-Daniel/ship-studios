---
name: deploy
description: "Use when the user wants to ship the current work end-to-end — \"/deploy\", \"deploy this\", \"commit push and merge\", \"open a PR and merge it\", \"ship it\", \"land this to main\". Commits all changes, pushes, opens (or reuses) a PR, watches CI to green, then merges into main. CODE/git skill — git + gh only, NO MCP audio tools, no API keys."
argument-hint: "[scope/summary] [--squash] [--no-merge] [--keep-branch]"
---

# Deploy: commit → push → PR → CI-green → merge

Goal: take the work in the current worktree from "uncommitted" to "merged into
`main`" in one ordered pass. **git + `gh` only** — no `stemmy-loops:*` /
`stemmy-gemini:*` tools, no `GEMINI_API_KEY`. Two invariants: **never commit to
`main`; never merge a red or conflicting PR.**

## Prerequisites

- `gh` authenticated for `Blankenship-Daniel/ship-studios` with merge rights
  (`gh auth status`). Remote `origin` (SSH); default branch `main`.
- Runs from a worktree under `.claude/worktrees/<name>/` (usually on a throwaway
  `worktree-*` branch with no upstream). Confirm with `git rev-parse --show-toplevel`.
- "CI green" = the **PR-triggered** checks pass: `test` (Python 3.12 **and** 3.13)
  + `base-deps`. `live-contract` is `workflow_dispatch`/`schedule`-only — it never
  appears on a PR; do not wait on it.
- Mandatory footers: commits end with
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`; PR
  bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## Recipe (ordered)

1. **Survey state (read-only), all before changing anything:**
   `git rev-parse --abbrev-ref HEAD` · `git status --porcelain` ·
   `git log --oneline origin/main..HEAD` (unpushed) ·
   `git rev-parse --abbrev-ref @{u} 2>/dev/null` (upstream?) ·
   `gh pr status` and `gh pr view --json number,state,mergeable 2>/dev/null` (PR
   already open for this branch?). Fetch first if `origin/main` looks stale
   (`git fetch origin main`).
2. **Stop if nothing to deploy:** clean tree **and** no unpushed commits **and**
   no open PR → report "nothing to deploy" and stop. Never create an empty
   commit or PR.
3. **Branch policy — never commit to `main`:**
   - On `main`: create a semantic branch first, e.g.
     `git switch -c fix-drum-prep-foo` (Conventional-Commits-derived kebab name).
   - On a feature branch (`<semantic>` or `worktree-*`): commit there as-is. Do
     **not** rename a worktree-checked-out branch — the PR title/body carry the
     semantics and the repo merges `worktree-*` PRs routinely.
4. **Commit (only if the tree is dirty).** Stage all; one Conventional-Commits
   message synthesized from the diff, with the footer. Use `$'…'` so the blank
   line + footer land correctly:
   ```bash
   git add -A
   git commit -m $'feat(<scope>): <summary>\n\n<why, wrapped>\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>'
   ```
   Pick `feat`/`fix`/`chore`/`docs` and a `<scope>` (e.g. `drum-prep`, `skills`)
   from the change. If the tree was already clean but commits are unpushed, skip to push.
5. **Push:** `git push -u origin HEAD` (sets upstream on a fresh branch; harmless on a tracked one).
6. **PR — reuse or create.** Reuse the open PR from step 1 if present; else:
   ```bash
   gh pr create --base main --title 'feat(<scope>): <summary>' \
     --body $'<what + why>\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)'
   ```
   Capture the PR number/URL.
7. **Watch CI to green.** Checks take a moment to attach after create — a `--watch`
   fired too early errors "no checks reported"; retry once or twice. Then:
   ```bash
   gh pr checks <pr> --watch --fail-fast --interval 20
   ```
   This blocks until checks finish; `--fail-fast` exits on the first failure.
   `live-contract` will not appear. If a PR genuinely has **zero** checks
   (none configured), don't block forever — treat as "no CI gate, proceed (CI not
   applicable)" and say so.
8. **Verify green explicitly (don't trust the exit code alone):**
   ```bash
   gh pr checks <pr> --json name,bucket,state
   ```
   Require `bucket == pass` for `test` (×2) and `base-deps`. Any `fail`/`cancel`
   = red → STOP (step Pitfalls), do not merge.
9. **Merge — only if green** (auto, no confirm; `--no-merge` skips this step and
   reports the green PR instead). Default merge commit:
   ```bash
   gh pr merge <pr> --merge          # or --squash if the user passed --squash
   ```
   Then **clean up the remote branch only** (unless `--keep-branch`):
   ```bash
   git push origin --delete <branch>
   ```
   Do **not** use `gh pr merge -d` from a worktree — git can't delete the local
   branch it has checked out, so `-d` fails mid-cleanup. Leave the local branch
   for the user / `clean_gone`.

## Outputs

No files written by the skill. Side effects: a commit on a feature branch, a
pushed branch, a PR opened→merged, a merge commit on `main`, and the deleted
remote branch.

## Reporting to the user

In order: branch used · commit subject · PR number + URL · CI verdict per check
(`test (3.12)`, `test (3.13)`, `base-deps` → pass/fail) · merge result (merge
commit SHA) · remote-branch-deleted note. On a stop, say exactly why (nothing to
deploy / CI red + the failing check names + log link / merge conflict) and what's
left to do.

## Pitfalls

- **Never merge red or conflicting.** Any `fail`/`cancel` in step 8, or
  `gh pr view --json mergeable` = `CONFLICTING` → STOP, surface the failing
  check(s)/conflict, leave the PR open. Conflict resolution / rebase is the user's call.
- **Worktree branch-delete gotcha.** Never `gh pr merge -d` here; delete the
  remote branch with `git push origin --delete <branch>` and leave the local one
  (it's checked out in this worktree).
- **`live-contract` is not a PR check** — gated to `workflow_dispatch`/`schedule`;
  it won't show in `gh pr checks` on a PR. Don't wait for it.
- **Footers are mandatory.** Use the `$'…'` forms so the blank line + exact footer
  text land. Repo history + reviewers expect both.
- **No wikilinks in this skill** — `scripts/lint_skills.py` fails on any unresolved
  double-bracket link, and no related code-deploy skill exists; name external plugin
  commands (`commit-push-pr`, `clean_gone`) in plain prose instead.
- **After merge the worktree trails `main`.** The skill does not switch the
  worktree's branch (out of scope); just note the drift.
- **Optional local pre-flight (off by default).** Remote CI is authoritative. For
  fast feedback before pushing you may run `uv run ruff check && uv run mypy &&
  uv run python scripts/lint_skills.py && uv run pytest -q` first (needs
  `uv sync --extra drum-prep`); abort the deploy on a local failure.
