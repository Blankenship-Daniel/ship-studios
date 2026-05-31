---
name: batch-master
description: Use when the user wants a whole EP/album/folder of mixes mastered consistently — "master this whole EP", "master all these tracks to the same loudness", "batch master this folder", "make the album consistent", "master all the songs for Spotify". Masters every mix in a folder to one shared platform target, then emits a cross-track loudness/true-peak consistency table flagging any track off the album median. [[master-track]] is single-file; this adds the album-level consistency read no single-file tool gives.
---

# Batch master — master a folder to one target, with a consistency table

Goal: master an EP/album's worth of near-final mixes so they hit **one
shared** loudness/true-peak target and sit together as a coherent release.
The per-track work is [[master-track]]'s chain in a loop; the load-bearing
novel piece — the thing no single-file tool can give — is the **cross-track
consistency read**: every master measured against the album median so
outliers surface as numbers, not vibes.

## Prerequisites

- Both `stemmy-loops` and `stemmy-gemini` registered and up.
- `[L]` render/measure/export need the `mixing` extra. `[G] mastering-feedback`
  needs `GEMINI_API_KEY` (perceptual read); `[G] check-streaming-targets` is
  pure DSP, no key.
- Resolve **up front, once for the whole set**: the folder of mixes, the
  shared `target_platform`, and the resulting `target_lufs` / `ceiling_dbtp`.
  Don't let tracks drift to individual targets.

## Recipe (ordered — per file, then cross-track)

Per track (loop the folder):

1. **Baseline** — `[L] measure-loudness` + `[L] measure-spectrum` +
   `[L] check-clipping`.
2. **Perceptual read** — `[G] mastering-feedback {path, target_platform}`.
   Release-readiness + harshness flags to steer that track's render.
3. **Render** — `[L] render-mastered` to the **shared** `target_lufs` /
   `ceiling_dbtp` → `projects/<album>/masters/`.
4. **Compliance** — `[G] check-streaming-targets` on the rendered master;
   re-render that track if it will be attenuated or breaches the ceiling.
5. **Export** — `[L] export-deliverables {presets, tag: true}` →
   `projects/<album>/deliverables/`.

Then across the set:

6. **Consistency table** — loop `[L] measure-loudness` over every rendered
   master and build a table: integrated LUFS, true-peak dBTP, LRA per track
   **plus deviation from the album median**. Flag anything beyond tolerance
   (e.g. > 0.5 LU off median, or any TP over ceiling).
7. **Tag survival** — run [[delivery-qc]] / `drum-prep verify-tags` across the
   deliverables: `export-deliverables tag=true` is known to silently drop the
   RIFF INFO chunk, so verify rather than assume.

## Outputs

- Per-track masters → `projects/<album>/masters/`.
- Deliverable matrix → `projects/<album>/deliverables/`.
- The **cross-track consistency table** — the headline artifact.

## Reporting to the user

Lead with the consistency table (LUFS / TP / LRA + Δ-from-median, outliers
flagged). Then per-track release-readiness, any re-renders and why, and the
tag-survival result. The table is the point — N individual masters without it
is just [[master-track]] run N times.

## Pitfalls

- **Consistency is a cross-file judgment.** The table is the deliverable, not
  just N masters in a folder.
- **One shared target for the set** — fix it once; don't let each track land
  at its own LUFS.
- **Verify tags survived export** (RIFF INFO drop) via [[delivery-qc]].
- **Targets are numbers** — `target_lufs: -14`, not `"-14 LUFS"`.
- **Don't loudness-paper a broken mix.** If `mastering-feedback` says a track
  isn't release-ready, route it to [[mix-check]] before mastering.

## Related

- [[master-track]] — the single-file master this loops and extends
- [[delivery-qc]] — the ship/don't-ship gate + tag-survival check
- [[variant-shootout]] — pick a loudness target before committing the batch
- [[mix-check]] — fix any track the perceptual read flags as not-ready
