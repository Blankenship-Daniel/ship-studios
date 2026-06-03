---
name: slice-oneshots
description: Use when the user wants the individual hits out of a loop/break for a sampler — "chop this break into hits", "slice into one-shots", "give me the individual drum hits", "extract the hits for my sampler", "cut this loop into single samples". Lightweight onset-slice → per-hit WAVs → QC → optional tag, WITHOUT sample-pack's sales packaging (no format matrix, README, or blurbs). For a sellable multiformat pack use [[sample-pack]] instead. Pure DSP, no API key.
argument-hint: <loop-or-break.wav>
---

# Slice one-shots — chop a loop/break into per-hit WAVs

Goal: the quick "give me the hits" path — detect onsets in a loop or break
and write each hit to its own WAV, tuned for slice quality and QC'd, with an
optional tag. This is the minimal counterpart to [[sample-pack]]: same
`extract-oneshots` engine, none of the sellable-pack assembly.

## Prerequisites

- `stemmy-loops` registered and up. `extract-oneshots`, `check-clipping`,
  `tag-deliverable` are pure DSP — no API key.
- Input is one loop / break / drum stem to chop. Know the material: a busy
  break wants a smaller `min_separation_ms`; sharp transients want a small
  `pre_pad_ms`; let `post_pad_ms` capture each hit's decay.

## Recipe (ordered)

1. **Pick slice params** — for the material, choose `min_separation_ms`
   (gap between hits, default 50), `pre_pad_ms` (before onset, default 5),
   `post_pad_ms` (after onset / tail, default 300). These determine slice
   quality more than anything else.
2. **Slice** — `[L] extract-oneshots {path, out_dir, min_separation_ms,
   pre_pad_ms, post_pad_ms}` → `hit_NN.wav` files. Read the per-hit peak back
   from the result.
3. **QC** — drop duds, doubles, and clipped slices using the **peak from the
   extract result** + `[L] check-clipping` on any suspect hit. **Do not use
   `inspect-loop` here** — its loudness / LRA / stereo metrics are meaningless
   on a ~300 ms one-shot.
4. **(Optional) tag** — `[L] tag-deliverable` per kept hit (comment = a role
   note like "kick" / "snare", `key`/`root_note` if the hit is pitched). Tag
   **out of place** (the RIFF INFO drop gotcha).

## Outputs

- One-shots → `projects/<track>/loops/oneshots/` (or `artifacts/<run>/` for
  scratch).

## Reporting to the user

Count kept vs dropped, the slice params used, any clipped hits found, and the
output dir. If you tagged, say what each carries.

## Pitfalls

- **This is the lightweight chop.** For a sellable multiformat pack with
  previews/blurbs, use [[sample-pack]]; to tune the pitched hits to the song
  key, use [[sampler-kit]].
- **`inspect-loop` is vacuous on one-shots** — QC on peak + `check-clipping`.
- **Tune `post_pad_ms` to the material** — too short truncates the decay, too
  long bleeds the next hit in.
- **Tag out of place** (RIFF INFO drop), then verify if it matters.

## Related

- [[sample-pack]] — the full sellable-pack assembly (one-shots + loops)
- [[sampler-kit]] — chop **and tune** the pitched hits to the song key
- [[loops-to-deliverables]] — when the deliverable is loops, not single hits
