---
name: ssl-4k-e
description: "Use when running the SSL 4K E channel strip (SL 4000 E console) for clean, weighty 'British console' tone on drums, bus, bass, or vocals — 'SSL 4K E', 'SSL E channel strip', 'SSL 4000 E', 'that SSL console weight/glue', 'Brown/Black/Orange EQ'. The measured deep-dive of [[vst-channel-strip]]; the clean/weighty counterpart to API forwardness ([[api-vision-channel-strip]]). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: drum-bus/glue/kick/snare/air]
---

# ssl-4k-e — drive the SSL 4K E Channel Strip (measured)

The plugin-specific, measured version of [[vst-channel-strip]] for the **SSL 4K E**
(`/Library/Audio/Plug-Ins/VST3/SSL 4K E.vst3`) — SSL's own **SL 4000 E** console-channel model, the
**clean / weighty / controlled** British-console counterpart to the API forward sound and the Neve/tape
warm sound. Full field guide — param surface, the EQ-colour table, the comp crest map, the bus shootout,
recipes, decision table, and our own isolation numbers — lives in
[`docs/vst/ssl-4k-e.md`](../../../docs/vst/ssl-4k-e.md). This skill is the workflow.

## The governing facts (read first)

1. **EQ COLOUR is the signature lever** — and the three cards are genuinely different *at identical dial
   settings* (measured): **'02 Brown' = brightest top + air** (musical, gritty), **'242 Black' = fattest
   lows + smoother top** ("legendary low-end weight"), **'132 Orange' (rare passive) = most forward
   2.5–5 kHz presence** ("great for kick & snare"). **Pick the colour, then dial.**
2. **The comp's FAST button is the punch lever, and it's TEXTBOOK — the OPPOSITE of the API Vision strip.**
   FAST attack **OUT** (slow/auto) lets transients through → **crest UP** (4:1 → 23.1, 10:1 → 25.1 vs dry
   21.6 = punch). FAST **IN** (~1 ms grabby VCA) clamps them → crest DOWN, denser/brighter. **Measure crest;
   don't carry the API "Medium beats Slow" rule over here.**
3. **Transparent at unity — color is opt-in.** Neutral ≈ dry (`analogue_vca` on/off negligible). Character
   = the EQ colour + the comp envelope + the **MIC preamp drive** (`mic_db` adds console grit).
4. **Punch is the comp; weight is the EQ. The E EQ is constant-Q** — it won't auto-narrow like API/SSL-G
   proportional-Q, so a big top boost just gets *bright*; get attack from the comp / Orange presence.
5. **Meters own this** (Gemini hears mono): crest = punch, correlation = tight, centroid/tilt = harshness
   watch. `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` / `check-clipping`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **`SSL 4K E.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"4K E"}`. It's the **4K E**, NOT
  `SSL Native Channel Strip 2` (different EQ + param surface — the 4K E's tell is `eq_colour`
  Brown/Black/Orange). iLok/PACE — renders headless here; **re-verify on a new machine**
  (`presets/vst/probe_plugin.py "SSL 4K E"` → `RENDERS ✓`).
- **⚠ Headless gotcha (measured):** `apply-vst-chain`'s float dict sets the **float** params
  (`*_gain_db`, `*_frequency_*`, `*_q`, `compressor_threshold_db`/`release_s`, `mic_db`, `width`, trims) but
  **CANNOT set the STRING enums** (`compressor_ratio`, `fader_level_db`, `pan`, `eq_colour`, `lf_type`/
  `hf_type`, every `Out`/`In` routing toggle) — it reports them `parameters_set` but the value **silently
  doesn't take** (numeric `compressor_ratio=4` → crest 22.3 vs the harness's `'4.0'` → 23.2). Use the
  **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`) for any ratio/colour/type/routing; it sets
  exact strings and snaps log-stepped corners (HPF) to the nearest valid value.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt) +
   `[L] measure-stereo` (corr). The "before" column.
2. **Pick the EQ colour for the tone** — Brown (air/musical) · Black (weight/clean) · Orange (forward
   mids, kick/snare). This decides the character before any move.
3. **Filter** — `filters_in='In'`, `high_pass_filter_hz` ~30–40 (bus) / 80–120 (snare) / 150–400 (OH) to
   strip sub before the dynamics. Route to the detector (`filters_to_s_c='In'`) to stop the kick
   over-triggering the bus comp.
4. **EQ** — LF **bell** for focused weight (Black @ 70–90) or shelf for broad warmth; de-box −2/−3 @
   400–500; small presence/attack with HMF; air via HF **shelf** (Brown). Small moves; constant-Q won't
   sharpen a big boost.
5. **Comp (the punch)** — `dynamics_in='In'`, ratio 2:1 (glue) … 4:1 (punch) … ∞ (limit), threshold for
   **3–6 dB GR**, release 0.1–0.3 s. **`compressor_fast_attack='Out'` for punch (crest up); `'In'` for
   grabby control/density.** `compressor_mix` <100 for parallel ("New York") on the channel.
6. **Apply via [[vst-preset]]** — `apply_vst_preset.py <preset.json> <in> <out>` (the `vst` venv);
   ready-made `presets/vst/ssl-4k-e-drum-bus.json` (Black weight + punch) / `ssl-4k-e-glue.json` (Brown
   glue). Re-set the comp threshold to your source level. Output → `projects/<track>/mix/`.
7. **Verify** — re-measure. Punch = **crest UP** (not just louder); weight = low band up, centroid steady
   (Black keeps it warm); tight = corr up + mono-sum loss small; `check-clipping` (auto-makeup pushes
   true-peak). A/B loudness-matched with `[L] render-ab`. Optional `[G] detect-mix-issues` for over-comp.

## Recipes (measured / from the manual)

| Goal | Colour | HPF | EQ | Comp (ratio / FAST / GR) |
|---|---|---|---|---|
| **Drum bus: weight + punch** ★ | Black | ~40 | LF-bell +3 @80, −2/−3 @450, +1.5 @3k | 4:1 / **out** / 3–6 dB |
| Bus glue | Brown | ~30 | +2 @60 shelf, −2 @400, +2 @12k shelf | 2:1 / out / 2–3 dB |
| Parallel glue | Brown | ~30 | small | 10:1 / in / **MIX ~40** |
| Punchy kick | Orange | 30–40 | +3–4 @60–80, +3 @3–5k | 4:1 / in (grab) / 3–6 dB |
| Snare snap | Orange | 80–120 | +2–3 @200, +3–4 @3–5k | 4:1 / taste / modest |
| Air / open top | Brown | — | HF **shelf** +2–4 @ 10–12k | light |

★ the validated winner (`presets/vst/ssl-4k-e-drum-bus.json`): crest 21.6→23.2, centroid stays warm
(2223→2272), corr 0.983, mono-sum loss 0.64 dB.

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset (and `.state` if `dump_state`).
- Report: colour + key moves (HPF / EQ / comp ratio+FAST+GR), before→after **crest / centroid / corr**,
  that it ran headless, and that punch came from the comp (not the EQ). A/B loudness-matched.

## Pitfalls

- **String enums don't set via the float dict** — ratio/colour/type/routing/fader/pan need the harness.
- **FAST attack is the opposite of the API strip** — FAST-out is the punchier (higher-crest) setting here.
- **Constant-Q EQ** — big top boosts go bright, not snappy; use the comp / Orange for attack.
- **Auto make-up raises level + true-peak** — loudness-match before judging; re-set threshold per source.
- **It's the 4K E, not Channel Strip 2** — confirm the path; don't mix the two param surfaces.
- **iLok/PACE** — re-verify load+render on any new machine before trusting it.

## Related

- [`docs/vst/ssl-4k-e.md`](../../../docs/vst/ssl-4k-e.md) — the full measured field guide
- [[vst-channel-strip]] — the generic strip skill this specializes · [[ssl-bus-compressor-2]] — the SSL bus glue comp (pair the 4K E channel with the SSL bus comp)
- [[api-vision-channel-strip]] / [[kit-bb-a5]] — the API forward counterparts · [[studer-a800]] / [[kit-bb-n105]] — the Neve/tape warm counterparts
- [[vst-preset]] — apply enum/string chains (required here) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge colour/setting variants
- [[vst-chain]] — the backbone recipe · [[fabfilter-pro-q-4]] — surgical/clean EQ pairing · [[stem-master]] — per-stem corrective stage a strip fits
- [[mix-balance]] — balance the kit (measured loudness) before the strip · [[gemini-audio-understanding]] — why meters (not Gemini) own crest/peak/stereo
