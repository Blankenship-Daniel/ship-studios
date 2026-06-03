---
name: kit-bb-n73
description: "Use when running the KIT Plugins BB N73 (Blackbird Studio Neve 1073 channel strip) for warm, weighty, vintage 1073 tone on drums, bus, bass, guitar, or vocals — 'KIT BB N73', 'Blackbird Neve 1073', 'Neve 1073 channel', 'that classic 1073 sound', 'use the BB N73', or when you need the fixed-12k HF shelf + sweepable mid bell + low shelf + Mic-mode transformer drive dialed for warmth and low-end weight without harshness. The measured, plugin-specific deep-dive of [[vst-channel-strip]] — grounded in the real 18-param surface + isolation/drive/EQ numbers in docs/vst/kit-bb-n73.md. The classic 3-band 1073 counterpart to the 4-band Neve [[kit-bb-n105]] and the punchy API [[kit-bb-a5]] / [[api-vision-channel-strip]]. Stemmy MCP, the `vst` extra. iLok/PACE (verified-headless on this rig)."
---

# kit-bb-n73 — drive the KIT Plugins BB N73 (Blackbird Neve 1073 channel, measured)

The plugin-specific, measured version of [[vst-channel-strip]] for the **KIT Plugins BB N73**
(`KIT BB N73.vst3`) — an emulation of the **Neve 1073** mic-pre + 3-band EQ, modeled from twelve vintage
1073s at **Blackbird Studio**, Nashville. The **warm / weighty / classic-1073** character: the simpler 3-band
sibling of the 4-band Neve [[kit-bb-n105]] (31105) and the warm counterpart to the punchy API
[[kit-bb-a5]] / [[api-vision-channel-strip]]. Full field guide — real param surface, the Mic-drive harmonic
map, the 3-band EQ, the licensing/headless caveat, recipes, and our isolation numbers — lives in
[`docs/vst/kit-bb-n73.md`](../../../docs/vst/kit-bb-n73.md). This skill is the workflow.

## The governing facts (read first)

1. **It's a 1073 — 3 EQ bands, not the N105's four.** A **FIXED 12 kHz** HF shelf (`high_shelf_gain`, *no*
   frequency selector), a sweepable **mid bell** (`mid_frequency` `360/700/1.6k/3.2k/4.8k/7.2k`), a sweepable
   **low shelf** (`low_frequency` `35/60/110/220`), and a steep **HPF** (`50/80/160/300`). **No low-mid band,
   no LPF, no Hi-Q.** All three EQ bands are **±18 dB** (measured).
2. **The Neve color is MIC-MODE ONLY — measured.** In `Line` mode `pre_amp_sensitivity` *and*
   `pre_amp_saturation` are **inert (byte-identical, 0.00 % THD)**. `pre_amp_mode="Mic"` adds the transformer
   drive — and **a lot** of gain (**−80 = MAX, ~+23 dB over −20**).
3. **`pre_amp_saturation=TRUE` is mandatory in Mic mode.** ON = the controlled soft-transformer path
   (~0.2–0.3 % THD, level-managed). **OFF + driven = raw digital CLIP (23 % THD @ −50, 46 % @ −80)** — only
   for deliberate overdrive. *(Opposite emphasis from the N105, where Mic was always gentle.)*
4. **Mic drive = WEIGHT + warmth, not sheen.** On the drum bus it added low-end weight **beyond the EQ alone**
   (low ratio 0.542→**0.671** vs 0.605 from the same EQ clean), stayed **dark** (centroid +81 vs +571 clean),
   and **kept crest** (23.6→23.1). Warmth from the transformer, **not an EQ air boost** — the house warm-tight
   preference. *(N105 = sheen + crest up; N73 = weight + stays dark. Pick N73 for thick classic-1073 lows.)*
5. **No host Auto-Gain** (GUI-only). Mic drive jumps level → compensate with `output_gain` (linear) and/or
   the harness peak-trim. **`master_bus_toggle` IS host-exposed** (`MST On` = subtle 8058/8078 glue, ~1.9 %
   THD) — unlike the N105's GUI-only Master Buss.
6. **Every param is an enum.** Numeric gains/trims (`*_gain`, `*_trim`, `pre_amp_sensitivity`, `output_gain`)
   accept a **float** — `apply-vst-chain`'s float dict reaches those. **Frequencies (`"60 Hz"`), modes
   (`"Mic"`), `eq`, `phase`, `hum`, `master_bus_toggle` are STRING/bool enums** → set via the **[[vst-preset]]**
   harness (`apply_vst_preset.py`), which also gain-stages.
7. **Meters own this** (Gemini hears mono): crest = punch kept, centroid/tilt = warmth vs harshness,
   true-peak = clip. `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` / `check-clipping`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **`KIT BB N73.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"N73"}`. It's **iLok/PACE** but
  **verified to render headless on this machine**. Before trusting it elsewhere, screen with
  `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "N73"` (expect `RENDERS ✓`). **Never run
  an unlicensed/trial instance unattended** (iLok Cloud needs constant internet; an unauthorized node
  demo-silents — loads≠renders).
- **String-enum + bool params** (`pre_amp_mode="Mic"`, `mid_frequency="3.2 kHz"`, `low_frequency="60 Hz"`,
  `hpf_frequency="50 Hz"`, `pre_amp_saturation`, `eq`, `phase`, `hum`, `master_bus_toggle`) → set via the
  **[[vst-preset]]** harness; `apply-vst-chain`'s `parameters` is float-only (gains/trims only) and can't
  reach them, nor gain-stage.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt + low/low-mid
   ratios) + `[L] measure-microdynamics`. The "before" column.
2. **Pick character** — *warm/weighty classic-1073* (its strength). Feed a dry-ish, measured-balanced bus/loop
   ([[mix-balance]] first). Tighten with `hpf_frequency` (`"50 Hz"` bus; higher on close mics — snare 80, OH
   160–300; **HPF OFF on kick** to keep the lows).
3. **Color (Mic transformer drive)** — `pre_amp_mode="Mic"`, **`pre_amp_saturation=true`** (mandatory),
   `pre_amp_sensitivity` ~−45 to −50 for moderate warmth/weight; push toward −60…−80 for more (watch the
   low-mid scoop). **Compensate the level jump with `output_gain`** (e.g. −12). *(`Line` mode = clean EQ
   console, no drive color. `saturation=false` in Mic = clipping overdrive, creative only.)*
4. **EQ (weight + de-box, keep it warm)** — `eq="EQ On"`. **Weight:** `low_frequency="60 Hz"` (or 110),
   `low_gain≈+3`. **De-box:** `mid_frequency="700 Hz"`, `mid_gain≈−2`. For warm, **leave HF off** — let the
   transformer be the only top lift. For a brighter "Neve air" variant set `high_shelf_gain≈+2` (fixed 12 k;
   measured centroid 3209→3420). For glue add `master_bus_toggle="MST On"`.
5. **Apply** — via [[vst-preset]] (`apply_vst_preset.py <preset.json> <in> <out>`); `dump_state` for repro.
   Output → `projects/<track>/mix/`.
6. **Verify** — re-measure. Warm-weighty = **low ratio up + low-mid de-boxed + centroid stays dark + crest
   preserved** (drive added weight, didn't squash); `check-clipping` (Mic drive raises true-peak). A/B
   loudness-matched with `[L] render-ab`.

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset (and `.state` if dumped).
- Ready-made: `presets/vst/bb-n73-warm-drum-bus.json` — the measured warm-weighty 1073 drum bus (Mic sat sens
  −47 + HPF 50 + LF +3@60 + de-box −2@700, HF off, output −12). Dry→processed: crest 23.6→23.1, centroid
  3128→3209 (transformer weight, **stays dark**), low ratio .542→.671, low-mid .378→.267, tilt stays −2.2.

## Reporting to the user

State Mic/Line + saturation on/off + drive amount (sensitivity), the EQ moves, the before→after **crest /
centroid / tilt / low + low-mid ratios**, that it ran headless (iLok-authorized here), and that the warmth
came from the **transformer drive, not an EQ air boost** (low weight up, centroid stayed dark). A/B
loudness-matched so taste isn't a level illusion.

## Pitfalls

- **LINE preamp is inert** — switch to **Mic** for any drive; in Mic, **keep `pre_amp_saturation` ON**
  (off + driven = raw digital clip).
- **No host Auto-Gain** — Mic drive jumps level; compensate with `output_gain`/trims (the harness also
  peak-trims) and re-check `check-clipping`.
- **HF is a FIXED 12 kHz shelf** (no freq selector — that's the 1073); **no LPF**; **HPF top = 300 Hz**;
  all three EQ bands **±18 dB**.
- **`apply-vst-chain` can't set the string/bool enums or gain-stage** → use [[vst-preset]] (gains/trims-only
  float moves can go through `apply-vst-chain`).
- **analog hum is negligible offline** — leave it off for clean stems.
- **N73 ≠ N105** (1073 3-band vs 31105 4-band). The Master-Buss here **is** the API/8058-derived output stage
  and **is** host-exposed (`master_bus_toggle`).
- **iLok/PACE** — verify it renders ([[vst-verify]]); iLok Cloud needs constant internet; never trust an
  unlicensed/trial instance unattended. Pin versions; persist `dump_state`.
- A channel strip is per-track/bus tone, not mastering — keep it off the master 2-bus (use [[vst-master]]).
- **Loudness-match before any A/B** — Mic drive + boosts raise level; "better" is often just "louder."

## Related

- [`docs/vst/kit-bb-n73.md`](../../../docs/vst/kit-bb-n73.md) — the full measured field guide
- [[kit-bb-n105]] — KIT's 4-band Neve **31105/8078** strip (cleaner, more sheen + Hi-Q; the N73's bigger sibling) · [[kit-bb-a5]] — KIT's Blackbird **API** console strip (the punchy sibling) · [[api-vision-channel-strip]] — UAD API strip · [[studer-a800]] — warm Neve/tape master stage
- [[vst-channel-strip]] — the generic channel-strip skill this specializes · [[vst-preset]] — apply enum/gain-staged chains
- [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants · [[vst-chain]] — the backbone recipe
- [[warm-drum-bus]] — the pure-DSP warm bus (tape/tilt, no plugin) · [[drum-punch]] — pure-DSP transient design · [[stem-master]] — per-stem corrective stage a strip fits
- [[mix-balance]] — balance the kit (measured loudness) before the strip · [[gemini-audio-understanding]] — why meters (not Gemini) own crest/peak/stereo
