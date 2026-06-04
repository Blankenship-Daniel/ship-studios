---
name: vst-eq
description: "Use when the user wants to EQ a stem/bus/loop with their own EQ plugin — 'EQ this with a Pultec', 'add some Maag air', 'run a Neve EQ on the bass', 'surgical-EQ this with Pro-Q', 'sweeten the top with my vintage EQ'. Applies a headless-safe EQ plugin (FabFilter Pro-Q, Maag EQ4, UAD Pultec/Neve) with measured tilt/spectrum before/after, optionally guided by find-resonances. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [eq/intent]
---

# vst-eq — EQ a track with your own EQ plugin

Goal: shape tone with a real **EQ plugin** — surgical (FabFilter Pro-Q 4), vintage musical (Pultec,
Neve 1073), or air (Maag EQ4). A task preset of `[[vst-chain]]`. For *automatic* corrective EQ from
a reference, prefer the pure-DSP `[L] apply-eq`/`match-eq`; reach here when the user wants a specific
plugin's curve/character.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). `[G] find-resonances` (optional;
  pure DSP — no `GEMINI_API_KEY`, it lives on the stemmy-gemini server but makes no model call).
  Candidates ([`docs/vst/README.md`](../../../docs/vst/README.md)):
  `FabFilter Pro-Q 4`, `Maag EQ4`, `UAD Pultec EQP-1A`, `UAD Pultec MEQ-5`, `UAD Neve 1073`, `EQP-1A`,
  `Neutron 4 Equalizer` (iZotope — dynamic EQ + M/S → [[neutron-4-equalizer]]) / `Neutron 4 Sculptor`
  (iZotope — target spectral leveler → [[neutron-4-sculptor]]) — both render & engage headless. (iZotope's
  `Ozone 11 Equalizer` is **DAW-only** — its EQ is inert offline → [[ozone-11-equalizer]].)

## Recipe

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + 5-band) + `[L] measure-loudness`.
2. **Find targets (optional)** — `[G] find-resonances` to get narrow-Q peaks + notch dB; translate
   those into the plugin's bell bands.
3. **Pick the EQ** — surgical vs vintage vs air per intent; confirm path via `[L] list-vst-plugins`.
4. **Apply** — `[L] apply-vst-chain {path, out_path:"projects/<track>/mix/<stem>_eq.wav",
   plugins:[{plugin_path, parameters?}], dump_state:true}`. Set bands via `parameters` or a saved `state_path`.
5. **Verify** — re-`measure-spectrum`; confirm the tilt/band moved as intended and `changed:true`.

## Outputs

- `projects/<track>/mix/<stem>_eq.wav` + `.state` blob.

## Reporting to the user

- The EQ + the moves (bands/shelves), before→after tilt + 5-band deltas, `.state` path.

## Pitfalls

- **Verify it renders + use `uaudio_*`.** Loads ≠ renders — confirm the tilt/band actually moved (a
  0.00 spectrum change = passthrough → run `[[vst-verify]]`). For UADx (Pultec/Neve) pick the
  `uaudio_*.vst3` build, never the `UAD ….component` twins (they ignore params). If a unit needs
  gain-staging or enum params, drive it via `[[vst-preset]]`.

- **Vintage EQs aren't surgical** — Pultecs/Neves have fixed/stepped freqs and their own curves; use
  Pro-Q for precise notches.
- **Pultec low-end trick** — boosting + attenuating the same low band is a feature, not a mistake.
- For transparent reference-matching, `[L] match-eq` (pure DSP) is more controllable than a plugin.

## Related

- `[[vst-chain]]` · `[[vst-compress]]` · `[[vst-channel-strip]]` (EQ+comp in one)
- `[[mix-check]]` (find the problems first) · `[[vst]]` — index/doctrine
