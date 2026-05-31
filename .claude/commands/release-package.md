---
description: Assemble finished masters into a distribution-ready release — consistent tags, format matrix, compliance, consistency manifest.
argument-hint: <masters-dir> [artist/album/year] [platform]
---

Invoke the **release-package** skill on `$ARGUMENTS`.

`$1` is a folder of finished masters (one per track); remaining args give artist/album/year and target platform. The skill applies consistent `originator`/comment tags across the set, runs `check-streaming-targets` + `check-delivery-spec` per track, exports the format matrix to `projects/<album>/release/`, verifies tag survival, and emits a loudness-consistency manifest (Δ-from-median). It does NOT master — non-compliant tracks route back to [[batch-master]]. Note `tag-deliverable` has no album/ISRC field, so those ride in the comment as reference text. Defer to the skill; report the consistency table + the metadata limitation.
