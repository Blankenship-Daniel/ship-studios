---
name: logic-extract
description: Use when the user wants the raw recordings out of a Logic Pro project — "get the stems out of Logic", "pull the raw tracks from my Logic project", "where are my Logic audio files", "I have a .logicx, extract the multitrack", "grab the untrimmed recordings before processing". Copies the original per-input recordings out of the project package into the workspace, organized by take, without ever mutating the package. Filesystem + ffprobe/afinfo only — no MCP servers. Hands off to [[multitrack-triage]].
argument-hint: <path/to/Project.logicx>
---

# Extract raw recordings from a Logic Pro project

Goal: get the **original, pre-processing recordings** out of a Logic project and
into a clean workspace folder, **without touching the project**. This is the
front door before [[multitrack-triage]] → [[drum-prep]]. Filesystem + read-only
probing only — no `stemmy-*` tools, no DSP.

## Raw recordings vs "stems" — get this right first

Two very different things; ask which the user means:

- **Raw recordings (this skill).** The actual files captured during tracking,
  fully intact and untrimmed — Logic edits (trim/comp/fade) are *non-destructive*,
  so the source files are never altered. They live **inside the project package**.
  This is what you want for re-mixing from scratch, phase-alignment, or archival.
- **Processed/edited stems.** What you hear on the timeline (edits + plugins +
  automation). Those don't exist as files until the user does
  **File → Export → All Tracks as Audio Files** in Logic (with *Bypass Effect
  Plugins* ON for dry stems). The hub can't trigger that — it's a Logic UI action.

If they want the timeline result, point them at the Logic export. If they want
the true source captures, continue here.

## Prerequisites

- Path to the `.logicx` project (a package) or a project folder.
- Enough disk for a copy — raw multitrack sessions are multi-GB.
- `ffprobe`/`afinfo`/`sox` for read-only probing (all present on macOS + brew).

## Recipe (ordered)

1. **Locate the audio.** Inside the package:
   `"<name>.logicx/Media/Audio Files/"` (older projects: `Audio Files/` at the
   package or folder root). A `.logicx` is a macOS package — list it directly
   (`ls "<name>.logicx/Media/Audio Files"`); in Finder it's right-click → Show
   Package Contents. If files are missing, they may be referenced elsewhere —
   Logic's **File → Project Management → Consolidate / Find Missing** is the fix
   (a user action).
2. **Inventory before copying.** `afinfo`/`soxi` each file for sample rate,
   channels, duration. Note the naming: Logic names by **interface input**, not
   instrument (`A ADAT 1`, `A MIC_LINE 5`, `B MIC_LINE_HIZ 1_2`, …). The
   `#01/#02/#03` suffix is the **take / record pass**; `... merged` / `merged_1`
   are Logic punch/cycle artifacts (sub-fragments of a take — not separate
   sources).
3. **Copy out, never move.** Copy into `artifacts/<slug>-raw/` (gitignored
   scratch). Use `cp -p`. Leave the package byte-for-byte intact — Logic
   references these files by name+location, so renaming/moving in place breaks
   the project ("missing audio" on next open).
4. **Organize by take** while copying: group files sharing a `#NN` pass into
   `take-NN/`, strip the take number from the filename, replace spaces with
   underscores (`A ADAT 1 #02.wav` → `take-02/A_ADAT_1.wav`). Put the
   `merged`/`merged_1` artifacts in a `take-NN-merge-fragments/` subfolder — keep
   them, don't mix them with clean takes.
5. **Verify the copy** is complete and faithful: file-count and total-bytes match
   the source; the package still has all originals.

## Outputs

```
artifacts/<slug>-raw/
  take-01/  take-02/  ...        # one folder per record pass, underscore names
  take-NN-merge-fragments/       # Logic punch/cycle artifacts, set aside
```

Use Bash (`cp -p`, `mkdir -p`) + read-only `afinfo`/`soxi`. Do not call any
`stemmy-loops:*` / `stemmy-gemini:*` tool here.

## Reporting to the user

State the exact destination, the file-count / byte parity vs source, and confirm
the package is untouched. Summarize what you found: how many takes, the input
naming scheme, sample rate/bit depth, and any merge-fragments set aside. Then
hand off: "run [[multitrack-triage]] on `artifacts/<slug>-raw/` to clean, split
songs, drop dead channels, and label roles."

## Pitfalls

- **Never mutate the package.** Copy out; the `.logicx` is the master.
- **Interface names ≠ instruments.** Don't assume `ADAT 1` is overheads — role
  ID happens in [[multitrack-triage]], with the user confirming.
- **Different `#NN` ≠ alternate takes of one song.** Different passes can be
  entirely different songs (verified later in triage). Don't pre-collapse them.
- **`merged`/`merged_1` are redundant fragments**, not extra channels — keep but
  quarantine so they never reach role mapping.

## Related

- [[multitrack-triage]] — the very next step: clean + song-split + role-label
- [[drum-prep]] — align the labeled kit once triage emits a `kit.json`
- [[new-track]] — scaffold a durable `projects/<slug>/` once you know what you have
