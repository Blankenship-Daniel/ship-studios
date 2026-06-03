---
name: sampler-kit
description: Use when the user wants a tuned, playable drum kit from a break — "make a sampler kit", "chop and tune these hits to the key", "build a tuned drum kit from this break", "tune the kick/toms so they don't clash with the bass". Chops a break into one-shots, tunes the PITCHED hits (kick/toms) to the song root, QCs, tags, and exports a multiformat one-shot kit. Distinct from [[sample-pack]] (sellable assembly) and [[slice-oneshots]] (no tuning). You designate which hits are pitched — there is no auto kick/snare classifier.
argument-hint: <break.wav> [key/root]
---

# Sampler-kit — chop, tune to key, tag, export a one-shot kit

Goal: turn a break into a usable, **key-tuned** one-shot kit — chop the hits,
retune the pitched ones (kick, toms) to the song's root so they don't beat
against the bass, level/QC, tag, and export the format matrix. The
differentiator over [[slice-oneshots]] is the tuning; over [[sample-pack]],
the per-hit pitch work rather than sales packaging.

**Scope (be honest):** `extract-oneshots` emits generic `hit_NN.wav` with **no
kick/snare/hat classification**, and Gemini `classify-audio` is confounded by
drum bleed — so *you/the user designate which slices are pitched* (by index),
or tune all. Output is a tagged multiformat **one-shot kit**, not a key-mapped
sampler instrument patch (no `.sfz` / `.exs` generation).

## Prerequisites

- `stemmy-loops` (`extract-oneshots`, `tune-kick`, `tag-deliverable`,
  `export-deliverables`) — pure DSP, no API key.
- The **local** `drum-prep` CLI (`uv sync --extra drum-prep`) for `drum-prep
  tune` (measures the fundamental and retunes a sample by resampling). See
  [[drum-tune]].
- Song key / root and BPM from `projects/<track>/track.md`.

## Recipe (ordered)

1. **Slice** — `[L] extract-oneshots {path, out_dir, min_separation_ms,
   pre_pad_ms, post_pad_ms}` → `hit_NN.wav` (as in [[slice-oneshots]]).
2. **Designate pitched hits** — pick which slices are pitched (kick, toms) by
   index; leave snare/hats/cymbals untuned. There's no reliable auto-classifier
   (see Scope).
3. **Measure fundamentals** — `[L] tune-kick` on each pitched hit → fundamental
   Hz / note / cents off (or `drum-prep tune <hit>` for the same read).
4. **Retune to the song root** — `drum-prep tune <hit> --out <f>` resamples the
   pitched hit toward the target note from `track.md`. Resampling shifts pitch
   **and** length/timbre — right for a sub-y kick/tom, judge by ear.
5. **Level + QC** — `[L] check-clipping` on the retuned hits and renormalize if
   the resample overshot 0 dBFS; drop duds. **Not `inspect-loop`** (vacuous on
   one-shots).
6. **Tag + export** — `[L] tag-deliverable` per hit (`key`, `root_note`, `bpm`,
   `comment`) → `[L] export-deliverables {presets, tag: true}` →
   `drum-prep verify-tags` / [[delivery-qc]] (RIFF INFO drop).

## Outputs

- Tuned kit → `projects/<track>/loops/kit/` + the exported deliverable matrix.

## Reporting to the user

Per-hit fundamental + retune (target note, cents moved), which hits were tuned
vs left alone, the clip/level checks, and the export paths. State plainly: this
is a tagged, tuned **one-shot kit**, not a mapped sampler instrument file.

## Pitfalls

- **No auto hit-classification** — designate the pitched hits; don't trust
  Gemini `classify-audio` (drum bleed reads "snare" on everything).
- **Resampling changes pitch *and* duration/timbre** — right for kick/tom
  sub-tuning, wrong for a snare whose rattle character must survive.
- **`inspect-loop` is vacuous on one-shots** — QC on peak + `check-clipping`.
- **Tag out of place + `verify-tags`** (RIFF INFO drop on export).
- **Not a sampler instrument patch** — no `.sfz`/`.exs`; it's a tuned, tagged
  multiformat one-shot set.

## Related

- [[slice-oneshots]] — the same chop without tuning
- [[sample-pack]] — sellable multiformat pack assembly
- [[drum-tune]] — measure a drum's fundamental / retune a single sample
- [[delivery-qc]] — verify tags survived the export
