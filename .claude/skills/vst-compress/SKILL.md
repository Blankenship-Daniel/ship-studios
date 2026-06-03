---
name: vst-compress
description: "Use when the user wants to compress a stem/bus with their own compressor plugin — 'run an 1176 on the vocal', 'LA-2A the bass', 'bus-compress the drums with my plugin', 'glue this with a real comp', 'add an opto/FET/VCA compressor'. Applies a headless-safe compressor (Black 76, Comp FET-76, FabFilter Pro-C, SSL Bus Comp, Tube-Tech CL 1B) with crest/PLR measured before/after. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [comp/intent]
---

# vst-compress — compress a track with your own comp plugin

Goal: apply a real **compressor** — FET (1176-style: `Black 76`, `Comp FET-76`), opto
(`UAD Tube-Tech CL 1B`), VCA/bus (`SSL Native Bus Compressor 2`, `UAD API 2500`), or clean
(`FabFilter Pro-C 2`) — with the dynamics change proven via crest/PLR. A task preset of `[[vst-chain]]`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). Candidates
  ([`docs/vst/README.md`](../../../docs/vst/README.md)): `Black 76`, `Comp FET-76`, `FabFilter Pro-C 2`,
  `SSL Native Bus Compressor 2`, `UAD Tube-Tech CL 1B`, `UAD API 2500`.

## Recipe

1. **Baseline** — `[L] measure-microdynamics` (crest/PLR/punch) + `[L] measure-loudness`.
2. **Pick the comp** by character (FET = fast/aggressive, opto = smooth/program-dependent, VCA/bus =
   glue); confirm path via `[L] list-vst-plugins`.
3. **Apply** — `[L] apply-vst-chain {path, out_path:"projects/<track>/mix/<stem>_comp.wav",
   plugins:[{plugin_path, parameters?}], dump_state:true}`. Dial threshold/ratio/attack/release via
   `parameters` (native range) or a saved `state_path`.
4. **Verify** — re-`measure-microdynamics`; confirm crest dropped *as intended* (not collapsed) and
   `changed:true`. Re-`measure-loudness` to watch makeup gain.

## Outputs

- `projects/<track>/mix/<stem>_comp.wav` + `.state` blob.

## Reporting to the user

- The comp + settings (ratio/attack/release), before→after crest/PLR + LUFS, `.state` path.

## Pitfalls

- **Verify it renders, gain-stage, use `uaudio_*`.** Loads ≠ renders — confirm crest actually *dropped*
  (a flat crest = passthrough → run `[[vst-verify]]`). Tube/opto comps need a healthy input level (~+18 dB)
  to grab — `apply-vst-chain` can't gain-stage, so use `[[vst-preset]]`; many comp controls (input/threshold
  enums) are non-float and also need the preset harness. For UADx (Fairchild/LA-2A/1176) use `uaudio_*.vst3`.

- **Louder ≠ better** — makeup gain can disguise over-compression; judge by crest, not level.
- **Attack sets punch** — too-fast attack kills transients on drums; verify with microdynamics.
- Parallel feel? Some comps have built-in mix/blend; otherwise this is fully-wet (no parallel here).

## Related

- `[[vst-chain]]` · `[[vst-eq]]` (order matters — decide EQ↔comp) · `[[vst-channel-strip]]` (both in one)
- `[[drum-punch]]` (pure-DSP transient design) · `[[vst]]` — index/doctrine
