---
name: drum-mix
description: Use when the user wants to mix a prepped multi-mic drum kit to a stereo bus — "mix the drum kit", "balance and pan the drums", "bounce the kit to stereo with the room and plate". Sets balance by measured loudness offsets vs the overhead anchor, pans by perspective (drummer/audience), channel-balances a spaced room, and folds in an optional FX/plate return; flat mode does a unity bounce. Tone/timing prep ([[drum-prep]]) and mastering ([[master-track]]) are separate stages. Local drum-prep CLI, not the stemmy MCP servers.
argument-hint: <stems dir> [feel] [perspective]
---

# Mix a prepped multi-mic drum kit to a stereo bus

Goal: fold a phase-aligned, reference-matched kit down to one stereo bus —
balanced by measured loudness, panned by listening perspective, with the room
channel-balanced and an optional FX/plate return folded in. The overhead is the
anchor: it already holds the kit's natural relative levels and image, so every
other mic is balanced *against it* rather than to an absolute target. This is a
flat unity sum, not a fader/automation mix — glue and loudness belong to
[[master-track]], tone/timing to [[drum-prep]].

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/scipy/soundfile/pyloudnorm). No keys/network.
- A prepped kit: phase-aligned and (ideally) reference-matched, same sample rate,
  overheads present (stereo or an L/R pair). Roles auto-detect from filenames; pin
  with a `kit.json` if needed. An FX/aux return (role `fx`: plate/reverb/send) is
  **auto-detected and folded in as a stereo return** — pass `--plate` only to fold
  one that lives OUTSIDE the stems dir or to set a custom `--plate-offset`.

## Recipe (ordered)

1. **Confirm the two taste-forks first** — surface both before running:
   - `--feel roomy | punchy | natural | dry` — how loud the room/overhead
     ambience sits vs the close mics (`dry` pulls the room down hardest).
   - `--perspective drummer | audience` — whose left/right. `drummer` puts the
     hi-hat LEFT and flips the overhead/room L↔R; `audience` mirrors it.
2. **Mix** — `drum-prep mix "<SRC>" [--feel …] [--perspective …] [--plate PATH]`.
   Behavior:
   - resolves kit roles from `<SRC>`; reads the actual stems from `--stems-dir`
     (default `<SRC>/ref-matched/` if present, else `<SRC>`).
   - **Balance** = per-**role** integrated-loudness (LUFS) offsets measured vs the
     overhead anchor, shaped by the chosen feel.
   - **Pan** by perspective; a **spaced room pair is channel-balanced** (L/R
     trimmed to match) before placement.
   - **FX returns** (role `fx`) fold in as stereo returns, never summed as a kit
     mic. An `fx`-role stem already in the dir auto-folds at the feel's `fx` offset;
     `--plate PATH` folds an external return at `--plate-offset` dB (default
     `-19.0`). If `--plate` points at a file already in the dir it is **deduped**
     (folded once, the explicit offset winning) — so it's safe either way.
   - `--flat` overrides all of it: a **unity bounce** — overhead/room kept stereo,
     mono mics centred, one anti-clip trim — i.e. a flat print of the prepped kit.
   - **No bus compression or limiting** — glue + loudness are [[master-track]]'s
     job.
   Full surface: `drum-prep mix <SRC> [--manifest M] [--stems-dir DIR]
   [--out-dir DIR] [--feel roomy|punchy|natural|dry] [--perspective
   audience|drummer] [--plate PATH] [--plate-offset -19.0] [--flat] [--t0 44]
   [--dur 12]`. `--t0`/`--dur` set the excerpt window.

## Outputs

- `<SRC>/mix/` (default; override with `--out-dir`) — a 24-bit WAV stereo bus plus
  a 12 s excerpt. One **global** anti-clip trim is applied to the whole bus so the
  inter-stem balance is preserved.

## Reporting to the user

Give the per-stem balance table: **role, loudness offset (dB vs anchor), applied
gain, placement (pan / L-R / centre)**. Then the **global anti-clip trim**, the
final bus **peak / LUFS**, and the **plate level** (if `--plate` was used). Always
restate the two taste-forks actually chosen (feel + perspective) so the user can
re-run with the other fork.

## Pitfalls

- **Balance by measured loudness — keep the overhead UNDER the close mics.** This skill sets per-role
  levels vs the OH anchor; if the OH leads, the cymbals/hi-hat dominate (set it a few LU under kick/snare).
  De-spill spill-heavy close mics with `[[bleed-gate]]` before raising them. The general measure-driven
  method (+ ad-hoc stem sets) is `[[mix-balance]]`. Never eyeball gains or peak-normalize the sum — a
  balance problem is not an EQ problem.
- **It's a flat unity sum, not a fader/automation mix.** No moves over time, no
  bus comp. For finer or section-by-section balance, mix from the stems in a DAW.
- **An FX return is auto-folded by its `fx` role, not summed as a mic.** An
  `fx`-role stem in the dir folds as a stereo return on its own; `--plate` is only
  for a return that lives OUTSIDE the dir or to set a custom offset, and a `--plate`
  that points at an in-dir fx file is deduped (folded once) — no double-count.
- **Detect clean first.** Role detection is what keeps a return OUT of the mic sum,
  so make sure each return carries the **FX role** (see [[drum-prep]]) before
  mixing — a return mis-detected as a kit mic *will* be balanced/panned as one.
- **`--flat` ignores feel/perspective/plate** — it's a unity print, not a balanced
  mix. Don't reach for it expecting placement.

## Related

- [[drum-prep]] — prep the kit (phase-align + reference-match) before mixing
- [[stem-process]] — per-stem corrective + console/tape color before the sum
- [[drum-reference-match]] — per-stem tonal match, the usual upstream step
- [[drum-audition]] — loudness-matched A/B of the kit before/after
- [[warm-drum-bus]] — warm/tight drum-bus tone chain after the sum (tape + tilt + low control)
- [[master-track]] — glue, loudness, and platform-ready master of the bus
- [[mix-check]] — MCP perceptual/measurement diagnosis of a finished mix
