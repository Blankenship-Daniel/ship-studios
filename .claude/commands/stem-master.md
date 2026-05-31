---
description: Per-stem corrective mixdown (resolve masking, de-harsh, transient-shape) then sum and hand to mastering.
argument-hint: <stems-dir-or-map> [target platform/LUFS]
---

Invoke the **stem-master** skill on `$ARGUMENTS`.

`$1` is the folder/map of named stems; any remaining args name the eventual master target (platform / LUFS / ceiling). The skill measures each stem, resolves cross-stem masking with `analyze-stem-masking` → `apply-eq`, corrects/transient-shapes per stem, sums via `drum-prep stem-mix`, verifies the carve, then hands the bus to [[master-track]]. It does NOT limit — don't restate the recipe; defer to the skill and report per-stem moves + the handoff.
