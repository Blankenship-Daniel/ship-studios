---
name: finalize-mix
description: "Use when a mix needs bus 'glue'/density BEFORE mastering — 'glue the mix bus', 'make it gel', 'add some bus compression/saturation', 'tighten the low end and widen the top before mastering'. Gentle mix-bus processing — the stage between mixing and [[master-track]] — WITHOUT limiting. Stemmy MCP."
---

# Finalize a mix — bus glue + density before mastering

This is **glue, NOT loudness.** The job is gentle stereo-bus processing that
makes a clean mix gel — light bus compression, subtle saturation, controlled
low end and top width — *immediately before* [[master-track]]. It does **not**
limit, does **not** hit a LUFS target, and does **not** maximize. Gemini
repeatedly flags "glue / density / cohesion" as belonging just before the
limiter, which is exactly this stage; mastering loudness happens downstream.

One server is in play: every corrective + render tool here lives on
**stemmy-loops** (`[L]`), all pure DSP, no env/network — with one **optional**
exception, a third-party VST3/AU plugin insert (step 3b) for character the
pure-DSP tools can't give. Tool names below are verified against the tool
surface — spelled exactly (hyphen vs underscore).

## Prerequisites

- `.mcp.json` registers `stemmy-loops` (sibling at `../stemmy-loops-mcp`).
  Confirm the server is up.
- `measure-loudness` (and the `render-*` tools) need the `mixing` extra
  (pyloudnorm); the other tools here — `compress-loop`, `saturate-loop`,
  `adjust-stereo`, `measure-spectrum`, `measure-stereo` — are core DSP. Install
  `mixing` regardless, since the recipe baselines loudness. All are pure DSP
  with **no** API key. The optional VST insert (step 3b) additionally needs the
  `vst` extra (`uv sync --extra vst`, adds Pedalboard) plus your own installed
  plugins; skip it and nothing else changes.
- The input is a near-final **stereo** mix bus, not stems and not loops.
  Resolve the path up front. If the mix isn't clean yet (tonal/phase/balance
  problems), run [[mix-check]] first — glue can't fix a broken mix and it
  can't be undone downstream.

## Recipe (ordered — measure before/after each move)

1. **Baseline** — `[L] measure-loudness {path}` + `[L] measure-spectrum
   {path}` + `[L] measure-stereo {path}`. Capture crest/PLR (so compression
   can be judged), tilt + 5-band ratios (so saturation's harmonic/tonal
   change is visible), and L/R correlation + mono-sum loss (so widening is
   bounded). This is the "before" column.
2. **Bus glue compression** — `[L] compress-loop {path, out_path, ...}`.
   *Gentle* downward compression: low ratio, slow-ish attack/release, a few
   dB of gain reduction at most. The goal is cohesion, not control. Read the
   GR stats back and confirm crest dropped only modestly.
3. **Density / harmonics** — `[L] saturate-loop {path, out_path, ...}`.
   Subtle oversampled tape / soft-clip for harmonic density and a touch of
   warmth. Keep drive low; this is seasoning, not distortion.
3b. **(Optional) Character via a 3rd-party plugin** — `[L] apply-vst-chain
   {path, out_path, plugins:[{plugin_path, parameters?}], dump_state:true}`.
   Reach for a VST3/AU *effect* (a bus compressor, tape/console emulation, a
   character saturator) when a plugin gives glue/color the pure-DSP steps
   above can't. Find paths with `[L] list-vst-plugins`. Keep it subtle like
   the rest of this stage, and `dump_state:true` writes the patch next to the
   output so the render is reproducible. **This is the one non-deterministic,
   opt-in step** — it loads an external binary (needs the `vst` extra), is
   effects-only, and is VST3-everywhere / AU-macOS-only. Skip freely.
4. **Low-end + width** — `[L] adjust-stereo {path, out_path, ...}`. Bass
   mono-maker first (mono the lows below a crossover), *then* tasteful M/S
   width on the top. Always mono before you widen so the low end stays
   centered and mono-compatible.
5. **Confirm** — re-run `[L] measure-loudness` + `[L] measure-spectrum` +
   `[L] measure-stereo` on the finalized bus. Verify crest didn't collapse,
   tilt moved only as intended, and mono-sum loss didn't get worse. Write the
   result to `projects/<track>/mix/`.

## Outputs

- Finalized (glued) mix bus → `projects/<track>/mix/`.
- Keep the intermediate measurement JSON in the run; the user-facing artifact
  is the single finalized stereo file, ready to hand to [[master-track]].

## Reporting to the user

Give a before → after read of the deltas:

- **crest reduction** from the bus compressor, plus the **GR amount** (how
  many dB of gain reduction);
- **tilt / harmonic change** from the saturation;
- **width / correlation change** from `adjust-stereo` (and confirmation the
  lows are mono).

Then state explicitly that this is glue/density only — **no limiting, no LUFS
target hit** — and point at [[master-track]] for loudness.

## Pitfalls

- **Glue a properly-balanced bus only.** If elements sit wrong (too much hat/cymbal, a buried or over-loud
  part), fix the LEVELS with `[[mix-balance]]` first — bus EQ/comp/glue can't fix a balance problem and
  bakes it in.
- **This is glue, not loudness.** Do **not** limit and do **not** render to a
  LUFS target here — that is [[master-track]]'s job. Hitting loudness at this
  stage double-processes the master and can't be undone.
- **Keep it subtle — it can't be undone downstream.** Over-compression or
  heavy saturation bakes into every later stage. When unsure, do less.
- **Measure crest before/after** so you can prove you didn't over-compress.
  A large crest collapse means back off the ratio / makeup.
- **Mono the lows *before* widening.** Widening first can decorrelate bass and
  worsen mono-sum loss.
- **Don't finalize a broken mix.** If [[mix-check]] flagged tonal/phase/
  balance issues, fix those first — glue is cohesion, not correction.
- **A VST insert (step 3b) is non-deterministic.** If you use it, pin the
  plugin version and keep its `dump_state` blob in the project — unlike the
  pure-DSP steps, a VST render won't reproduce across plugin updates. Still
  measure before/after, and know a misbehaving plugin can crash the render.
- **Calibrate tone on a REPRESENTATIVE section, not a short excerpt.** A chain
  dialed on one bright/quiet passage over- or under-processes the whole track
  (e.g. a warm tilt tuned on a bright intro over-darkened the full mix — centroid
  dropped much further over 10 min than on the opening 60 s). Verify on the full
  render or a representative window and re-measure; adjust if the signature drifts.

## Related

- [[mix-check]] — run first if the mix isn't clean; finalize is downstream of it
- [[master-track]] — the next stage; loudness + limiting + delivery live there
- [[drum-mix]] — when the bus you're gluing is a drum kit, not the full mix
- [[warm-drum-bus]] — a specific warm/tight drum-bus tone chain (tape + tilt + low-band control)
- [[song-mix]] — full-song balancing before this finalize/glue pass
- [[vst-saturate]] / [[vst-channel-strip]] — the plugin form of step 3b's glue/color (your own tape/console)
