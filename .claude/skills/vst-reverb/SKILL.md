---
name: vst-reverb
description: "Use when the user wants reverb/space on a stem or send via their own plugin — 'add a plate to the snare', 'put this vocal in a hall', 'make a reverb send', 'give the mix some room/space', 'wash this in Valhalla'. Applies a headless-safe reverb (ValhallaPlate, FabFilter Pro-R 2, SSL Native FlexVerb), favouring a parallel/wet send with a mono-compatibility check. Stemmy MCP, the `vst` extra."
---

# vst-reverb — reverb / space with your own plugin

Goal: add reverberant space — plate, room, or hall — via a real reverb plugin, kept controllable
and mono-safe. A task preset of `[[vst-chain]]`, with a **parallel (wet) send** bias so the dry
transient survives.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). Candidates
  ([`docs/vst/README.md`](../../../docs/vst/README.md)): `ValhallaPlate`, `FabFilter Pro-R 2`,
  `SSL Native FlexVerb`, `ValhallaShimmer`. (Avoid `AIR Studios Reverb` — blocked here.)

## Recipe

1. **Baseline** — `[L] measure-loudness` + `[L] measure-stereo` (correlation + mono-sum loss, so the
   reverb doesn't wreck mono compatibility).
2. **Pick the space** — plate (bright, snare/vocal), room (glue), hall (size/depth); confirm path via
   `[L] list-vst-plugins`.
3. **Apply (prefer a wet send)** — render a **100% wet** pass with the plugin's mix at full, then keep
   it as a parallel reverb bus to blend under the dry — or set the plugin's internal dry/wet via
   `parameters` for an insert. `[L] apply-vst-chain {path, out_path:"projects/<track>/mix/<stem>_verb.wav",
   plugins:[{plugin_path, parameters?}], dump_state:true}`.
4. **Verify** — re-`measure-stereo`; confirm mono-sum loss didn't worsen materially and `changed:true`.

## Outputs

- A wet/processed WAV in `projects/<track>/mix/` (+ `.state`). If wet-only, note it's a send to blend.

## Reporting to the user

- The reverb + decay/size, wet vs insert, before→after correlation/mono-sum loss, `.state` path.

## Pitfalls

- **Verify it renders + use `uaudio_*`.** Loads ≠ renders — confirm the wet pass actually changed the
  signal (a 0.00 change = passthrough → run `[[vst-verify]]`). For UADx reverbs (EMT 140, AKG BX 20,
  Capitol/Hitsville chambers) use the `uaudio_*.vst3` build, not the `UAD ….component` twins. Enum/bool
  params (decay range, mode) need `[[vst-preset]]` rather than the float-only `apply-vst-chain` dict.

- **Reverb decorrelates** — always check mono-sum loss; long wide tails can hollow out in mono.
- **Insert vs send** — a 100% wet insert buries the dry; prefer a parallel blend for transient material.
- HPF the reverb return (low-mud) — many reverbs have an input/return filter; use it.

## Related

- `[[vst-chain]]` · `[[vst-delay]]` (time FX) · `[[vst]]` — index/doctrine
