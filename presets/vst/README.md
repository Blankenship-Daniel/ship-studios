# VST presets

Reusable, saved VST chains for the `[[vst]]` skill suite — a portable recipe (gain-stage → plugin
chain → M/S narrow → trim) plus the byte-exact `.state` blobs, so a signature sound can be re-applied
to any file and reproduced later.

## Available

| Preset | For | Sound |
|---|---|---|
| [`vintage-1960s.json`](vintage-1960s.json) | drum bus / mix | warm, dark, tube-glued, tape-saturated, period-mono 1960s drums (UADx Pultec → Fairchild 670 → Ampex ATR-102) |
| [`tight-70s.json`](tight-70s.json) | drum bus | punchy, dry, present, tape-glued 1970s drums (UADx Neve 1073 → dbx 160 → Studer A800 @15 IPS, driven for peak-control) |

## Apply

```bash
# run with the stemmy-loops `vst` venv (has pedalboard); plugins resolve from /Library/Audio/Plug-Ins/VST3/
../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py \
    presets/vst/vintage-1960s.json  <in.wav>  <out.wav>
```

`apply_vst_preset.py` sets each plugin's params directly (handles UADx enum/float/bool params that
`apply-vst-chain`'s float-only dict can't reach) and adds the input gain-stage + narrowing that live
outside the plugins.

## Format

```jsonc
{
  "name": "...", "description": "...", "intended_for": "...",
  "plugin_build": "...",                 // which install build to load
  "target_signature": { ... },           // measured dry->processed, to sanity-check a re-apply
  "recipe": {
    "input_gain_db": 18,                 // drive into the analog stage (integral!)
    "output_peak_dbfs": -1.0,
    "width": 0.72,                        // M/S narrow (1.0 = untouched, 0 = mono)
    "chain": [ {"file": "uaudio_x.vst3", "params": {"name": value, ...}}, ... ]
  },
  "states": [ "name.states/0_*.state", ... ]  // byte-exact opaque plugin states (optional fallback)
}
```

## ⚠️ Plugin build note (hard-won)

UADx plugins ship in **two builds** on this Mac; presets use the one that renders headless:
- ✅ **`/Library/Audio/Plug-Ins/VST3/uaudio_*.vst3`** — UADx native, **processes offline**.
- ❌ `…/Components/UAD ….component` & `…/VST3/Universal Audio/UAD ….vst3` — **pass audio through
  unprocessed** in a headless host (need UA's GUI host runtime). Don't use these in presets.

A preset's `recipe.params` are the portable form (they reproduce the sound from scratch). The
`.state` blobs are a byte-exact fallback for the same plugin versions, restorable via
`apply-vst-chain`'s `state_path`.
