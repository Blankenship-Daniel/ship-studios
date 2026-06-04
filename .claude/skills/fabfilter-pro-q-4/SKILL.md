---
name: fabfilter-pro-q-4
description: "Use when running FabFilter Pro-Q 4 for surgical, dynamic, or spectral EQ on a stem/bus/loop — 'Pro-Q 4', 'FabFilter EQ', 'surgical-EQ this', 'notch out that resonance', 'dynamic EQ the mud', 'spectral de-harsh / de-ess with Pro-Q', 'mid/side EQ the master', 'add Pro-Q Warm character'. The measured, plugin-specific deep-dive of [[vst-eq]] — a 24-band parametric EQ with per-band dynamic EQ, the new Spectral Dynamics (Soothe-style), Character saturation, and Zero-Latency/Natural/Linear phase, grounded in the real 581-param Pedalboard surface + our render results in docs/vst/fabfilter-pro-q-4.md. Renders headless, no-iLok. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: notch|de-harsh|de-ess|dynamic|mid-side|tilt|character]
---

# fabfilter-pro-q-4 — drive FabFilter Pro-Q 4 (measured)

The plugin-specific, measured workflow for **FabFilter Pro-Q 4** (`/Library/Audio/Plug-Ins/VST3/FabFilter
Pro-Q 4.vst3`) — a 24-band, fully-parametric EQ with **per-band dynamic EQ**, the new **Spectral Dynamics**
(a Soothe/Gullfoss-style frequency-selective de-harsh/de-ess/resonance mode), analog **Character** saturation,
and three phase modes. The **surgical/transparent** member of [[vst-eq]] (vs the vintage Pultec/Neve or the
air-only Maag). Full field guide — real param surface, footguns, recipes, our numbers, sources —
[`docs/vst/fabfilter-pro-q-4.md`](../../../docs/vst/fabfilter-pro-q-4.md). This skill is the workflow.

## The governing facts (read first)

1. **Renders headless AND no-iLok — uniquely safe here.** It loads + processes through Pedalboard 0.9.23
   (param-response confirmed), and FabFilter uses a **simple license key, no iLok/PACE/UAD dongle** — so unlike
   the [[vst]] landmines it's a clean render-farm candidate. Use the **VST3** Pro-Q 4 path
   (the AU `.component` twin + Pro-Q 3 are also installed — don't grab those).
2. **A bare load is NOT flat — it restores FabFilter's last-saved GUI curve** (ours came up as the screenshot:
   band 1 Low Cut @30 Hz, band 2 Bell @202, band 3 Bell @4085). So every "fresh" render rides a leftover curve.
   **Flatten first** (disable all 24 bands → verified bit-exact bypass, 1.5e-16), then configure only the bands
   you want, or restore a `dump_state` blob.
3. **`apply-vst-chain`'s float dict can't really drive Pro-Q.** All 581 params are Pedalboard `valid_values`
   lists; the **string enums** (`band_N_shape`/`_slope`/`_used`, `processing_mode`, `character`) can't be set
   via a float-only dict, and you can't *enable an Unused band* through it. Our `band_8_gain=-12 @500 Hz` move
   via `apply-vst-chain` was a **no-op** (band 8 was Unused). **Use the [[vst-preset]] harness**
   (`apply_vst_preset.py`, `setattr` — reaches strings + bools) for any real move.
4. **Numeric params snap to the grid; the standout features all measure.** `setattr` floats snap (gain ≈0.06 dB,
   freq log: −5.0→−4.98, 80→80.18). Dynamic EQ + Spectral Dynamics + Character all render offline: our **Spectral
   Dynamics** de-harsh band ducked **5 kHz by 3.0 dB** while **sparing 4 kHz (−0.1) and 8 kHz (+0.4)** — surgical,
   not a static cut; `character="Warm"` added **+0.5 dB** color on an otherwise-flat instance. **Set every dynamic
   param explicitly** — an unset `band_N_dynamic_range` silently inherits the restored state's value (a footgun
   we hit). **Meters own it** (Gemini hears mono) — read centroid/tilt/band-ratios, not vibes.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G] find-resonances`
  / `find-sibilance` (optional, **pure DSP — no key**) to target the surgical/de-ess bands.
- **`FabFilter Pro-Q 4.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"Pro-Q 4"}` and take the
  **VST3** path. Screen a new install with `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "Pro-Q 4"`
  (expect `RENDERS ✓`). No-iLok, but **loads ≠ renders** — always measure detail after.
- **Enum gotcha:** `apply-vst-chain`'s `parameters` is float-only — it can tweak `band_N_frequency`/`gain`/`q`/
  `dynamic_range`/`spectral_density`/`gain_scale`/`output_level` **on a band that's already Used+enabled+shaped**,
  but it **cannot** set `band_N_shape`/`_slope`/`_used`, enable a band, or set `processing_mode`/`character`.
  For those (i.e. almost always) use the **[[vst-preset]]** harness, which `setattr`s every param.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness`
   (+ `measure-stereo` for an M/S move). The "before" column.
2. **Find targets (optional)** — `[G] find-resonances` → narrow-Q peaks + notch dB (→ static or dynamic Bells);
   `[G] find-sibilance` → center Hz/Q/threshold (→ a dynamic or **Spectral** high band).
3. **Pick the moves** from the table below. Choose the **phase mode**: **Natural Phase** (best quality, keeps
   drum transients) or **Zero Latency** for most work; **Linear Phase** only to avoid phase cancellation (parallel
   sums / mastering) — it pre-rings transients. (Spectral bands force linear-phase on themselves regardless.)
4. **Build a flatten-first preset** (`presets/vst/fabfilter-proq4-*.json`): disable bands 4–24, then for each
   used band set `*_used="Used"`, `*_enabled=true`, `*_shape`, `*_frequency`, `*_gain`, `*_q` (+`*_slope` for
   cuts; +`*_dynamics_enabled`/`*_dynamic_range`/`*_threshold` for dynamic; +`*_spectral_enabled`/`*_spectral_density`
   for spectral), plus `processing_mode`/`character`. Apply: `../stemmy-loops-mcp/.venv/bin/python
   presets/vst/apply_vst_preset.py <preset.json> <in> projects/<track>/mix/<stem>_proq4.wav`. Set `dump_state=true`
   (via `apply-vst-chain`) once dialed for a byte-stable re-render.
5. **Prove it** — re-`measure-spectrum`/`measure-loudness`. Confirm the intended band/tilt moved and **detail
   changed** (a 0.00 spectrum delta = passthrough). For a dynamic/spectral band, the cut shows on peaks while
   steady level is preserved (that's the point). A/B loudness-matched (`[L] render-ab` / [[level-match]]).
6. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch over-EQ (thin/dull/harsh); cross-check any mono
   "dark/boxy" flag against the stereo bands ([[gemini-audio-understanding]]). It's a per-track/bus
   insert, not a master — hand the result to [[master-track]] for loudness.

## Move table

| Goal | Pro-Q 4 move |
|---|---|
| **Surgical notch** | Bell, narrow Q (sweep with band **solo** if hunting), cut −3…−6 dB (or Q10–20 deeper for a ring). Level-dependent → make it **dynamic**. |
| **De-harsh / resonance** ★ | Bell over the harsh zone, **`spectral_enabled=true`**, negative `dynamic_range`, `spectral_density` high (surgical) — ducks only the ringing freqs. (Pure-DSP twin: [[de-harsh]].) |
| **De-ess** | dynamic/Spectral Bell 5–10 kHz, Q≈4–5, range −2…−6 dB, threshold so only esses duck. Pair any air shelf with it. (Twin: [[de-ess]].) |
| **Dynamic mud/boom** | Bell, `dynamics_enabled`, negative range, threshold so it cuts only on loud hits (e.g. 50–80 Hz boom, 200–350 Hz mud). (Twin: [[dynamic-eq]].) |
| **M/S master** | per band `stereo_placement` Mid/Side: Side HPF→~120–150 Hz (mono lows) + ~7 kHz air shelf; Mid low-cut + small −250 Hz. Small moves, 3/6 dB display. |
| **Tilt / tone** | `Tilt Shelf` / `Flat Tilt`, or shelves; `gain_scale` to scale the whole curve. |
| **Analog color** | `character="Subtle"` (transformer) or `"Warm"` (tube, 2nd harmonic) — no amount knob, apply selectively. |
| **Reference match** | EQ Match in-plugin (busy curve, prune by ear) — or prefer pure-DSP `[L] match-eq` / [[reference-match]] for control. |

★ the shipped example `presets/vst/fabfilter-proq4-drum-deharsh.json` (HPF 35 + −3 @250 + a **Spectral Dynamics**
band @5k: gain 0 / dynamic_range −8 / density 70, Natural Phase): measured 5 kHz −3.0 dB while 4 kHz (−0.1) & 8 kHz
(+0.4) are **spared** (surgical), 250 Hz −2.5 dB. Sets `dynamic_range` explicitly (unset = inherits restored state).

## Outputs

- `projects/<track>/mix/<stem>_proq4.wav` + the reusable `presets/vst/fabfilter-proq4-*.json` (and `.state` if dumped).

## Reporting to the user

State the moves (bands: shape/freq/gain/Q, which are dynamic/spectral), the phase mode + character, the
before→after **tilt / centroid / target-band deltas**, that it ran headless (no-iLok), and the preset/`.state`
path. A/B loudness-matched so taste isn't a level illusion.

## Pitfalls

- **For a multi-mic KIT pass, don't use the default `apply_vst_preset.py` harness** — it **upmixes mono→stereo**
  (`np.repeat`, before the chain) AND **peak-normalizes** to `output_peak_dbfs` (default −1.0), breaking a mono close mic's
  channel count and the measured inter-stem LUFS balance. `output_peak_dbfs: null` gives **faithful gain** (no renorm) but
  **still upmixes** — so for a per-stem soothe/EQ prefer `[L] apply-vst-chain` (preserves channels, no renorm) or a
  channel-preserving render ([[stem-process]]). A single stereo bus/loop: the harness is fine.
- **Don't trust a bare load to be flat** (restores the last GUI curve) and **don't drive it via the float dict**
  (can't shape/enable bands) — flatten + configure via [[vst-preset]], or a `dump_state` blob.
- **Spectral forces linear phase on that band** (latency/pre-ring) — keep its resolution Low/Medium, esp. >1 kHz;
  dynamics aren't supported above High resolution.
- **Per-stem kit soothe stays sample-aligned** — though Spectral runs linear-phase, Pedalboard 0.9.23
  **auto-compensates** the band's latency (impulse probe: flattened Pro-Q + one 5 kHz spectral band = **0 samples in==out**),
  so soothing the individual mics of a multi-mic kit doesn't smear them out of phase. Safe to de-harsh per-stem **before** summing ([[stem-process]]).
- **Linear Phase isn't free** — pre-ring softens transients; use Natural Phase / Zero Latency on drum/lead material.
- **Character has no amount knob; Auto Gain isn't metered** — verify level with a meter before any A/B.
- **Pro-Q 3 ≠ Pro-Q 4** — dynamic EQ/M/S/EQ-Match/Spectrum-Grab/Atmos were already in 3; new in 4 = Spectral
  Dynamics, dyn-EQ attack/release + free SC, Character, EQ Sketch, Instance List, fractional slopes, All Pass.
- **`spectral_tilt` (the 4.02 feature) isn't in the Pedalboard surface** on this rig — don't script it.
- A surgical EQ is a tonal insert, not mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/fabfilter-pro-q-4.md`](../../../docs/vst/fabfilter-pro-q-4.md) — the full measured field guide
- [[vst-eq]] — the generic EQ skill this specializes · [[vst-preset]] — apply enum/flatten-first chains ·
  [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- Pure-DSP twins (no plugin, deterministic): [[de-harsh]] (suppress-resonances) · [[dynamic-eq]] (apply-dynamic-eq) ·
  [[de-ess]] · [[reference-match]] / [[house-curve]] (match-eq) · `[L] apply-eq`
- [[mix-check]] (find the problems first) · `[G] find-resonances` / `find-sibilance` to target the surgical/de-ess
  bands · [[gemini-audio-understanding]] — why meters (not Gemini) own the spectrum read
