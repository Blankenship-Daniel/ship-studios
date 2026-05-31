---
name: drum-normalize
description: Use when the user wants to normalize or gain-stage a multi-mic drum kit — "normalize the drums", "bring the kit to -1 dB", "gain-stage these stems". Applies a balance-preserving GLOBAL gain by default (per-file optional, with a warning) so the inter-mic balance and stereo image survive. Local drum-prep CLI, not the stemmy MCP servers.
---

# Normalize / gain-stage a multi-mic drum kit

Lead with the domain rule: on a multi-mic kit the **relative** mic levels ARE the
balance, so normalizing each file independently DESTROYS it. The whole kit must
move together. `mode=global` (default) finds the loudest peak across the *entire*
set and applies that **one** gain to every stem and to both channels of the
stereo files — inter-mic balance and stereo image untouched. `mode=per-file`
maximizes each stem independently but changes the balance (and the sound of the
kit). Source bit depth / format is preserved.

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/scipy/soundfile). No keys/network.
- A folder of drum-mic stems, same sample rate. Roles need not be detected —
  normalize is role-agnostic; it acts on every audio file in the dir.

## Recipe (ordered)

1. **Normalize** — `drum-prep normalize "<stems dir>"`. Full signature:
   `drum-prep normalize <SRC> [--out-dir DIR] [--target-dbfs -1.0] [--mode global|per-file] [--include PATH ...]`
   - `--target-dbfs` (default `-1.0`) — where the loudest peak lands. **If the
     kit already peaks at 0 dBFS, a global normalize to 0 is a no-op** — target
     below 0 to actually gain headroom.
   - `--mode global` (default) — one gain from the set's loudest peak → balance +
     image preserved. `--mode per-file` — each stem to target → **warned
     against** (changes the kit balance).
   - `--include PATH` (repeatable) — fold an extra file (e.g. an fx return living
     in a sibling dir) into the **same** global gain so it tracks the kit.
   - `--out-dir` — default `<SRC>/normalized/`.

## Outputs

- `<dir>/normalized/` — every stem (and any `--include` file) gained,
  length-preserved, source format preserved (24-bit AIFF stays AIFF, etc.).

## Reporting to the user

Lead with `set_peak_dbfs` (the loudest peak across the kit), `global_gain_db`
(the single trim applied), and `gain_spread_db` — **0 means balance preserved**;
any non-zero spread means per-file ran and the balance moved. Then the per-file
table: in/out peak dBFS, gain dB, channels. State the mode plainly so the user
knows whether the kit sound changed.

## Pitfalls

- **per-file changes the kit sound** — only reach for it when the user explicitly
  wants each stem maxed and accepts a re-balance; otherwise stay global.
- **Already at 0 dBFS → target below 0** — a global normalize to 0 is a no-op
  when something already peaks at 0; pick `-1.0` (or lower) to buy headroom.
- **Not a required step.** Phase-align is gain-invariant (correlation ignores
  level) and reference-match does its own headroom trim — normalize only when the
  user actually wants gain-staging, not as a reflex before those flows.

## Related

- [[drum-prep]] — run align + match + audition end to end
- [[drum-phase-align]] — gain-invariant; normalize is not a prerequisite
- [[drum-mix]] — bus the prepped kit to a stereo mix
