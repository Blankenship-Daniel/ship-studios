---
name: pultec-eqp-1a
description: "Use when running the UAD/UADx Pultec EQP-1A program EQ for broad, musical vintage tone on a drum bus, kick, bass, mix bus, vocal, or master — 'Pultec EQP-1A', 'the Pultec low-end trick', 'boost and cut the same low frequency', 'big but tight low end', 'air without fizz', 'that passive tube EQ'. The deep-dive of [[vst-eq]] / [[vst-master]]; broad/musical, pair with [[fabfilter-pro-q-4]] for notches. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: lowend-trick|air|de-harsh|smile|presence|colour]
---

# pultec-eqp-1a — drive the UADx Pultec EQP-1A program EQ (measured)

The plugin-specific, measured workflow for the **UADx Pultec EQP-1A EQ**
(`/Library/Audio/Plug-Ins/VST3/uaudio_pultec_eqp-1a.vst3`) — UA's model of the legendary **Pultec EQP-1A "Program
Equalizer"**: a **passive LC (inductor) equalizer + push-pull vacuum-tube makeup amp + transformers**. The iconic
**broad, gentle, musical vintage EQ** of [[vst-eq]] / [[vst-master]] — next to the passive British [[helios-type-69]],
the Motown [[hitsville-eq-mastering]] / [[hitsville-eq]], and the clean surgical [[fabfilter-pro-q-4]]. Its two famous
moves: the **low-end trick** (boost + atten the *same* low freq → big-but-tight bottom) and **air-without-fizz**
(boost one HF, atten a different HF). Full field guide — real param surface, footguns, recipes, our numbers, sources:
[`docs/vst/pultec-eqp-1a.md`](../../../docs/vst/pultec-eqp-1a.md). This skill is the workflow.

## The governing facts (read first — all measured on this rig, Pedalboard)

1. **Renders headless — use the `uaudio_` build.** `uaudio_pultec_eqp-1a.vst3` loads + processes (UADx native). The
   `UAD Pultec EQP-1A.component` / `… Legacy.component` twins are the **passthrough** offline build — never load those
   ([[vst-verify]]). UADx native is **iLok/PACE** lineage but **renders offline** once locally
   authorized (machine or iLok-USB, not iLok-Cloud).
2. **The Boost/Atten/Bandwidth knobs are 0–10 DIAL POSITIONS, not dB**, and **nonlinear** — most action is knob 4→8;
   8→10 barely moves. Measured low boost @60 CPS: knob 4 ≈ +4 dB, knob 6 ≈ +11, knob 8 ≈ +15. **Dial to the meter,
   not to a number.**
3. **The LOW-END TRICK is real and measurable.** `lf_boost` + `lf_atten` at the *same* `low_freq` do **not** cancel —
   the boost shelf peaks *below* the CPS, the atten dips a region *above* it. Measured @60 CPS B7/A5 → **+12 dB @60
   with a −2.4 dB scoop @1k**: big tight low end, boxy low-mids pulled. Higher CPS = broader bump reaching higher;
   lower CPS = tighter/lower.
4. **AIR-WITHOUT-FIZZ works** because the HF boost freq (`high_freq`) and HF cut freq (`hf_atten_freq`) are
   **independent**: 16 KCS boost + 10 KCS atten → **+2.7 dB @16k** air while pulling 3–8k down.
5. **The colour is the CURVES, not saturation.** THD ≈ **0.002 % @ −18 dBFS, ~0.01 % @ −6 dBFS** (faintly
   odd-harmonic). It's a near-hi-fi passive EQ — broad musical shelf/bell shapes + a gentle insertion colour, *not*
   drive. For obvious analogue weight stack tape ([[ampex-atr-102]]) or vari-mu ([[fairchild-660]]) after it.
6. **"Sounds good flat" = +1.1 dB insertion + top-softening, and `enable=Out` is NOT a null.** Engaged-flat reads
   **+1.1 dB** broadband (matches UA's documented ~1.13 dB) with a gentle top roll; `enable=Out` is a hair *brighter*
   (the tube/transformer path stays in); only `master_bypass=true` truly nulls. → **always loudness-match the A/B.**
7. **5 of 12 params are STRING enums → use the [[vst-preset]] harness, not `apply-vst-chain`'s float dict.**
   `low_freq`, `high_freq`, `hf_atten_freq`, `enable`, `output` (the frequency selectors + engage + dB trim) are
   string enums the float dict silently misses — exactly the character controls. **Meters own it** (Gemini hears mono).

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]` perceptual tools
  (optional, `GEMINI_API_KEY`) for an A/B read.
- Confirm the build: `[L] list-vst-plugins {name_contains:"Pultec"}` → take the **`uaudio_pultec_eqp-1a.vst3`** path.
  Screen with `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "pultec_eqp"` (expect `RENDERS ✓`).
  Dump the live surface any time: `… presets/vst/dump_params.py uaudio_pultec_eqp-1a`. Re-measure curves with
  `… scripts/mix/pultec_sweep.py`.
- **It loads ≠ it rendered** — always re-measure detail after (a 0.00 spectrum delta = the `.component` passthrough
  twin loaded instead).

## The parameter surface (12 enums — authoritative)

| Param | Values | What it does (measured) |
|---|---|---|
| `low_freq` | `20·30·60·100 CPS` (str) | LF shelf corner for **both** low Boost & Atten |
| `lf_boost` | 0.0–10.0 | **low SHELF boost**, peaks *below* the CPS (knob 4≈+4, 6≈+11, 8≈+15 dB @60) |
| `lf_atten` | 0.0–10.0 | **low SHELF cut**, reaches *higher* than the boost |
| `high_freq` | `3·4·5·8·10·12·16 KCS` (str) | HF **peak/bell** boost centre (3 = upper-mid presence, 16 = air) |
| `hf_boost` | 0.0–10.0 | **HF peak boost** (knob 6≈+6, 8≈+9, 10≈+15 dB at centre) |
| `hf_q` | 0.0–10.0 | **BANDWIDTH** of the HF boost bell: **0 = SHARP (tall/narrow)**, **10 = BROAD (lower/wider)** |
| `hf_atten_freq` | `5·10·20 KCS` (str) | HF **shelf-cut** corner, **independent** of the boost freq (5 = hinge ~1k, 20 = top only) |
| `hf_atten` | 0.0–10.0 | **HF SHELF cut** (high shelf; the freq is the hinge) |
| `enable` | `In`·`Out` (str) | EQ engage — **`Out` ≠ null** (amp/transformer stays in, slightly brighter) |
| `output` | `OFF·-12.0…+12.0 dB` (str) | clean output trim (a UA addition; doesn't change THD) |
| `power`/`master_bypass` | bool | unit power / plugin bypass — **`master_bypass=true` is the only TRUE null** |

> **No tube on/off toggle exists** — the bottom-left GUI lever is engage/IN; the tube+transformer model is always on.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + low/low-mid ratios) + `[L] measure-loudness`
   (crest/PLR). The "before" column. Decide the job: **low weight+tight** (→ the trick), **air/de-fizz** (→ HF
   boost+atten), or **broad smile/glue** (→ gentle both).
2. **Build a preset** (`presets/vst/pultec-*.json`) setting **all 12** params explicitly (the string selectors via the
   harness). Pick the CPS / KCS first, then dial the boost/atten knobs *toward the meter*, not to a dB number.
3. **Apply** with the harness:
   `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
   projects/<track>/mix/<stem>_pultec.wav` (it peak-normalizes, absorbing the +1 dB insertion). Set `dump_state=true`
   via `apply-vst-chain` once dialed for a byte-stable re-render.
4. **Prove it** — re-`measure-spectrum`/`measure-loudness`. Expect the **EQ move you dialed** (low ratio up + low-mid
   scoop for the trick; +air at 12–16k & a 5–8k dip for air-without-fizz) and **crest roughly HELD** (it's EQ, not
   compression — if crest drops a lot, you drove something else). A 0.00 delta = passthrough twin loaded.
5. **A/B loudness-matched** ([[level-match]] / `[L] render-ab`) — the Pultec flatters itself with +1 dB makeup, so
   never judge tone unmatched.
6. **QC** — `[G] detect-mix-issues` / `mastering-feedback` (genre/intent set) for over-bright or muddy; cross-check
   any mono "dark/harsh" flag against the meters ([[gemini-audio-understanding]]). It's a per-track/bus EQ
   insert — hand the result to [[master-track]] for loudness/limiting (on a 2-bus, the Pultec sits *before* the limiter).

## Move table (measured)

| Goal | Pultec move |
|---|---|
| **Drum bus — warm + tight** ★ | low-end trick `60 CPS` B5/A4 (+ `5 KCS` atten 2 de-harsh, `16 KCS` boost 4 sheen) → low up, low-mid scoop 0.18→0.12, centroid 1593→1231, crest −1.2 dB (14.6→13.4 — the low-end boost slightly densifies; the one shipped preset that does NOT hold crest) (shipped `pultec-drum-lowend-glue`). |
| **Kick — weight + tight** | low-end trick `30–60 CPS`, boost ~4–5 / atten ~4–5 (thump + clean low-mid scoop). |
| **Bass — tight + de-mud** | low-end trick `30 CPS` (or 60), boost ≈ atten 4–6. |
| **Snare — body + snap** | low boost `100 CPS` body; HF boost `5–8 KCS` for crack. |
| **Air without fizz** ★ | `16 KCS` boost 6 (q8) + `10 KCS` atten 4 → +1.5 dB @16k air, 5–8k pulled, centroid/low untouched, crest held (shipped `pultec-air-without-fizz`). For OH/cymbals/bright bus/vocal tops. |
| **De-harsh only** | HF atten alone: `5 KCS` (broad darken/de-harsh) or `10 KCS`; leave the boost band off. |
| **Mix-bus / master smile** ★ | gentle `30 CPS` B3/A2 + `16 KCS` boost 4 (q10), no HF cut → low +, +0.9 @16k air, crest held (shipped `pultec-master-smile`). Keep moves ≤2 dB; *before* the limiter. |
| **Focused HF presence** | sharpen the bell: lower `hf_q` (0–2) + a lower `high_freq` (5–8 KCS). |
| **"Tone print" colour only** | EQ flat, run through — the faint insertion colour + ~+1 dB makeup (loudness-match to hear it). |

## Outputs

- `projects/<track>/mix/<stem>_pultec.wav` + the reusable `presets/vst/pultec-*.json` (and `.state` if dumped).

## Reporting to the user

State the path, the moves (CPS + boost/atten, KCS + boost/q, ATTEN-SEL + atten), the before→after **crest / centroid /
tilt / low & low-mid ratio / target-band deltas** (crest should hold — it's EQ), that it ran headless via the
`uaudio_` build, and the preset/`.state` path. A/B loudness-matched so the +1 dB insertion isn't read as "better."

## Pitfalls

- **Wrong build = silent passthrough** — load `uaudio_pultec_eqp-1a.vst3`, not the `UAD …`/`Legacy .component` twins.
- **Float dict can't drive it** — the frequency selectors + `enable`/`output` are string enums → [[vst-preset]] harness.
- **Knobs aren't dB** — 0–10 positions, nonlinear (action 4→8); read the spectrum, don't trust the number.
- **`enable=Out` isn't a bypass** — it keeps the amp path (brighter); only `master_bypass=true` nulls. The unit
  always prints ~+1 dB makeup + colour → **loudness-match every A/B** or "Pultec'd" is just "louder."
- **It barely saturates** — for real analogue weight/glue, stack tape/vari-mu after it; the Pultec is curves, not drive.
- **It's broad, not surgical** — for narrow notches use [[fabfilter-pro-q-4]]; for level-dependent problems [[dynamic-eq]].
- It's a per-track/bus EQ insert, **not** mastering — keep it off the 2-bus loudness stage (sits *before* the limiter).

## Related

- [`docs/vst/pultec-eqp-1a.md`](../../../docs/vst/pultec-eqp-1a.md) — the full measured field guide (Part A measured + Part B history/usage, cited)
- [[vst-eq]] / [[vst-master]] — the generic skills this specializes · [[vst-preset]] — apply enum/all-explicit chains ·
  [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- Vintage-EQ siblings: [[helios-type-69]] (passive British preamp+EQ, warm) · [[hitsville-eq-mastering]] / [[hitsville-eq]]
  (Motown passive graphic) · [[fabfilter-pro-q-4]] (clean surgical/dynamic — pair for notches) · [[pultec-hlf-3c]] (the
  collection's HP/LP filter sibling)
- Pure-DSP twins (no plugin): broad/tilt/shelf EQ + the trick (low-shelf boost + low-mid bell cut) → `[L] apply-eq`;
  air/presence → [[excite]]; tube/tape colour → `[L] saturate-loop` / [[studer-a800]] / [[ampex-atr-102]]; level-dependent → [[dynamic-eq]]
- [[mix-check]] (find the problems first) · [[warm-drum-bus]] / [[drum-stems-warm-loops]] (where the low-end trick fits) ·
  [[vst-verify]] (why the build matters) · [[gemini-audio-understanding]] (trust meters over mono ears)
