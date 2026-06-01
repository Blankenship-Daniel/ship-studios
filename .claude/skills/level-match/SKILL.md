---
name: level-match
description: Use when you need two files at the same loudness for an honest comparison, or one file brought to a loudness without mastering it — "level-match these so I can A/B fairly", "normalize this to the reference's loudness", "match the loudness of <ref> without limiting", "bring this to -14 LUFS, gain only", "is it actually better or just louder?". Applies ONE peak-safe linear gain (a clamp, not a limiter). Pure DSP, no API key. Stemmy MCP.
---

# Level-match — gain-only, peak-safe loudness match

Goal: bring a file to a target loudness — or to a reference file's loudness —
with a **single linear gain**, so you can compare fairly or set up an A/B
without "louder = better" fooling the ear. `[L] match-loudness` measures
integrated LUFS, applies one gain, and (peak-safe by default) clamps that gain
so the true peak stays under a ceiling. It is **not** a limiter and does **no**
tone-shaping — just level.

The overlap trap: `render-mastered` changes dynamics (HPF → EQ → limiter);
`render-ab` *builds* the A/B file; this only **normalizes level**. Use it as the
honest-comparison primitive that other skills lean on
(`[[reference-match]]`, `[[variant-shootout]]`).

## Prerequisites

- `stemmy-loops` up. `[L] match-loudness` needs the `mixing` extra; no key.
- Provide **exactly one** of `target_lufs` or `reference_path`.

## Recipe

1. **Match** — `[L] match-loudness {path, out_path, reference_path}` (match a
   reference's LUFS) **or** `{path, out_path, target_lufs: -14}` (match a number).
   Leave `peak_safe: true` and set `ceiling_dbtp` (default −1) unless you have a
   reason not to.
2. **Read the result** — in/out LUFS, in/out true peak, the applied gain, and
   **`peak_capped`** (true if the ceiling bit before the file reached the
   target — meaning it's peak-limited, not loudness-matched; to go louder you'd
   need actual limiting via `render-mastered`).

## Outputs

- Level-matched file → `projects/<track>/mix/` (or alongside the A/B set it
  feeds).

## Reporting to the user

State in LUFS → out LUFS, the applied gain, the true peaks, and **whether
`peak_capped` fired**. If it did, say plainly the file couldn't reach the target
by gain alone (it's peaky) and that real loudness needs `[[master-track]]`.

## Pitfalls

- **Exactly one target.** Passing both `target_lufs` and `reference_path` (or
  neither) is an error.
- **`peak_capped` means it didn't fully match.** A peaky file clamps below
  target — don't report it as matched; it's a level ceiling, not a master.
- **Gain only — no tone, no dynamics.** If the goal is to *sound* like the
  reference, that's `[[reference-match]]`; if it's to be release-loud, that's
  `[[master-track]]`.

## Related

- [[reference-match]] — tonal match (this is the loudness half of an honest A/B)
- [[variant-shootout]] — leans on level-matching to compare variants fairly
- [[master-track]] — when you need real loudness (limiting), not gain-only
- [[house-curve]] — level-match while tuning tone across a set
