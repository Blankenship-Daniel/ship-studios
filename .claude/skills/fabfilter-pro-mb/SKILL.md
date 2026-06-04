---
name: fabfilter-pro-mb
description: "Use when running FabFilter Pro-MB for multiband dynamics — band-split compression/expansion, dynamic-EQ-style resonance/mud/boom taming, de-ess, multiband bus glue, M/S dynamics, or upward presence/air — 'Pro-MB', 'multiband compress this bus', 'tame the harshness only when it spikes', 'dynamic de-ess', 'glue the drum bus per band', 'upward-expand the presence'. The plugin-specific deep-dive of [[vst-compress]] / [[multiband-compress]]. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: de-harsh|de-ess|multiband-glue|tame-mud|tame-boom|add-presence|tighten|m-s|parallel]
---

# fabfilter-pro-mb — drive FabFilter Pro-MB (measured)

The plugin-specific, measured workflow for **FabFilter Pro-MB** (`/Library/Audio/Plug-Ins/VST3/FabFilter
Pro-MB.vst3`) — a **6-band multiband dynamics** processor that does **compression AND expansion, downward AND
upward**, on dynamic (movable) crossover bands, each with its own side-chain (Band/Free, internal/external),
Mid/Side operation, and three phase modes. It's the **multiband / dynamic-EQ** member of [[vst-compress]] —
the band-split, dynamics-driven counterpart to the parametric [[fabfilter-pro-q-4]] (Pro-Q dynamic EQ has no
band-split) and the broadband [[fairchild-660]] / [[ssl-bus-compressor-2]]. Full field guide — real param
surface, footguns, recipes, our numbers, sources — [`docs/vst/fabfilter-pro-mb.md`](../../../docs/vst/fabfilter-pro-mb.md).
This skill is the workflow.

## The governing facts (read first — measured on this rig)

1. **Renders headless AND no-iLok — uniquely safe here.** It loads + processes through Pedalboard 0.9.23
   (probe: pushed `output_level` → Δ 2.44; **156 params**), and FabFilter uses a **simple license key, no
   iLok/PACE/UAD dongle** — so unlike the [[vst]] landmines it's a clean render-farm
   candidate (same as [[fabfilter-pro-q-4]]). Use the **VST3** path (an AU `.component` twin is also installed).
2. **A bare load is a TRUE passthrough — the OPPOSITE of Pro-Q.** All 6 band slots default to `Unused`, and a
   fresh `load_plugin` measured **0.0000 dB** vs the input across every band. So **you do NOT flatten Pro-MB**
   (Pro-Q restores its last GUI curve and must be flattened — Pro-MB does not). Just `Enabled` the bands you want.
3. **RANGE is the master "amount" knob — set it NONZERO or the band is inert.** Measured: a band `Enabled`,
   `threshold=-35`, `ratio=4.00:1`, but **`range=0`** rendered **bit-for-bit identical to the dry input**.
   `band_N_range` (−30…+30 dB) is the *maximum gain change*; `threshold`/`ratio` only shape *how* it gets there.
   The #1 Pro-MB footgun: dialing threshold/ratio without a nonzero range does **nothing**.
4. **The four quadrants** = `dynamics_mode` (Compression/Expansion) × sign of `range` (measured on a 3–9 kHz band):
   **Compression + negative range** = downward comp (duck loud; −24/8:1 → 5 kHz **−8.5 dB**, lows untouched);
   **Compression + positive range** = upward comp (lift quiet, add density); **Expansion + positive range** =
   **upward expansion** (boost the loud part of the band; +12 → presence **+5.6 dB**, crest **+1.4** — a dynamic
   exciter/air); **Expansion + negative range** = downward expansion/gate (reduce *below* threshold — so the
   **threshold must sit ABOVE the quiet passages**, the inverse of compression; subtle on busy drums).
5. **All 156 params are enums → `apply-vst-chain`'s float dict can't drive it.** Measured: setting
   `band_1_range/threshold/crossover` via `apply-vst-chain` returned **`changed:false`** (the band stayed
   `Unused` — `band_1_state` is a *string* enum the float dict can't set, as are `dynamics_mode`, `ratio`, the
   slopes, `processing_mode`). **Use the [[vst-preset]] harness** (`apply_vst_preset.py`, `setattr` — reaches
   strings + bools) for any real move, or a `dump_state` blob.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G] find-resonances`
  / `find-sibilance` (optional, **pure DSP — no key**) to target the band(s).
- **`FabFilter Pro-MB.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"Pro-MB"}` and take the
  **VST3** path. Screen a new install with `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "Pro-MB"`
  (expect `RENDERS ✓`). No-iLok, but **loads ≠ renders** — always measure detail after.
- **Enum gotcha:** `apply-vst-chain`'s `parameters` is float-only — it can tweak a numeric param on a band that's
  *already* `Enabled` with a nonzero range, but it **cannot** enable a band or set any string enum. For real
  moves use the **[[vst-preset]]** harness, which `setattr`s every param. Inspect the surface with
  `presets/vst/dump_params.py "Pro-MB"`.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness`
   (crest/PLR — multiband dynamics change crest) (+ `measure-stereo` for an M/S move). The "before" column.
2. **Find targets (optional)** — `[G] find-resonances` → narrow peaks / problem bands; `[G] find-sibilance` →
   center Hz for a dynamic de-ess band; or read the spectrum for the boomy/muddy/harsh zone.
3. **Pick the quadrant + bands** from the table below. Choose `processing_mode`: **Dynamic Phase** (default —
   transient-safe, low latency, no pre-ring; right for drums) / **Minimum Phase** (lowest latency) / **Linear
   Phase** (only when phase coherence across a parallel sum matters — it pre-rings transients).
4. **Build a preset** (`presets/vst/fabfilter-promb-*.json`): for each band set `band_N_state="Enabled"`,
   `band_N_low_crossover`/`high_crossover` (+`_low_slope`/`_high_slope`), `band_N_dynamics_mode`,
   `band_N_threshold`, **a NONZERO `band_N_range`**, `band_N_ratio`, `band_N_attack`/`release`/`knee`/`lookahead`
   (attack/release are **0–100 % percentages, not ms** — no published ms mapping, program/frequency-dependent), `band_N_level`; plus globals `processing_mode`,
   `mix` (0–200 %, <100 = parallel), `oversampling`. Apply: `../stemmy-loops-mcp/.venv/bin/python
   presets/vst/apply_vst_preset.py <preset.json> <in> projects/<track>/mix/<stem>_promb.wav`. Set `dump_state=true`
   (via `apply-vst-chain`) once dialed for a byte-stable re-render.
5. **Prove it** — re-`measure-spectrum`/`measure-loudness`. Confirm the **targeted band moved while the others
   didn't** (band-split: lows stay flat when you work the presence), and detail changed (a 0.00 delta = the
   range-0 / disabled-band footgun). For a dynamic band the cut shows on peaks while steady level holds. A/B
   loudness-matched (`[L] render-ab` / [[level-match]]).
6. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch over-processing (pumping/thin/dull); cross-check
   any mono "dark/boxy" flag against the stereo bands ([[gemini-audio-understanding]]). It's a
   per-track/bus insert, not a master — hand the result to [[master-track]] for loudness.

## Move table (quadrant in **bold**)

| Goal | Pro-MB move |
|---|---|
| **De-harsh / dynamic de-ess** ★ | one band over the harsh/sibilant zone (de-harsh ~3–9 kHz, de-ess ~5–9 kHz), **Compression − range**, threshold so it ducks only the spikes. (Pure-DSP twins: [[de-harsh]] / [[de-ess]].) |
| **Multiband bus glue** ★ | 2–3 bands (lows, low-mid, presence), **Compression − range** gentle (−3…−6), ratio 2–4:1. Only the problem zones move. (Twin: [[multiband-compress]].) |
| **Tame mud / boom dynamically** | band on 30–120 Hz (boom) or 200–600 Hz (mud), **Compression − range**, threshold to catch the loud notes only. (Twin: [[dynamic-eq]].) |
| **Add presence / air dynamically** | band over the dull zone, **Expansion + range** (upward expansion — boosts the band's loud part; measured +5.6 dB presence, crest up). (Twin: [[excite]].) |
| **Density / upward comp** | broadband or per-band, **Compression + range** (lifts the quiet part toward the loud). |
| **Tighten tails / dynamic gate** | band (or full range), **Expansion − range**, threshold set ABOVE the quiet passages (inverse of comp). |
| **M/S width dynamics** | per-band `stereo_link_mode="Side"` (or `"Mid"`) + Compression/Expansion to control the side or mono the lows dynamically. |
| **Parallel multiband** | dial the move, then global `mix` < 100 % (0–200). Measured: mix 50 halved the duck. |
| **External-trigger duck** | `band_N_side_chain_input="External Input"` (+ `side_chain_filtering="Free"` to choose the trigger slice). |

★ shipped examples: `presets/vst/fabfilter-promb-drum-deharsh.json` (1 band, 3–9 kHz, Compression, range −9 →
measured **5 kHz −4.7 dB, 4 kHz −4.0, 6.3 kHz −4.6** while **1 kHz −0.05, 500 Hz 0.00, lows untouched**; centroid
1593→1506, tilt −2.71→−3.01) · `presets/vst/fabfilter-promb-drum-multiband-glue.json` (3 bands: lows + low-mid +
presence). Both set a **nonzero range** on every band and rely on the **passthrough-default** (no flatten needed).

## Outputs

- `projects/<track>/mix/<stem>_promb.wav` + the reusable `presets/vst/fabfilter-promb-*.json` (and `.state` if dumped).

## Reporting to the user

State the bands (range Hz / quadrant / threshold / range dB / ratio), the phase mode + any parallel `mix`, the
before→after **tilt / centroid / target-band deltas + crest**, that the **other bands stayed flat** (band-split),
that it ran headless (no-iLok), and the preset/`.state` path. A/B loudness-matched so it's not a level illusion.

## Pitfalls

- **Range 0 = no-op** — the band must have a NONZERO `range`; threshold/ratio alone do nothing (measured).
- **Don't flatten** (unlike Pro-Q) — bare load is a true passthrough; but **don't drive it via the float dict**
  either (can't enable a band / set string enums → `changed:false`). Use the [[vst-preset]] harness or a `dump_state`.
- **Expansion threshold is inverted** — a downward expander only acts *below* threshold; set the threshold up
  into the quiet passages or it never engages (measured no-op at threshold −35 on a loud band).
- **attack/release are 0–100 % percentages, NOT ms** — there is no published ms mapping (realized ms is
  program/frequency-dependent); below ~50 % = faster, above ~50 % = slower — calibrate by isolation render/ear.
- **Linear Phase pre-rings transients** — use Dynamic Phase (default) or Minimum Phase on drum/lead material.
- **Pro-MB ≠ Pro-Q dynamic EQ** — Pro-MB band-SPLITS (true multiband, sidechain, M/S, parallel); Pro-Q dynamic EQ
  is parametric with no band-split. Reach for Pro-MB when you need band isolation / sidechain / parallel / M/S
  dynamics; Pro-Q when you want a surgical parametric curve. A multiband insert is not mastering ([[master-track]]).

## Related

- [`docs/vst/fabfilter-pro-mb.md`](../../../docs/vst/fabfilter-pro-mb.md) — the full measured field guide
- [[vst-compress]] / [[multiband-compress]] — the generic skills this specializes · [[vst-preset]] — apply
  enum/multi-band chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index
- Pure-DSP twins (no plugin, deterministic): [[multiband-compress]] (multiband-compress) · [[dynamic-eq]]
  (apply-dynamic-eq) · [[de-harsh]] (suppress-resonances) · [[de-ess]] · [[excite]] (excite-loop)
- Sibling FabFilter: [[fabfilter-pro-q-4]] (parametric / dynamic / spectral EQ — no band-split) ·
  broadband comps [[fairchild-660]] / [[ssl-bus-compressor-2]] · [[mix-check]] (find the problems first) ·
  `[G] find-resonances` / `find-sibilance` to target the bands
