---
name: vst-chain
description: "Use when the user wants to run an arbitrary chain of their own VST3/AU effect plugins on an audio file — 'run these plugins on my mix', 'apply Pultec then Black 76 to this stem', 'process this through a VST chain', 'insert my plugin on this loop'. The generic, headless, measured apply-vst-chain workflow that every other vst-* skill is a preset of. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [plugins/intent]
---

# vst-chain — apply a headless VST3/AU effect chain to a WAV

Goal: process one WAV through an **ordered chain of headless-safe effect plugins**, offline and
headless, with a measured before/after so the change is proven and reproducible. This is the
backbone of the `[[vst]]` suite — the per-task skills just preset the category and which meters
to read.

## Prerequisites

- `[L] apply-vst-chain` + `[L] list-vst-plugins` (needs `uv sync --extra vst` in `../stemmy-loops-mcp`).
- A stereo/mono **WAV** (stem, bus, loop). Resolve the path up front.
- Plugins installed **and authorized** on this Mac. Only headless-safe titles — see
  [`docs/vst/README.md`](../../../docs/vst/README.md). No `GEMINI_API_KEY` needed unless you add a
  `[G]` measurement step.

## Recipe (ordered — the canonical VST recipe)

1. **Baseline** — `[L] measure-loudness {path}` + `[L] measure-spectrum {path}` (add
   `[L] measure-stereo` if width/space matters). This is the "before" column.
2. **Choose plugins** — pick candidates from the inventory ([`docs/vst/README.md`](../../../docs/vst/README.md));
   confirm each on-disk path with `[L] list-vst-plugins {name_contains:"<name>"}`. **Prefer the build that
   renders** — for UADx use `uaudio_*.vst3`, never the `UAD ….component` twins (they passthrough). If unsure a
   plugin actually processes, pre-screen with `[[vst-verify]]` (loads ≠ renders). Confirm ambiguous picks with the user.
3. **Apply** — `[L] apply-vst-chain {path, out_path:"projects/<track>/mix/<name>_vst.wav",
   plugins:[{plugin_path, parameters?}, …], dump_state:true}`. Order = signal flow. Set `parameters`
   in the plugin's native range (often 0..1); for a precise patch, restore a prior `state_path` blob.
   **Two things apply-vst-chain can't do** → hand off to `[[vst-preset]]`: (a) a **gain-stage** (analog
   units need ~+18 dB to engage), and (b) **enum/string/bool params** (its `parameters` is float-only).
4. **Verify — processing probe, not just `changed`.** Re-run `[L] measure-spectrum` (+ `measure-loudness`/
   `measure-microdynamics`) and confirm the move landed in the *detail*. A **0.00 change in spectrum/crest/tilt
   = passthrough** even when `changed:true` — stop, run `[[vst-verify]]` / switch to the `uaudio_*` build.
   Don't ship a passthrough/demo render.
5. Write to `projects/<track>/mix/` (loops → `projects/<track>/loops/`).

## Outputs

- Processed WAV in `projects/<track>/mix/`.
- One `.state` blob per plugin beside it (from `dump_state:true`) → reproducible re-render via `state_path`.

## Reporting to the user

- The chain (plugins, order, key params), before→after **LUFS / peak / tilt** deltas, the `changed`
  flag, and the dumped `.state` path(s). State plainly that it ran headless (no GUI).

## Pitfalls

- **Loads ≠ renders.** A clean load (or `changed:true`) isn't proof of processing — a plugin can pass
  audio through or ignore its params (UAD `.component` build, unauthorized/demo). Verify *detail* changed;
  pre-screen with `[[vst-verify]]`.
- **Gain-stage analog units.** Tube comp / tape / console barely process a quiet bus — drive the input
  (~+18 dB) via `[[vst-preset]]`; `apply-vst-chain` has no gain-stage.
- **Enum/bool params need `[[vst-preset]]`** — `apply-vst-chain` is float-only; `output='-6.0 dB'`,
  `gain='Low'`, `auto_cal=False` can't go through its dict.
- **Order matters** — EQ-before-comp vs comp-before-EQ are different results; mirror intended signal flow.
- **Non-deterministic** — pin plugin versions and keep the `.state` blob / preset; a VST render won't
  reproduce bit-exactly (tape flutter etc.) the way the pure-DSP tools do.
- **AU is macOS-only** — prefer the VST3 path for portability.

## Related

- `[[vst]]` — suite index + doctrine · `[[vst-browse]]` — find plugin paths
- `[[vst-channel-strip]]` / `[[vst-eq]]` / `[[vst-compress]]` / `[[vst-saturate]]` / `[[vst-reverb]]` / `[[vst-delay]]` / `[[vst-de-ess]]` / `[[vst-master]]` / `[[vst-amp]]` — task presets of this recipe
- `[[finalize-mix]]` — the pure-DSP glue stage where a VST insert (step 3b) lives
