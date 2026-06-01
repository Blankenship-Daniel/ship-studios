---
name: vst-delay
description: "Use when the user wants delay/echo on a stem or send via their own plugin — 'add a tape echo to the vocal', 'quarter-note delay on the guitar', 'slapback on the snare', 'throw a dub delay', 'EP-34 this'. Applies a headless-safe delay (UAD EP-34 Tape Echo, Delay BRIGADE, FabFilter Timeless 3), favouring a parallel/wet send. Stemmy MCP, the `vst` extra."
---

# vst-delay — delay / echo with your own plugin

Goal: add rhythmic echo or slapback via a real delay plugin — tape echo (`UAD EP-34 Tape Echo`),
BBD/analog (`Delay BRIGADE`), or flexible/tempo (`FabFilter Timeless 3`). A task preset of
`[[vst-chain]]` with a parallel-send bias.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). Candidates
  ([`docs/vst/README.md`](../../../docs/vst/README.md)): `UAD EP-34 Tape Echo`, `Delay BRIGADE`,
  `FabFilter Timeless 3`. **BPM** drives tempo-synced times — read `projects/<track>/track.md`, never guess.

## Recipe

1. **Baseline** — `[L] measure-loudness` (+ `[L] measure-stereo` if it'll be a ping-pong/wide delay).
2. **Pick the delay & time** — tape (warm, self-oscillating feel), analog (dark repeats), digital
   (clean/precise). Compute delay time from BPM (¼ = 60000/BPM ms, ⅛, dotted-⅛ for that lift);
   confirm path via `[L] list-vst-plugins`.
3. **Apply (prefer a wet send)** — 100% wet pass to blend in parallel, or set internal mix via
   `parameters`. `[L] apply-vst-chain {path, out_path:"projects/<track>/mix/<stem>_dly.wav",
   plugins:[{plugin_path, parameters?}], dump_state:true}`.
4. **Verify** — re-`measure-loudness`/`measure-stereo`; confirm `changed:true` and the repeats sit under the dry.

## Outputs

- Wet/processed WAV in `projects/<track>/mix/` (+ `.state`). Note if it's a send to blend.

## Reporting to the user

- The delay + time (note value + ms), feedback/feel, wet vs insert, `.state` path.

## Pitfalls

- **BPM required for sync** — get it from `track.md`; a guessed time smears the groove.
- **Feedback runaway** — high feedback on a self-oscillating tape echo can build up; keep it bounded.
- Filter the repeats (darker = further back) so the delay supports rather than clutters.

## Related

- `[[vst-chain]]` · `[[vst-reverb]]` (space) · `[[groove-tighten]]` (BPM/timing) · `[[vst]]` — index/doctrine
