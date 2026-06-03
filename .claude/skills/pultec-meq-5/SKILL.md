---
name: pultec-meq-5
description: "Use when running the UAD/UADx Pultec MEQ-5 Mid-Range Equalizer for broad, musical MIDRANGE shaping on drums, drum bus, guitars, vocals, bass, or a mix bus — 'Pultec MEQ-5', 'MEQ-5', 'Pultec midrange EQ', 'de-honk / de-box this', 'scoop the mids', 'midrange presence / attack', 'add presence to the snare', 'that passive Pultec mid EQ', or when you want forgiving low-mid/mid/high-mid moves from a passive LC + tube EQ. The measured, plugin-specific deep-dive of [[vst-eq]] — three overlapping sections (LOW PEAK boost 200-1000 Hz · DIP cut 200-7000 Hz · HIGH PEAK boost 1.5-5 kHz) + an output trim; grounded in the real 10-param surface + transfer-function / THD / render numbers in docs/vst/pultec-meq-5.md. The MIDRANGE companion to [[pultec-eqp-1a]] (lows + air) and [[pultec-hlf-3c]] (filters). BROAD/musical, not surgical (pair with [[fabfilter-pro-q-4]] for notches). Stemmy MCP, the `vst` extra. UADx native (iLok account; verified-headless on this rig)."
argument-hint: <audio.wav> [goal: de-box|presence|warm-body|scoop|attack]
---

# pultec-meq-5 — drive the UADx Pultec MEQ-5 mid-range EQ (measured)

The plugin-specific, measured workflow for the **UADx Pultec MEQ-5 EQ**
(`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_meq-5.vst3`) — UA's model of the **Pultec MEQ-5 "Mid-Range
Equalizer"**: a **passive LC (inductor) EQ + tube make-up amp + transformers**, focused entirely on the
**midrange (≈200 Hz–7 kHz)**. Three overlapping sections — **LOW PEAK** boost, a **DIP** cut, and a **HIGH
PEAK** boost — plus an output trim. The **MIDRANGE** member of the Pultec Passive EQ Collection, next to the
lows+air [[pultec-eqp-1a]] and the HP/LP-filter [[pultec-hlf-3c]]. **Broad and musical** (a "colour" EQ), not
surgical. Full field guide — param surface, curve tables, recipes, history — lives in
[`docs/vst/pultec-meq-5.md`](../../../docs/vst/pultec-meq-5.md). This skill is the workflow.

## The governing facts (read first — all measured on this rig, Pedalboard)

1. **Renders headless — load the `uaudio_` build.** `uaudio_pultec_meq-5.vst3` loads + processes (UADx native;
   hm_peak=10 @3k moved the signal 0.285 max-abs). `master_bypass=True` is the **only TRUE null** (bit-identical
   to input). Don't load any `UAD …`/`Legacy .component` twin (passthrough offline). iLok account, no dongle —
   **re-verify on a new machine** ([[vst-verify]]).
2. **The MEQ-5 0–10 dial is ROUGHLY dB here** — *unlike* the [[pultec-eqp-1a]] (nonlinear, not-dB) and
   [[hitsville-eq-mastering]] ("8 ≈ +5 dB") knobs. Measured: **LOW PEAK ≈ +1 dB/unit → +10.7 dB max**;
   **HIGH PEAK ≈ +0.9/unit → +8.8 dB max**; the **DIP saturates** (~−1.4 @2, −4.9 @4, −8.9 @6, **−11 dB max**,
   barely moving past ~7). So amounts ≈ the dB you'll get for boosts; the DIP gives most of its cut by 6.
3. **Three sections, fixed-stepped frequencies, overlapping BROAD bells (passive).** LOW PEAK **200/300/500/700/
   1000 CPS**; DIP **200/300/500/700/1k/1.5k/2k/3k/4k/5k/7k CPS** (11 steps); HIGH PEAK **1.5/2/3/4/5 KCS**. Boost
   bells are ~1.5–2 octaves wide; the DIP ~1 octave; the HIGH PEAK gets **narrower** at higher settings (5 KCS is a
   focused presence bell, 1.5 KCS is broad). `CPS`=Hz, `KCS`=kHz.
4. **Boost + DIP at the same frequency does NOT cancel** — it focuses. Measured LOW PEAK 700 @10 + DIP 700 @10 →
   **+2.3 dB @700** with slightly scooped shoulders = a tighter, more resonant midrange peak (the MEQ-5's
   "Pultec-style" interaction).
5. **It's the MIDRANGE box — no real lows or air.** Nothing below ~200 Hz, nothing above 5 kHz. For sub/low-shelf
   weight + 10–16 kHz air use [[pultec-eqp-1a]]; for HP/LP filtering [[pultec-hlf-3c]]; for true surgical notches
   [[fabfilter-pro-q-4]].
6. **Colour = the curves + a gentle level-dependent harmonic, driven by INPUT.** At unity the magnitude is
   near-flat (±0.04 dB, +0.15 @200, −0.5 @15k) — the modeled tube/transformer add a faint harmonic that **grows
   with input level** (THD 0.012 % @−18 → 0.096 % @0 dBFS). The **`output` trim is a CLEAN post-gain** that does
   NOT saturate → to drive it for colour, **raise the input** (`input_gain_db` in the harness), not the output.
7. **It's an EQ, not dynamics, and a per-track/bus insert.** Crest roughly holds (cuts densify a touch). Do
   loudness/limiting AFTER in [[master-track]]; **meters own it** (Gemini hears ~16 kbps mono) — verify with
   `[L] measure-spectrum`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- Confirm the build: `[L] list-vst-plugins {name_contains:"MEQ"}` → take the **`uaudio_pultec_meq-5.vst3`** path.
  Dump the live surface any time: `../stemmy-loops-mcp/.venv/bin/python presets/vst/dump_params.py uaudio_pultec_meq-5`.
  Re-measure the curves: `… scripts/mix/meq5_sweep.py`.
- **It loads ≠ it rendered** — re-measure detail after; a 0.00 spectrum delta = the `.component` twin loaded.

## The parameter surface (10 enums — authoritative)

| Param | Values | What it does (measured) |
|---|---|---|
| `lm_freq` | `200·300·500·700·1000 CPS` (str) | **LOW PEAK** boost centre (low-mid body) |
| `lm_peak` | 0.0–10.0 (float) | LOW PEAK boost amount (**≈ +1 dB/unit, +10.7 dB max**) |
| `mid_freq` | `200·300·500·700 CPS · 1·1.5·2·3·4·5·7 KCS` (str) | **DIP** cut centre (de-box/de-honk) |
| `mid_dip` | 0.0–10.0 (float) | DIP cut amount (**nonlinear, saturates ~−11 dB by ~7**) |
| `hm_freq` | `1.5·2·3·4·5 KCS` (str) | **HIGH PEAK** boost centre (presence/attack) |
| `hm_peak` | 0.0–10.0 (float) | HIGH PEAK boost amount (**≈ +0.9 dB/unit, +8.8 dB max**) |
| `enable` | `In·Out` (str) | EQ engage (`Out` ≠ a true null — use `master_bypass`) |
| `output` | `OFF·−12.0…+12.0 dB` (str) | **clean** output trim (UA addition; does NOT saturate) |
| `power` / `master_bypass` | bool | unit power / plugin bypass (`master_bypass=True` = true null) |

> ⚠ **The three AMOUNT knobs (`lm_peak`/`mid_dip`/`hm_peak`) ARE float-settable by `apply-vst-chain`'s float
> dict — but the FREQUENCY selectors (`lm_freq`/`mid_freq`/`hm_freq`), `output`, and `enable` are STRING enums it
> silently drops.** A float-dict build keeps the DEFAULT freqs (lm 200 / mid 700 / hm 1.5 k) so your LOW/HIGH PEAK
> land on the wrong bands. **Use the [[vst-preset]] harness** (`apply_vst_preset.py`, `setattr` handles every enum).

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + low/low-mid/mid/high-mid ratios) +
   `[L] measure-loudness` (crest). The "before". Decide the job: **de-honk/de-box** (DIP), **presence/attack**
   (HIGH PEAK), or **warmth/body** (LOW PEAK).
2. **Pick frequencies first, then amounts.** Choose `lm_freq`/`mid_freq`/`hm_freq` (vintage CPS/KCS labels), then
   dial amounts — here they're ~dB, so e.g. `mid_dip=4` ≈ −5 dB. Keep boosts modest (3–5) and stack sections;
   watch boost↔dip overlap (broad bells interact — re-measure).
3. **Build a preset** setting **all 10** params explicitly (string selectors + `output` + `enable` via the
   harness). Optionally `input_gain_db` > 0 to drive the gentle Pultec harmonic colour.
4. **Apply via [[vst-preset]]** — `apply_vst_preset.py <preset.json> <in> <out>` (the `vst` venv; it peak-normalizes).
   Ready-made: `presets/vst/pultec-meq5-drum-presence.json` · `pultec-meq5-mid-scoop.json` ·
   `pultec-meq5-warm-body.json`. Output → `projects/<track>/mix/`.
5. **Prove it** — re-`measure-spectrum`/`measure-loudness`: the mid-band ratios/centroid moved as dialed, crest
   roughly held (it's EQ). A 0.00 delta = passthrough twin. A/B loudness-matched with `[L] render-ab`.

## Move table (measured)

| Goal | MEQ-5 move | Shipped preset |
|---|---|---|
| **De-honk / de-box** ★ (its signature) | DIP `500–1000 CPS` @4–6 (boxy/cardboard mids), small HIGH PEAK to restore | `pultec-meq5-mid-scoop` (DIP 700 @5 + HIGH PEAK 4k @3 + LOW PEAK 200 @2) |
| **Drum presence / attack** ★ | LOW PEAK `200 @3` body + DIP `500 @4` de-box + HIGH PEAK `3k @5` attack | `pultec-meq5-drum-presence` (centroid 2223→2261, high-mid 0.035→0.051) |
| **Warmth / body** | LOW PEAK `200–500 CPS` @4–6 (low-mid weight), gentle DIP `2k` to keep honk down | `pultec-meq5-warm-body` (low-mid 0.327→0.433, centroid 2223→2069, crest held) |
| **Snare/tom presence** | HIGH PEAK `3–5 KCS` @4–6 (5 KCS = focused, 1.5 KCS = broad) | — |
| **Nasal/harsh tame** | DIP `1.5–3 KCS` @3–5 | — |
| **Focused mid peak** | boost + DIP the **same** CPS (nets ~+2 dB, tighter shoulders) | — |
| **Tone-print colour only** | flat EQ + `input_gain_db` up (drive the amp; output trim won't) | — |

## Outputs

- `projects/<track>/mix/<stem>_meq5.wav` + the reusable `presets/vst/pultec-meq5-*.json` (and `.state` if dumped).
- Report: section(s) + freq (CPS/KCS) + amount per section + any output trim, before→after **mid-band ratios /
  centroid / crest** (crest should hold — it's EQ), that it ran headless (real Δ, not 0.00), and that
  mastering/limiting is deferred to [[master-track]]. A/B loudness-matched.

## Pitfalls

- **Wrong build = silent passthrough** — load `uaudio_pultec_meq-5.vst3`, not a `UAD …`/`Legacy .component` twin.
- **Float dict mis-places the bands** — the three AMOUNT knobs set via the float dict, but the FREQ selectors +
  `output` + `enable` are string enums it drops → defaults (lm 200/mid 700/hm 1.5k). Use the [[vst-preset]] harness.
- **The dial IS roughly dB here** (don't carry over EQP-1A/Hitsville "knobs aren't dB" — that's THIS plugin's
  distinction); but the DIP saturates (most cut by 6) and boost≠cut in shape — re-measure.
- **It's midrange-only** — no lows < 200 Hz, no air > 5 kHz; reach for [[pultec-eqp-1a]] / [[pultec-hlf-3c]] / [[excite]].
- **It's broad, not surgical** — narrow notches → [[fabfilter-pro-q-4]]; level-dependent problems → [[dynamic-eq]].
- **Drive the INPUT for colour, not the output** — `output` is a clean post-gain; the harmonic colour tracks input level.
- **It's an EQ, not a comp** — no glue/punch; master/limit later in [[master-track]]. Loudness-match every A/B.

## Related

- [`docs/vst/pultec-meq-5.md`](../../../docs/vst/pultec-meq-5.md) — the full measured field guide (Part A measured + Part B history/usage, cited)
- **Pultec Passive EQ Collection siblings:** [[pultec-eqp-1a]] (lows + 3–16k air + the low-end trick) · [[pultec-hlf-3c]] (passive HP/LP filters) — chain MEQ-5 for the mids between them
- [[vst-eq]] — the generic EQ skill this specializes · [[vst-preset]] — apply enum/all-explicit chains (use here) · [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- Vintage-EQ neighbours: [[helios-type-69]] (warm British preamp+EQ) · [[hitsville-eq]] / [[hitsville-eq-mastering]] (Motown graphic) · [[fabfilter-pro-q-4]] (clean surgical/dynamic — pair for notches)
- [[master-track]] — loudness/limiting AFTER · [[finalize-mix]] — bus-glue stage · [[mix-check]] (find the problem first) · [[drum-punch]] (attack via transients, not EQ)
- [[vst-verify]] (why the build matters) · [[gemini-audio-understanding]] (trust meters over mono ears)
