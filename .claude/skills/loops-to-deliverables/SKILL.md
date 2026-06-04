---
name: loops-to-deliverables
description: Use when the user wants finished loop deliverables from a drum stem or full mix — "slice this into loops and master them", "make tagged loops from this drum stem", "loop pack from this track". Extracts loops, cleans + seam-fixes each, masters, tags, and exports the format matrix. Optionally attaches audible descriptions. Primarily stemmy-loops, with an optional stemmy-gemini describe step.
argument-hint: <stem-or-mix.wav> <bpm>
---

# Turn a stem or mix into tagged, mastered loop deliverables

Goal: go from raw audio to a polished, tagged, multi-format loop pack. The
chain extracts loop candidates, then per loop: cleans (DC/HPF; declick off on
percussive material),
optimizes the seam so it wraps bit-exactly, masters to a consistent
loudness, tags with BPM/key/bars, and exports 44.1/16 + 48/24 + 96/24.

Almost everything here is **stemmy-loops** (extraction is loops' core
competence; the per-loop processing tools are pure DSP). The one optional
cross-server step is `stemmy-gemini`-adjacent: audible descriptions come from
`stemmy-loops:describe-loops` (which itself wraps Gemini under the hood), so
no direct gemini-server call is required for the standard flow.

## Prerequisites

- `stemmy-loops` registered and running.
- Full-mix input (not an isolated drum stem) → set `separate: true` on
  `find-loops` / `analyze-loops` so Demucs extracts drums first. That needs
  the `separate` extra installed on the loops server.
- `render-mastered` needs the `mixing` extra; `clean-loop`, `optimize-seam`,
  `tag-deliverable`, `export-deliverables` are core DSP.
- Optional `describe-loops` needs the `listen` extra + `GEMINI_API_KEY`.
- Resolve input path + **BPM** up front. BPM is required and is a number
  (`bpm: 120`, not `"120 BPM"`). If the user doesn't know it, ask — loop
  extraction has no auto-tempo (it kept octave-locking wrong).

## Recipe (ordered)

> **Already-mastered source branch.** If the input is *already a finished
> master* (e.g. loops cut from a mastered drum bus / a released track), **skip
> `clean-loop` (step 2) and skip the per-loop `render-mastered` (step 4)**.
> Re-mastering an already-mastered source double-processes it — a second
> limiter pass on already-loud audio just clips and pumps. The chain collapses
> to: `find-loops` → `optimize-seam` → `tag-deliverable` → `export-deliverables`.
> Use the full clean→seam→master→tag→export chain only when slicing a *raw*
> stem/mix that hasn't been mastered.

1. **Extract loops** — choose one:
   - `stemmy-loops:find-loops {path, bpm, bars, top_n, separate, out_dir}` —
     the fast slice chain (ingest → downbeat → find-candidates → select →
     write-loops). Default choice; returns `manifest.json`.
   - `stemmy-loops:analyze-loops {path, bpm, bars, top_n, separate, ...}` —
     use instead when the user wants role labels / structure / per-loop
     features; returns `manifest.json` + `analysis.json`. Slower.
   Write to `artifacts/<run>/`.
2. **Per selected loop — clean** — `stemmy-loops:clean-loop {path, out_path,
   declick: false, ...}`. DC removal + HPF (+ optional denoise/gate) before any
   loudness work, so the master stage isn't amplifying rumble. **`declick`
   defaults to True and smears drum attacks** (it reads sharp percussive edges as
   clicks — ~100k false "repairs" on a kick stem), so pass `declick: false` for
   drum/percussive loops (the common case here); reserve `declick: true` for
   tonal sources with genuine click artifacts.
3. **Per loop — optimize the seam** — `stemmy-loops:optimize-seam {path,
   out_path}`. Searches ±256 samples for the best wrap point + equal-power
   crossfade so `loop + loop` closes bit-exactly. This is what makes it
   actually loop.
4. **Per loop — master** — `stemmy-loops:render-mastered {path, out_path,
   target_lufs, ceiling_dbtp, ...}`. Master each cleaned/seamed loop to a
   consistent target so the pack is loudness-coherent. A sample-pack-typical
   pair is `target_lufs: -12`, `ceiling_dbtp: -1.0` — confirm with the user
   if they have a house standard.
5. **Per loop — tag** — `stemmy-loops:tag-deliverable {path, out_path, bpm,
   key, root_note, bars, comment, originator}`. Embeds BPM/key/root/bars in
   the RIFF LIST/INFO chunk + writes a `tags.json` sidecar. `originator` is
   required (set it to the studio/user name). Pull `bars` from the manifest;
   ask for `key`/`root_note` if not known.
6. **Per loop — export the matrix** — `stemmy-loops:export-deliverables
   {path: <tagged loop>, out_dir: projects/<track>/deliverables/, presets:
   ["distribution_44k_16", "production_48k_24", "master_96k_24"], tag: false}` —
   the 44.1/16 + 48/24 + 96/24 formats. TPDF dither across all three. Export
   with **`tag: false`** then re-tag each exported WAV with `tag-deliverable`
   afterward — `tag: true` silently drops the RIFF `LIST`/`INFO` chunk + the
   `.tags.json` sidecar (see the Pitfalls). (Preset names are an exact
   allow-list; omit `presets` to get the `distribution_44k_16` +
   `production_48k_24` default pair.)
7. **Optional — audible descriptions** — `stemmy-loops:describe-loops
   {out_dir}`. Gemini-backed groove / feel / kit-emphasis notes attached to
   the set, for pack metadata or for the user to pick favorites.

## Outputs

- Raw extraction (WAVs + manifest) → `artifacts/<run>/`.
- Final tagged, multi-format deliverables → `projects/<track>/deliverables/`.
- Keep intermediate cleaned/seamed/mastered WAVs in the run dir; the user-
  facing artifact is the `deliverables/` matrix.

## Reporting to the user

List the loops that made the cut with bar length + score (from the
manifest), and for each the exported formats. Note the master target used
and that every loop is seam-closed. If `describe-loops` ran, fold its one-
liners in so the user can pick. If extraction returned fewer loops than
`top_n`, say why (the scorer rejects broken candidates) and point at
diagnosis options.

## Pitfalls

- **Order matters: clean → seam → master → tag → export.** Mastering before
  seam-optimizing bakes loudness into a seam you're about to move; tagging
  before mastering loses tags the render won't carry. Don't reorder.
- **Run per loop, not on the batch.** `clean-loop` / `optimize-seam` /
  `render-mastered` take one WAV each. Loop over the manifest's loops.
- **`separate: true` only for full mixes.** On an already-isolated drum stem
  it wastes Demucs time; omitting it on a full mix yields garbage loops.
- **BPM is authoritative per loop.** A rescued loop may carry a slightly
  perturbed BPM in the manifest — tag with the per-loop value, not blindly
  the input BPM.
- **declick=false on percussive material.** `clean-loop`'s `declick` defaults to
  True and smooths drum transients — the very attack a drum loop sells. Mirror
  [[stem-process]]: declick off for drums; only on for tonal/clicky sources.
- **This produces loop deliverables, not a stereo master.** For a full-track
  master use [[master-track]].
- **`export-deliverables tag=true` silently drops the RIFF INFO.** Despite the
  flag, the exported WAVs come out with only `fmt ` + `data` — no `LIST`/`INFO`
  chunk and no `.tags.json` sidecar. The success return lies. Treat export as
  *un*tagged and re-tag afterward (see next pitfall).
- **`tag-deliverable` in-place (`out_path == path`) fails.** It writes through
  a `<path>.rewrite.tmp` temp file, and libsndfile can't infer a format from
  the `.tmp` extension, so the call errors. **Fix:** tag with `out_path != path`
  — keep it in the **same dir** and insert a suffix before the extension (the
  pattern the `loops` pipeline uses: `a.wav` → `a.master.wav` → `a.tagged.wav`),
  e.g. `{path: kick.master.wav, out_path: kick.tagged.wav}` → sidecar
  `kick.tagged.tags.json`. Then move the tagged WAV back over the export. Pairs
  with the export pitfall above (`tag: false`, then re-tag): **verify the WAV
  actually contains a `LIST` chunk** (e.g. grep the header for `LIST`) — don't
  trust the success return.

## Fan-out

Extraction (step 1) is the barrier; **after it, each loop is independent** — the
per-loop chain (clean → seam → master → tag → export, steps 2–6) reads/writes its
own files with no cross-loop dependency. For many loops, fan out one agent per loop
(each runs its whole ordered chain), then the optional `describe-loops` (step 7)
runs once over the set. Don't split a single loop's own chain — the order matters.

## Related

- [[understand-audio]] — recon the source (events, structure) before slicing
- [[master-track]] — stereo-track master (different deliverable shape)
- [[sample-pack]] — a sellable oneshots+loops kit with a README/blurbs (this is the loop-only chain it builds on)
- [[new-track]] — scaffold `projects/<track>/` first if it doesn't exist
- [[gemini-audio]] — what the optional Gemini `describe-loops` step can/can't hear
