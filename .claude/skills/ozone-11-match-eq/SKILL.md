---
name: ozone-11-match-eq
description: "DAW-ONLY: the iZotope Ozone 11 Match EQ (learns a reference's spectral curve and matches your master to it) is iLok-blocked headless on this rig — it won't authorize in an unattended no-GUI process, and the learn step is GUI-driven anyway — so this plugin-specific deep-dive of [[vst-eq]] teaches how to dial it in your DAW and which HEADLESS match-EQ ([[reference-match]]) to use in the pipeline instead. Use when asked: 'Ozone Match EQ', 'match this reference tone', 'match EQ to a reference', 'tonal match with Ozone'."
argument-hint: <mix.wav> <reference.wav> [match-strength]
---

# ozone-11-match-eq — drive the Ozone 11 Match EQ (reference match)

The plugin-specific, measured version of [[vst-eq]] for the **iZotope Ozone 11 Match EQ** — it **learns a
reference track's spectral curve and applies the corrective EQ** to make your master match it. Full family field
guide — render verdicts, the iLok story, DAW recipes — [`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md).
This skill is the workflow.

## The governing facts (read first)

1. **It does NOT render in the headless pipeline on this rig — it's iLok-blocked, AND the learn step is GUI-only.**
   Measured: the Ozone 11 **Match EQ** (and Maximizer / Dynamics / Imager / Vintage* / the rest) **hangs on
   authorization** in an unattended no-GUI Pedalboard process (probe: `LOAD-FAIL`/timeout). Even if it loaded,
   **capturing the reference curve ("Learn") is a GUI workflow** — there's no headless way to feed it a reference.
   Only the **`Ozone 11 Equalizer`** even loads, and **its EQ doesn't engage** ([[ozone-11-equalizer]]) — so **all
   Ozone 11 modules are DAW-only here.** **Never run Match EQ through `[L] apply-vst-chain` / the `[[vst-preset]]`
   harness — it will hang the render or ship an unprocessed copy + a false `changed:true`.** (That's why there is
   deliberately **no `presets/vst/ozone-11-match-eq-*.json`**.)
2. **Use it in the DAW, hand the bounce to the pipeline.** Learn the reference + apply on the master, **bounce to
   a 24-bit WAV**, drop it in `projects/<track>/mix/` (or `masters/`), then verify the match with the pipeline's
   pure-DSP meters.
3. **For a reference match INSIDE the pipeline, use the verified-headless path:** **[[reference-match]]** — pure-DSP
   `[L] match-eq` derives the source-minus-reference delta curve from a reference and renders the correction as a
   min/linear-phase FIR, no plugin, no learn step. For one shared tone across an EP, **[[house-curve]]** builds a
   reusable profile from refs and matches each mix. Both do exactly what Match EQ does, deterministically.
4. **Meters own tone** (Gemini hears ~16 kbps mono and under-reads highs / over-reads lows): verify the bounce
   with `[L] measure-spectrum` (tilt + 5-band toward the reference) / `[L] compare-tonality` (per-band delta vs
   the ref) — never judge a match off a mono "dark"/"boomy" vibe ([[gemini-audio-understanding]]).

## Decision: where am I being asked to use it?

- **"Match this reference with Ozone in the pipeline" / a headless render** → you **cannot** with this plugin
  (iLok + GUI learn). Say so plainly and offer the substitute: **[[reference-match]]** (pure-DSP match-EQ) or
  **[[house-curve]]** for an EP. Do **not** silently swap — tell the user Match EQ is iLok-blocked/GUI-bound
  headless and what you'll use instead. In most cases the pure-DSP match is the *better* answer anyway.
- **"How do I set Match EQ / how much to match" / they're in the DAW** → give DAW settings (below) + the
  bounce→measure loop.

## Recipe (DAW hand-off — the way this plugin works here)

1. **Learn + apply in the DAW:**
   - **Load the reference** into Match EQ's snapshot and **Learn** its curve; learn **your master** too.
   - **Amount/strength ~50%** to start — full match (100%) chases the reference's room/balance too hard and
     sounds unnatural; halfway keeps your mix's character.
   - **Smoothing** up to avoid a jagged corrective curve (it should look like broad tilt + a couple of bumps, not
     a comb).
2. **Bounce the channel/bus to a 24-bit WAV** → `projects/<track>/mix/<track>_ozonematch.wav`.
3. **Measure the bounce** (the "after"): `[L] measure-spectrum` (tilt + 5-band moved toward the reference),
   `[L] compare-tonality` of the bounce vs the reference (residual per-band delta should shrink), `measure-loudness`.
4. **A/B loudness-matched:** `[L] render-ab` your mix vs the matched bounce (and/or vs the reference); optionally
   `[G] compare-to-reference` on the matched pair. Confirm it's closer to the ref, not just louder/darker.
5. **Continue the pipeline** — [[master-track]] / [[finalize-mix]] / [[delivery-qc]] as normal.

## (Optional) prove the block yourself

If unsure it's still iLok-blocked (e.g. another machine, or after an iZotope update), screen it with
[[vst-verify]] — a `LOAD-FAIL`/timeout = it won't authorize headless (do not use it in the pipeline). Even on a
clean load, the **Learn/reference-capture is GUI-bound**, so the headless `[L] match-eq` ([[reference-match]])
remains the in-pipeline path regardless.

## Outputs

- A DAW recipe (reference / match amount / smoothing) + the measured before→after **tilt / 5-band / residual
  delta vs the reference** on the **bounce**. No `projects/.../mix/` render is produced *by the pipeline* for this
  plugin — the render is the user's DAW bounce (the pure-DSP substitute [[reference-match]] *does* render one).

## Reporting to the user

Lead with the constraint: **"Ozone 11 Match EQ is iLok-blocked headless and its Learn step is GUI-only (verified)
— dial it in your DAW and bounce, or I'll use [[reference-match]] / [[house-curve]] (pure-DSP match-EQ) instead
(usually the better answer here)."** Then give the settings, and once there's a bounce, the before→after **tilt /
5-band / residual delta vs the reference**, A/B loudness-matched.

## Pitfalls

- **Don't headless-render it** — it hangs the render (iLok) or ships an unprocessed copy; `changed:true` would lie.
- **The Learn step is GUI-only** — there's no headless way to capture the reference curve; use `[L] match-eq`.
- **100% match sounds wrong** — full match copies the reference's room/balance; ~50% strength + smoothing keeps
  your mix's identity (the same `match_strength ~0.5` doctrine as [[reference-match]]).
- **A match-EQ is not a fix for a broken mix** — diagnose with [[mix-check]] first; matching papers over the tone,
  not the problems.
- **Mono codec lies about tone** — confirm the match against `[L] measure-spectrum` / `[L] compare-tonality`, not a
  Gemini "dark"/"boomy" call ([[gemini-audio-understanding]]).

## Related

- [`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md) — the Ozone family field guide (render verdicts, iLok, DAW recipes)
- [[reference-match]] — the in-pipeline HEADLESS match-EQ substitute (pure-DSP `[L] match-eq`, no plugin/learn) · [[house-curve]] — one shared tonal target across an EP
- [[ozone-11-equalizer]] — the Ozone EQ sibling (inert headless) · [[ozone-11-imager]] · [[ozone-11-maximizer]] — the iLok-blocked limiter · [[izotope]] — the iZotope suite index
- [[vst-eq]] — the generic plugin-EQ skill this specializes · [[vst-verify]] — prove render-vs-blocked · [[vst]] — index/doctrine
- [[mix-check]] (diagnose first) / [[master-track]] / [[delivery-qc]] — where the bounce goes next · [[gemini-audio-understanding]] — why meters (not Gemini) own the tonal read
