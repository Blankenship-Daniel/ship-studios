---
name: vst-verify
description: "Use when you need to know whether a plugin actually PROCESSES audio headless, not just loads — 'does this plugin really work here', 'is <plugin> passthrough', 'my plugin did nothing / output unchanged', 'verify these render headless', 'uaudio vs UAD which one works', 'rebuild the headless-safe list properly'. A processing-probe: pushes a parameter and confirms the output responds (0.00 = passthrough). The backstop the rest of the vst suite relies on. Stemmy MCP, the `vst` extra."
---

# vst-verify — does this plugin RENDER headless, or just load?

Goal: prove a plugin actually processes audio offline, because **loads ≠ renders**. Some plugins
instantiate cleanly yet pass audio through unchanged or ignore their parameters — most notably the
**UAD `.component` / `UAD ….vst3` build** (vs the `uaudio_*.vst3` build that works), and any
unauthorized/demo plugin. The headless-safe inventory ([`docs/vst/README.md`](../../../docs/vst/README.md))
was built from a *load* probe, so it **overcounts** — this skill is the render check.

## Prerequisites

- `presets/vst/probe_plugin.py` (the probe engine) run with the stemmy-loops `vst` venv
  (`../stemmy-loops-mcp/.venv/bin/python`, has pedalboard). `[L] apply-vst-chain` / `[L] measure-loudness`
  for an in-context spot check. No `GEMINI_API_KEY` needed.

## Recipe

1. **Probe the candidate(s)** — pass plugin paths or basenames:
   ```bash
   ../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py \
       uaudio_175_b.vst3  "/Library/Audio/Plug-Ins/Components/UAD Pultec EQP-1A.component"
   ```
   It renders a loud test burst at default and with one parameter pushed to an extreme, and compares:
   responds → `RENDERS ✓`; ignores the param → `PASSTHROUGH ✗`.
2. **Interpret** — `Δparam` is the discriminator (param-response). `Δvs-in` is *not* reliable (plugin
   latency inflates it). For UADx, prefer the `uaudio_*.vst3` path; the `UAD ….component`/`.vst3` twins
   typically come back `PASSTHROUGH ✗ (ignores params)`.
3. **In-context spot check (optional)** — for a plugin you're about to use, `[L] measure-spectrum` the
   input, `[L] apply-vst-chain` a strong move (e.g. a +12 dB bell, or an output trim), `[L] measure-spectrum`
   the output; a **0.00 detail change = passthrough**, regardless of `changed:true`.
4. **Refresh the inventory (on demand)** — to turn the load-probe list into a render-verified one, probe
   the titles in [`demo/headless-safe-titles.txt`](../../../demo/headless-safe-titles.txt) and keep only
   `RENDERS ✓`. This is a big job (hundreds of plugin loads) — do it deliberately, not casually.

## Outputs

- A render-ok / passthrough verdict per plugin (on screen). Optionally a render-verified plugin list.

## Reporting to the user

- Per plugin: `RENDERS ✓` or `PASSTHROUGH ✗`, the path/build (`uaudio_*` vs `UAD …`), and the `Δparam`.
  When a plugin a skill wanted is passthrough, name the working alternative (the `uaudio_*` twin, or a
  different vendor).

## Pitfalls

- **`changed:true` is not enough** — `apply-vst-chain` reports `changed` on any difference incl. latency;
  judge by *detail* (spectrum/crest/tilt) or the probe's `Δparam`.
- **UAD two builds** — `/Library/Audio/Plug-Ins/VST3/uaudio_*.vst3` renders; `…/Components/UAD ….component`
  and `…/VST3/Universal Audio/UAD ….vst3` ignore params headless. Always probe the `uaudio_*` path.
- **iLok/UADx authorization** — a plugin can be licensed for a DAW yet passthrough in this offline host;
  the probe tells you what actually works here, today.

## Related

- `[[vst]]` — suite index/doctrine · `[[vst-chain]]` / `[[vst-browse]]` — feed verified picks into these
- `[[vst-preset]]` — once verified, capture the chain as a preset
