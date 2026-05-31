---
name: sample-pack
description: Use when the user wants to assemble a sellable sample pack — "make a sample pack", "package these as a kit for sale", "oneshots + loops into a pack", "build a drum kit pack with previews". Assembles one-shots + loops into a tagged, organized, multi-format pack with metadata/blurbs. Primarily stemmy-loops.
---

# Assemble a sellable sample pack

Goal: turn a source (drum stem, mix, or an already-finished loop set) into a
**sellable pack** — isolated one-shots plus loops, each tagged with
BPM/key/root/bars, exported as the standard format matrix, then organized
into a clean pack tree with a README/contact-sheet and optional per-item
blurbs for the store listing.

This is almost entirely **stemmy-loops** (`stemmy-loops:*`) — extraction,
tagging, and export are its core DSP. The only optional cross-server reach is
`stemmy-loops:describe-loops` (Gemini under the hood) for marketing blurbs.
Never invent a tool — every name below is verified.

## Prerequisites

- `stemmy-loops` registered and running.
- `extract-oneshots` needs the loops server's onset stage; `find-loops` on a
  full mix needs `separate: true` → the `separate` extra. `render-mastered`
  (loudness-coherent pack) needs the `mixing` extra. `tag-deliverable` /
  `export-deliverables` are core DSP.
- Optional `describe-loops` / `caption-loops` need the `listen` / `llm`
  extra (+ `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`) — only for blurbs.
- Resolve up front: source path(s), **BPM** (a number — `bpm: 120`, not
  `"120 BPM"`; required by `extract-oneshots` / `find-loops`), key/root if
  known, and a pack name. If BPM is unknown, ask — extraction has no reliable
  auto-tempo.

## Recipe (ordered)

1. **Extract the hits** — `stemmy-loops:extract-oneshots {path, bpm, out_dir:
   artifacts/<run>/oneshots}`. One WAV per onset → the kit elements
   (kick/snare/hat/etc). Run per source stem if the hits come from separate
   close mics.
2. **Extract the loops** — `stemmy-loops:find-loops {path, bpm, bars, top_n,
   separate, out_dir: artifacts/<run>/loops}` for the loop side, or run the
   full clean → seam → master chain via [[loops-to-deliverables]] when the
   loops need polishing. Both write `manifest.json`.
3. **Tag each deliverable** — `stemmy-loops:tag-deliverable {path,
   out_path, bpm, key, root, bars, originator}` on every one-shot and loop.
   Embeds BPM/key/root/bars + a `tags.json` sidecar. Tag the whole pack
   consistently — same key/originator across items.
4. **Export the format matrix** — `stemmy-loops:export-deliverables {path,
   out_dir, presets: ["44.1/16", "48/24", "96/24"], tag: true}` per item.
   TPDF dither + metadata carry-forward.
5. **Organize the pack tree** — assemble the exported files into a sellable
   layout (filesystem, no MCP tool):
   ```
   projects/<track>/pack/<pack-name>/
     oneshots/        # by kit element: kicks/ snares/ hats/ …
     loops/           # by tempo/element or flat
     README.txt       # pack name, BPM, key, file counts, license + contact
   ```
   Write the README/contact-sheet: pack name, BPM, key, count per category,
   license terms, contact. Naming consistent and human-readable.
6. **Optional — per-item blurbs / marketing copy** —
   `stemmy-loops:describe-loops {dir}` for audible groove/feel notes, or
   `stemmy-loops:caption-loops {dir}` for short feature-derived captions.
   Fold these into the README or a per-item sidecar for the store listing.

## Outputs

- Extraction scratch → `artifacts/<run>/`.
- Final pack tree → `projects/<track>/pack/<pack-name>/` with `oneshots/`,
  `loops/`, and the README/contact-sheet. The user-facing artifact is the
  pack folder.

## Reporting to the user

Show the **pack tree** (the folder layout). Give **file counts per category**
(N kicks, N snares, N loops, …). State **tag coverage** — how many items
carry BPM/key/root/bars vs. how many came through untagged. List the pack
path and the README path.

## Pitfalls

- **`export-deliverables` silently drops RIFF INFO tags.** Tags written by
  `tag-deliverable` can vanish on export. **Verify** the exported pack with
  `drum-prep verify-tags <pack-dir>` and re-tag/re-embed if coverage dropped
  (see [[delivery-qc]] / [[stemmy-loops-tagging-gotchas]]). Don't ship a pack
  whose files lost their metadata.
- **Keep loudness consistent across the pack.** Master every loop to the same
  `target_lufs` (a sample-pack-typical target, not a streaming master target)
  so items don't jump in level between previews. One-shots should be
  peak-normalized consistently, not loudness-matched.
- **Consistent naming + keys.** A buyer browses by filename — same casing,
  same key labels, same BPM in the name across the whole pack.
- **BPM is a number.** `bpm: 120`, not `"120 BPM"`.

## Related

- [[loops-to-deliverables]] — the clean → seam → master → tag → export loop chain this pulls from
- [[delivery-qc]] — verify tags survived and the pack is shippable
- [[drum-tune]] — tune one-shots/loops to a consistent key before packing
