---
name: mastering-plan
description: Use when the user wants a mastering chain DESIGNED before rendering — "what mastering chain should I use", "suggest a master chain for this", "I want it loud and warm, plan the master", "recommend EQ/comp/limiter settings for mastering", "give me a starting chain for club/streaming/vinyl", "plan the master from a creative brief". Meter-grounded, typed chain PLAN (no audio rendered). Gemini-driven, needs GEMINI_API_KEY. Stemmy MCP.
argument-hint: <near-final-mix.wav> [intent/platform brief]
---

# Mastering plan — meter-grounded chain design (no render)

Goal: turn a near-final mix + a brief into ONE complete, typed mastering chain
*before* committing to a render. Two entries, pick by what the user gives you:

- `[G] master-assistant` — when the user gives a **creative brief**
  (`intent`: loud / dynamic / warm / bright / balanced / punchy, `intensity`:
  subtle / medium / strong, optional `style`, `target_platform`). Measures
  ground-truth meters, builds a deterministic starting chain, and has Gemini
  *listen* and refine it.
- `[G] recommend-mastering-chain` — when you want a **measure-first** proposal:
  it measures LUFS/TP/RMS/crest/tilt, builds a platform-sized chain, and returns
  Gemini's `agree_with_chain` flag + `refinements`.

Both **emit a plan, not audio** — the typed chain (`eq_moves`, compression,
saturation, stereo, limiter, `expected_lufs`) drops straight into
`[[master-track]]`'s render step (`render-mastered` / `apply-eq`). This is the
planning front-end to `[[master-track]]`, not a renderer.

## Prerequisites

- `stemmy-gemini` up + `GEMINI_API_KEY` (both tools listen). The meters they
  ground on are measured server-side.
- A near-final **stereo** mix. If the mix isn't clean, run `[[mix-check]]`
  first — a plan can't fix a broken mix.

## Recipe

1. **Pick the entry** — creative brief → `[G] master-assistant {path, intent,
   intensity, style?, target_platform}`. No brief / "just suggest one" →
   `[G] recommend-mastering-chain {path, target_platform}`.
2. **Read the plan** — the returned `chain` (EQ moves, bus comp, optional
   multiband, saturation, stereo, limiter) + `meters` it was grounded on +
   `engineer_notes`. For `recommend-mastering-chain`, weigh `agree_with_chain`
   and fold in `refinements`.
3. **Hand off to render** — pass the typed chain to `[[master-track]]`: the
   `eq_moves` → `apply-eq`/`render-mastered eq_bands`, the `expected_lufs` →
   `target_lufs`, the limiter ceiling → `ceiling_dbtp`. Then verify compliance
   there (`check-streaming-targets`).

## Outputs

- The typed chain (a plan/JSON) — **no audio**. Record it in the run / `track.md`
  so the master is reproducible. Rendering happens in `[[master-track]]`.

## Reporting to the user

Present the chain as concrete moves (EQ bands, comp ratio/threshold, limiter
ceiling, `expected_lufs`), state the **meters it was grounded on**, and flag any
Gemini `refinements` / disagreement. Be explicit: this is a plan — nothing was
rendered yet; next step is `[[master-track]]`.

## Pitfalls

- **It plans, it doesn't render.** No master WAV comes out of this — don't
  report a finished master.
- **Gemini hears mono ~16 kbps.** The numbers are meter-grounded for exactly
  this reason; trust the meters over any by-ear loudness/stereo claim
  ([[gemini-audio-understanding]]).
- **Don't plan on a broken mix.** Tonal/phase/balance problems → `[[mix-check]]`
  first; mastering can't fix them.
- **The chain is a starting point.** Re-measure after the real render in
  `[[master-track]]` and adjust — the plan is grounded, not infallible.

## Related

- [[master-track]] — renders the plan; the natural next step
- [[mix-check]] — run first if the mix isn't clean
- [[finalize-mix]] — bus glue before you plan the master
- [[gemini-audio-understanding]] — why the plan is meter-grounded (Gemini = mono)
