---
description: Triage a folder of raw interface-named multitrack into clean, song-split, role-labeled kits ready for drum-prep.
argument-hint: <raw stems dir>
---

Invoke the **multitrack-triage** skill on `$ARGUMENTS`.

`$1` is a folder of raw multi-mic recordings (e.g. `artifacts/<slug>-raw/` from
[[logic-extract]]). The skill: scans levels/clipping (`scripts/scan-channels.sh` +
`[L] check-clipping`), quarantines DAW merge-fragments, splits dual-mono pairs
(`scripts/split-dual-mono.sh`), groups takes into SONGS by ear
(`[G] compare-audio-files` on the instrument channel), picks the best of redundant
takes, drops truly-dead channels (verified across takes), optionally declips
(`scripts/declip.sh`), infers roles (spectrum for close mics + correlation for the
overhead pair — NOT Gemini classify, which bleed confounds), and writes a
`kit.json` per song for [[drum-prep]]. Writes a `MANIFEST.md`. Defer to the skill
for the gotchas (AIFF-in-`.wav`, `.wav` extensions in kit.json, atrim-in-filter).
