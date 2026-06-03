---
name: kit-bb-a5
description: "Use when running the KIT Plugins BB A5 (Blackbird Studio API Legacy console strip) for punchy/forward 'American console' tone on drums, bus, bass, or guitar — 'KIT BB A5', 'Blackbird channel strip', 'API console on the drums', 'that Blackbird/API punchy sound', 'use the BB A5', or when you need the 55A/55L/56L API EQ modules + Mic-mode console drive dialed without harshness. The measured, plugin-specific deep-dive of [[vst-channel-strip]] — grounded in the real 46-param surface + isolation/drive/EQ numbers in docs/vst/kit-bb-a5.md. Stemmy MCP, the `vst` extra. iLok/PACE (verified-headless on this rig)."
argument-hint: <audio.wav> [goal: punchy-bus/clean-eq/smash]
---

# kit-bb-a5 — drive the KIT Plugins BB A5 (Blackbird API console strip, measured)

The plugin-specific, measured version of [[vst-channel-strip]] for the **KIT Plugins BB A5**
(`KIT BB A5.vst3`) — an emulation of the **API Legacy consoles at Blackbird Studio**. The
**forward/punchy "American console"** character: a sibling to [[api-vision-channel-strip]] (the UAD API
strip) and the contrast to the warm Neve/tape direction ([[studer-a800]]). Full field guide — real
param surface, the drive/harmonic map, the 3 EQ modules, the MSTR-BUSS gotcha, recipes, decision table,
and our own isolation numbers — lives in [`docs/vst/kit-bb-a5.md`](../../../docs/vst/kit-bb-a5.md).
This skill is the workflow.

## The governing facts (read first)

1. **MIC is the colored/driven path; LINE is cleaner — measured + maker-confirmed.** `pre_amp_source="Mic
   Mode"` + `pre_amp_gain` is the color engine (even+odd harmonics; H3 −64→−14 dB as gain 0→100). Line
   mode adds only a level-driven 3rd harmonic, and `pre_amp_gain` is **inert for color in Line**.
2. **The "input knob" is DRIVE, not level.** Color/glue = driving a stage: Mic-pre gain (strongest), or
   hitting the channel amp with hot `input_trim` / a pushed `master_fader` (3rd, level-driven). Driving
   `input_trim +18` took drum crest **11.6 → 8.0** (compression). `output_trim` / Line gain / MSTR-BUSS
   are clean make-up.
3. **MSTR BUSS makes it CLEANER here — opposite of the marketing.** `master_bus=true` drove all harmonics
   to ≤ −150 dB on a single render. Use it for a **transparent EQ pass**; for grit, leave it OFF.
4. **Keep the top modest (proportional-Q, no Q knob).** A big 2–5 kHz boost auto-narrows into a brittle
   peak — and 2–5 kHz is where API snap *and* harshness live. Punch from **low weight + de-box**, air
   from a small high shelf. 5 kHz is in both 55L hi-mid and the 56L — don't stack it.
5. **Three EQ modules:** `eq_choice` = **55A** (API 550A 3-band) · **55L** (API 550L 4-band) · **56L**
   (API 560L 10-band graphic). `*_filter_type`: **false=bell, true=shelf**. `*_continuous_gain=true` to
   set any ±dB.
6. **Meters own this** (Gemini hears mono): crest = punch, centroid/tilt = harshness watch, true-peak =
   clip. `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` / `check-clipping`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **`KIT BB A5.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"BB A5"}`. It's **iLok/PACE**
  but **verified to render headless on this machine**. Before trusting it, screen with
  `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "KIT BB A5"` (expect `RENDERS ✓`).
  **Never run an unlicensed/trial instance unattended** (it pops a GUI challenge / degrades output).
- **String-enum + bool params** (`pre_amp_source="Mic Mode"`, `eq_choice="55L"`, `55l_high_filter_type`,
  `master_bus`) → set via the **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`, `setattr`);
  `apply-vst-chain`'s `parameters` is float-only and can't reach them, nor gain-stage.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt) +
   `[L] measure-microdynamics`. The "before" column.
2. **Pick character** — *forward/punchy console* (its strength). Feed a dry-ish, measured-balanced
   bus/loop. Tighten sub first with `high_pass_filter` (`"40 Hz"` bus; higher on close mics).
3. **Color (Mic drive)** — `pre_amp_source="Mic Mode"`, `pre_amp_gain` ~25–40 for subtle even+odd console
   color + light peak-managing glue. Push toward 50–75 for odd-harmonic grit; `pre_amp_pad=true` if it
   slams. **For a clean EQ-only pass instead, use `Line Mode` (+ `master_bus=true`).**
4. **EQ** — `eq_on_off=true`, pick `eq_choice`: **55L** (4-band, most flexible) for a bus; **55A** (3-band
   + FLTR band-limit) for fast broad strokes; **56L** (graphic) for kick/whole-spectrum sculpting. Set
   `55l_continuous_gain=true`. Weight (low +3–4 @100, bell), **de-box** (lo-mid −3/−4 @ 300–500), modest
   presence (hi-mid ≤+2 @ 5k), small air shelf (hi +2–3 @ 12.5k, `type=true`). **Keep the top modest.**
5. **Glue (optional)** — leave `master_bus=false` to keep channel grit; push the **fader** (and trim
   output) for more channel-amp drive (squashes crest — a "smash"). `hum=false` for clean renders.
6. **Apply** — via [[vst-preset]] (`apply_vst_preset.py <preset.json> <in> <out>`), or build a chain in
   the harness; `dump_state` for repro. Output → `projects/<track>/mix/`.
7. **Verify** — re-measure. Forward = centroid/tilt up *moderately* (not into harsh 2–5 kHz spikes);
   punch = crest healthy (light glue OK, not collapsed); `check-clipping` (Mic gain + fader raise
   true-peak). A/B loudness-matched with `[L] render-ab`.

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset (and `.state` if dumped).
- Ready-made: `presets/vst/blackbird-a5-drums.json` — measured forward/punchy drum-bus chain (Mic g35 +
  55L weight/de-box/air + HPF 40; tilt −2.63→−2.23, low-mid de-boxed .18→.12, light glue crest 14.4→11.2).

## Reporting to the user

State Mic/Line + drive amount, the EQ module + moves, the before→after **crest / centroid / tilt**, that
it ran headless (iLok-authorized), and whether color came from Mic drive vs EQ vs the fader. Note MSTR
BUSS state (clean vs grit). A/B loudness-matched so taste isn't a level illusion.

## Pitfalls

- **MIC = colored, LINE = clean** (backwards from intuition) — use Mic for console grit.
- **MSTR BUSS is the *clean* mode here**, not glue — on for a transparent EQ pass, off for grit.
- **`pre_amp_gain` is inert for color in Line** — drive via Mic gain, or hot `input_trim`/fader.
- **No Q knob** (proportional-Q) — big 2–5 kHz boosts auto-narrow into brittle peaks; cut box / drive
  Mic instead; don't stack 5 kHz across 55L hi-mid + 56L.
- **`apply-vst-chain` can't set the string/bool enums or gain-stage** → use [[vst-preset]].
- **Mic gain jumps level** — peak-trim the output (the harness does) and re-check `check-clipping`.
- **iLok/PACE** — verify it renders ([[vst-verify]]); never trust an unlicensed/trial instance unattended.
- A channel strip is per-track/bus tone, not mastering — keep it off the master 2-bus (use [[vst-master]]).

## Related

- [`docs/vst/kit-bb-a5.md`](../../../docs/vst/kit-bb-a5.md) — the full measured field guide
- [[api-vision-channel-strip]] — the UAD API strip (sibling American-console deep-dive) · [[studer-a800]] — the warm Neve/tape counterpart
- [[vst-channel-strip]] — the generic channel-strip skill this specializes · [[vst-preset]] — apply enum/gain-staged chains
- [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants · [[vst-chain]] — the backbone recipe
- [[drum-punch]] — pure-DSP transient design · [[stem-master]] — per-stem corrective stage a strip fits · [[mix-balance]] — balance the kit before the strip
- [[gemini-audio-understanding]] — why meters (not Gemini) own crest/peak/stereo
