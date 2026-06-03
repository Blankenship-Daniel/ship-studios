---
name: pultec-hlf-3c
description: "Use when running the UAD/UADx Pultec HLF-3C for clean, musical high-pass / low-pass FILTERING on a stem, bus, mix, or master — 'Pultec HLF-3C', 'Pultec filter', 'high-pass the rumble', 'roll off the harsh top', 'low-cut / high-cut filter', 'tame the cymbals / hiss / digital edge', 'band-limit this', 'lo-fi / telephone / vintage filter effect', or when you want a smooth passive filter instead of a surgical Butterworth HPF/LPF. The measured, plugin-specific deep-dive of [[vst-eq]] — a PURE FILTER (low-cut 50–2000 CPS + high-cut 1.5–15 KCS, no boost/Q/gain, 0.000% THD), grounded in the real 4-enum-param surface + isolation/slope/render numbers in docs/vst/pultec-hlf-3c.md. NOT a tonal EQ (that's the EQP-1A) — it only removes the extremes. Stemmy MCP, the `vst` extra. UADx native (iLok account, no dongle; verified-headless on this rig)."
argument-hint: <audio.wav> [goal: low-cut|high-cut|band-limit|lofi|tame-top|rumble]
---

# pultec-hlf-3c — drive the UADx Pultec HLF-3C passive filter (measured)

The plugin-specific, measured workflow for the **UADx Pultec HLF-3C EQ**
(`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_hlf-3c.vst3`) — UA's model of the **Pultec / Pulse Techniques HLF-3C**,
a **passive high-pass + low-pass FILTER set** (the "Pultec Filter"). It is **not** a boost/cut tonal EQ — that's the
**EQP-1A** ([[vst-eq]]) / **MEQ-5**. The HLF-3C has exactly two jobs: a stepped **LOW CUT-OFF** (high-pass, 50–2000
CPS) and a stepped **HIGH CUT-OFF** (low-pass, 1.5–15 KCS). It removes the extremes; it adds nothing. Full field guide
— real param surface, footguns, recipes, our numbers, sources — [`docs/vst/pultec-hlf-3c.md`](../../../docs/vst/pultec-hlf-3c.md).
This skill is the workflow.

## The governing facts (read first — all measured on this rig, Pedalboard 0.9.23)

1. **Renders headless — use the `uaudio_` build.** `uaudio_pultec_hlf-3c.vst3` loads + processes (UADx native, iLok
   *account*, no dongle here). The `UAD Pultec HLF-3C.component` / `/Universal Audio/…vst3` twins are the
   **passthrough** offline build — never load those ([[vst-verify]]).
2. **⚠️ The standard probe FALSE-FLAGS it as passthrough.** `presets/vst/probe_plugin.py` reports
   "PASSTHROUGH ✗ (ignores params)" — a **false negative**: the plugin has no gain/level/drive param, so the probe
   falls back to the first param (`low_cut`) and `extreme()` pushes it to its *first* enum value `'Off'` = the
   default → it compares **Off-vs-Off** → Δ0. It DOES render. **Verify by dialing a *real* value** (e.g.
   `low_cut='500 CPS'` → −59 dB @50 Hz). [[vst-verify]] with a real setting, not the canned probe.
3. **It's a PURE PASSIVE FILTER — it cannot warm/thicken/air/excite.** 4 params, **no boost, no Q, no gain**, and
   **0.000 % THD** at every level (just a +0.59 dB passband makeup gain). It only *subtracts* frequencies. For
   warmth/weight/air/saturation use a different box (`[L] saturate-loop` · [[excite]] · [[helios-type-69]] · tape)
   **before or after** — never expect tone-shaping from this unit.
4. **Slopes (measured) — passive, smooth, ~18 dB/oct, labels aren't −3 dB.** *LOW CUT (HPF):* the label reads ~the
   **−4 dB** point; the true **−3 dB sits ~6–12 % ABOVE** the label (50 CPS → −3 dB at ~59 Hz; 500 → 557; 1000 →
   1061). Slope steepens from ~12 dB/oct at the knee to **~18 dB/oct** deep (50 CPS = −28 dB @20 Hz). *HIGH CUT
   (LPF):* label ≈ the **−3 dB** point; **gentlest at the very top** (15 KCS ≈ **12 dB/oct**, only −5 @15k) and
   **~18 dB/oct** lower down (10 KCS = −3 @10k/−11.5 @15k; 5 KCS = −3.8 @5k/−18 @10k). To cut *more*, **move the
   freq a step**, don't expect a steeper slope.
5. **All 4 params are enums → drive it with the [[vst-preset]] harness, not `apply-vst-chain`'s float dict.**
   `low_cut`, `high_cut`, `enable` are **string** enums (`'50 CPS'`, `'5 KCS'`, `'In'`) the float dict silently
   misses. `enable='Out'` (the In/Out toggle) **and** `master_bypass=true` are both true bypasses (0.00 dB).
6. **Meters own it** (Gemini hears mono). The proof of a filter move is the **`measure-spectrum`** band/centroid/tilt
   delta — and **crest is the tell**: band-limiting *raises* crest (rumble/sustain removed → more peaky). A 0.00
   delta = the passthrough twin loaded.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]` perceptual
  tools (optional, `GEMINI_API_KEY`) for an A/B read.
- Confirm the build: `[L] list-vst-plugins {name_contains:"HLF"}` → take the **`uaudio_pultec_hlf-3c.vst3`** path.
  Dump the live surface any time: `../stemmy-loops-mcp/.venv/bin/python presets/vst/dump_params.py uaudio_pultec_hlf-3c`.
- **Do NOT trust `probe_plugin.py` here** (false passthrough, see fact 2) — verify with a real `low_cut`/`high_cut`
  value and re-measure the spectrum. A 0.00 spectrum delta = the `.component` twin loaded instead.

## The parameter surface (4 enums — authoritative)

| Param | Values | What it does (measured) |
|---|---|---|
| `low_cut` | `Off` · `50` · `80` · `100` · `150` · `250` · `500` · `750` · `1000` · `1500` · `2000 CPS` | **high-pass** (CPS = Hz); label ≈ −4 dB pt, ~18 dB/oct |
| `high_cut` | `1.5` · `2` · `3` · `4` · `5` · `6` · `8` · `10` · `12` · `15 KCS` · `Off` | **low-pass** (KCS = kHz); label ≈ −3 dB pt, top-gentle (12 dB/oct @15k) → ~18 dB/oct lower |
| `enable` | `In` · `Out` | the In/Out toggle — `Out` = **true bypass** (0.00 dB) |
| `master_bypass` | `false` · `true` | plugin bypass (also true bypass) |

> **That's the whole unit.** No boost, no cut, no Q, no frequency-gain, no drive, no output trim. If you reach for a
> param that isn't one of these four, you want a different plugin (EQP-1A for boost/cut, Pro-Q 4 for surgery).

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness` (crest).
   The "before" column. Decide the job: **clean the bottom** (low_cut), **tame the top** (high_cut), **musical
   band-limit** (both), or **lo-fi effect** (both, aggressive).
2. **Pick the corner(s)** from the move table. Remember the label ≠ −3 dB on the low-cut (it's ~the −4 dB point) and
   the high-cut is gentlest at 15 KCS. **To cut more, step the frequency, not the slope.**
3. **Build/pick a preset** (`presets/vst/pultec-hlf-3c-*.json`) setting **all 4** params explicitly, and apply with
   the harness: `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
   projects/<track>/mix/<stem>_hlf3c.wav`. (Three ship: `drum-bus-shape`, `lofi-bandpass`, `tame-harsh-top`.) Set
   `dump_state=true` via `apply-vst-chain` once dialed for a byte-stable re-render.
4. **Prove it** — re-`measure-spectrum`/`measure-loudness`. **Low-cut → lows below the corner drop, mids/top
   untouched, crest UP**; **high-cut → top above the corner drops, body untouched, centroid DOWN**; **band-limit →
   both, crest UP**. A 0.00 delta = passthrough twin (wrong build, or `enable='Out'`).
5. **Color elsewhere if needed** — the HLF-3C can't add anything. If the result is dull after a high-cut, add a
   presence bell / [[excite]] *below* the cut; if it's thin after a low-cut, that low energy is gone — don't expect
   the filter to give it back.
6. **QC** — `[G] detect-mix-issues` / `mastering-feedback` for over-filtering (thin/dull/muffled); cross-check any
   mono "dark/thin" flag against the meters ([[gemini-audio-understanding]]). It's a corrective filter
   insert, not a master — hand the result to [[master-track]] for loudness.

## Move table (measured on the Watercolors drum loop)

| Goal | HLF-3C move |
|---|---|
| **Clean sub rumble / mic-stand / room thump** ★ | `low_cut 50 CPS` (−3 dB ~59 Hz, kick body intact), `high_cut Off`. For a boomy bus push to `80`–`150 CPS`. |
| **Tame harsh / fizzy / over-bright top** ★ | `high_cut 10 KCS` (−3 @10k/−11.5 @15k; centroid 1593→1324, tilt −2.7→−3.5; body untouched — the shipped `tame-harsh-top`). Darker: `8`/`6 KCS`. |
| **Gentle musical drum-bus band-limit** ★ | `low_cut 50` + `high_cut 15 KCS` (lows trimmed, top softened, **crest 14.6→15.9** — the shipped `drum-bus-shape`). |
| **Just an "air trim" / vintage finished top** | `high_cut 12`–`15 KCS` (15k ≈ 12 dB/oct, only −5 @15k — the softest rolloff). |
| **Lo-fi / telephone / old-radio** ★ | `low_cut 250` + `high_cut 3 KCS` → ~250 Hz–3 kHz band, lows gutted (ratio 0.80→0.01), dominant peak 70→199 Hz, **crest 14.6→24.1** (the shipped `lofi-bandpass`). Harder: `500`/`1.5 KCS`. |
| **Tighten a boomy bottom (keep the kick)** | `low_cut 80`–`150 CPS` (steeper-feeling because the corner is higher). |
| **Mastering rumble cut (subtle)** | `low_cut 50 CPS`, `high_cut Off` — the lowest available corner; for an infrasonic-only cut prefer `[L] apply-eq` (HLF-3C's lowest is 50). |
| **Warmth / weight / air / saturation** | **NOT this box** — it only subtracts. Use `[L] saturate-loop` / [[excite]] / [[helios-type-69]] / tape before or after. |

## Outputs

- `projects/<track>/mix/<stem>_hlf3c.wav` + the reusable `presets/vst/pultec-hlf-3c-*.json` (and `.state` if dumped).

## Reporting to the user

State the corners set (low-cut Hz / high-cut kHz, or "off"), the before→after **centroid / tilt / target-band /
crest** deltas (crest UP = band-limited), that it ran headless via the `uaudio_` build (and that the standard probe
false-flags it), that it's a **pure filter — no tone/color added**, and the preset/`.state` path.

## Pitfalls

- **Wrong build = silent passthrough** — load `uaudio_pultec_hlf-3c.vst3`, not the `UAD …`/`/Universal Audio/` twins.
- **Don't trust `probe_plugin.py`** — it false-flags this unit (no gain param → Off-vs-Off). Verify with a real value.
- **It's a filter, not an EQ** — no boost/cut/Q/gain. It can't warm, thicken, brighten, or excite. Wrong tool for tone.
- **Float dict can't drive it** — `low_cut`/`high_cut`/`enable` are string enums → [[vst-preset]] harness.
- **Labels aren't −3 dB on the low-cut** (≈ −4 dB pt; true −3 dB ~10 % above) and the **high-cut is weakest at 15k** —
  to cut more, **step the frequency**, don't expect a steeper slope.
- **`enable='Out'` or `master_bypass=true` = no effect** (0.00 dB) even with corners dialed — keep `enable='In'`.
- **Over-filtering is one-way** — removed lows/highs are gone; re-measure before stacking another cut.
- It's a corrective filter insert, **not** mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/pultec-hlf-3c.md`](../../../docs/vst/pultec-hlf-3c.md) — the full measured field guide (Part A measured + Part B history/usage, cited)
- [[vst-eq]] — the generic skill this specializes · [[vst-preset]] — apply enum/all-explicit chains · [[vst-verify]] — prove the build renders (with a REAL value here) · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- Pultec siblings (tonal, NOT filters): [[fabfilter-pro-q-4]] (surgical/dynamic EQ) · [[helios-type-69]] (passive inductor EQ + drive) · [[hitsville-eq]] / [[hitsville-eq-mastering]] (Motown graphic EQ) — and the UADx **EQP-1A** / **MEQ-5** boost-cut Pultecs (no measured skill yet)
- Pure-DSP twins (no plugin): high/low-pass + tilt → `[L] apply-eq`; **dynamic** harshness (ring/level-dependent) → [[de-harsh]] / [[de-ess]] (a static high-cut just dulls); add air/presence → [[excite]]; saturation/warmth → `[L] saturate-loop`
- [[mix-check]] (find what to filter first) · [[vst-verify]] (why the build matters)
