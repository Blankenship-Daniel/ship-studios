---
name: fold-learnings
description: Use when a session uncovered durable lessons and you want them folded back to IMPROVE the repo's own artifacts with what you now know — "save what we learned", "fold these learnings in", "consolidate the session takeaways", "update CLAUDE.md / the skills with what we found", "capture this gotcha", "turn this into a skill", "remember this for next time". Harvests the session's learnings (this conversation first, optionally the transcript JSONL), dedupes against what's already captured, routes each to the artifact it improves — an existing skill body, a new skill (via /create-skill), a workflow, CLAUDE.md, or a user-memory entry — PRESENTS the plan for per-item approval, applies, then verifies with lint_skills.py. Session + local shell; drives the create-skill workflow.
argument-hint: [scope/area hint] [--dry-run|--apply]
---

# fold-learnings — fold session learnings into their durable home

Goal: take what THIS session learned and **improve the repo's `.claude/**` artifacts
with it** — correct/sharpen the skill, workflow, command, or CLAUDE.md it touches, or
persist a fact to the user-memory store when it doesn't sharpen a specific artifact.
The discipline: harvest → **dedupe** against what's already captured → route each
learning to the artifact it improves → **gate on per-item approval** (folding into
shared, always-loaded homes is consequential) → apply → **lint must pass**. The sibling
of `/create-skill` — this one drives it when a learning warrants a brand-new skill.

This is a **dev/meta** skill: it operates *on* `.claude/**`, not on audio. It calls no
DSP tools; it reads the conversation/transcript and writes Markdown/JS.

## When to use / not

- **Use** at the end of a session that produced durable lessons (a plugin behaviour, a
  tool trap, an ordering rule, a measured signature, a preference, a new procedure).
- **Not** for live work mid-task, and **not** to record things the repo already encodes
  (code structure, git history, a fix that's just a commit). If a "learning" is only
  relevant to this one conversation, drop it — durable homes are for reuse.

## Prerequisites

- The **in-context conversation** is the primary, highest-signal source — no tool needed.
- The **user-memory dir** (out-of-repo): `/Users/ship/.claude/projects/-Users-ship-Documents-code-ship-studios/memory/` (+ its `MEMORY.md` index). This path encodes the **main** checkout, not the worktree — always write memory there.
- `uv` available for the verify step (`uv run python scripts/lint_skills.py`).
- Optional transcript (for detail compacted out of a long session) — locate it read-only:
  ```bash
  base="${CLAUDE_PROJECT_DIR:-$(pwd)}"
  project_dir="$HOME/.claude/projects/$(printf '%s' "$base" | sed 's|/|-|g')"
  transcript="${CLAUDE_SESSION_ID:+$project_dir/$CLAUDE_SESSION_ID.jsonl}"
  [ -f "$transcript" ] || transcript=$(ls -t "$project_dir"/*.jsonl 2>/dev/null | head -1)
  echo "${transcript:-no transcript found}"
  ```
  Read it; never pbcopy / move / rename / truncate it (Claude Code is still appending).

## Routing — which artifact each learning improves

First match wins. The action is usually **edit an existing artifact**, not just append.

| Signal of the learning | Home / action |
|---|---|
| Sharpens a recipe **one existing skill** owns (gotcha, prereq, corrected fact, a link) | **Edit `.claude/skills/<n>/SKILL.md`** — a `## Pitfalls` bullet, a `## Prerequisites` line, a corrected step, or a `## Related` wikilink |
| A reusable **multi-step procedure** someone would re-run | **New skill** — drive `/create-skill` (it returns content; the SESSION writes it) |
| A **parallel fan-out / judge-panel / batch / cross-checked** procedure over N items | **New `.claude/workflows/<n>.js`** (+ a thin driving skill + a `## Workflows` row) |
| **Repo-wide doctrine** (spans many skills / the whole pipeline) | **CLAUDE.md**: a `### Rules` bullet · a `### Field notes` gotcha · a `## Combined tool surface` row · a `## Canonical pipelines` step (then `/audit-pipeline-lockstep`) |
| A **measured / tool-specific / session-local** fact, plugin behaviour, approved signature, API/version finding | **Memory entry** (`<kebab>.md` + a `MEMORY.md` line); `type: reference` (durable how-to) or `project` (repo state/decision) |
| A **user preference / feedback** | **Memory** `type: feedback`/`user` — UNLESS it's really a public reusable recipe, then promote to a skill (how `[[warm-drum-bus]]` grew from a preference) |
| A **deprecated** command/flag | Guidance only — do **not** recreate command wrappers (a skill already serves `/name`); fold the note into the owning skill or memory |
| "automate this on every X" (hook/agent) | The repo uses **no hooks and no durable agents** — surface as a *recommendation*; only on explicit request route to a `settings.json` hook (the `update-config` skill) or a new agent, and flag it as a new pattern |

**Mnemonic:** *sharpens one skill → edit its body · a repeatable how-to → new skill ·
N-way parallel → workflow · cross-cutting doctrine → CLAUDE.md · a measured/tool/
session-local fact or a preference → memory.* **CLAUDE.md is injected every turn — keep
it lean**: default a bare fact to memory; promote to CLAUDE.md only when it's genuinely
repo-wide doctrine that every turn benefits from.

## Recipe (ordered)

1. **Harvest** — enumerate what the session learned, from the conversation first
   (surprises, corrected assumptions, measured facts, new procedures, preferences,
   dead-ends). Read the transcript (above) only for detail that scrolled out of context.
   Honor a leading **`scope/area`** arg ("the drum-prep work") to focus the harvest.
2. **Dedupe** — for each candidate, grep before proposing so you don't double-record:
   `grep -ri "<keyword>" <memoryDir>/MEMORY.md`, `grep -n "<keyword>" .claude/skills/<n>/SKILL.md`,
   `grep -n "<keyword>" CLAUDE.md`. Mark each `new` / `update-existing` / `already-captured(skip)`;
   for `update-existing`, append to / correct the existing entry — never a duplicate slug.
3. **Classify + route** — apply the table above. For several candidates, **drive the
   `fold-learnings` workflow** (one agent classifies + re-greps + drafts the exact patch
   per learning, a skeptic challenges each route); for one or two, do it inline. The
   session gathers args inline (`validSkills` = `ls -d .claude/skills/*/`; the CLAUDE.md
   tool surface for `validTools`) and passes the harvested `learnings`.
4. **Present + approve** — show a compact `title → home → exact target` table, then gate
   with **AskUserQuestion** (Approve / Skip / Redirect / Other-free-text) per item, or
   batched. The session owns this — workflows can't prompt. In `--dry-run` (the default)
   **stop here and report the plan**; only `--apply` (or explicit approval) proceeds.
5. **Apply** approved items using the Formats below. For a new skill, drive `/create-skill`
   and **write its returned `content` to the returned `path` yourself** (the workflow
   writes nothing), then `/audit-skill-consistency` it. For a new workflow, hand-author the
   `.js` (mirror `stem-process.js` / `create-skill.js`) + add a `## Workflows` row.
6. **Verify** — after any `.claude/skills/**` write run `uv run python scripts/lint_skills.py`
   (**must pass** — frontmatter, wikilink resolution, `[G]`-keyless labels). Suggest
   `/audit-skill-consistency` (edited/new skills) and `/audit-pipeline-lockstep` (changed
   pipeline prose). **Never run `ruff format`** — the repo is intentionally not
   ruff-format-clean; hand-wrap long lines instead.
7. **Report** — per learning: home → exact path → action taken (or skip/redirect/
   already-captured); the lint result; the audit-workflow follow-ups; and **explicitly
   flag** that memory writes are out-of-repo (local-only, not in the PR) while
   `.claude/**` + CLAUDE.md edits ARE in the PR.

## Formats (match these exactly)

**Memory file** → `<memoryDir>/<kebab>.md`:

```markdown
---
name: <kebab-slug>
description: <one line — what this captures>
metadata: 
  node_type: memory
  type: user|feedback|project|reference
  originSessionId: <the current $CLAUDE_SESSION_ID, or omit if unknown>
---

<terse markdown; bold the load-bearing claim; date facts ("2026-06-04 …");
cross-link sibling memories by slug — memory→memory wiki-links are valid HERE>
```
then append one line to `<memoryDir>/MEMORY.md` (newest at the tail):
`- [<Human Title>](<kebab-slug>.md) — <terse summary; semicolons separate clauses>`

**CLAUDE.md** — match the existing bullet shapes: a Field note
`- **<bold lead-in>** — <gotcha>, <so-what>.`; a Rule `- **<bold imperative>.** <why>.`;
a tool row in the correct `[L]`/`[G]`(+key) sub-table.

**Skill-body edit** — append to the target skill's `## Pitfalls` / `## Prerequisites` /
`## Related`, in house style (terse, imperative, bold the rule). Every new wiki-link
in a SKILL.md must resolve to a real skill dir or docs stem (lint gates this — unlike
memory files, a SKILL.md may **not** wiki-link a memory slug or a workflow name).

## Fan-out

Drive the **`fold-learnings` workflow** when a session yields several candidates — it
fans out one agent per learning to re-grep memory/CLAUDE.md/the target skill, route, and
draft the exact patch, plus a skeptic agent per route ("is this already covered / wrong
home?"). The **session keeps** the three things a workflow can't do: harvesting (only the
session sees the in-context conversation), the AskUserQuestion approval gate, and every
file write (workflows have no filesystem). Go solo (inline) for one or two learnings.

## Verify

`uv run python scripts/lint_skills.py` (CI gate) after any skill write · `/audit-skill-consistency`
on edited/new skills · `/audit-pipeline-lockstep` if a canonical pipeline's prose changed ·
sanity-check that a new `MEMORY.md` line resolves to its file. **Never `ruff format`.**

## Report

A table of learning → home → exact path → action (or skipped/redirected/already-captured);
the lint result; which audit workflows to run; and the in-PR (`.claude/**`, CLAUDE.md) vs
local-only (memory) split of what was written.

## Pitfalls

- **Never write secrets** harvested from the transcript/conversation (API keys, tokens,
  pasted credentials, file contents) into any durable home. Scrub before folding.
- **The memory dir is OUTSIDE the repo** (`~/.claude/projects/...`) → its writes are
  local-only and never appear in the repo PR; don't `git add` it. Say so in the report.
- **Don't fold plugin-provided knowledge into repo `.claude/**`.** Skills from plugins
  (`studio:` / `huggingface:` / `serena:` / `plugin-dev:` …) live under `~/.claude/plugins/`;
  a lesson about one of them is a memory entry (or an upstream fix), never this repo's doctrine.
- **Three distinct encoded dirs:** the memory dir encodes the **main** checkout; repo
  `.claude/**` + CLAUDE.md edits land in the **worktree** cwd (correct — that's the PR);
  the transcript dir encodes the **session cwd**. Don't conflate them.
- **Keyless `[G]` tools** — `find-sibilance` / `find-resonances` / `check-streaming-targets`
  are pure DSP (no key); never write that one needs a Gemini key (lint fails on that).
- **`/create-skill` writes nothing** — it returns `{path,name,content}`; the session writes
  it, then audits. Don't assume the file exists after the workflow returns.
- **Keep CLAUDE.md lean** — it loads every turn; default to memory and only graduate a
  fact to CLAUDE.md when it's truly cross-cutting doctrine.
- **Don't recreate deprecated command wrappers** — a skill already serves `/name`; add a
  `.claude/commands/<short>.md` only as a short alias for a longer skill name.
- **Editing a `## Canonical pipelines` step** can drift CLAUDE.md ↔ `ship_studios/pipelines.py`
  ↔ `tests/test_pipelines.py` — run `/audit-pipeline-lockstep` for that pipeline after.

## Related

No sibling *skills* — this is a dev/meta skill. It drives the `/create-skill` workflow and
is checked by `/audit-skill-consistency` · `/audit-pipeline-lockstep`; `/repo-review` →
`/repo-review-fix` review the whole repo. (Those are **workflows** — referenced as `/name`,
never as wiki-links, which resolve only to skills/docs.)
