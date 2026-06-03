# Softube Transient Shaper — field guide: tighten / punch drums, 2-band, headless

How to drive the **Softube Transient Shaper** (`/Library/Audio/Plug-Ins/VST3/Transient Shaper.vst3`) — a
**2-band stereo transient control unit** (Softube, Sweden, 2015). It reshapes a hit's **attack (PUNCH)** and
**decay (SUSTAIN)** *independently of level* (no threshold), and can apply each move to the **whole band, only
the lows, or only the highs** around one crossover. It's the plugin-specific, measured deep-dive behind the
[[softube-transient-shaper]] skill — the **transient-design** counterpart to the native [[drum-punch]]
(`shape-bands`) tool and the console/tape tone of [[api-vision-channel-strip]] / [[studer-a800]].

**Part A** is *measured on this rig* (real Pedalboard param surface + our render results); **Part B** is a
*web-research synthesis, cited* (the manual + reviews). 

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo + the crest/PLR that prove
> "tighter." Verify every move with `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics`. A
> transient move that "sounds tighter" but doesn't raise crest/PLR is a level illusion.

---

## TL;DR (the headline, measured)

1. **"Tighten" = reduce SUSTAIN, not add PUNCH.** Sustain < 0 cuts the tail/ring (tighter); PUNCH adds *attack*
   and, pushed, an **unnatural click** — on our drum bus `punch +3` made the snare clicky/spitty (Gemini
   `detect-mix-issues` flagged it; same over-shape trap as [[drum-bus-dry-punchy-variant]]). For a clean
   tighten keep **punch 0**.
2. **WIDE sustain cut chokes the cymbals/hats.** A full-band negative sustain gates the high-frequency decay
   (unnatural). Fix: **`sustain_band=LOW`** (with the crossover ~700 Hz) → tighten the kick/snare *body/boom*
   while cymbals/hats keep their natural decay. This is the manual's own logic (Lo-band for toms, Hi-band for
   room/cymbals).
3. **It renders headless via Pedalboard** (`changed:true`, iLok authorized here). Softube/iLok is usually a
   render-farm landmine ([[vst-hosting-outside-daw]]) — **re-verify load+render on any other machine.**
4. **Level-independent (no threshold)** — it reacts to transient *shape*, not gain, so you don't gain-stage
   into it (unlike the API strip). The output `clip` soft-clips at 0 dB; keep input with headroom or it
   engages.

---

## Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin("…/Transient Shaper.vst3")` → `name="Transient
Shaper"`, `manufacturer="Softube"`, renders (`changed:true`). Neutral render (all 0, clip on) still nudges
peak/crest slightly (−1.94→−2.80 peak, 23.0→22.3 crest) — the output/clip stage isn't bit-unity, so
**always re-measure**, don't assume 0 = bypass.

**Param surface (Pedalboard snake_case):**

| Param | Type | Range / values | GUI control |
|---|---|---|---|
| `punch_db` | float dB | −20 … +20 (0=neutral) | PUNCH knob (attack) |
| `punch_band` | enum | `LOW` / `WIDE` / `HIGH` | band switch by PUNCH |
| `punch_type` | enum | `SLOW` / `FAST` | FAST/SLOW switch by PUNCH |
| `sustain_db` | float dB | −20 … +20 (0=neutral) | SUSTAIN knob (decay) |
| `sustain_band` | enum | `LOW` / `WIDE` / `HIGH` | band switch by SUSTAIN |
| `crossover_freq_hz` | float Hz | 100 … 4000 (default 700) | CROSSOVER knob (one, shared) |
| `output_level_db` | float dB | −48 … +12 | LEVEL knob (pre-clip) |
| `clip` | bool | True / False | CLIP / NO CLIP |
| `bypass` | bool | | — |

**Enum gotcha (important):** `[L] apply-vst-chain`'s `parameters` dict is **float-only** — it can set
`punch_db` / `sustain_db` / `crossover_freq_hz` / `output_level_db` but **NOT the enums** (`*_band`,
`punch_type`) or `clip`. For band/type/clip moves, set them in Pedalboard directly (`p.sustain_band="LOW"`)
or via the **`presets/vst/apply_vst_preset.py`** harness ([[vst-preset]]) — which `setattr`s every param.
Enum strings are **exact** (`"LOW"`, not "LO"); if unsure, set a bad value once and read the error's
`valid values` list.

**Measured tighten result (Watercolors no-room drum bus, 60 s, normalized −1 dBFS):**

| Setting | crest | note |
|---|---|---|
| no TS (un-shaped sum) | 21.7 | baseline |
| `sustain −5, punch 0`, **WIDE** | 22.3 | tighter, but Gemini flagged **choked hats/tails** (WIDE gates HF decay) |
| `sustain −8, punch +3`, WIDE | 23.1 | **over-shaped**: clicky snare (the +3 punch) + choked tails (the −8) |
| **`sustain −5, punch 0`, `band LOW`, xover 700** ★ | 22.1 | **clean tighten** — cymbals/hats keep decay (centroid 2447 vs WIDE's 2146); choke gone |

★ shipped as `projects/watercolors/mix/bus_tight.wav`. Gemini's residual "dark/boxy" on it was a **mono-downmix
artifact** — in stereo it's the *brightest* of the warm/punchy/tight variants ([[gemini-mastering-feedback-cross-check]]).

---

## Part B — how it works (web-research synthesis, cited + verified)

**What it is.** A "2-band stereo transient control unit" (Softube, Sweden, Feb 2015). Original Softube design
— an expansion of the **Console 1** transient algorithm with dual-band operation; **not** modeled on specific
hardware. Native VST/VST3/AU/AAX + a Console 1 module.

**The principle (verified `confirmed`/`mixed`).** **Level-independent**: "doesn't need a threshold control and
will react the same even if you change the gain" — it tracks transient *shape*, not absolute level. This is the
same threshold-independent behavior as the **SPL Transient Designer**, BUT "Differential Envelope Technology"
is **SPL's trademark** — the *behavior* is confirmed; do **not** attribute that named mechanism to Softube
(Softube only says "level independent"). Detectors differ: PUNCH analyzes the **stereo** signal, SUSTAIN the
**mono L+R** sum (review-sourced).

**Controls (all confirmed vs the manual):**
- **PUNCH** ±20 dB = the attack/onset. "Add Punch to … sound as if the drummer is hitting harder; lower it to
  make hits softer." Only does anything on **fast-transient** material.
- **SUSTAIN** ±20 dB = the decay. **Below 0 reduces sustain** (kill ring/boom/tom rumble); above 0 adds body.
- **HI / WIDE / LO band switch on EACH** (independent for Punch vs Sustain): **WIDE** = full range, **LO** =
  only below the crossover, **HI** = only above it.
- **PUNCH FAST / SLOW** (`confirmed`): does two coupled things — (1) detection speed (**FAST** = faster, catches
  sharp transients; **SLOW** = needed for slow-build transients FAST would miss), and (2) shaping window
  (**FAST** shapes a *shorter* slice = snappier; **SLOW** shapes a *longer* slice = fatter). Manual: *FAST for
  kick HF click, SLOW for snare "fatness."*
- **CROSSOVER** 100 Hz–4 kHz (default 700) — **one shared** split for both band switches (you can't set a
  different crossover for Punch vs Sustain — the design's main limitation).
- **LEVEL** −48…+12 dB, sits **before** the soft-clipper (drives it). **CLIP** = soft-clip at 0 dB ("adds
  power to each transient without too-loud output"). Meters: **GAIN CHANGE** Hi/Lo (±20), **OUTPUT** L/R, Clip LED.

**Manual drum recipes (verbatim — the gold):**

| Goal | Punch | P-band | P-type | Sustain | S-band | Crossover | Clip |
|---|---|---|---|---|---|---|---|
| Kick **click** | + | HIGH | FAST | — | — | 700 Hz | ON |
| Snare **fatness/crack** | + | WIDE | SLOW | (−, to kill ring) | (LOW) | — | ON |
| **Tighten** boomy kick/toms | — | — | — | − | LOW | ~700 | — |
| Overheads **room/shimmer** | — | — | — | + | HIGH | 1–2 kHz | — |
| Drum-**bus** glue (tiny) | 1–4 dB | HIGH | SLOW/FAST | — | — | 2–4 kHz | opt |

**Pitfalls (third-party, but we reproduced them):** over-boosting attack on an already-sharp hit → unnatural
**click/pop**; heavy negative sustain → **gate-like choked tail**; raising sustain raises **bleed/noise**; big
attack boosts across multi-mic kits can expose **phase** issues; over-processing a bus can **pump**. Softube's
own docs don't warn about these.

**vs alternatives:** SPL Transient Designer = full-band only (no crossover), smoother sustain. True multiband
shapers (Trinity, Transify, Neutron) = 3–4 *independent* per-band attack/sustain. Softube sits between: 2-band,
but one Punch + one Sustain value routed per band via one shared crossover. For pure low-end tightening of a
drum bus, our native [[drum-punch]] / `multiband-compress` are deterministic alternatives that need no plugin.

---

## Sources
- Softube official manual — https://www.softube.com/user-manuals/transient-shaper
- Softube product page — https://www.softube.com/us/plug-ins/transient-shaper
- MusicRadar review — https://www.musicradar.com/reviews/tech/softube-transient-shaper-622779
- SonicScoop transient roundup — https://sonicscoop.com/ultimate-transient-shaping-plugin-roundup/
- SPL Transient Designer (DET trademark) — https://spl.audio/en/spl-produkt/transient-designer-4-mk2/ · https://www.soundonsound.com/reviews/spl-transient-designer
- MasteringBox techniques — https://www.masteringbox.com/learn/transient-shaper-techniques
