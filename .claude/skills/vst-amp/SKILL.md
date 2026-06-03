---
name: vst-amp
description: "Use when the user wants guitar/bass amp or pedal tone on a DI/clean track via their own plugin — 'reamp this DI', 'add a guitar amp sim', 'run the bass through an amp', 'TONEX/NAM this', 'give the guitar a Marshall/metal tone'. Applies a headless-safe amp/pedal sim (TONEX, NeuralAmpModeler, UAD Softube Amp Rooms) to a DI/clean source. Stemmy MCP, the `vst` extra."
argument-hint: <DI.wav> [tone: clean/crunch/high-gain, bass/guitar]
---

# vst-amp — guitar/bass amp + pedal tone with your own plugin

Goal: turn a clean **DI / direct** guitar or bass track into amped tone via a real amp-sim plugin —
profile/capture (`TONEX`, `NeuralAmpModeler`) or modelled amp rooms (`UAD Softube Bass/Metal Amp
Room`). A task preset of `[[vst-chain]]` aimed at tracking / reamping, not the 2-bus.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). Input = a **DI / clean** source
  (amp sims on an already-amped signal stack badly). Candidates
  ([`docs/vst/README.md`](../../../docs/vst/README.md)): `TONEX`, `NeuralAmpModeler`,
  `UAD Softube Bass Amp Room`, `UAD Softube Metal Amp Room`, `UAD Softube Amp Room Half-Stack`.

## Recipe

1. **Baseline** — `[L] measure-loudness` + `[L] measure-spectrum` on the DI (so the amp's tonal
   shift + level are visible).
2. **Pick the amp/capture** — clean/edge/crunch/high-gain; bass vs guitar; pick a capture (NAM/TONEX)
   or amp room. Confirm path via `[L] list-vst-plugins`. NAM/TONEX need a capture/model file loaded —
   restore it via a saved `state_path` (the `parameters` API can't load arbitrary capture files).
3. **Apply** — `[L] apply-vst-chain {path, out_path:"projects/<track>/stems/<name>_amp.wav",
   plugins:[{plugin_path, parameters? / state_path?}], dump_state:true}`. Stack a drive/pedal sim
   *before* the amp if wanted (chain order = pedalboard → amp).
4. **Verify** — re-`measure-loudness`/`measure-spectrum`; confirm `changed:true` and the tone shifted.
   Amped output is hotter — set level for the mix, don't clip.

## Outputs

- `projects/<track>/stems/<name>_amp.wav` (a new amped stem for the mix) + `.state` blob(s).

## Reporting to the user

- The amp/capture + gain character, before→after spectrum/level, the `.state` path (capture preserved).

## Pitfalls

- **Verify it renders, gain-stage, use `uaudio_*`.** Loads ≠ renders — confirm the tone actually shifted
  (a 0.00 change = passthrough → run `[[vst-verify]]`). Amp sims want a healthy DI level in — drive it via
  `[[vst-preset]]` if quiet. NAM/TONEX capture files + amp enum controls aren't floats; restore them via a
  saved `state_path`/preset, not `apply-vst-chain`'s dict. For UADx amps use the `uaudio_*.vst3` build.

- **DI in, not amped** — feeding an already-amped signal double-amps it; use the direct track.
- **Capture files** — NAM/TONEX tones live in a loaded model file; capture it into `dump_state` so the
  render reproduces (parameters alone won't restore the model).
- This is a tracking/reamp tool — keep it off the mix/master bus.

## Related

- `[[vst-chain]]` · `[[vst-saturate]]` (lighter color) · `[[song-mix]]` (mix the amped stem in) · `[[vst]]` — index/doctrine
