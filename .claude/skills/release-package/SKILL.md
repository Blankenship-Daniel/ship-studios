---
name: release-package
description: Use when the user wants finished masters assembled into a distribution-ready release — "package this release for distribution", "prep these masters for DistroKid/Bandcamp/CD Baby", "assemble the album/EP for upload", "make a release folder", "get these tracks ready to ship to a distributor". Assembles ALREADY-mastered tracks with consistent artist/album tagging, the export format matrix, per-platform compliance, and one loudness-consistency manifest. Distinct from [[batch-master]] (which masters) — this assembles + QCs + tags existing masters; it does not master.
argument-hint: <masters-dir> [artist/album/year] [platform]
---

# Release-package — assemble finished masters for distribution

Goal: take a folder of finished masters (one per track) and produce a coherent,
shippable release — consistent metadata across the set, the standard export
format matrix, a per-platform compliance pass, and a single loudness-consistency
sheet a distributor or label can trust. This is the **assembly + QC** stage that
sits after mastering; it does **not** master (that's [[batch-master]] /
[[master-track]]).

**Scope (be honest):** `tag-deliverable` carries `originator` + a free-text
`comment` + `bpm`/`key`/`root_note` — it has **no** album / year / ISRC /
track-number field. So album / year / ISRC ride in the `comment` as
human-readable reference text, **not** a machine-parsed distributor tag. In
practice distributors take metadata from their own upload form; what this skill
guarantees is the audio, the format matrix, compliance, and cross-track
consistency. (To embed real release metadata, `tag-deliverable` needs new
fields — see the `skill-gap-unblock-paths` memory note; ask and I'll add them.)

## Prerequisites

- `stemmy-loops` (`tag-deliverable`, `export-deliverables`, `measure-loudness`)
  + `stemmy-gemini` (`check-streaming-targets`, `check-delivery-spec`, pure DSP,
  no key) + the local `drum-prep verify-tags`.
- Input is a folder of **finished masters** (one per track). Resolve up front:
  artist/label, album, year, track order, and the target platform.

## Recipe (ordered)

1. **Resolve release metadata** — artist/label, album, year, track order,
   target platform. Build the ordered per-track list.
2. **Consistent tagging** — per track `[L] tag-deliverable {originator:
   "<artist> — <album> (<year>)", comment: "track NN/MM; ISRC <id>; <license>",
   bpm, key}`. Use the **same** `originator` across every track (consistency is
   the whole point). Tag **out of place** (RIFF INFO drop gotcha).
3. **Compliance** — per track `[G] check-streaming-targets` (LUFS/TP vs the
   platform) + `[G] check-delivery-spec` (clip / DC / format pre-flight). Flag
   anything non-compliant and route it back to [[batch-master]] /
   [[master-track]] — don't silently ship it.
4. **Export the matrix** — per track `[L] export-deliverables {presets:
   ["distribution_44k_16", "production_48k_24", "master_96k_24"], tag: true}`
   (the 44.1/16 + 48/24 + 96/24 formats) → `projects/<album>/release/`.
5. **Tag survival** — `drum-prep verify-tags` / [[delivery-qc]] across the
   release; `export-deliverables tag=true` silently drops the RIFF INFO chunk,
   so verify rather than assume.
6. **Consistency manifest** — loop `[L] measure-loudness` over the release
   masters → a table of LUFS-I / true-peak / LRA + **Δ-from-album-median**,
   outliers flagged. Add `[L] analyze-album-normalization {dir, target_lufs}`
   for the shared album gain a platform will apply (TD1008 vs album-integrated)
   so the sheet shows real playback levels, not just source LUFS. This is the
   shippable QC sheet.

## Outputs

- Release folder → `projects/<album>/release/` (per-track format matrix).
- The loudness-consistency manifest — the headline QC artifact.

## Reporting to the user

Confirm the consistent `originator`/comment applied across all tracks, the
per-track compliance result, the loudness-consistency table, the tag-survival
result, and the file paths. **State the ISRC/album-tag limitation explicitly**
so nobody assumes machine-parsed distributor metadata was embedded.

## Pitfalls

- **It doesn't master.** Assembles finished masters; a track that fails
  compliance goes back to [[batch-master]] / [[master-track]], not the limiter
  here.
- **No machine-parsed album/ISRC tag yet** — it rides in `comment` as reference
  text (`tag-deliverable` lacks the fields). The distributor's upload form is
  the real source of truth.
- **Verify tags survived export** (RIFF INFO drop) via [[delivery-qc]].
- **Keep `originator` identical across tracks** — consistency is the deliverable.

## Related

- [[batch-master]] — master the folder first if the tracks aren't final
- [[master-track]] — master/fix a single non-compliant track
- [[delivery-qc]] — the ship/don't-ship gate + tag-survival check
- [[sample-pack]] — the loop/one-shot equivalent of a packaged release
