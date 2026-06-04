---
name: master-track
description: Use when the user wants to master a near-final stereo mix to a platform-ready master — "master this track", "get this to -14 LUFS", "make it streaming-ready", "final master for Spotify", "loud but clean", "export master deliverables". Drives the full measure → perceptual feedback → render → re-check → export chain across BOTH MCP servers (loops for DSP measurement/render/export, gemini for the perceptual mastering read and streaming compliance).
argument-hint: <mix.wav> [target platform/LUFS]
---

# Master a track to a platform-ready deliverable

Goal: take a near-final stereo mix and produce a master that hits a chosen
LUFS / true-peak target, is verified compliant against the destination
platform, and ships as the standard format matrix. This skill measures the
source objectively, gets a perceptual read on whether it's release-ready,
renders to the target, re-verifies, and exports.

Two servers are in play. The DSP measurement, render, and export tools live
on **stemmy-loops** (`stemmy-loops:*`); the perceptual and per-platform
compliance tools live on **stemmy-gemini** (`stemmy-gemini:*`). Never invent
a tool — every name below is verified.

## Prerequisites

- `.mcp.json` registers both `stemmy-loops` and `stemmy-gemini` (siblings at
  `../stemmy-loops-mcp`, `../stemmy-gemini-mcp`). Confirm both servers are up.
- `stemmy-loops` measurement/render/export tools used here need the `mixing`
  extra (`render-mastered`, `measure-loudness`); the rest are core DSP.
- `stemmy-gemini` perceptual tools (`mastering-feedback`) need
  `GEMINI_API_KEY`. The per-platform check (`check-streaming-targets`) is
  pure DSP and needs **no** key.
- Resolve up front: input WAV, target platform, and the resulting
  `target_lufs` / `ceiling_dbtp`. Sensible defaults if unstated: streaming
  → `target_lufs = -14`, `ceiling_dbtp = -1.0`; club → `-9` / `-0.3`. If the
  user names a platform but not numbers, pick the platform's canonical pair
  and say so.

## Recipe (ordered)

1. **Baseline loudness** — `stemmy-loops:measure-loudness {path}`. Capture
   integrated / short-term / momentary LUFS, true-peak dBTP, crest, PLR,
   LRA, DR before touching anything. This is the "before" column.
2. **Baseline tonal balance** — `stemmy-loops:measure-spectrum {path}`.
   Tilt and 5-band ratios so the render target can be reasoned about
   (e.g. don't push a dark mix loud and call it done).
3. **Baseline stereo** — `stemmy-loops:measure-stereo {path}`. L/R
   correlation + worst-case mono-sum loss; a master that collapses in mono
   is not release-ready regardless of LUFS.
4. **Clipping / DC / polarity** — `stemmy-loops:check-clipping {path}`.
   Confirm the source isn't already clipped or polarity-inverted going into
   the limiter.
5. **Baseline distortion** — `stemmy-loops:measure-distortion {path}`. THD /
   aliasing proxy so the limiter stage can be judged for *added* distortion
   after the render.
6. **Perceptual mastering read** — `stemmy-gemini:mastering-feedback {path,
   target_platform}`. Master-bus critique with platform guidance and a
   release-readiness boolean. **Map the platform first:** `target_platform` here
   is a critique *mood* (`general`/`streaming`/`club`/`broadcast`/`vinyl`),
   **not** a service name — collapse any streaming service (spotify / apple_music
   / youtube / tidal) to `streaming`; the literal service name goes only to
   `check-streaming-targets` in step 8 (the two tools take disjoint vocabularies
   and each rejects the other's value). Use this to steer the render target (e.g.
   if it flags harshness, set `high_pass_hz` modestly and/or back off
   `transient_shape`). *Alternative:* for a complete, typed starting chain
   rather than a critique, run [[mastering-plan]] (`master-assistant` from a
   creative brief, or `recommend-mastering-chain` measure-first) and drive
   step 7 from its `eq_moves` / `expected_lufs` / limiter ceiling.
7. **Render the master** — `stemmy-loops:render-mastered {path, out_path,
   target_lufs, ceiling_dbtp, ...}`. HPF → transient shape → optional zero-phase
   EQ → loudness normalize → limiter → optional resample + dither. Pass
   `eq_bands` (a zero-phase corrective move), `high_pass_hz`, `transient_shape`,
   `bit_depth`, `sample_rate` only when the measurements/feedback called for
   them. Write to `projects/<track>/masters/`.
8. **Verify streaming compliance** — `stemmy-gemini:check-streaming-targets
   {path: <rendered master>, platforms}`. Per-platform LUFS-I + true-peak
   compliance with recommended attenuation.
9. **Re-render if non-compliant** — if step 8 reports the platform will
   attenuate or the true-peak ceiling is breached, adjust `target_lufs` /
   `ceiling_dbtp` and repeat steps 7–8. Don't ship a master the platform
   will turn down.
10. **Export the format matrix** — `stemmy-loops:export-deliverables {path:
    <approved master>, out_dir: projects/<track>/deliverables/, presets:
    ["distribution_44k_16", "production_48k_24", "master_96k_24"], tag: true}`
    — the 44.1/16 + 48/24 + 96/24 formats. TPDF dither + metadata
    carry-forward.

## Outputs

- Rendered master → `projects/<track>/masters/`.
- Final deliverable matrix → `projects/<track>/deliverables/`.
- Keep intermediate measurement JSON in the run, but the user-facing
  artifacts are the master + the three exported formats.

## Reporting to the user

Give a before → after table: integrated LUFS, true-peak dBTP, crest/PLR,
LRA. State the release-readiness verdict from `mastering-feedback` and the
per-platform compliance result from `check-streaming-targets`. List the
exported file paths. If you re-rendered, say what you changed and why.

## Pitfalls

- **Don't master a broken mix.** If `mastering-feedback` says not release-
  ready, or `measure-stereo` shows large mono-sum loss, hand back to
  [[mix-check]] before rendering — limiting won't fix tonal/phase problems.
- **`render-mastered` does not loop-trim or seam-fix.** It's a stereo-master
  stage. Loop deliverables go through [[loops-to-deliverables]] instead.
- **Verify on the rendered file, not the source.** Step 8 must point at the
  `out_path` from step 7, never the original mix.
- **Targets are numbers.** `target_lufs: -14`, not `"-14 LUFS"`.
- **High-crest material trades loudness for headroom + dynamics.** For very transient sources (crest ~25–27 dB, e.g. an unsquashed drum bus), a gentle / headroom-preserving master lands around `target_lufs: -22` at a `-3` dBTP ceiling (~4 dB of peak control, dynamics intact). Chasing the `-14` streaming default would force ~6+ dB of limiting and leave ~1 dB headroom. Read step 1's crest/PLR before locking the target — you can pick two of {loudness, headroom, dynamics}, not all three. Don't loudness-paper a peaky mix.

## Fan-out

The **baseline measurement is parallel** — steps 1–6 (`measure-loudness` /
`measure-spectrum` / `measure-stereo`, `check-clipping`, `measure-distortion`, and
the `mastering-feedback` read) all read the source independently. Run them as
concurrent Agent calls, then render. The render → verify → re-render → export tail
(steps 7–10) is a sequential mutate-chain and stays serial. For a whole folder,
the `batch-master` workflow already fans this out one-agent-per-track.

## Related

- [[mastering-plan]] — design the chain (typed EQ/comp/limiter targets) before rendering step 7
- [[mix-check]] — run first if the mix isn't clean; mastering is downstream
- [[reference-match]] — when "master it" really means "make it sound like <ref>"
- [[loops-to-deliverables]] — when the deliverable is loops, not a stereo master
- [[understand-audio]] — perceptual recon of a reference before choosing a target
- [[gemini-audio]] — limits of the Gemini mastering read (mono-deaf to stereo/true-peak/loudness — trust the meters for those)
- [[vst-master]] — the opt-in VST alternative: master with your own plugin chain (EQ→comp→limiter) instead of the pure-DSP render
