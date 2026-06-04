---
name: ozone-11-imager
description: "DAW-ONLY: the iZotope Ozone 11 Imager (4-band multiband stereo imager — widen/narrow per band + mono-maker) is iLok-blocked headless on this rig — it won't authorize in an unattended no-GUI process, so this plugin-specific deep-dive of [[vst-master]] teaches how to dial it in your DAW and which HEADLESS stereo tool (`[L] adjust-stereo`) to use in the pipeline instead. Use when asked: 'Ozone Imager', 'widen the master', 'multiband stereo width', 'mono the lows', 'stereoize with Ozone'."
argument-hint: <audio.wav | goal> [goal: widen|narrow|mono-the-lows|per-band]
---

# ozone-11-imager — drive the Ozone 11 Imager (multiband width)

The plugin-specific, measured version of [[vst-master]] for the **iZotope Ozone 11 Imager** — Ozone's
**4-band multiband stereo imager**: widen or narrow the stereo field **independently per band**, plus a
**mono-maker** to collapse the lows. Full family field guide — render verdicts, the iLok story, DAW recipes —
[`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md). This skill is the workflow.

## The governing facts (read first)

1. **It does NOT render in the headless pipeline on this rig — it's iLok-blocked.** Measured: the Ozone 11
   **Imager** (and Maximizer / Dynamics / Match EQ / Vintage* / the rest) **hangs on authorization** in an
   unattended no-GUI Pedalboard process (probe: `LOAD-FAIL`/timeout). Only the **`Ozone 11 Equalizer`** even
   loads, and **its EQ doesn't engage either** ([[ozone-11-equalizer]]) — so **all Ozone 11 modules are DAW-only
   here.** iZotope's NI/iLok licensing won't satisfy in a headless subprocess. **Never run the Imager through
   `[L] apply-vst-chain` / the `[[vst-preset]]` harness — it will hang the render or ship an unprocessed copy +
   a false `changed:true`.** (That's why there is deliberately **no `presets/vst/ozone-11-imager-*.json`**.)
2. **Use it in the DAW, hand the bounce to the pipeline.** Dial the Imager on the master/bus, **bounce to a
   24-bit WAV**, drop it in `projects/<track>/mix/` (or `masters/`), then verify the image with the pipeline's
   pure-DSP stereo meters.
3. **For per-band width / a mono-maker INSIDE the pipeline, use a verified-headless option:** **`[L] adjust-stereo`**
   — the pure-DSP imager (graduated bass mono-maker 12/24/48 dB-per-octave slope + M/S width). For deeper
   multiband width also reach for the Neutron modules' `width` param ([[neutron-4-equalizer]]). Together these
   own width + low-end mono like the Imager does.
4. **Meters own stereo** (Gemini hears mono and can't read width at all): verify the bounce with
   `[L] measure-stereo` (L-R correlation + mono-sum loss) — a widened master that **collapses in mono** is the
   #1 imager footgun; reject it if mono-sum loss spikes ([[gemini-audio-understanding]]).

## Decision: where am I being asked to use it?

- **"Widen / mono-the-lows this WAV with Ozone in the pipeline" / a headless render** → you **cannot** with this
  plugin (iLok). Say so plainly and offer the substitute: **`[L] adjust-stereo`** (pure-DSP mono-maker + width).
  Do **not** silently swap — tell the user the Imager is iLok-blocked headless and what you'll use instead.
- **"How do I set the Imager / per-band width" / they're in the DAW** → give DAW settings (below) + the
  bounce→measure loop.

## Recipe (DAW hand-off — the way this plugin works here)

1. **Pick the per-band width + mono-maker in the DAW:**
   - **Mono the lows (default first move):** mono-maker / band-1 width down to ~0 below **~120 Hz** — tight,
     phase-safe bass.
   - **Widen the air:** band-4 (highs) width up a little; band-2/3 (mids) leave near neutral so vocals/snare
     stay centered.
   - **Narrow a too-wide mix:** pull width down per band; don't fix a width problem with EQ.
   - Watch the Imager's own correlation meter — but trust the bounce meter for the deliverable.
2. **Bounce the channel/bus to a 24-bit WAV** → `projects/<track>/mix/<track>_ozoneimg.wav`.
3. **Measure the bounce** (the "after"): `[L] measure-stereo` (L-R correlation should stay healthy; **mono-sum
   loss must not spike** — that's the collapse alarm), `[L] measure-spectrum` (width moves shouldn't shift tilt).
4. **A/B loudness-matched + mono-check:** `[L] render-ab` dry vs the imaged bounce, then **sum to mono** and
   confirm nothing vanishes. Confirm it's wider/tighter, not phasey.
5. **Continue the pipeline** — [[master-track]] / [[finalize-mix]] / [[delivery-qc]] as normal.

## (Optional) prove the block yourself

If unsure it's still iLok-blocked (e.g. another machine, or after an iZotope update), screen it with
[[vst-verify]] — a `LOAD-FAIL`/timeout = it won't authorize headless (do not use it in the pipeline); a clean
render with a measurable **mono-sum-loss / correlation** change = it engaged (re-enable it). A bare `changed:true`
is **not** sufficient proof for a stereo unit — verify the correlation actually moved.

## Outputs

- A DAW recipe (per-band width / mono-maker freq) + the measured before→after **L-R correlation / mono-sum loss**
  on the **bounce**. No `projects/.../mix/` render is produced *by the pipeline* for this plugin — the render is
  the user's DAW bounce.

## Reporting to the user

Lead with the constraint: **"Ozone 11 Imager is iLok-blocked headless (verified) — dial it in your DAW and
bounce, or I'll use `[L] adjust-stereo` (pure-DSP mono-maker + M/S width) instead."** Then give the settings, and
once there's a bounce, the before→after **L-R correlation / mono-sum loss** with an honest mono-fold check.

## Pitfalls

- **Don't headless-render it** — it hangs the render (iLok) or ships an unprocessed copy; `changed:true` would lie.
- **Widening collapses in mono** — the #1 imager footgun; always `[L] measure-stereo` and mono-sum the bounce.
- **Don't widen the lows** — keep bass mono (mono-maker below ~120 Hz); widening sub causes phase cancellation.
- **`adjust-stereo` is a TOOL, not a plugin** — cite it as `[L] adjust-stereo`; it's the pure-DSP substitute, no key.
- **Width is not EQ** — fix a "narrow/dull" tone with [[fabfilter-pro-q-4]] / `[L] apply-eq`, not the imager.

## Related

- [`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md) — the Ozone family field guide (render verdicts, iLok, DAW recipes)
- `[L] adjust-stereo` — the in-pipeline HEADLESS stereo substitute (graduated bass mono-maker + M/S width, pure DSP) · [[neutron-4-equalizer]] — multiband `width` headless alternative
- [[ozone-11-equalizer]] — the Ozone EQ sibling (inert headless) · [[ozone-11-maximizer]] — the iLok-blocked limiter · [[ozone-11-match-eq]] · [[izotope]] — the iZotope suite index
- [[vst-master]] — the generic plugin-mastering skill this specializes · [[vst-verify]] — prove render-vs-blocked · [[vst]] — index/doctrine
- [[master-track]] / [[finalize-mix]] / [[delivery-qc]] — where the bounce goes next · [[gemini-audio-understanding]] — why meters (not Gemini) own stereo/width
