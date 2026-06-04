# iZotope Nectar 3 — field guide: the all-in-one vocal channel strip (measured headless)

How to drive **iZotope Nectar 3** (`/Library/Audio/Plug-Ins/VST3/Nectar 3.vst3`) in this pipeline — iZotope's
**vocal channel strip**, a stack of independent modules (gate, two compressors, de-esser, two EQs, saturation, delay,
reverb, harmony, dimension, limiter, unmask) in one 696-param plugin you engage à la carte. This doc is **measured on
this rig** — the real Pedalboard param surface plus the headline finding that **it renders & engages headless, but its
drive modules are OFF at default** and the AI Vocal Assistant is GUI-only. The task skill [[nectar-3]] is the workflow
over this doc.

---

## TL;DR (the headline — read this first)

1. **It RENDERS & engages headless** (NI/iLok-account-authorized on this Mac). It loads + processes through the offline
   Pedalboard host — unlike the [[tape-j-37]] / Ozone iLok landmines, Nectar's modules actually run. Use the **VST3**
   `Nectar 3.vst3` path. **Re-verify on a new machine** with [[vst-verify]] (the sine→THD / band-delta test) — loads ≠
   renders; a 0.00 spectrum/loudness delta = passthrough.
2. **The drive modules are OFF at default — you MUST drive them.** `saturation_amount` defaults to **0** (no color),
   `comp_1_threshold_db` and `comp_2_threshold_db` to **0** (no GR). A bare default instance is near-passthrough on
   those modules; engage the module (`*_bypass="False"`) and set the amount/threshold explicitly or you'll ship an
   unprocessed copy with a false `changed:true`.
3. **It's a VOCAL tool — use it on ISOLATED VOCALS** (or a bright mono lead). Our numbers are on a **vocal clip**. For
   drums / bus / master reach for the dedicated console (e.g. [[ssl-4k-e]] / [[api-vision-channel-strip]]), comp, and
   tape skills instead.
4. **Params are enums (numeric + string/bool).** `[L] apply-vst-chain`'s float dict sets the **numeric** ones
   (`saturation_amount`, `comp_N_threshold_db`/`_ratio`, `deesser_frequency_hz`/`_threshold_db`, EQ band gains/freqs)
   on an **already-engaged** module — but the **string/bool** enums (every `*_bypass`, `saturation_mode`,
   `comp_N_mode`, the EQ band `*_shape`) need the **[[vst-preset]] harness** (`apply_vst_preset.py`, `setattr`) or a
   dumped `.state`.
5. **The AI "Vocal Assistant" is GUI-only** and the **harmony** module is a pitch/harmony generator (GUI/MIDI-driven) —
   neither has headless utility; you drive the manual DSP modules yourself.
6. **Meters own tone** (Gemini hears ~16 kbps mono): judge any Nectar move with `[L] measure-spectrum`
   (tilt/centroid/bands), `measure-loudness` (crest/PLR), `measure-stereo`. A/B loudness-matched with `[L] render-ab`
   ([[level-match]]) so "warmer" isn't just "louder".

---

# Part A — measured on this rig

Probe: `Nectar 3.vst3` loaded via Pedalboard (stemmy-loops `vst` extra, 0.9.23), processing a **vocal clip**
(baseline crest **17.5 dB**, centroid **846 Hz**). Numbers below are that clip; state the source when you reuse them.

## The verdict: loads, engages, renders — when you DRIVE the modules

| test | measured | reading |
|---|---|---|
| bare default instance | near-passthrough on saturation + both comps | the drivers are at amount/threshold 0 |
| engage Saturation, `mode=Tape`, `amount=60` + Comp 1 `threshold_db=−18`, `ratio=3` | **real, big change** (below) | the DSP runs offline |
| → >6 kHz | **+9.9 dB** | saturation harmonics / air |
| → crest | **17.5 → 16.0 (−1.5 dB)** | Comp 1 leveling |
| → low / low-mid / mid | **−2.7 / −2.8 / −4.9 dB** | tonal re-weighting toward the top |
| → centroid | **846 → 1132 Hz** | brighter |

**Conclusion:** Nectar 3 is a **working headless processor** — but only on the modules you engage and drive. The
"default = passthrough on the drivers" trap is the Nectar-specific version of the repo's **"loads ≠ renders"** warning
(`docs/vst/README.md`): the plugin instantiates and accepts params, yet the saturation/comp do nothing until you raise
`saturation_amount` / lower `comp_N_threshold_db` off their 0 defaults. Always re-measure detail after.

## The module surface (Pedalboard-exposed — the headliners)

696 params total (24 bands × 2 EQs + 8 harmony voices dominate the count). Every module has a `*_bypass`
(`False` = engaged; **string/bool → harness only** to toggle) and a `*_wet_mix`. The audio-relevant drivers:

| Module | Key params | Values *(default)* | Notes |
|---|---|---|---|
| **Saturation** | `saturation_mode` | `Analog`·`Retro`·`Tape`·`Tube`·`Warm`·`Decimate`·`Distort` *(**Tape**)* | string → harness; the color recipe |
| | `saturation_amount` | `0…100` *(**0**)* | **OFF at default** — drive it |
| | `saturation_high_shelf_*` | freq 1k–20k *(7k)* · gain ±12 *(0)* | post-saturation tone trim |
| **Comp 1 / Comp 2** | `comp_N_threshold_db` | `−40…0` *(**0**)* | **OFF at default**; lower = more GR |
| | `comp_N_ratio` | `1…50` *(2.5)* | numeric |
| | `comp_N_attack_ms` / `_release_ms` | 0.1–300 / 1–1200 *(5 / 50)* | numeric |
| | `comp_N_mode` | `Digital`·`Vintage`·`Optical`·`Solid-State` *(Digital)* | string → harness |
| | `comp_N_auto_gain` | bool *(True)* | bool → harness |
| **De-esser** | `deesser_frequency_hz` | `800…8000` *(2500)* | the sibilant band |
| | `deesser_threshold_db` | `−20…0` *(**0** = no action)* | relative duck; `deesser_listen` to audition (GUI) |
| **EQ 1 / EQ 2** | `eq_N_bM_gain_db` / `_frequency_hz` / `_q` | ±15 / 20–20k / 0.1–40 | 24 bands each, numeric |
| | `eq_N_bM_shape` | `Bell`·`Proportional Q`·`Vintage Bell`·shelves·`Flat/Resonant Highpass/Lowpass`·`Baxandall` | string → harness |
| | `eq_N_bM_threshold_db` | −80…0 | per-band **dynamic-EQ** threshold |
| **Gate** | `gate_open_db` / `gate_close_db` / `gate_ratio` / `gate_attack_ms` / `gate_release_ms` | — | numeric; clean between phrases |
| **Limiter** | `limiter_bypass` *(True)* · `limiter_threshold_db` *(−0.1)* | — | OFF by default; output safety only |
| **Global** | `global_input_gain` / `global_output_gain` | ±60/±10 *(0)* | gain-staging |

> **Skip headless:** **Harmony** (`harmony_*`, 8 voices) is a pitch/harmony *generator* (GUI/MIDI-driven — needs note
> input to do anything useful); **Delay / Reverb / Dimension** are time/space FX better served by [[neoverb]] /
> [[vst-reverb]] / [[vst-delay]]; **Unmask** wants a companion track's sidechain (use [[unmask-stems]]). The AI
> **Vocal Assistant** (auto-Learn) is **GUI-only** — it won't run in the offline subprocess.

---

# Part B — how the plugin works (usage synthesis)

## 1. What it is

Nectar 3 (iZotope, 2018) is a **vocal-production suite**: one plugin holding a serial chain of vocal-tuned modules.
The signal flows in module order (Gate → EQ → Comp/De-ess/Saturation/etc. as routed), each independently bypassable.
It is the iZotope answer to a hardware vocal channel ([[manley-voxbox]]) — but software-flexible, with two compressors
(serial or parallel via `*_wet_mix`), two EQs (one before, one after dynamics, by convention), and seven saturation
flavors. Its headline feature in the DAW is the **Vocal Assistant** (it listens and auto-builds a chain), which is
exactly the part that **doesn't** run headless — so in this pipeline you drive the modules manually.

## 2. The modules that matter headless

- **Saturation** — seven modes; `Tape`/`Tube`/`Warm`/`Analog` add harmonics + a top lift (measured **+9.9 dB >6 kHz**
  at `amount=60`), `Decimate`/`Distort` are lo-fi/aggressive. Off at `amount=0` — this is the warmth/air knob.
- **Compressor 1 & 2** — full-featured (threshold/ratio/attack/release + four character modes). Off at
  `threshold_db=0`. Lower threshold = more GR = lower crest (measured **−1.5 dB** at `−18 / 3:1`). Run serially for
  leveling-then-grab, or in parallel (`comp_N_wet_mix < 100`) for NY-style.
- **De-esser** — single-band dynamic; set `deesser_frequency_hz` to the sibilant zone (6–8 k typical), raise
  `deesser_threshold_db` until only esses duck. Pure-DSP twin: [[de-ess]].
- **EQ 1 & 2** — 24 surgical/musical bands each, with shapes (bells, shelves, Baxandall, pass) and a per-band
  **dynamic** threshold. For a simple HPF + presence/air move the pure-DSP `[L] apply-eq` is often quicker.
- **Gate** — full gate for cleaning breaths/spill between phrases.

## 3. The levers

- **`saturation_mode` + `saturation_amount`** — the color. Tape (default) = the safe warm/air lane; Tube/Warm fuller;
  Analog subtle; Decimate/Distort overt. Auto-gain inside the module means **A/B loudness-matched** to judge honestly.
- **`comp_N_threshold_db` (relative to input) + `comp_N_mode`** — leveling. Optical = smooth vocal, Vintage = colored,
  Solid-State = punchy, Digital = clean.
- **`deesser_threshold_db`** — it's a *relative* duck, not "lower = more"; verify the 4–9 k band actually dropped.
- **EQ shapes** are string enums — pick `Bell` / a shelf / a pass per band in the harness, then set freq/gain/Q numeric.

## 4. Recipes (drive these via the harness, then measure)

| Goal | Modules | Settings |
|---|---|---|
| **Warmth + air + leveling** ★ | Saturation + Comp 1 | `saturation_mode=Tape`, `saturation_amount=60`; `comp_1_threshold_db=−18`, `comp_1_ratio=3` → measured >6 k **+9.9 dB**, crest **−1.5**, centroid **846→1132** |
| Warmth / saturation only | Saturation | `Tape`/`Tube`/`Warm`, `amount` 20–60 (60 ≈ a real move) |
| Smooth vocal leveling | Comp 1 | `Optical` mode, `threshold_db` −15…−20, `ratio` 2.5–4, medium attack/release |
| De-ess | De-esser | `deesser_frequency_hz` 6–8 k, raise `deesser_threshold_db` until only esses duck |
| Tone | EQ 1/EQ 2 | HPF (a `Highpass` band) + a presence bell + an air shelf; shapes via harness |
| Clean between phrases | Gate | set `gate_open_db`/`gate_close_db`/`gate_ratio` to the noise floor |

*Default to dial from:* **engage one module at a time, drive it off its 0 default, measure, repeat.**

## 5. Pipeline integration

1. `[L] measure-spectrum` + `measure-loudness` — the "before" column (it's a vocal: crest + centroid + tilt).
2. Build a `presets/vst/nectar3-*.json` engaging only the modules you want (set each `*_bypass` + the string modes +
   the numeric drives), apply via `presets/vst/apply_vst_preset.py` → `projects/<track>/mix/<stem>_nectar3.wav`. Set
   `dump_state=true` (via `apply-vst-chain`) once dialed for a byte-stable re-render.
3. **Measure** the result — saturation → centroid/>6k up; comp → crest down; de-ess → 4–9 k down. A 0.00 delta =
   passthrough (module not engaged or amount still 0).
4. **A/B honestly** with `[L] render-ab` (loudness-matched). For a perceptual read, `[G] detect-mix-issues` on the
   loudness-matched pair (cross-check any mono "harsh/dull" call against the meters).
5. Continue the normal pipeline — a vocal channel is a per-track insert; master with [[master-track]].

## 6. Pitfalls & gotchas

- **The drivers are OFF at default** — `saturation_amount=0`, comp thresholds `=0`; you'll ship a passthrough with a
  false `changed:true` if you don't drive them. (There IS a real `presets/vst/nectar3-*.json` for this plugin — unlike
  the passthrough [[tape-j-37]].)
- **It's a vocal tool** — don't reach for it on drums/bus/master; use the console/comp/tape skills there.
- **Float dict can't engage a module or set a mode** — `*_bypass`, `saturation_mode`, `comp_N_mode`, EQ `*_shape` are
  string/bool → the [[vst-preset]] harness (or a `.state`).
- **The harness upmixes mono→stereo and peak-normalizes** (`output_peak_dbfs`, def −1.0) — fine for a single vocal
  insert; for channel-preserving work use `[L] apply-vst-chain`.
- **De-ess threshold isn't "lower = more"** — it's a relative duck; verify the band moved.
- **Harmony = a pitch generator** (GUI/MIDI), the **Vocal Assistant is GUI-only** — don't expect either headless.
- **Re-verify on another machine** — headless render here depends on the NI/iLok-account auth; [[vst-verify]] before trusting it elsewhere.

## 7. When to use Nectar 3 vs the alternatives

| Want | Use |
|---|---|
| An all-in-one vocal channel (comp + EQ + de-ess + sat), headless | **Nectar 3** (this) |
| An all-tube vocal channel character | [[manley-voxbox]] |
| Just saturation/warmth | [[vst-saturate]] (`[L] saturate-loop`, [[fabfilter-saturn-2]], tape) |
| Just leveling | [[vst-compress]] (`[L] compress-loop`) |
| Just de-ess | [[de-ess]] / [[vst-de-ess]] |
| Just surgical/musical EQ | [[fabfilter-pro-q-4]] / `[L] apply-eq` |
| Reverb / space on the vocal | [[neoverb]] / [[vst-reverb]] |

---

## Sources

iZotope Nectar 3 product/help docs (izotope.com — module list, Vocal Assistant, saturation modes) · the iZotope
Neutron field guide [`docs/vst/izotope-neutron.md`](izotope-neutron.md) (shared enum-harness + headless-auth pattern) ·
the repo VST doctrine [`docs/vst/README.md`](README.md) (loads ≠ renders) · **our own Pedalboard load + render
measurements** on `Nectar 3.vst3` (Part A) — the default-off-drivers finding + the measured vocal-clip deltas.
