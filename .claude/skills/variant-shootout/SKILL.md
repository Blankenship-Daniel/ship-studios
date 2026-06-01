---
name: variant-shootout
description: "Use when the user wants to compare processing options by ear — 'try a few master loudness targets and let me pick', 'A/B these mix versions', 'which reference-match strength sounds best', 'shoot out 0.75 vs 0.9'. Renders N loudness-matched variants and presents them for a pick, optionally ranked by Gemini. Spans both MCP servers."
---

# Shoot out processing variants for a by-ear pick

Goal: when a step has a tunable knob — master loudness target, ceiling,
reference-match strength, drum-mix feel — render several candidates, present
them **loudness-matched** so the choice is on tone/feel and not on raw level,
and let the user pick. This skill judges; it does **not** decide. Surface the
fork with a recommendation and the numbers behind it; the human owns the call.

Two servers are in play. The render and A/B tools live on **stemmy-loops**
(`[L]`); the perceptual ranking tool lives on **stemmy-gemini** (`[G]`). Drum
kits route through the local `drum-prep` CLI instead. Never invent a tool —
every name below is verified against CLAUDE.md.

## Prerequisites

- `.mcp.json` registers both `stemmy-loops` and `stemmy-gemini` (siblings at
  `../stemmy-loops-mcp`, `../stemmy-gemini-mcp`). Confirm both are up.
- `[L]` render/A/B tools (`render-mastered`, `render-ab`, `measure-loudness`)
  need the `mixing` extra; pure DSP, no key.
- `[G] compare-audio-files` needs `GEMINI_API_KEY`. Ranking is **optional** —
  skip it and just present the A/B pairs if no key or the user only wants to
  listen.
- Resolve up front: the input WAV, **which knob** is being shot out, and the
  **list of values** to try (e.g. `target_lufs ∈ {-14, -12, -10}`, or
  reference-match `strength ∈ {0.75, 0.9}`). If the user gives a vague range,
  pick 2–4 concrete points and say so. More than ~5 variants is fatigue, not
  signal — cap it.

## Recipe (ordered)

1. **Baseline the source** — `[L] measure-loudness {path}` and
   `[L] measure-spectrum {path}`. The "before" column the variants move from.
2. **Render the variants** — one call per knob value, each into its **own
   sibling dir**, never overwriting:
   - Loudness/ceiling shootout → `[L] render-mastered {path, out_path:
     projects/<track>/masters/v_<value>/master.wav, target_lufs|ceiling_dbtp,
     ...}` per value.
   - Reference-match strength → re-run the [[reference-match]] EQ at each
     strength (or for a kit, `drum-prep reference-match <dir> --strength <s>
     --out-dir <dir>/ref-matched-<s>`).
   - Drum-mix feel → `drum-prep mix <dir> --feel <feel> --out-dir
     <dir>/mix-<feel>`.
3. **Measure each variant** — `[L] measure-loudness` + `[L] measure-spectrum`
   on every rendered file. This is the variant matrix: param → measured LUFS /
   true-peak / tilt. Confirm the renders actually landed on their targets.
4. **Build loudness-matched A/B files** — pair each variant against the
   baseline (or against each other) with `[L] render-ab {processed: <variant>,
   reference: <baseline>, out_path: projects/<track>/mix/ab_<value>.wav}`. It
   loudness-matches and concatenates `[reference | gap | processed]` into one
   WAV so each comparison is level-fair. For a drum kit use `drum-prep
   audition <dir> --reference <ref>` instead, which emits loudness-matched
   compare halves directly.
5. **Optional perceptual rank** — `[G] compare-audio-files {paths: [<variant
   WAVs, 2–10>], ...}`. Returns discriminating features and a relative
   ordering. Feed it the variants (not the A/B concatenations) so it judges the
   candidates themselves.
6. **Present the fork** — lay out the matrix, the A/B file paths to audition,
   the optional Gemini ranking, and your recommendation with its trade-off.
   Stop and let the user choose.

## Outputs

- Each variant in its own dir under `projects/<track>/masters/` (or the kit's
  `ref-matched-<s>/` / `mix-<feel>/`).
- Loudness-matched A/B WAVs → `projects/<track>/mix/ab_*.wav`.
- No "winner" is written or promoted — the user picks; promotion is a separate,
  explicit step.

## Reporting to the user

- **Variant matrix**: one row per param value → measured integrated LUFS,
  true-peak dBTP, spectral tilt (and any other knob-relevant number).
- **A/B paths**: the loudness-matched files to listen to, labeled by value.
- **Recommendation**: your pick and the residual deltas behind it (e.g. "v_-12
  holds tilt within 0.4 dB of baseline while +2 LU louder; v_-10 starts
  flattening transients"). Frame it as a suggestion, then explicitly hand the
  choice back.

## Pitfalls

- **ALWAYS loudness-match before comparing.** Louder reads as better — an
  un-matched A/B is a level test, not a tone test. That's the whole point of
  the `render-ab` / `drum-prep audition` step; never skip it. To level-match a
  pair without building a concatenated A/B file, [[level-match]] applies the
  gain-only normalization directly.
- **One dir per variant.** Don't write into the same `out_path` twice or you'll
  clobber the candidate you're trying to compare against.
- **This judges, it doesn't decide.** Do not auto-promote a winner, overwrite
  `mix/` or `masters/<final>`, or proceed downstream on the model's pick.
  Surface the fork and wait.
- **Cap the count.** 2–4 well-chosen points beat 8 — and `compare-audio-files`
  takes 2–10 files, so a huge sweep won't even rank in one call.
- **Targets are numbers.** `target_lufs: -12`, `strength: 0.9` — not strings.

## Related

- [[drum-reference-match]] — generate the per-strength kit variants this shoots out
- [[drum-audition]] — loudness-matched kit A/B halves to feed the comparison
- [[level-match]] — gain-only loudness match (the primitive behind a fair A/B)
- [[master-track]] — once a loudness/ceiling variant wins, master to it for real
- [[reference-match]] — the EQ step whose strength this can sweep
- [[vst-shootout]] — the same shootout discipline for VST plugin chains
