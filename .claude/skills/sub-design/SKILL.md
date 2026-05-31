---
name: sub-design
description: Use when a kick/low end needs more weight that EQ can't give — "add sub to the kick", "the low end won't get deep enough", "reinforce the sub", "my reference has way more sub". Synthesizes an envelope-followed sine sub at the kick's fundamental and blends it under — low-end EXTENSION/sustain, not EQ. Local drum-prep CLI, not the stemmy MCP servers.
---

# Reinforce a kick's low end with a synthesized sub layer

Goal: add genuine low-end **extension** a kick lacks, not boost what's already
there. Close kick mics often capture little true fundamental — there's nothing
down low for an EQ to lift, so a band boost just amplifies noise and mud. This
flow **generates** the missing energy: a sine at the kick's fundamental,
amplitude-following the kick's own envelope so it fires on every hit and decays
with it, blended under at a target level relative to the kick.

**Lead with WHY:** a reference-match sub residual that "won't close" is almost
always sustain/extension the source physically lacks — generate it here, don't
chase it with band-EQ. [[drum-reference-match]] now flags exactly this case and
points you to this skill.

**Local DSP** (`drum_prep` package, `drum-prep` console script) — no MCP tools.

## Prerequisites

- `uv sync --extra drum-prep` (numpy/scipy/soundfile). No keys/network.
- A single kick stem (the in/beater mic, or a kick sum). Any channel count —
  the sub is summed into every channel. Source format is preserved.

## Recipe (ordered)

1. **Run it** — `drum-prep sub-design "<kick.wav>" --out "<kick-sub.wav>"`.
   - Detects the kick fundamental via Welch PSD peak, **clamped to 30–80 Hz**;
     override with `--sub-hz <Hz>` if detection lands on a partial or bleed.
   - Generates a sine at that frequency, amplitude-followed by the kick envelope,
     scaled to `--amount-db` (default `-3.0`) relative to the kick RMS, summed in.
   - Anti-clips: one global trim to a -1 dBFS ceiling if the sum overshoots.
2. **Audition** — listen, then dial `--amount-db` (more negative = subtler).
   Re-run; it's cheap and deterministic. There is no fade-in: too much muds the
   low end fast, so move in 1–2 dB steps.

## Outputs

- `<out>` — the kick with the sub blended in, same format/sample-rate/channels
  as the source. The report JSON gives `sub_hz`, `amount_db`, `sub_gain_db`
  (applied gain on the sine), `anti_clip_trim_db`, and the low-band (<60 Hz)
  energy `low_60_before_db` → `low_60_after_db` with the delta.

## Reporting to the user

Lead with the **<60 Hz before → after** delta — that's the extension you added,
in dB. Then give `sub_hz` (and whether it was detected or forced via `--sub-hz`)
and `amount_db`. Flag any non-zero `anti_clip_trim_db` (the sum hit the ceiling
and was trimmed — consider a lower `--amount-db`). State plainly that this is a
**tracked sine added under the kick**, not a kick replacement or a band boost.

## Pitfalls

- **It adds a tracked sine, not a new kick.** It reinforces the fundamental; it
  won't fix attack, click, or body — that's EQ/transient work.
- **Too much `--amount-db` muds the low end.** Always audition; the default `-3`
  is a starting point, not a target. Subtle usually wins.
- **Detected `sub_hz` can land on a partial** if the kick is tuned high or the
  mic has bleed — force it with `--sub-hz` (kicks usually sit ~40–60 Hz).
- **Sub vs bass clash:** if the generated sub fights the bassline in the full
  mix, sidechain/duck the sub at mix time — that's a [[drum-mix]] / mix decision,
  not something this stem-level tool resolves.
- Do this **after** phase-align and reference-match, before mastering — the
  synthesized sine is phase-coherent and shouldn't be re-aligned.

## Related

- [[drum-reference-match]] — flags an unclosable sub residual and sends you here
- [[drum-mix]] — where a sub-vs-bass clash gets sidechained/balanced
- [[master-track]] — the downstream stage that finalizes the low end
