---
name: ssl-native-channel-strip-2
description: "Use when running the SSL Native Channel Strip 2 for clean/precise console tone, glue, surgical EQ, or gating on a stem or bus — 'SSL Native Channel Strip 2', 'SSL channel strip on the drums/vocal/bus', 'that clean SSL console sound', 'SSL EQ + comp', 'gate the snare with the SSL', or when you want the XL 9000K 4-band EQ (E/G), the channel comp, and the gate/expander dialed without added color. The measured, plugin-specific deep-dive of [[vst-channel-strip]] — grounded in the real 51-param Pedalboard surface + our isolation/comp-map/E-vs-G/preset renders in docs/vst/ssl-native-channel-strip-2.md. The CLEAN SSL counterpart to the warm Neve ([[kit-bb-n105]]/[[studer-a800]]) and forward API ([[api-vision-channel-strip]]/[[kit-bb-a5]]). Stemmy MCP, the `vst` extra. iLok/PACE (verified-headless on this rig)."
---

# ssl-native-channel-strip-2 — drive the SSL Native Channel Strip 2 (measured)

The plugin-specific, measured workflow for the **SSL Native Channel Strip 2**
(`/Library/Audio/Plug-Ins/VST3/SSL Native Channel Strip 2.vst3`) — SSL's software channel strip modelled on the
**XL 9000 K SuperAnalogue** console. It's the **clean / clinical** member of the strip family: precise EQ + glue,
the counterpart to warm Neve/tape ([[kit-bb-n105]] / [[studer-a800]]) and forward API ([[api-vision-channel-strip]]
/ [[kit-bb-a5]]), and the channel sibling of the SSL glue comp ([[ssl-bus-compressor-2]]) and the other SSL strip
([[ssl-4k-e]], the UAD 4000 E). Full field guide — param surface, modules, the E/G + routing, recipes, decision
table, our own measured numbers — lives in
[`docs/vst/ssl-native-channel-strip-2.md`](../../../docs/vst/ssl-native-channel-strip-2.md). This skill is the workflow.

## The governing facts (read first)

1. **`apply-vst-chain` CANNOT drive this strip — every meaningful control is a string enum or a log-stepped freq.**
   The float dict *can* set numeric gains (a trap — you'll think it worked while `eq_type`/`*_type`/`peak`/
   `fast_attack`/`gate_expander`/all routing stayed default). **Always use the [[vst-preset]] harness**
   (`presets/vst/apply_vst_preset.py`, `setattr` per param) or a `dump_state` blob. Enum strings are exact:
   `"In"`/`"Out"`, `"G"`/`"E"`, `"Shelf"`/`"Bell"`, `"RMS"`/`"Peak"`, `"Gate"`/`"Exp"`, `"Regular"`/`"Fast Attack"`.
2. **Clean at unity — color is your moves, not the box.** All sections default ⇒ crest 24.91→24.91 (passthrough).
   **Do NOT gain-stage into it** for "tone" (unlike the API/tape units). SSL = the EQ/comp choices.
3. **The channel comp's NORMAL attack barely compresses drums (~1 dB GR even at min threshold) — FAST ATTACK is
   the working drum mode.** And on drums fast attack + 0.1 s release *raised* crest here (transient-emphasis), not
   squashed it. Use normal attack for transparent glue at tiny GR; **measure GR + crest, don't assume.**
4. **E vs G EQ is real but subtle:** G slightly brighter/airier (centroid 5224 vs E 5098 @ +5 dB shelf), E warmer/
   fuller + constant-Q at low gain. **G** for broad bus tone, **E** for drums + surgical mid cuts.
5. **Meters own this** (Gemini hears mono): crest = punch/glue, correlation = tight, centroid/tilt = bright-vs-warm.
   `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` / `check-clipping`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- The **`SSL Native Channel Strip 2.vst3`** (VST3 — `[L] list-vst-plugins {name_contains:"channel strip"}`). Renders
  headless via Pedalboard, **iLok/PACE machine-authorized here** — iLok is a render-farm landmine, so **re-verify
  load+render on any other machine** ([[vst-hosting-outside-daw]]); machine activation (not Cloud) is the reliable
  headless route. AU twin is macOS-only — use the VST3.
- **Run patches through the [[vst-preset]] harness** — `presets/vst/apply_vst_preset.py <preset.json> <in> <out>`
  with the `vst` venv. `apply-vst-chain`'s `parameters` is float-only and silently misses every enum.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest/PLR) + `[L] measure-spectrum` (centroid/tilt) on the source.
2. **Pick the role** (drum bus / kick / snare+gate / OH / vocal / bass / mix bus) from the decision table in the
   field guide; default signal order is **Filters → EQ → Dynamics**.
3. **Build the patch** in a `presets/vst/*.json` (the harness sets enums). Levers:
   - **Filters:** `high_pass_filter_hz` (18 dB/oct; **log-stepped — `35.0` valid, `40.0` errors**; `"OUT"`=off),
     `low_pass_filter_khz` (12 dB/oct). Route to the detector with `filters_to_s_c="In"` so kick/bass don't
     over-trigger the comp.
   - **EQ:** `eq_in="In"`, `eq_type` **`"E"`** (drums/surgical) or **`"G"`** (bus/broad). LF/HF default `"Shelf"`,
     switch `"Bell"`. **LF gain is ±16.5 measured** (others ±20) — a +20 LF value is off-grid.
   - **Comp:** `dynamics_in="In"`, `compressor_ratio` (1→∞), `compressor_threshold_db` (drives auto make-up),
     **`compressor_fast_attack="In"`** to actually grab drums, `compressor_peak` (`"RMS"` soft / `"Peak"` hard),
     `compressor_release_s`, `compressor_mix` <100 for parallel.
   - **Gate:** `gate_range_db` >0 to engage (15–25 dB leaves natural bleed, not 40), `gate_threshold_db`,
     `gate_expander` (`"Gate"` ~40:1 / `"Exp"` 2:1), `gate_attack="Fast Attack"` for drum edges, `gate_hold_s` (max 4.0).
   - **De-ess / key:** `eq_to_s_c="In"` (boost the sibilant band so the comp keys on it) or `external_s_c="In"` (EXT).
4. **Apply** via `apply_vst_preset.py` (set `dump_state` / persist the `.state` for a reproducible re-render).
   Output → `projects/<track>/mix/`. (`input_gain_db` 0 — don't drive a clean console.)
5. **Prove it** — re-`measure-loudness`/`measure-spectrum`. Glue = crest steady/down at low GR; punch = **crest UP**;
   tone = centroid/tilt moved as intended. Loudness-match the A/B with **OUT TRIM** (or `[L] render-ab`).
6. **QC** — `[G] detect-mix-issues` (genre/intent set) for over-comp pump / harsh top; cross-check any mono "dark"
   claim against the stereo meters ([[gemini-mastering-feedback-cross-check]]). It's a **bus/stem insert, not a
   master** — hand off to [[master-track]] for loudness.

## Ready-made preset

- `presets/vst/ssl-native-cs2-drum-bus.json` — clean punchy drum bus: HPF 35, **E**-EQ (LF +3 @90, LMF −3 @450,
  HF +2.5 shelf @10k), comp **FAST** 4:1 thr −8 RMS auto-makeup. **Validated:** crest 24.9→**28.96** (MCP),
  −0.99 dBTP. Gentler mix-bus variant documented in its `notes`.

## Reporting to the user

State sections engaged + key settings (HPF / EQ type+moves / comp ratio+attack mode+GR / gate), the before→after
**crest / centroid / correlation**, that it ran headless (iLok-verified here), and that tone came from the EQ/comp
(SSL is clean — no drive). A/B loudness-matched so taste isn't a level illusion.

## Pitfalls

- **Never `apply-vst-chain`'s float dict for this strip** — it silently sets only numeric gains and misses every
  enum. Use [[vst-preset]].
- **`high_pass_filter_hz` is log-stepped** — an off-grid value (e.g. `40.0`) errors; the harness then warns and
  leaves the HPF at `"OUT"` (silently off). Pick a value the plugin accepts (`35.0` works).
- **LF gain ±16.5 measured, not ±20** — a 20 dB LF is off-grid.
- **Normal attack ≠ drum compression** (~1 dB GR). FAST ATTACK is the drum mode; measure crest.
- **PEAK is the knee switch** (RMS soft / Peak hard), not a separate detector toggle.
- **Don't gain-stage into it** — SSL is clean; drive adds nothing but level.
- **`EQ > DYN > FILTER` order is disallowed** — filter stays adjacent to EQ unless routed to the sidechain.
- **iLok per-machine** — verify load+render on any new node; don't clone the iLok DB.

## Related

- [`docs/vst/ssl-native-channel-strip-2.md`](../../../docs/vst/ssl-native-channel-strip-2.md) — the full measured field guide
- [[vst-channel-strip]] — the generic channel-strip skill this specializes · [[ssl-4k-e]] — the other SSL strip (UAD 4000 E) · [[ssl-bus-compressor-2]] — the SSL glue comp (pair on the bus)
- [[api-vision-channel-strip]] / [[kit-bb-a5]] (forward API) · [[kit-bb-n105]] / [[studer-a800]] (warm Neve/tape) — the colored counterparts to SSL's clean
- [[vst-preset]] — apply enum/gain-staged chains (REQUIRED for this strip) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants
- [[vst-eq]] / [[fabfilter-pro-q-4]] (surgical EQ) · [[vst-compress]] (dynamics) · [[drum-punch]] (pure-DSP transient design)
- [[mix-balance]] — balance the kit (measured loudness) before the strip · [[stem-master]] — per-stem corrective stage a strip fits · [[gemini-audio-understanding]] — why meters (not Gemini) own crest/peak/stereo
