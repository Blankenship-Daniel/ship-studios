---
name: vst-channel-strip
description: "Use when the user wants a console channel strip on a stem or bus via their own plugins — 'put an SSL/Neve/API channel strip on this', 'run the vocal through a console strip', 'give the drum bus that console sound', 'channel-strip the bass'. Applies a headless-safe channel-strip plugin (British Channel, bx_console, SSL Native Channel Strip, UAD Neve/API) with measured before/after. Stemmy MCP, the `vst` extra."
argument-hint: <stem.wav> [console/character]
---

# vst-channel-strip — console channel strip on a stem/bus

Goal: run a stem or bus through a real **console channel-strip** plugin (HPF + EQ + comp + drive in
one) for cohesive console tone. A task preset of `[[vst-chain]]` — same headless/measured doctrine.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). Input = one WAV stem/bus.
- Headless-safe candidates ([`docs/vst/README.md`](../../../docs/vst/README.md)): `British Channel`,
  `bx_console SSL 4000 E`, `bx_console AMEK 200`, `SSL Native Channel Strip 2`,
  `UAD API Vision Channel Strip`, `UAD Neve 1073`, `Nectar 3` (iZotope's all-in-one **vocal** channel
  strip — renders & engages headless → [[nectar-3]]).

## Recipe

1. **Baseline** — `[L] measure-loudness` + `[L] measure-spectrum` + `[L] measure-microdynamics` (crest/PLR).
2. **Pick the strip** — choose by character (SSL = punchy/modern, Neve/AMEK = warm, API = forward);
   confirm path via `[L] list-vst-plugins {name_contains}`. Confirm with the user if more than one fits.
   For the **UAD API Vision Channel Strip** there's a measured deep-dive: [[api-vision-channel-strip]]
   (the 215/235/225/550/560 modules, the crest map, de-harsh recipe).
3. **Apply** — `[L] apply-vst-chain {path, out_path:"projects/<track>/mix/<stem>_strip.wav",
   plugins:[{plugin_path, parameters?}], dump_state:true}`. Dial the strip's own HPF/EQ/comp via
   `parameters` (native range) or restore a saved `state_path`.
4. **Verify** — re-measure loudness/spectrum/microdynamics; confirm `changed:true` and crest didn't
   collapse. Flag demo-mode silence.

## Outputs

- `projects/<track>/mix/<stem>_strip.wav` + the `.state` blob.

## Reporting to the user

- Which strip + its character, the EQ/comp moves, before→after tilt + crest/PLR, the `.state` path.

## Pitfalls

- **Verify it renders, gain-stage, use `uaudio_*`.** Loads ≠ renders — confirm the move shows in the
  *detail* (spectrum/crest/tilt), not just `changed:true`; a 0.00 change = passthrough → run `[[vst-verify]]`.
  Analog units (console/tube) need gain-staging (~+18 dB) to engage — `apply-vst-chain` can't, so use
  `[[vst-preset]]`. For UADx pick the `uaudio_*.vst3` build (the `UAD ….component` twins passthrough).

- **It's a whole chain in one box** — don't also stack `[[vst-eq]]`+`[[vst-compress]]` unless intended.
- **Watch crest** — the built-in comp can over-squash; check microdynamics before/after.
- A channel strip is per-track tone, not mastering — keep it off the 2-bus (use `[[vst-master]]`).

## Related

- `[[api-vision-channel-strip]]` / `[[studer-a800]]` — measured per-plugin deep-dives (forward API console / warm Neve-tape)
- `[[vst-chain]]` (backbone) · `[[vst-eq]]` / `[[vst-compress]]` (à-la-carte instead of a strip)
- `[[stem-master]]` — per-stem corrective stage where a strip fits · `[[vst]]` — index/doctrine
