---
name: api-vision-channel-strip
description: "Use when running the UAD/UADx API Vision Channel Strip for tight/punchy/forward drums or bus tone — 'API channel strip on the drums', 'API Vision', 'punchy American console sound', 'tight aggressive drum bus', 'use the API strip', or when you need the 215/235/225/550/560 modules dialed for punch without harshness. The measured, plugin-specific deep-dive of [[vst-channel-strip]] — grounded in the real param surface + isolation/shootout numbers in docs/vst/api-vision-channel-strip.md. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: punchy-bus/glue/de-harsh]
---

# api-vision-channel-strip — drive the UAD API Vision Channel Strip (measured)

The plugin-specific, measured version of [[vst-channel-strip]] for the **UAD/UADx API Vision Channel Strip**
(`uaudio_api_vision_channel_strip.vst3`) — the **forward/punchy American-console** counterpart to the
Neve/Studer tape sound ([[studer-a800]]). Full field guide — param surface, the 6 modules + signal flow, the
levers, the crest map, recipes, decision table, and our own isolation/shootout numbers — lives in
[`docs/vst/api-vision-channel-strip.md`](../../../docs/vst/api-vision-channel-strip.md). This skill is the workflow.

## The governing facts (read first)

1. **"Slow attack = punch" is FALSE here — measured.** On this strip, **Medium (18 ms) attack maximized crest
   (FB 31.3); Slow (75 ms) gave the LEAST (28.6/27.9)** — opposite of the textbook. The 225 comp adds punch at
   every setting (all ≫ dry 25.0), but **measure crest across attack settings; don't assume.**
2. **The strip is clean at unity — color is opt-in.** All modules off ≈ no change. The "API color" is
   **2nd-order (even) harmonic** + transformer push, engaged by driving the **212** and the EQ/comp (not tape's
   odd/3rd, and not always-on).
3. **Keep the 550 top flat for un-harsh punch.** 2–5 kHz is where API snap *and* harshness live, and
   proportional-Q makes a big boost there auto-narrow into a brittle peak (our shootout: 5 k/10 k boosts pushed
   centroid +535/+714 — the Neve harshness again). Get punch from the **comp envelope + low thump + de-box**,
   not from boosting the top. **5 kHz is in both `550_hmf` and `550_hf` — never stack it.**
4. **Meters own this** (Gemini hears mono): crest = punch, correlation = tight, centroid/tilt = harshness watch.
   `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` / `check-clipping`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- The **`uaudio_api_vision_channel_strip.vst3`** build (UADx native — renders headless). Confirm with
  `[L] list-vst-plugins {name_contains:"vision"}`. The `UAD ….component` twin passes through offline — never use it.
- Enum/float/bool params (`225_attack='Medium'`, `225_type='Old (FB)'`, `550_lf_freq=100.0`, `eq_on=true`) →
  set via the **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`); `apply-vst-chain`'s `parameters`
  is float-only and can't gain-stage. **Every module's `_on` is off by default** — engage what you use.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt) +
   `[L] measure-microdynamics`. The "before" column.
2. **Gain-stage** — drive the input (`line_gain` for a Line bus, or the harness `input_gain_db`) for *subtle*
   color, **not** clipping (use `pad` if it slams). Drive is a color knob, not a loudness knob.
3. **Tighten** — `215_on=true`, `215_hp_filter≈40` Hz (bus) to strip sub before the dynamics. Higher on close
   mics (snare 80–120, OH 200–400).
4. **Punch (the comp)** — `225_on=true`, `225_type` New (FF, tight/modern) or Old (FB, glue), `225_ratio` 3–4,
   `225_knee` Hard, `225_release` ~0.1–0.2 s, target **3–6 dB GR**. **`225_attack`: measure crest across
   Fast/Medium/Slow** and pick the punchiest for your material (Medium often wins; Slow is calmest). `sc_link=true`
   on a stereo bus.
5. **Tone (550, optional)** — `eq_on=true`, `eq_type=550L`. Low thump (`550_lf` +3–6 @ 50–100, Peak), de-box
   (`550_lmf` −3/−4 @ 400–500). **Keep the top flat** unless you want an intentional accent; if you must, small
   (≤4 dB) and don't stack 5 kHz across HMF+HF. (PREDYN to EQ into the comp; default is comp-before-EQ.)
6. **Apply** — via [[vst-preset]] (`apply_vst_preset.py <preset.json> <in> <out>`), `dump_state` for repro.
   Output → `projects/<track>/mix/`.
7. **Verify** — re-measure. Punch = **crest UP** (not just louder); tight = correlation up + sub controlled;
   un-harsh = centroid/tilt didn't spike into 2–5 kHz; `check-clipping` (drive pushes true-peak). A/B
   loudness-matched with `[L] render-ab`.

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset (and `.state` if dumped).
- Ready-made: `presets/vst/tight-70s-api.json` — the shootout-winning tight/dry/punchy drum-bus chain.

## Reporting to the user

State the modules engaged + key settings (HPF / comp type+attack+ratio+GR / 550 moves), the before→after
**crest / centroid / correlation**, that it ran headless, and whether punch came from the comp vs EQ. A/B
loudness-matched so taste isn't a level illusion.

## Pitfalls

- **Don't assume "slow attack = punch"** — measure the crest map; Medium often wins here.
- **Keep the 550 top flat** — 5 kHz boosts re-create the hi-mid harshness; proportional-Q sharpens big boosts.
  Cut box / drive the comp instead.
- **No THRUST on the 225L** (it's a 2500 feature) — approximate with `215_dyn_sc` + a sidechain HPF.
- **SC buttons remove the module from the AUDIO path** (they steer the detector) — lit EQ-SC = no EQ on output.
- **Default flow is comp-before-EQ** — use `eq_predyn` to EQ into the comp.
- **Presets don't carry your level** — re-set the 225/235 thresholds to the track.
- **It colors only when driven** — a quiet bus through it is nearly passthrough; drive the 212 (gain-staged).

## Related

- [`docs/vst/api-vision-channel-strip.md`](../../../docs/vst/api-vision-channel-strip.md) — the full measured field guide
- [[vst-channel-strip]] — the generic channel-strip skill this specializes · [[studer-a800]] — the warm Neve/tape counterpart (API = forward, tape = warm)
- [[vst-preset]] — apply enum/gain-staged chains · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants
- [[vst-chain]] — the backbone recipe · [[drum-punch]] — pure-DSP transient design · [[stem-master]] — per-stem corrective stage a strip fits
- [[mix-balance]] — balance the kit (measured loudness) before the strip · [[gemini-audio-understanding]] — why meters (not Gemini) own crest/peak/stereo
