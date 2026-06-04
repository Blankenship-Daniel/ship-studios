---
name: ozone-11-equalizer
description: "DAW-ONLY: the iZotope Ozone 11 Equalizer (8-band post/matching/dynamic EQ with M/S & L/R) loads headless but its EQ does NOT engage offline on this rig — only the locked output gain responds (a naive probe falsely reports 'RENDERS' because muting it via −144 dB output reads as a change), so this plugin-specific deep-dive of [[vst-eq]] teaches how to dial it in your DAW and which HEADLESS EQ ([[fabfilter-pro-q-4]]) to use in the pipeline instead. Use when asked: 'Ozone Equalizer', 'Ozone 11 EQ', 'Ozone EQ on the master', 'match EQ with Ozone', 'mid-side EQ with Ozone'."
argument-hint: <audio.wav | goal> [goal: surgical|tilt|mid-side|de-harsh|match]
---

# ozone-11-equalizer — drive the Ozone 11 Equalizer (8-band)

The plugin-specific, measured version of [[vst-eq]] for the **iZotope Ozone 11 Equalizer** — Ozone's
**8-band post / matching / dynamic EQ** with per-band **Mid/Side & Left/Right** modes (a core stage of the
Ozone master chain). Full family field guide — render verdicts, the iLok story, DAW recipes —
[`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md). This skill is the workflow.

## The governing facts (read first)

1. **Its EQ does NOT engage in the headless pipeline on this rig — it's DAW-only.** The Equalizer is the **only**
   Ozone 11 module that even *loads* in an unattended no-GUI Pedalboard process (Maximizer / Dynamics / Imager /
   Match EQ / Vintage* / the rest **hang on iLok authorization** — `LOAD-FAIL`/timeout). But **measured, the EQ
   never engages headless:** enabling any band and setting gain produced **0 dB change** on every band; only the
   **locked output gain** at an extreme (`−144 dB` ≈ mute) responded — which is exactly why a naive probe falsely
   reports it **"RENDERS"** (it "changed" by being muted, not EQ'd). So **all Ozone 11 modules are DAW-only here.**
   **Never run the Equalizer through `[L] apply-vst-chain` / the `[[vst-preset]]` harness — you'll ship an
   unprocessed copy and a false `changed:true` (or an all-or-nothing mute).** (That's why there is deliberately
   **no `presets/vst/ozone-11-equalizer-*.json`**.)
2. **Use it in the DAW, hand the bounce to the pipeline.** Dial the Equalizer on the channel/bus, **bounce to a
   24-bit WAV**, drop it in `projects/<track>/mix/` (or `masters/`), then measure with the pipeline's pure-DSP meters.
3. **For an EQ INSIDE the pipeline, use a verified-headless option:** [[fabfilter-pro-q-4]] (full surgical /
   dynamic / spectral EQ with M/S, renders headless & **no-iLok** — the direct substitute), or pure-DSP
   `[L] apply-eq` (RBJ shelves/bells/tilt, M/S width-aware), [[de-harsh]] for ringing resonances, and
   [[reference-match]] / [[house-curve]] for a match-EQ move. All own tone like the Ozone EQ does.
4. **Meters own tone** (Gemini hears ~16 kbps mono and under-reads highs / over-reads lows): verify the bounce
   with `[L] measure-spectrum` (tilt + centroid + 5-band) / `measure-loudness` / `measure-stereo` —
   never EQ off a mono "dark"/"boomy" vibe ([[gemini-audio-understanding]]).

## Decision: where am I being asked to use it?

- **"EQ this WAV with Ozone in the pipeline" / a headless render** → you **cannot** with this plugin (its EQ
  doesn't engage offline). Say so plainly and offer the substitute: [[fabfilter-pro-q-4]] or pure-DSP
  `[L] apply-eq` / [[de-harsh]] / [[reference-match]]. Do **not** silently swap — tell the user the Ozone EQ is
  inert headless and what you'll use instead.
- **"How do I dial the Ozone EQ / which band/mode" / they're in the DAW** → give DAW settings (below) + the
  bounce→measure loop.

## Recipe (DAW hand-off — the way this plugin works here)

1. **Pick the EQ moves + per-band mode in the DAW:**
   - **Surgical notch:** a narrow band (high Q), cut a few dB at the offending freq (find it first with
     [[mix-check]] / `[L] measure-spectrum`).
   - **Broad tilt / tone:** a low shelf + high shelf (or Ozone's tilt), ±1–3 dB — gentle on a master.
   - **Mid/Side:** set a band to **Mid** to clean low-mid mud, or **Side** to lift air width (verify mono after).
   - **Dynamic band:** engage the band's dynamic mode to tame a resonance only when it spikes (the
     [[dynamic-eq]] move, in-box).
   - **Match:** Ozone's matching mode learns a reference curve (GUI step) — for that, prefer [[reference-match]].
2. **Bounce the channel/bus to a 24-bit WAV** → `projects/<track>/mix/<track>_ozoneeq.wav`.
3. **Measure the bounce** (the "after"): `[L] measure-spectrum` (tilt/centroid moved as intended; no new 2–5 kHz
   rise), `measure-loudness`, `measure-stereo` (Side moves → correlation / mono-sum loss — reject if mono collapses).
4. **A/B loudness-matched:** `[L] render-ab` dry vs the EQ bounce; optionally `[G] compare-to-reference` on the
   matched pair. Confirm it's better, not just louder.
5. **Continue the pipeline** — [[mix-check]] / [[master-track]] / [[finalize-mix]] as normal.

## (Optional) prove the inert-EQ yourself

If unsure the EQ still fails to engage (e.g. another machine, or after an iZotope update), screen it with
[[vst-verify]] — the decisive test is **enable a band + set a large gain, then `[L] measure-spectrum`**: 0 dB
band change = the EQ is inert (do not use it headless); a real per-band move = it engaged (re-enable it). A bare
`changed:true` is **not** sufficient — the locked output gain alone (mute at −144 dB) trips a naive probe.

## Outputs

- A DAW recipe (bands / Q / gain / M-S or L-R mode / dynamic on-off) + the measured before→after **tilt /
  centroid / 5-band / mono correlation** on the **bounce**. No `projects/.../mix/` render is produced *by the
  pipeline* for this plugin — the render is the user's DAW bounce.

## Reporting to the user

Lead with the constraint: **"Ozone 11 Equalizer's EQ doesn't engage in the headless pipeline (verified — only its
output mute responds, which fakes out a naive probe) — dial it in your DAW and bounce, or I'll use
[[fabfilter-pro-q-4]] / pure-DSP `[L] apply-eq` instead."** Then give the settings, and once there's a bounce, the
before→after **tilt / centroid / 5-band / mono correlation**, A/B loudness-matched.

## Pitfalls

- **Don't headless-render it** — the EQ is inert; you ship an unprocessed copy and a false `changed:true` (or an
  all-or-nothing mute via the locked output gain).
- **The probe's "RENDERS" is a false positive** — it changed because the locked output gain muted it, not because
  the EQ worked. Verify per-band, not just `changed:true`.
- **Side/Mid moves can collapse mono** — always `[L] measure-stereo` the bounce; a Side air lift is a mono-fold risk.
- **Mono codec lies about tone** — don't EQ off a Gemini "dark"/"boomy" call; confirm tilt/centroid against
  `[L] measure-spectrum` first ([[gemini-audio-understanding]]).
- **Set levels / balance before EQ** ([[mix-balance]]); a balance problem is not an EQ problem.

## Related

- [`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md) — the Ozone family field guide (render verdicts, the inert-EQ / false-RENDERS finding, DAW recipes)
- [[fabfilter-pro-q-4]] — the in-pipeline HEADLESS EQ substitute (surgical/dynamic/spectral/M-S, no-iLok) · `[L] apply-eq` — pure-DSP RBJ EQ
- [[de-harsh]] — pure-DSP resonance/ringing suppressor · [[dynamic-eq]] — pure-DSP level-dependent band · [[reference-match]] / [[house-curve]] — pure-DSP match-EQ (the Ozone "match" substitute)
- [[ozone-11-maximizer]] — the iLok-blocked Ozone limiter sibling · [[ozone-11-imager]] · [[ozone-11-match-eq]] · [[izotope]] — the iZotope suite index
- [[vst-eq]] — the generic plugin-EQ skill this specializes · [[vst-verify]] — prove engage-vs-inert · [[vst]] — index/doctrine
- [[mix-check]] / [[master-track]] / [[finalize-mix]] — where the bounce goes next · [[gemini-audio-understanding]] — why meters (not Gemini) own the spectrum read
