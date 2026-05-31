---
name: new-track
description: Use when the user starts a new project — "new track", "start a new song", "scaffold a project", "set up a working dir for <name>", "make me a folder for the remix". Pure filesystem scaffolding under projects/<slug>/; calls NO MCP tools. Sets up the stems/mix/masters/refs/loops/deliverables layout the other skills read from, then points the user at the next skill.
---

# Scaffold a new track working directory

Goal: create the standard per-track folder layout under `projects/` so every
downstream skill ([[mix-check]], [[master-track]], [[reference-match]],
[[loops-to-deliverables]]) has a predictable place to read inputs from and
write outputs to. This is filesystem-only — **no MCP tool calls**, no audio
processing.

## Prerequisites

None beyond a writable `projects/` directory at the hub root. No servers, no
API keys.

## Recipe (ordered)

1. **Slugify the track name.** Lowercase, spaces → hyphens, strip anything
   that isn't `[a-z0-9-]`. "My New Banger (Remix)" → `my-new-banger-remix`.
   If the name collides with an existing `projects/<slug>/`, suffix `-2`,
   `-3`, … rather than clobbering.
2. **Create the directory tree** under `projects/<slug>/` (the canonical layout
   from CLAUDE.md — downstream skills read these exact names):
   - `stems/` — the user drops the source stems / drum stems / mix WAV here.
   - `mix/` — corrected mixes from [[mix-check]] / [[reference-match]] and
     A/B auditions land here.
   - `masters/` — rendered master from [[master-track]] (plural; "always
     master into `masters/`").
   - `refs/` — reference tracks for [[reference-match]] / compare-to-reference.
   - `loops/` — extracted + processed loop deliverables.
   - `deliverables/` — the exported format matrix (44.1/16, 48/24, 96/24).
3. **Write `projects/<slug>/track.md`** with the track name and placeholder
   fields the other skills consume (sampler-kit, groove-tighten, stem-master,
   drum-punch, stem-split all read `track.md`):
   - Track name, source file (to be filled when dropped in `stems/`).
   - BPM (required by [[loops-to-deliverables]]; ask or leave a placeholder).
   - Key / root note (for tagging deliverables).
   - Target platform + `target_lufs` / `ceiling_dbtp` (for [[master-track]]).
   - A short "next steps" line naming which skill to run.

## Outputs

```
projects/<slug>/
  stems/          ← drop the source WAV / stems here
  mix/
  masters/
  refs/
  loops/
  deliverables/
  track.md
```

Use the Bash tool (`mkdir -p`) and the Write tool for `track.md`. Do not
call any `stemmy-loops:*` or `stemmy-gemini:*` tool — there's nothing to
measure or render yet.

## Reporting to the user

Tell them the exact created path, that the source WAV goes in `stems/` (and a
reference, if any, in `refs/`), and which skill to run next:

- Mix needs fixing first → [[mix-check]], then [[master-track]].
- Mix is already clean → straight to [[master-track]].
- Want it to sound like a reference → [[reference-match]].
- Want a loop / sample pack from it → [[loops-to-deliverables]].

## Pitfalls

- **Don't overwrite an existing project.** Check for `projects/<slug>/`
  first; suffix on collision.
- **No tool calls.** If you find yourself reaching for `measure-loudness`
  here, you've overstepped — this skill only makes folders and a notes file.
- **Relative `projects/`, absolute when writing.** The convention is
  `projects/<slug>/` relative to the hub root; resolve to an absolute path
  for the actual `mkdir` / Write so you don't depend on cwd.

## Related

- [[mix-check]] — first stop once the source WAV is in `stems/`
- [[master-track]] — master a clean mix to a platform target
- [[reference-match]] — match the mix to a reference track
- [[loops-to-deliverables]] — slice the source into a tagged loop pack
- [[understand-audio]] — recon a reference before deciding the target
