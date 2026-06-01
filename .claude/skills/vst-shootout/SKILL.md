---
name: vst-shootout
description: "Use when the user wants to compare several VST chains/presets and pick the best — 'try a few vintage chains and pick the best', 'shoot out these plugin variants', 'A/B my VST chains', 'which compressor/tape sounds best on this', 'explore a few mastering chains'. Renders N VST chain/preset variants on one source, measures each, and adversarially judges them to a winner. The VST-chain cousin of variant-shootout (which is loudness/mix-version focused). Stemmy MCP, the `vst` extra."
---

# vst-shootout — render N VST chains and judge to a winner

Goal: explore a creative VST decision (which chain / preset / settings) by rendering several variants
on the same source, measuring each, and **adversarially judging** them — the workflow used to choose
the vintage-1960s drum sound. Distinct from `[[variant-shootout]]` (master-loudness / mix-version
focused); this compares **plugin chains**.

## Prerequisites

- `[L] apply-vst-chain` (or `presets/vst/apply_vst_preset.py` for gain-staged/enum chains) + `[L] measure-*`
  via the `vst` venv. Optional ears: `[G] compare-to-reference` / `[G] mastering-feedback` (needs `GEMINI_API_KEY`).
  Plugins must **render** — pre-screen with `[[vst-verify]]`; use `uaudio_*` paths.

## Recipe

1. **Define 2–5 variants** — distinct chains, presets, or param sweeps (e.g. "warm/dark", "hard-smash",
   "175-B tube"). Give each a short label + recipe.
2. **Render SERIALLY** — one variant after another (UADx dislikes concurrent hosts → don't parallelize the
   renders) → `projects/<track>/mix/<label>.wav`. Use `[[vst-preset]]`/`apply_vst_preset.py` when the
   variant needs gain-staging or enum params.
3. **Measure each** — `[L] measure-loudness` + `[L] measure-spectrum` (+ `measure-stereo`/`measure-microdynamics`
   as relevant). Build a comparison table.
4. **Judge** — score the variants against the goal across distinct lenses (tone, dynamics, image,
   musicality). For a rigorous pick, run a **Workflow adversarial judge panel** (parallel lenses →
   synthesis) — requires multi-agent opt-in. Optionally add Gemini ears via `[G] compare-to-reference`.
5. **Pick + refine** — declare the winner, note dissent, apply one concrete refinement, and (optionally)
   `render-ab` a loudness-matched audition. Save the winner with `[[vst-preset]]`.

## Outputs

- N variant WAVs + a measurement comparison table; the winner (optionally saved as a preset + an A/B).

## Reporting to the user

- The comparison table (per-variant key metrics), the winner + one-line rationale per variant, any
  cross-lens dissent, and the suggested refinement.

## Pitfalls

- **Render serially** — concurrent UADx hosts contend and can fail; one variant at a time.
- **Loudness-match for the listen** — gain/comp/tape make variants different loudness; use `[L] render-ab`
  (loudness-matched) so the pick isn't just "louder wins".
- **Verify renders first** — a passthrough variant will look like a near-duplicate; pre-screen with `[[vst-verify]]`.

## Related

- `[[variant-shootout]]` — the loudness/mix-version sibling · `[[vst-chain]]` / `[[vst-preset]]` — render the variants
- `[[vst-verify]]` — pre-screen · `[[vst]]` — index/doctrine
