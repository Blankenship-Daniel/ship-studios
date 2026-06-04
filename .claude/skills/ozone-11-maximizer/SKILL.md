---
name: ozone-11-maximizer
description: "DAW-ONLY: the iZotope Ozone 11 Maximizer (IRC true-peak limiter / loudness maximizer) is iLok-blocked headless on this rig — it won't authorize in an unattended no-GUI process, so this plugin-specific deep-dive of [[vst-master]] teaches how to dial it in your DAW and which HEADLESS limiter ([[fabfilter-pro-l-2]]) to use in the pipeline instead. Use when asked: 'Ozone Maximizer', 'Ozone 11 limiter', 'maximize loudness with Ozone', 'IRC limiter', 'master loudness with Ozone'."
argument-hint: <master.wav | goal> [target: -14lufs|loud|club|transparent]
---

# ozone-11-maximizer — drive the Ozone 11 Maximizer (IRC limiter)

The plugin-specific, measured version of [[vst-master]] for the **iZotope Ozone 11 Maximizer** — Ozone's
flagship **IRC (Intelligent Release Control) true-peak brickwall limiter / loudness maximizer** (the final
stage of the Ozone master chain). Full family field guide — render verdicts, the iLok story, DAW recipes —
[`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md). This skill is the workflow.

## The governing facts (read first)

1. **It does NOT render in the headless pipeline on this rig — it's iLok-blocked.** Measured: the Ozone 11
   **Maximizer / Dynamics / Imager / Match EQ** (and most Ozone 11 modules) **hang on authorization** when
   loaded in an unattended no-GUI Pedalboard process (probe: `LOAD-FAIL`/timeout). Only **`Ozone 11 Equalizer`**
   ([[ozone-11-equalizer]]) renders headless here. iZotope uses NI/iLok licensing that won't satisfy in a
   headless subprocess. **Never run the Maximizer through `[L] apply-vst-chain` / the `[[vst-preset]]` harness —
   it will hang the render or ship an unprocessed copy.** (That's why there is deliberately **no
   `presets/vst/ozone-11-maximizer-*.json`**.)
2. **Use it in the DAW, hand the bounce to the pipeline.** Dial the Maximizer on the master bus, **bounce to a
   24-bit WAV**, drop it in `projects/<track>/masters/`, then verify with the pipeline's pure-DSP meters.
3. **For a limiter INSIDE the pipeline, use a verified-headless option:** [[fabfilter-pro-l-2]] (true-peak
   brickwall, 8 styles, renders headless & **no-iLok** — the direct substitute), or the pure-DSP
   `[L] render-mastered` limiter stage ([[master-track]]). Both own the ceiling like the Maximizer does.
4. **Meters own loudness/peak** (Gemini hears mono): verify the bounce with `[L] measure-loudness`
   (LUFS-I / true-peak dBTP / PLR) + `[G] check-streaming-targets` (pure DSP, **no key**) — never trust the
   plugin's own readout for the deliverable.

## Decision: where am I being asked to use it?

- **"Maximize / limit this WAV in the pipeline" / a headless render** → you **cannot** with this plugin (iLok).
  Say so plainly and offer the substitute: [[fabfilter-pro-l-2]] or pure-DSP [[master-track]]. Do **not**
  silently swap — tell the user the Maximizer is iLok-blocked headless and what you'll use instead.
- **"How do I set the Maximizer / what IRC mode" / they're in the DAW** → give DAW settings (below) + the
  bounce→measure loop.

## Recipe (DAW hand-off — the way this plugin works here)

1. **Pick the IRC mode + ceiling** in the DAW:
   - **Transparent master (default):** `IRC IV` mode, **Threshold** down for ~3–6 dB GR, **Ceiling −1.0 dBTP**
     (−2 dBTP for peaky/transient material — Spotify normalizes peaky masters *up* and is peak-safe, so leave headroom).
   - **Loud/streaming −14 LUFS:** raise Threshold to taste while watching true-peak; keep Character low.
   - **Aggressive/club:** `IRC IV` + higher Threshold, accept more GR.
2. **Print/bounce the master bus to a 24-bit WAV** → `projects/<track>/masters/<track>_ozonemax.wav`.
3. **Measure the bounce** (the "after"): `[L] measure-loudness` (LUFS-I to target, true-peak ≤ ceiling, PLR not
   crushed), `[L] check-clipping` (no inter-sample clip).
4. **Streaming compliance:** `[G] check-streaming-targets` (Spotify/Apple/YouTube/Tidal; pure DSP, **no key**).
   Re-bounce (adjust ceiling/threshold) if a platform will attenuate.
5. **Deliver:** `[L] export-deliverables` (presets + tags) / [[delivery-qc]].

## Outputs

- A DAW recipe (IRC mode / Threshold / Ceiling / Character) + the measured before→after **LUFS-I / true-peak /
  PLR** on the **bounce**. No `projects/.../masters/` render is produced *by the pipeline* — the render is the
  user's DAW bounce.

## Reporting to the user

Lead with the constraint: **"Ozone 11 Maximizer is iLok-blocked headless (verified) — dial it in your DAW and
bounce, or I'll use [[fabfilter-pro-l-2]] / pure-DSP [[master-track]] instead."** Then give the settings, and
once there's a bounce, the before→after **LUFS-I / true-peak / PLR** + streaming-compliance table.

## Pitfalls

- **Don't headless-render it** — it hangs the render (iLok) or ships an unprocessed copy; `changed:true` would lie.
- **A limiter owns the ceiling** — set the ceiling to your `dBTP` target; don't let a later stage re-limit.
- **True-peak ≠ sample peak** — verify dBTP (4× oversampled) on the bounce, not just sample peak.
- **Don't loudness-paper a broken mix** — fix with [[mix-check]] first; the Maximizer is the last stage, not a fix.

## Related

- [`docs/vst/izotope-ozone.md`](../../../docs/vst/izotope-ozone.md) — the Ozone family field guide (render verdicts, iLok, DAW recipes)
- [[fabfilter-pro-l-2]] — the in-pipeline HEADLESS limiter substitute (true-peak, no-iLok) · [[master-track]] — pure-DSP master + limiter
- [[ozone-11-equalizer]] — the one Ozone 11 module that DOES render headless · [[izotope]] — the iZotope suite index
- [[vst-master]] — the generic plugin-mastering skill this specializes · [[vst-verify]] — prove render-vs-blocked · [[vst]] — index/doctrine
- [[delivery-qc]] / [[batch-master]] — where the bounce goes next · [[gemini-audio-understanding]] — why meters (not Gemini) own loudness/peak
