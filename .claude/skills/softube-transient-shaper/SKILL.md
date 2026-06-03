---
name: softube-transient-shaper
description: "Use when running the Softube Transient Shaper to tighten or punch drums/transients — 'Softube Transient Shaper', 'transient shaper on the drums', 'tighten the transients / tighten the kick tail', 'add snare crack/attack', 'control the cymbal wash', 'less ring/boom on the drum bus', or any attack/sustain shaping with that plugin. The measured, plugin-specific deep-dive of [[drum-punch]] / [[vst-chain]] — a 2-band, level-independent attack(PUNCH)/decay(SUSTAIN) shaper, grounded in the real Pedalboard param surface + the manual recipes + our render results in docs/vst/softube-transient-shaper.md. Stemmy MCP, the `vst` extra."
---

# softube-transient-shaper — drive the Softube Transient Shaper (measured)

The plugin-specific, measured workflow for the **Softube Transient Shaper** (`/Library/Audio/Plug-Ins/VST3/Transient
Shaper.vst3`) — a **2-band stereo** unit that reshapes **attack (PUNCH)** and **decay (SUSTAIN)** *independently of
level*, each routable to the whole band / lows / highs around one crossover. It's the transient-design sibling of
the native [[drum-punch]] (`shape-bands`) and the tone of [[api-vision-channel-strip]] / [[studer-a800]]. Full
field guide (param surface, manual recipes, our numbers, pitfalls, sources) →
[`docs/vst/softube-transient-shaper.md`](../../../docs/vst/softube-transient-shaper.md). This skill is the workflow.

## The governing facts (read first)

1. **"Tighten" = reduce SUSTAIN, not add PUNCH.** Sustain < 0 cuts the tail/ring (tighter). PUNCH adds *attack*
   and, pushed, an **unnatural click** (we made a snare clicky with `punch +3`; Gemini flagged it — the same
   over-shape trap as [[drum-bus-dry-punchy-variant]]). Clean tighten = **punch 0**, negative sustain.
2. **WIDE sustain cut chokes cymbals/hats.** Full-band negative sustain gates the HF decay (unnatural). Use
   **`sustain_band=LOW`** (xover ~700) to tighten the kick/snare *body/boom* while highs keep natural decay —
   the manual's own Lo/Hi-band logic. (Measured: LOW-band −5 kept centroid 2447 vs WIDE's 2146; choke gone.)
3. **Level-independent (no threshold).** It tracks transient *shape*, not gain — do NOT gain-stage into it
   (unlike the API strip). The `clip` soft-clips at 0 dB; keep input headroom or it engages.
4. **Meters own "tighter"** (Gemini hears mono): **crest / PLR up = tighter** (sustain cut) or **more punch**
   (attack up). A move that "feels tighter" without a crest/PLR change is an illusion. Cross-check Gemini's
   "dark/choked" claims against the stereo meters ([[gemini-mastering-feedback-cross-check]]).

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- The plugin renders **headless via Pedalboard** (iLok authorized here) — but Softube/iLok is a render-farm
  landmine ([[vst-hosting-outside-daw]]): **verify load+render on any new machine** (`changed:true`).
- **Enum gotcha:** `apply-vst-chain`'s `parameters` is **float-only** — it sets `punch_db`/`sustain_db`/
  `crossover_freq_hz`/`output_level_db` but **NOT** the enums (`punch_band`/`sustain_band`/`punch_type`) or
  `clip`. For band/type/clip moves use the **[[vst-preset]]** harness `presets/vst/apply_vst_preset.py`
  (`setattr`s every param) — e.g. `presets/vst/softube-ts-tighten-low.json`, `…-kick-click.json`. Enum strings
  are exact (`"LOW"`/`"WIDE"`/`"HIGH"`, `"FAST"`/`"SLOW"`).

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt) on the source.
2. **Pick the move** from the table below; **band-limit it** (LOW for body/boom, HIGH for click/air) so you
   don't choke the wrong range.
3. **Apply.** Float-only move (WIDE band, SLOW punch) → `[L] apply-vst-chain {plugins:[{plugin_path:".../Transient
   Shaper.vst3", parameters:{sustain_db:-5, punch_db:0}}]}` (absolute paths). Band/type/clip move → run a
   `presets/vst/softube-ts-*.json` through `apply_vst_preset.py` with the `vst` venv. Set `dump_state=true` (or
   the harness) for a reproducible re-render.
4. **Prove it** — re-`measure-loudness`/`measure-spectrum`. Expect **crest/PLR UP** for a tighten or a punch
   move; centroid roughly steady (LOW-band) or up (HIGH punch). A/B loudness-matched.
5. **QC for over-shaping** — `[G] detect-mix-issues` (genre/intent set): catch **clicky/spitty** attack (back off
   PUNCH) or **gate-like choked tails** (ease negative SUSTAIN, or go LOW-band / parallel). Then cross-check any
   "dark/boxy" flag against the stereo bands before acting (Gemini mono artifact).
6. It's a **bus/stem insert**, not a master — hand the result on (e.g. to [[master-track]]) for loudness.

## Recipes (from the manual + our results)

| Goal | Punch | P-band | P-type | Sustain | S-band | Xover | Clip |
|---|---|---|---|---|---|---|---|
| **Tighten** boomy kick/toms ★ | 0 | — | — | −4…−6 | **LOW** | ~700 | off |
| Kick **click** | +2…+5 | HIGH | FAST | 0 | — | 700 | on |
| Snare **crack + fat** | +2…+4 | WIDE | SLOW | −2…−3 | LOW | ~700 | on |
| Overheads **room/shimmer** | 0 | — | — | +2…+4 | HIGH | 1–2 kHz | off |
| Tame **cymbal wash** | 0 | — | — | −2…−4 | HIGH | 1–2 kHz | off |
| Drum-**bus** glue (tiny) | +1…+4 | HIGH | SLOW | 0 | — | 2–4 kHz | opt |

★ the validated clean tighten (`presets/vst/softube-ts-tighten-low.json`). Avoid WIDE negative sustain (chokes
hats) and high PUNCH (clicky) — see the governing facts.

## Related
[[drum-punch]] (native transient design — no plugin) · [[vst-chain]] / [[vst-preset]] · [[api-vision-channel-strip]] · [[studer-a800]] · [[drum-bus-dry-punchy-variant]] · [[gemini-mastering-feedback-cross-check]] · field guide: `docs/vst/softube-transient-shaper.md`
