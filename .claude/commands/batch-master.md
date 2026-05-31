---
description: Master a whole EP/album folder to one shared target, with a cross-track loudness/true-peak consistency table.
argument-hint: <mixes-dir> [target platform/LUFS]
---

Invoke the **batch-master** skill on `$ARGUMENTS`.

`$1` is the folder of near-final mixes; remaining args set the single shared target (platform / LUFS / ceiling) for the whole set. The skill runs [[master-track]]'s measure → mastering-feedback → render → check-streaming-targets → export chain per file, then loops `measure-loudness` over every master to emit the cross-track consistency table (Δ-from-median, outliers flagged) and verifies tag survival. Defer to the skill; lead the report with the consistency table.
