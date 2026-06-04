---
name: stem-master
description: Use when the user wants to mix-and-master starting from individual stems instead of one stereo bounce — "master from stems", "stem mastering", "I have drum/bass/vocal/music stems, master them", "fix each stem then master", "the kick and bass mask each other, sort it on the stems". Treats each stem correctively (resolve cross-stem masking, de-harsh, transient-shape), sums via drum-prep stem-mix, then hands the bus to [[master-track]]. The unique value is per-stem corrective access BEFORE the limiter — a stereo-bus master physically can't do that.
argument-hint: <stems-dir-or-map> [target platform/LUFS]
---

# Stem master — per-stem corrective mixdown, then hand to mastering

Goal: when you hold the individual stems (drums, bass, vocal, music), fix
problems *on the stems* where you still can — carve the bass out from under
the kick, de-harsh the vocal, add attack to the drums — then sum and master.
A stereo-bus master cannot reach inside a collision; this skill can.

Be precise about what this is: you **mix** stems, then **master** the bus.
This skill does the per-stem **corrective mix** + masking resolution + sum.
The actual loudness/limiting/compliance/export is **not** done here — it is
[[master-track]]'s job, run on the summed bus. Don't duplicate it.

## Prerequisites

- Both `stemmy-loops` and `stemmy-gemini` registered and up.
- Pure DSP, no key: `[G] analyze-stem-masking`, `[G] find-resonances`,
  `[G] find-sibilance`, `[G]`/`[L] measure-*`. `[L] apply-eq`,
  `compress-loop`, `shape-bands` run on the base install (the loudness reads
  need the `mixing` extra); no key. (There is no `core` extra.)
- **Summing is local:** `drum-prep stem-mix` is the drum-prep CLI
  (`uv sync --extra drum-prep`), not an MCP tool. No MCP tool sums an
  arbitrary named-stem set.
- Input is a **map of named stems**. Pull BPM/key from
  `projects/<track>/track.md` if any per-stem tuning is needed.

## Recipe (ordered — measure before/after)

1. **Baseline per stem** — `[L] measure-loudness` + `[L] measure-spectrum`
   on each stem. The "before" column.
2. **Cross-stem masking** — `[G] analyze-stem-masking {stem map}`. Per
   collision: dominant stem, stem-to-cut, center Hz, cut dB, Q. (Optional
   `[L] detect-masking` cross-check.) This is the [[unmask-stems]] step,
   embedded.
3. **Surgical pulls per stem** — `[G] find-resonances` / `[G] find-sibilance`
   on the offending stems for precise notch / de-ess settings.
4. **Corrective EQ per losing stem** — `[L] apply-eq`, one call per stem,
   complementary cuts from steps 2–3 (carve bass under kick, tame vocal mud).
   Cut the loser; boost owners only when a band is genuinely thin. For
   problems a static cut can't handle: `[[de-ess]]` (sibilant stems, from the
   `find-sibilance` settings), `[[de-harsh]]` (ringing/harsh stems), and
   `[[dynamic-eq]]` for level-dependent collisions (carve only when the kick
   hits).
5. **Dynamics / transients where measured** — `[L] compress-loop` to tame a
   dynamic stem, `[[multiband-compress]]` when one band's dynamics misbehave,
   `[L] shape-bands` / `[[drum-punch]]` to add attack to the drum stem — only
   where step 1's crest/spectrum justified it.
6. **Sum the corrected stems** — `drum-prep stem-mix <dir>` → one stereo bus
   (loudness-offset sum with per-stem spec). Local DSP.
7. **Verify the carve worked** — re-run `[G] analyze-stem-masking` +
   `[L] measure-spectrum` on the corrected stems/sum; confirm overlaps shrank
   and nothing was hollowed.
8. **Hand off to mastering** — route the summed bus to [[master-track]] for
   loudness, limiting, streaming compliance, and the export matrix. **Do not
   limit here.**

## Outputs

- Corrected stems → `projects/<track>/stems/corrected/`.
- Summed bus → `projects/<track>/mix/`.
- Then [[master-track]] produces `masters/` + `deliverables/`.

## Reporting to the user

A per-stem move table (stem, freq, cut dB, Q, why), the before → after
masking-overlap read, the summed-bus path, and an explicit "now run
[[master-track]] on the bus" handoff.

## Pitfalls

- **Mix the stems, master the bus.** No `render-mastered`, no LUFS target
  here — that's [[master-track]] on the sum. This stage is corrective + sum.
- **`apply-eq` is single-file.** One call per stem, never a batch.
- **Summing is local-only** (`drum-prep stem-mix`); no MCP tool sums a stem
  set, so don't try to `render-ab` a sum.
- **Cuts → all, boosts → owners.** Resolve masking with complementary cuts
  (the drum-prep guardrail), not by boosting the dominant stem.

## Fan-out

The per-stem stages are independent files — **baseline (step 1) and the
per-losing-stem corrective EQ (steps 3–5) fan out one agent per stem**. The
`stem-process` workflow fans out the per-stem diagnosis specifically (and runs its
executor as one UADx-safe pass); reach for it when treating a full kit. The sum
(step 6) is the barrier; loudness/limiting is the separate [[master-track]]
hand-off (step 8), not parallelized here.

## Related

- [[unmask-stems]] — the masking-only subset, when that's all you need
- [[stem-process]] — batch per-stem corrective + console/tape COLOR (with a reusable executor + re-sum A/B); this skill is the MCP corrective→sum→master path, stem-process is the standalone per-stem treatment stage
- [[de-ess]] / [[de-harsh]] / [[dynamic-eq]] / [[multiband-compress]] — the per-stem corrective skills step 4–5 hand off to
- [[master-track]] — the downstream stage that masters the summed bus
- [[song-mix]] / [[drum-mix]] — balance-and-sum stems (no correction)
- [[mix-check]] — single-bounce diagnosis when you lack stems
