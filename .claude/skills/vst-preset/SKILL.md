---
name: vst-preset
description: "Use when the user wants to save a VST chain for reuse or apply a saved one — 'save this chain as a preset', 'apply the vintage-1960s preset to this mix', 'reuse that drum sound on another track', 'make a preset from these plugins', 'list my vst presets'. Save & apply reusable VST chains (input gain-stage + enum/bool params + M/S narrow + state blobs) via presets/vst/. The home for the two things apply-vst-chain can't do: gain-staging and non-float params. Stemmy MCP, the `vst` extra."
---

# vst-preset — save & apply reusable VST chains

Goal: capture a working VST chain as a portable, reproducible **preset** and re-apply it to any file.
A preset stores the whole signal path — the **input gain-stage** (which analog units need to engage)
and **enum/string/bool params** — both of which `[L] apply-vst-chain`'s float-only `parameters` can't
express. Backed by `presets/vst/apply_vst_preset.py`; see [`presets/vst/README.md`](../../../presets/vst/README.md).

## Prerequisites

- `presets/vst/apply_vst_preset.py` + `presets/vst/*.json` run with the stemmy-loops `vst` venv
  (`../stemmy-loops-mcp/.venv/bin/python`, has pedalboard). Plugins must **render** headless — verify
  with `[[vst-verify]]`; use `uaudio_*.vst3` paths for UADx.

## Recipe

### Apply a preset
1. `[L] measure-loudness` + `[L] measure-spectrum` the input (baseline).
2. ```bash
   ../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py \
       presets/vst/<name>.json  <in.wav>  projects/<track>/mix/<name>_out.wav
   ```
3. Re-measure; compare against the preset's `target_signature` to confirm it landed (tape/flutter makes
   it non-bit-exact but the signature matches). Flag a miss → `[[vst-verify]]` the plugins.

### Save a preset
1. Dial the chain (via `[[vst-chain]]` / the harness): input gain, each plugin's params (floats **and**
   enums/bools), `width`, output trim. Confirm it renders (`[[vst-verify]]`).
2. Write `presets/vst/<name>.json` to the schema (see [`presets/vst/README.md`](../../../presets/vst/README.md)):
   `name`, `description`, `intended_for`, `plugin_build` (`uaudio_*`), `target_signature` (measured
   dry→processed), and `recipe`: `{input_gain_db, output_peak_dbfs, width, chain:[{file, params}]}`.
3. Capture byte-exact `.state` blobs (the render's `dump_state` output) into `presets/vst/<name>.states/`
   as the fallback; the `recipe.params` are the portable source of truth.

## Outputs

- Saved: `presets/vst/<name>.json` (+ `<name>.states/`). Applied: a processed WAV in `projects/<track>/mix/`.

## Reporting to the user

- Save: the preset path + its `target_signature`. Apply: before→after deltas vs the target, the out path.

## Pitfalls

- **The gain-stage is integral** — analog units (tube comp, tape, console) barely process a quiet bus;
  the preset's `input_gain_db` (~+18) is what makes them engage. Don't drop it.
- **`uaudio_*` only** — a preset built on a `UAD ….component` path will passthrough; use the `uaudio_*` twin.
- **Non-deterministic** — tape wow/flutter means re-applies aren't bit-exact (that's real tape); the
  `target_signature` is how you confirm a faithful re-apply. Pin plugin versions.
- Recipe `params` reproduce from scratch and are portable; `.state` blobs are byte-exact but tied to this
  machine's plugin versions.

## Related

- `[[vst-chain]]` — dial a chain before saving · `[[vst-verify]]` — confirm it renders first
- `[[vst-shootout]]` — pick the best variant, then save it · `[[vst]]` — index/doctrine
- Example shipped: `presets/vst/vintage-1960s.json` (UADx Pultec → Fairchild 670 → Ampex tape → period-mono)
