---
description: Scaffold a new projects/<slug>/ working directory for a track.
argument-hint: <track name>
---

Invoke the **new-track** skill on `$ARGUMENTS`.

`$ARGUMENTS` is the track name. The skill slugifies it and scaffolds `projects/<slug>/` with `input/`, `mix/`, `master/`, `deliverables/`, and a `notes.md` (name, BPM, key, target platform/LUFS placeholders). Filesystem only — no MCP tool calls. Tell the user where to drop the source WAV and which command to run next (`/mix-check` → `/master`, or `/loops`).
