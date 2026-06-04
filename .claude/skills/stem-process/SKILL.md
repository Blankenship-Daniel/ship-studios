---
name: stem-process
description: "Use when the user wants to PROCESS the individual stems of a multi-mic kit — 'process the individual stems', 'clean up and color each stem', 'per-stem corrective + tone on my drums', 'treat each mic separately then re-sum', 'EQ/de-harsh/compress each drum stem'. Per-stem MEASURED corrective (clean, de-box, de-harsh, dynamic-EQ, transient) + optional console/tape color, with before/after verification and an optional re-sum A/B. Local DSP + the `vst` extra for color."
argument-hint: <stems-dir> [duration_s]
---

# stem-process — measured per-stem corrective + color for a multi-mic kit

Goal: treat **each mic/stem individually** — clean + correct its own problems (mud, box, ring, harshness,
soft transients) and optionally add console/tape **color** — then (optionally) re-sum and A/B so you hear
the net effect. The per-stem stage between [[drum-prep]] (align) and [[warm-drum-bus]] / [[drum-mix]] (the bus).

**Local DSP + VST** — drives the stemmy-loops corrective tools + (for color) the API Vision Channel Strip /
Studer via the stemmy-loops **`vst` venv**. Executor: [`scripts/mix/process_stems.py`](../../../scripts/mix/process_stems.py).
Run it with the loops vst venv (`../stemmy-loops-mcp/.venv/bin/python scripts/mix/process_stems.py ...`).
**Worktree caveat:** that `../` is wrong from a git worktree under `.claude/worktrees/<name>/` — the
sibling lives next to the **main** checkout. Resolve it there and pass the **absolute** venv path.

## The governing facts (obey)

- **declick OFF on percussive material** — it smears drum attacks. The executor forces `declick=false`.
- **Keep console EQ tops flat** — boosting 2–5 kHz (esp. 5 kHz, which sits in both the API 550 hmf AND hf
  bands) re-introduces harshness. Get punch from the comp, body from low/low-mid, not from a bright boost.
  See [[api-vision-channel-strip]] / [[studer-a800]].
- **Warmth = tape/tilt, not treble.** **Cuts** (de-box, de-harsh) clean a stem; broadband HPF shifts the
  tonal balance up, so a "cleaned" stem reads brighter — account for that at the bus ([[warm-drum-bus]]).
- **Measure every move.** Crest up = punch (not just louder); centroid/tilt watch for harshness; verify the
  intended change landed (de-harsh actually ducked the ring, transient actually raised crest).
- **Mono stays mono** — the executor collapses the stereo VST output back to mono for mono inputs so panning
  survives the re-sum.

## Recipe (ordered)

1. **Align first** — if raw, `drum-prep phase-align <kit>` → `<kit>/phase-aligned/` (deterministic; the
   `artifacts/` source is scratch and regenerable from the raw mics if lost).
2. **Diagnose each stem** — measure loudness / spectrum (third-octave) / stereo / microdynamics per stem and
   decide a **role-aware** plan: kick (tighten sub, cut 250–500 box, modest click), snare (de-box, de-harsh
   the ring, transient snap), hat (de-whoosh 160–500 + air, de-harsh 5–7 k), overhead (HPF mud, de-harsh,
   gentle air), room (HPF/denoise the hiss, glue). For breadth, fan the diagnosis out one-agent-per-stem with
   the `stem-process` workflow (parallel reads + per-stem plan authoring; the executor then runs as ONE serial
   UADx-safe pass) — optional, direct measurement works too. Emit a typed plan list (see
   `presets/mix/drums-stem-process.plans.json` for the schema).
3. **Process** — `scripts/mix/process_stems.py <plans.json> <src_dir> <out_dir> [duration_s]`. Per stem it
   runs: clean (declick off) → apply_eq (zero-phase) → suppress_resonances (de-harsh) → apply_dynamic_eq →
   shape_bands (transient) → excite (hiss-safe only) → **color** (API Vision Channel Strip, conservative,
   550 top flat). Prints before→after per stem. `duration_s>0` for a fast audition; `0`/omit for full length.
4. **Re-sum + A/B** (optional) — balance the raw vs processed stems to **identical** per-role targets
   (`scripts/mix/balance_stems.py`, same targets for both) so the A/B isolates the processing, then
   `render-ab` loudness-matched. Or hand the processed stems straight to [[warm-drum-bus]] / [[drum-mix]].

## Outputs

- Processed individual stems in `<out_dir>` (e.g. `artifacts/<kit>/processed/` or `projects/<track>/stems/`).
- Optional before/after kit A/B in `projects/<track>/mix/`.

## Reporting to the user

Per-stem before→after table (LUFS / crest / centroid / tilt), what each stem got and why, and — if re-summed
— the net kit centroid/tilt/crest/correlation with a loudness-matched A/B. Flag if the cleanup left the kit
brighter than wanted (route to [[warm-drum-bus]] to warm the bus).

## Pitfalls

- **Validate at a short duration FIRST, then commit to full-length** — catches bad params / rejected enum
  values cheaply (full-length per-stem + UAD color is ~minutes). But **don't tune tone on a 60 s excerpt and
  trust it globally** — a non-representative window mis-calibrates the full track; re-measure full-length.
- **declick off; tops flat; warmth via tape** (above) — the three ways this goes wrong.
- **Per-stem tape + bus tape over-darkens.** Studer color here STACKS with the bus tape in
  [[warm-drum-bus]] — cumulative high-cut (centroid drops, tilt steepens). A warm bus tilt can only
  CUT highs, so you can't recover the top at the bus: restore presence/air at the finalize stage with a
  zero-phase high-shelf lift (e.g. bell +1.5 @ 4 k below the 5–7 k harsh zone + high-shelf +3 @ 8 k) and
  verify centroid/tilt; if still dark, also back off the per-stem tape.
- **Per-stem cleanup ≠ a mix.** It corrects/colors stems; balance + bus tone are [[mix-balance]] /
  [[warm-drum-bus]] / [[drum-mix]]. Don't bake bus-level decisions into individual stems.
- **`apply-dynamic-eq` / `suppress-resonances` are newer/less-aged** — use conservatively and verify the
  measured effect; fall back to static `apply-eq` if a result looks off.

## Fan-out

The **per-stem diagnosis is the parallel win** (step 2): each stem's measure →
role-aware plan is independent, so the `stem-process` workflow fans it out one agent
per stem. The executor (step 3) then runs ONCE, serially — `process_stems.py` loads
the API Vision `uaudio_*` plugin per stem, and concurrent UADx hosts render
non-deterministically, so the processing pass is intentionally NOT parallelized.

## Related

- `stem-process` (workflow) — fans the per-stem diagnosis out (one agent per stem); the executor then runs as one serial UADx-safe pass
- [[drum-prep]] — align the kit first · [[stem-master]] — the corrective→sum→master cousin (this is the standalone per-stem stage)
- [[warm-drum-bus]] — warm/tight bus from the processed stems · [[drum-mix]] — role-aware kit sum · [[mix-balance]] — measured balance
- [[api-vision-channel-strip]] / [[studer-a800]] — the color engines (console / tape), measured
- Executor + plans: `scripts/mix/process_stems.py`, `presets/mix/drums-stem-process.plans.json`
