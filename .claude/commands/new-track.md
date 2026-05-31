---
description: Scaffold a new projects/<slug>/ working directory for a track.
argument-hint: <track name>
---

Invoke the **new-track** skill on `$ARGUMENTS`.

`$ARGUMENTS` is the track name. The skill slugifies it and scaffolds `projects/<slug>/` with `stems/`, `mix/`, `masters/`, `refs/`, `loops/`, `deliverables/`, and a `track.md` (name, BPM, key, target platform/LUFS placeholders). Filesystem only — no MCP tool calls. Tell the user to drop the source WAV in `stems/` (a reference in `refs/`) and which command to run next (`/mix-check` → `/master`, or `/loops`).
