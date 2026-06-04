---
name: kit-bb-n105
description: "Use when running the KIT Plugins BB N105 V2 (Blackbird Studio Neve 8078 / 31105 channel strip) for warm, thick, vintage Neve tone on drums, bus, bass, or vocals — 'KIT BB N105', 'Blackbird Neve channel', 'Neve 8078/31105 console', 'that warm Neve drum sound', 'use the BB N105', or when you need the 4-band 31105 EQ + Mic-mode transformer drive dialed for warmth without harshness. The measured, plugin-specific deep-dive of [[vst-channel-strip]] — grounded in the real 23-param surface + isolation/drive/EQ numbers in docs/vst/kit-bb-n105.md. The WARM Neve counterpart to the punchy API siblings [[kit-bb-a5]] / [[api-vision-channel-strip]]. Stemmy MCP, the `vst` extra. iLok/PACE (verified-headless on this rig)."
argument-hint: <audio.wav> [goal: warm-bus/weight/de-box/air]
---

# kit-bb-n105 — drive the KIT Plugins BB N105 V2 (Blackbird Neve 8078 channel, measured)

The plugin-specific, measured version of [[vst-channel-strip]] for the **KIT Plugins BB N105 V2**
(`KIT BB N105 V2.vst3`) — an emulation of a **Neve 8078** console channel (the **31105** input/EQ
module) at **Blackbird Studio**, Nashville. The **warm / thick / vintage Neve** character: the
counterpart to the forward/punchy American-console siblings [[kit-bb-a5]] and [[api-vision-channel-strip]],
and the on-brand pick for the house **warm + tight** drum bus. Full field guide — real param surface, the
Mic-drive harmonic map, the 4-band EQ, the licensing/headless caveat, recipes, decision table, and our own
isolation numbers — lives in [`docs/vst/kit-bb-n105.md`](../../../docs/vst/kit-bb-n105.md). This skill is
the workflow.

> **iLok/PACE:** verified-headless on THIS rig only — if authorization drifts, re-screen with
> [[vst-verify]] before trusting a render; never run an unlicensed/trial instance unattended.

## The governing facts (read first)

1. **The Neve color is MIC-MODE ONLY — measured.** `pre_amp_mode="Mic"` + `pre_amp_saturation=true` is
   the transformer-drive color (odd-harmonic Neve thickness). **In `Line` mode both `pre_amp_sensitivity`
   and `pre_amp_saturation` are INERT — byte-identical at every setting.** Mic sensitivity adds real gain
   (**−70 = MAX**, ~+16 dB over −15) and a *gentle* saturation (≤~1.4 % THD) that grows with drive.
2. **Mic drive = "tighten lows + add sheen," not squash.** On the drum bus it **trimmed sub (−2 to −3 dB),
   added air (+2 dB), and raised crest (23.6 → 24.5)**. Warmth comes from the transformer, **not from an
   EQ air boost** — exactly the house warm-tight preference (warm via the drive, not bright EQ).
3. **No host Auto-Gain.** The GUI Auto-Gain / Continuous / Master-Buss / Oversampling are **not exposed**
   to the host — only 23 params are automatable. Mic drive jumps the level → compensate by hand with
   `output_gain` (measured exactly linear), and/or the harness peak-trim.
4. **EQ = the real 31105 surface, all ±15 dB.** HF shelf↔peak (tops at **15 kHz** — 12 kHz is LPF only);
   HMF/LMF bells with **Hi-Q (mids-only)**; LF shelf↔peak; **HPF top = 270 Hz**, LPF to 18 k; filters
   ~−2 dB at the corner, ≈18 dB/oct family slope. Boosts are broad/musical (80-series).
5. **Every param is an enum.** Numeric gains (`*_gain`, `pre_amp_sensitivity`, `output_gain`) accept a
   **float** (rounded to 0.1 dB) — `apply-vst-chain`'s float dict reaches those. **Frequencies (`"56 Hz"`,
   `"15 kHz"`), modes (`"Shelf"`/`"Peak"`/`"Mic"`), Hi-Q, phase, eq, saturation are STRING/bool enums** →
   set via the **[[vst-preset]]** harness (`apply_vst_preset.py`, `setattr`), which can also gain-stage.
6. **N105 ≠ N73.** This is the **31105** (4-band 80-series EQ + console drive); KIT's **BB N73** is the
   1073. The marketing **"Master Buss" is API-derived** (Blackbird's API Legacy console — the [[kit-bb-a5]]
   plugin) and is **GUI-only here** anyway.
7. **Meters own this** (Gemini hears mono): crest = punch kept, centroid/tilt = warmth vs harshness,
   true-peak = clip. `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` / `check-clipping`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **`KIT BB N105 V2.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"N105"}`. It's **iLok/PACE**
  but **verified to render headless on this machine**. Before trusting it elsewhere, screen with
  `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "N105"` (expect `RENDERS ✓`).
  **Never run an unlicensed/trial instance unattended** (iLok Cloud needs constant internet; an
  unauthorized node demo-silents — loads≠renders).
- **String-enum + bool params** (`pre_amp_mode="Mic"`, `high_frequency="15 kHz"`, `low_mode="Shelf"`,
  `pre_amp_saturation`, `eq`, `phase`) → set via the **[[vst-preset]]** harness; `apply-vst-chain`'s
  `parameters` is float-only (gains only) and can't reach them, nor gain-stage.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt) +
   `[L] measure-microdynamics`. The "before" column.
2. **Pick character** — *warm/thick Neve* (its strength). Feed a dry-ish, measured-balanced bus/loop
   ([[mix-balance]] first). Tighten sub with `hpf_frequency` (`"47 Hz"` bus; higher on close mics —
   snare 82–150, OH 150–270).
3. **Color (Mic transformer drive)** — `pre_amp_mode="Mic"`, `pre_amp_saturation=true`,
   `pre_amp_sensitivity` ~−40 to −45 for subtle warmth; push toward −55…−70 for more odd-harmonic
   thickness. **Compensate the level jump with `output_gain`** (e.g. −12…−22). *(`Line` mode = clean EQ
   console with no drive color.)*
4. **EQ (tighten + weight, keep it warm)** — `eq="EQ On"`. **Weight:** `low_frequency="56 Hz"`,
   `low_mode="Shelf"`, `low_gain≈+2`. **De-box:** `lo_mid_frequency="470 Hz"`, `lo_mid_gain≈−2`. For warm,
   **leave HF off** — let the transformer be the only top lift. For a brighter "Neve air" variant add
   `high_frequency="15 kHz"`, `high_mode="Shelf"`, `high_gain≈+2` (measured +845 Hz centroid). Surgical
   pings: a mid bell with `hi_mid_hi_q="Hi-Q On"`.
5. **Apply** — via [[vst-preset]] (`apply_vst_preset.py <preset.json> <in> <out>`), or build a chain in the
   harness; `dump_state` for repro. Output → `projects/<track>/mix/`.
6. **Verify** — re-measure. Warm-tight = **low ratio up + low-mid de-boxed + sub tightened, tilt stays
   warm, crest preserved/up** (drive added sheen, didn't squash); `check-clipping` (Mic drive raises
   true-peak). A/B loudness-matched with `[L] render-ab`.

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset (and `.state` if dumped).
- Ready-made: `presets/vst/bb-n105-warm-drum-bus.json` — the measured warm-tight Neve drum bus (Mic sat
  sens −42 + HPF 47 + LF +2@56 + de-box −2@470, HF off, output −13). Dry→processed: crest 23.6→24.5,
  centroid 3128→3539 (transformer sheen, not EQ), low ratio .542→.588, low-mid .378→.327, tilt stays −1.9.

## Reporting to the user

State Mic/Line + drive amount (sensitivity), the EQ moves, the before→after **crest / centroid / tilt /
low+low-mid ratios**, that it ran headless (iLok-authorized here), and that the warmth came from the
**transformer drive, not an EQ air boost**. A/B loudness-matched so taste isn't a level illusion.

## Pitfalls

- **LINE preamp is inert** — switch to **Mic** for any drive/saturation; `pre_amp_sensitivity`/`saturation`
  do nothing in Line.
- **No host Auto-Gain** — Mic drive jumps level; compensate with `output_gain` (the harness also peak-trims)
  and re-check `check-clipping`.
- **HF EQ tops at 15 kHz** (12 kHz is LPF/LMF only); **Hi-Q is mids-only**; **HPF top is 270 Hz**.
- **`apply-vst-chain` can't set the string/bool enums or gain-stage** → use [[vst-preset]] (gains-only float
  moves can go through `apply-vst-chain`).
- **analog hum is negligible offline** — leave it off for clean stems.
- **N105 ≠ N73** (31105 vs 1073); the **Master-Buss is API** (GUI-only here, not Neve).
- **iLok/PACE** — verify it renders ([[vst-verify]]); iLok Cloud needs constant internet; never trust an
  unlicensed/trial instance unattended. Pin versions; persist `dump_state`.
- A channel strip is per-track/bus tone, not mastering — keep it off the master 2-bus (use [[vst-master]]).
- **Loudness-match before any A/B** — Mic drive + boosts raise level; "better" is often just "louder."

## Related

- [`docs/vst/kit-bb-n105.md`](../../../docs/vst/kit-bb-n105.md) — the full measured field guide
- [[kit-bb-a5]] — KIT's Blackbird **API** console strip (the punchy sibling; the N105's "Master Buss" is its console) · [[api-vision-channel-strip]] — UAD API strip · [[studer-a800]] — warm Neve/tape master stage
- [[vst-channel-strip]] — the generic channel-strip skill this specializes · [[vst-preset]] — apply enum/gain-staged chains
- [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants · [[vst-chain]] — the backbone recipe
- [[warm-drum-bus]] — the pure-DSP warm bus (tape/tilt, no plugin) · [[drum-punch]] — pure-DSP transient design · [[stem-master]] — per-stem corrective stage a strip fits
- [[mix-balance]] — balance the kit (measured loudness) before the strip · [[gemini-audio-understanding]] — why meters (not Gemini) own crest/peak/stereo
