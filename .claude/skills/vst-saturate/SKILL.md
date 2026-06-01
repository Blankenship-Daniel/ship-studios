---
name: vst-saturate
description: "Use when the user wants tape/analog color or harmonic saturation via their own plugin — 'run this through tape', 'add some Saturn drive', 'warm up the mix with a tape machine', 'add harmonics/grit', 'console color this stem'. Applies a headless-safe tape/saturation plugin (Tape Machine 80, FabFilter Saturn 2, Airwindows Consolidated) with added-harmonic/HF measured before/after. Stemmy MCP, the `vst` extra."
---

# vst-saturate — tape / harmonic color with your own plugin

Goal: add **harmonic density, warmth, or grit** via a real tape/saturation plugin — tape machine
(`Tape Machine 80`/`440`), multiband saturator (`FabFilter Saturn 2`), or console/tape character
(`Airwindows Consolidated`). A task preset of `[[vst-chain]]`. (Pure-DSP alternative: `[L] saturate-loop`.)

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). Candidates
  ([`docs/vst/README.md`](../../../docs/vst/README.md)): `Tape Machine 80`, `Tape Machine 440`,
  `FabFilter Saturn 2`, `Airwindows Consolidated`.

## Recipe

1. **Baseline** — `[L] measure-spectrum` + `[L] measure-distortion` (THD/HF) + `[L] measure-loudness`.
2. **Pick the flavor** — tape (warmth + gentle HF rolloff + head bump), multiband drive (Saturn),
   console (Airwindows); confirm path via `[L] list-vst-plugins`.
3. **Apply** — `[L] apply-vst-chain {path, out_path:"projects/<track>/mix/<stem>_sat.wav",
   plugins:[{plugin_path, parameters?}], dump_state:true}`. Keep drive subtle (color, not distortion).
4. **Verify** — re-`measure-distortion`/`measure-spectrum`; confirm added HF/harmonics landed and
   `changed:true`. Re-`measure-loudness` (saturation raises level — don't mistake louder for better).

## Outputs

- `projects/<track>/mix/<stem>_sat.wav` + `.state` blob.

## Reporting to the user

- The plugin + drive amount, added-harmonic/HF + tilt deltas, level change, `.state` path.

## Pitfalls

- **Verify it renders, gain-stage, use `uaudio_*`.** Loads ≠ renders — confirm added HF/harmonics landed
  (a 0.00 change = passthrough → run `[[vst-verify]]`). Tape/console need a hot input (~+18 dB) to saturate
  — `apply-vst-chain` can't gain-stage, so use `[[vst-preset]]`; tape controls (ips, tape_type, auto_cal)
  are enum/bool and need the preset harness too. For UADx (Ampex/Studer) use the `uaudio_*.vst3` build —
  for the **Studer A800** specifically, [[studer-a800]] is the measured, plugin-specific deep-dive
  (real param surface, the warm-vs-harsh levers, decision table).

- **Tape DARKENS — it doesn't add "even-order warmth."** Its harmonics are odd/3rd-order (can read harsh
  when over-driven); the real warmth is the LF head bump + gentle compression. If a tape chain sounds harsh,
  the cause is almost always **upstream EQ/drive**, not the tape — isolate & measure (see [[studer-a800]]).

- **Level-matched judgement** — saturation adds loudness; compare at matched level or you'll over-drive.
- **Tape adds HF rolloff + wow/flutter** — fine for glue, not if you need pristine transients.
- Subtle is the point; heavy drive belongs on a creative track, not the 2-bus.

## Related

- `[[studer-a800]]` — measured deep-dive for the UAD Studer A800 tape machine (the plugin-specific version of this skill)
- `[[vst-chain]]` · `[[finalize-mix]]` (its optional VST step 3b is exactly this) · `[[vst-amp]]` (heavier distortion)
- `[L] saturate-loop` (pure-DSP) · `[[vst]]` — index/doctrine
