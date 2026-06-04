---
name: reference-match
description: Use when the user wants a mix to sound like a reference track — "make it sound like <ref>", "match this reference", "A/B against this song", "get the same tonal balance as <ref>", "match the loudness of <ref>", "why doesn't mine sound as full as theirs". Derives numeric + perceptual deltas vs the reference, applies EQ to close the gap, and renders a loudness-matched A/B audition. Spans BOTH servers.
argument-hint: <mix.wav> <reference.wav>
---

# Match a mix to a reference

Goal: move a mix toward a reference track's tonal balance (and, by audition,
its loudness-normalized character), then hand the user a single A/B WAV they
can scrub. Three delta sources are reconciled — a numeric per-band curve, a
perceptual A/B read, and a second numeric cross-check — so the EQ moves are
defensible rather than one tool's opinion.

The numeric + perceptual delta tools live on **stemmy-gemini**; the second
numeric cross-check, the EQ, and the A/B render live on **stemmy-loops**.

## Prerequisites

- Both servers registered and running.
- `stemmy-gemini:compare-to-reference` (perceptual) needs `GEMINI_API_KEY`.
  `stemmy-gemini:match-reference-numeric` is pure DSP — **no** key.
- `stemmy-loops:render-ab` needs the `mixing` extra; `compare-tonality` and
  `apply-eq` are core DSP.
- Resolve `mix_path` and `reference_path` up front. If the user gives a
  Spotify/YouTube link instead of a file, ask them to drop a WAV in
  `projects/<track>/refs/` (reference) or `projects/<track>/stems/` (the mix)
  first — these tools read local audio.

## Recipe (ordered)

1. **Numeric delta curve** — `stemmy-gemini:match-reference-numeric
   {mix_path, reference_path}`. Per-third-octave delta-dB EQ curve plus
   LUFS / TP / RMS / crest / tilt deltas. This is the quantitative target.
2. **Perceptual A/B** — `stemmy-gemini:compare-to-reference {mix_path,
   reference_path, goal}`. Perceptual deltas (tonal / dynamics / stereo /
   loudness) with actionable moves. Catches things the curve doesn't, like
   "reference has more depth / wider chorus".
3. **Numeric cross-check** — `stemmy-loops:compare-tonality {loop_path:
   <mix>, reference_path: <ref>}`. Independent per-band (5-band) delta +
   suggested broad EQ moves + per-band confidence. Use this to confirm the
   step-1 curve's direction; trust high-confidence bands, discount low-
   confidence ones.
4. **Reconcile into an EQ move set** — collapse the third-octave curve (1)
   into a small number of shelves/bells, weighted by the confidence from (3)
   and sanity-checked against the perceptual notes (2). Don't apply 30 micro-
   bands; apply the few moves that close the biggest gaps.
5. **Apply EQ** — `stemmy-loops:apply-eq {path: <mix>, out_path, bands,
   tilt_db_per_octave}`. Write to `projects/<track>/mix/`. For a faithful
   render of the *whole* delta curve rather than a few bells, drive
   `stemmy-loops:match-eq {source_path: <mix>, reference_path: <ref>, ...}`
   (a min/linear-phase corrective FIR, `match_strength ≈ 0.5`) and follow with
   `apply-eq` only for surgical residuals.
6. **Render the audition** — `stemmy-loops:render-ab {processed: <corrected
   mix from step 5>, reference: <ref>, out_path}`. Loudness-matches the
   corrected mix to the reference and renders one `[reference | gap |
   matched processed]` WAV so the comparison is fair (loudness-normalized).

## Outputs

- Corrected mix → `projects/<track>/mix/`.
- A/B audition WAV → `projects/<track>/mix/` (single file, ready to scrub).

## Reporting to the user

Report the residual deltas after the move: re-state the largest pre-move
band gaps from step 1 and which ones the EQ targeted, plus the LUFS/tilt
delta. Note any perceptual gap from step 2 that EQ *can't* close (stereo
width, depth, arrangement) and route those elsewhere — width to a stereo
move, dynamics to [[mix-check]] compression. Point at the A/B file and tell
them what to listen for.

## Pitfalls

- **`render-ab` matches loudness; it does not master.** It exists to make
  the A/B fair, not to deliver a master. For a real master after matching,
  go to [[master-track]].
- **Don't apply the raw third-octave curve as 30 bands.** That over-fits to
  the reference's arrangement, not its tone. Reduce to a handful of
  shelves/bells.
- **EQ can't add depth or width.** If `compare-to-reference` says the
  reference is "wider / deeper", that's a stereo/reverb move, not an EQ move
  — say so rather than forcing it into `apply-eq`.
- **`compare-tonality` takes `loop_path`** (its param name), but it works on
  any WAV — pass the full mix there. The reference goes in `reference_path`.

## Fan-out

The **three delta reads are independent** — steps 1–3
(`match-reference-numeric`, `compare-to-reference`, `compare-tonality`) all read
the same mix + reference pair with no dependency. Issue them concurrently, then
reconcile (step 4); the EQ → render tail (steps 5–6) stays serial. For a whole
EP against ONE shared target, use the `house-curve` workflow (per-mix fan-out).

## Related

- [[house-curve]] — match a whole EP/album to ONE shared target (this is single mix ↔ single ref)
- [[level-match]] — gain-only loudness match for an honest A/B without rendering the full audition
- [[mix-check]] — fix problems the reference comparison surfaces (resonances, sibilance)
- [[master-track]] — master the matched mix to a platform target
- [[understand-audio]] — break down *what* the reference is doing before matching
- [[gemini-audio-understanding]] — why the perceptual A/B can't judge width/loudness (Gemini hears mono) — lean on the numeric deltas for those
