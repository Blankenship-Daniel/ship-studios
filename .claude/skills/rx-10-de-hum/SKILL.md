---
name: rx-10-de-hum
description: "DAW-ONLY: the iZotope RX 10 De-hum (mains hum / buzz remover — 50/60 Hz + harmonics) renders PASSTHROUGH headless on this rig — it self-bypasses offline (measured Δparam = 0.00 across all 6 pushed params, needs the GUI), so this plugin-specific deep-dive of [[vst-chain]] (RX repair) teaches how to dial it in your DAW and which HEADLESS de-hum path (a notch via `[L] apply-eq`, or [[rx-10-spectral-de-noise]]) to use in the pipeline instead. Use when asked: 'RX De-hum', 'remove the mains hum', 'kill the 50/60 Hz buzz', 'de-hum this recording', 'electrical hum/ground-loop buzz'."
argument-hint: <audio.wav | goal> [goal: 50hz|60hz|harmonics|ground-loop]
---

# rx-10-de-hum — drive the RX 10 De-hum (mains hum remover)

The plugin-specific, measured version of [[vst-chain]] (RX repair) for the **iZotope RX 10 De-hum**
(`RX 10 De-hum.vst3`) — iZotope's **mains-hum / buzz remover** (a tracking notch comb at 50/60 Hz + harmonics,
for ground loops, light dimmers, transformer buzz). Full family field guide — per-module render verdicts, the
param surfaces, the niche siblings — [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md). This skill is
the workflow.

## The governing facts (read first)

1. **It does NOT process in the headless pipeline on this rig — it renders PASSTHROUGH.** Measured: `RX 10
   De-hum.vst3` loads and echoes every parameter, but the DSP never engages — **Δ=0.00000 across all 6 pushed
   params** (it self-bypasses offline; it needs the GUI to engage its adaptive hum tracker). It's the textbook
   **"loads ≠ renders"** trap — unlike the **five RX modules that DO render & engage** ([[rx-10-voice-de-noise]],
   [[rx-10-spectral-de-noise]], [[rx-10-de-click]], [[rx-10-de-ess]], [[rx-10-de-reverb]]), De-hum is the one
   passthrough in the RX set here. **Never run De-hum through `[L] apply-vst-chain` / the `[[vst-preset]]` harness
   — you'll ship an unprocessed copy and a false `changed:true`.** (That's why there is deliberately **no
   `presets/vst/rx-de-hum-*.json`**.)
2. **Use it in the DAW, hand the bounce to the pipeline.** Dial De-hum (or the RX standalone) on the track,
   **bounce to a 24-bit WAV**, drop it in `projects/<track>/mix/` (or `stems/`), then verify with the pipeline's
   pure-DSP meters.
3. **For de-hum INSIDE the pipeline, use a verified-headless path:**
   - **A manual notch at the measured hum line via `[L] apply-eq`** — find the exact line first with [[mix-check]]
     (`[L] measure-spectrum`). ⚠ **Mains hum sits slightly OFF integer 50/60 Hz** (e.g. ~50.8 Hz, harmonics
     wander ±2–3 Hz) — re-center the notches on the **measured** lines (not integer multiples) at **~Q14**, and
     where the hum **overlaps the kick fundamental** use an **expander** (level-dependent), not a static notch,
     so you don't gut the kick.
   - **[[rx-10-spectral-de-noise]]** (which DOES render here) — subtract a steady tonal hum/buzz bed via FFT
     spectral subtraction (drive its `tonal_reduction_db`; keep it gentle so it doesn't eat musical highs).
4. **Meters own it** (Gemini hears ~16 kbps mono): verify the bounce with `[L] measure-spectrum` (the hum spike +
   its harmonics should be gone, the rest of the tone intact) / `measure-loudness`. Confirm against a **silent
   pre-roll** if there is one — the hum line is easiest to read where nothing else plays.

## Decision: where am I being asked to use it?

- **"De-hum this WAV with RX in the pipeline" / a headless render** → you **cannot** with this plugin (it
  passthroughs). Say so plainly and offer the substitute: a **notch via `[L] apply-eq`** on the measured line, or
  **[[rx-10-spectral-de-noise]]**. Do **not** silently swap — tell the user RX De-hum passthroughs headless and
  what you'll use instead.
- **"How do I set RX De-hum / which mains freq" / they're in the DAW** → give DAW settings (below) + the
  bounce→measure loop.

## Recipe (DAW hand-off — the way this plugin works here)

1. **Pick the base frequency + harmonics in the DAW:**
   - **Base:** `50 Hz` (Europe / most of the world) or `60 Hz` (Americas) — match the recording's mains.
   - **Harmonics:** enough to cover the buzz (hum is rich in odd/even multiples) — but only as many as you hear;
     each notch costs a sliver of tone.
   - **Adaptive/link mode** to let it track a slightly-flat mains line (this is the part that needs the GUI).
   - Use the De-hum **output-hum-only** monitor to confirm you're removing buzz, not music.
2. **Bounce the track to a 24-bit WAV** → `projects/<track>/mix/<track>_rxdehum.wav` (or learn/print in the RX
   standalone and export).
3. **Measure the bounce** (the "after"): `[L] measure-spectrum` (the hum spike at the mains line + harmonics gone;
   broadband tone unchanged), `measure-loudness`.
4. **A/B loudness-matched:** `[L] render-ab` dry vs the de-hummed bounce; confirm the hum left and the music
   didn't.
5. **Continue the pipeline** — [[mix-check]] / [[master-track]] / [[delivery-qc]] as normal. Corrective insert,
   not a master.

## (Optional) prove the passthrough yourself

If unsure it still passthroughs (e.g. another machine, or after an iZotope update), screen it with [[vst-verify]]
— push a De-hum param and `[L] measure-spectrum`: **Δ=0.00 = passthrough** (do not use it headless); a real notch
at the mains line = it engaged (re-enable it). A bare `changed:true` is **not** sufficient proof.

## Outputs

- A DAW recipe (base freq / harmonics / adaptive) + the measured before→after **mains-line + harmonic spectrum**
  on the **bounce**. No `projects/.../mix/` render is produced *by the pipeline* for this plugin — the render is
  the user's DAW bounce (the substitute `[L] apply-eq` / [[rx-10-spectral-de-noise]] *do* render one).

## Reporting to the user

Lead with the constraint: **"RX 10 De-hum renders passthrough headless (verified Δ=0 — it needs the GUI) — dial
it in your DAW and bounce, or I'll notch the measured mains line with `[L] apply-eq` (or use
[[rx-10-spectral-de-noise]]) instead."** Then give the settings, and once there's a bounce, the before→after
**mains-line + harmonic spectrum**, A/B loudness-matched.

## Pitfalls

- **Don't headless-render it** — it ships an unprocessed copy + a false `changed:true`; Δ=0 across every param.
- **Hum sits OFF integer 50/60 Hz** — a Q30 notch at exactly 50/60 Hz MISSES a ~50.8 Hz line; re-center on the
  **measured** lines (`[L] measure-spectrum`) at ~Q14, and confirm in a silent pre-roll.
- **Where hum overlaps the kick fundamental, expand — don't notch** — a static notch at the kick's note guts the
  kick; use a level-dependent move ([[dynamic-eq]]) instead.
- **Don't over-notch** — each harmonic notch costs tone; remove only the harmonics you actually hear.
- **It's a tonal-hum tool, not a de-noiser** — broadband hiss/rumble is [[rx-10-voice-de-noise]] / `[L]
  clean-loop`; a "harsh" mix is [[de-harsh]], not de-hum.

## Related

- [`docs/vst/izotope-rx.md`](../../../docs/vst/izotope-rx.md) — the full RX 10 field guide (per-module render verdicts; the De-hum passthrough finding)
- `[L] apply-eq` — the pure-DSP de-hum substitute (notch the measured mains line, ~Q14) · [[rx-10-spectral-de-noise]] — the RENDERS-headless tonal-hum subtractor · [[dynamic-eq]] — expand (don't notch) where hum overlaps the kick
- [[rx-10-voice-de-noise]] · [[rx-10-de-click]] · [[rx-10-de-ess]] · [[rx-10-de-reverb]] — the RX modules that DO render & engage headless · [[izotope]] — the iZotope suite index
- [[vst-chain]] — the generic headless VST workflow this specializes · [[vst-verify]] — prove render-vs-passthrough · [[vst]] — index/doctrine
- [[mix-check]] (find the exact hum line first) / [[master-track]] / [[delivery-qc]] — where the bounce goes next · [[gemini-audio-understanding]] — why meters (not Gemini) own the spectrum read
