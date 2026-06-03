# FabFilter Saturn 2 — field guide: multiband distortion / saturation, headless

How to drive **FabFilter Saturn 2** (`/Library/Audio/Plug-Ins/VST3/FabFilter Saturn 2.vst3`) — a **multiband
distortion & saturation** plug-in: up to **6 bands**, each with its own **distortion style** (28 of them — tube /
tape / amp / transformer / saturation + destructive FX), **Drive**, bipolar **Dynamics**, resonant **Feedback**,
a 4-control **Tone** EQ, **Mix** and **Level**, plus a deep modulation system. It's the **saturation/color**
member of the [[vst-saturate]] suite and the FabFilter sibling of [[fabfilter-pro-q-4]] (EQ) / [[fabfilter-pro-mb]]
(multiband dynamics). **Part A** is *measured on this rig* (the real Pedalboard param surface + our own render
results); **Part B** is a *web-research synthesis, adversarially verified, cited* (FabFilter's own docs + reviews).
The skill [[fabfilter-saturn-2]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the THD/centroid/crest
> that prove a saturation move. Verify every move with `[L] measure-distortion` / `measure-spectrum` /
> `measure-loudness` (+ `measure-stereo` for M/S). Saturation that "sounds" changed but shows a 0.00 delta is a
> passthrough. **And louder ≠ better** — Saturn's drive auto-compensation is *not* a LUFS match; A/B level-matched
> ([[level-match]] / `render-ab`).

---

## TL;DR (the headline, measured)

1. **It renders headless AND it's no-iLok** — uniquely safe here, like its Pro-Q 4 sibling. Saturn 2 loads +
   processes through Pedalboard 0.9.23 (probe Δparam = 8.6e-01). FabFilter uses a **simple license key, no
   iLok/PACE/dongle** (up to 3 machines, offline-activatable), so unlike the [[vst-hosting-outside-daw]] landmines
   it's a clean render-farm candidate. Use the **VST3** path (the AU `.component` twin is also installed).
2. **A bare load is NOT neutral — it restores FabFilter's last-saved GUI state.** `load_plugin(...)` came up
   exactly as the screenshot: **1 active band, style `Warm Tape`, drive 20, output −1 dB, HQ Off, Minimum Phase,
   L/R**. So any "fresh" render rides a leftover preset. **Set every param explicitly**, or restore a `dump_state`
   blob. The only **bit-exact passthrough** is `mix=0` or `bypass="Bypassed"` (both measured 0.0e0) — **`drive=0`
   is NOT clean** (Warm Tube @ drive 0 measured **+1.7 dB / 2.2 % THD**).
3. **The 28 distortion styles have distinct, measurable harmonic signatures** (1 kHz probe, drive 50): **Tube** =
   even **and** odd (Warm Tube even-leaning, H2 −22 dB); **Tape** = **odd-only — zero 2nd harmonic** (H2 ≈ −135 dB,
   H3 −24); **Saturation** = odd, very clean→dense; **Amp** = heavy odd (50–130 % THD); **Transformer** = mixed;
   **Foldback** = wavefolder (5th harmonic *louder* than the fundamental); **Rectify** = full-wave rectification
   (fundamental **removed** → octave-up 2k/4k/6k even harmonics); **Destroy** = bit-crush/decimation mush. Our
   measurements **agree with** the corrected web research (tube isn't purely "even", tape is odd-leaning).
4. **`apply-vst-chain`'s float dict can't really drive Saturn.** All 956 params are Pedalboard `valid_values`
   lists; the **string enums** — `band_N_style`, `band_N_crossover_slope`, `band_N_state`, `channel_mode`,
   `processing_mode`, `high_quality_mode` — can't be set through a float-only dict (the most important one,
   `band_N_style`, is a string). The float dict *can* nudge `band_N_drive`/`mix`/`dynamics`/tone/`crossover_frequency`
   on an already-configured instance, but for any real move **use the [[vst-preset]] harness** (`apply_vst_preset.py`,
   `setattr` — reaches strings + bools).

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin("…/FabFilter Saturn 2.vst3")` → `name="Saturn 2"`,
`is_instrument=False`, renders (a configured drive move changes the audio; `mix=0` == input). Tested with
**Pedalboard 0.9.23**, input `artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav` (the loop in
the screenshot).

`list-vst-plugins {name_contains:"Saturn"}` returns two — **use the VST3**:

| Name | Path | Use |
|---|---|---|
| **FabFilter Saturn 2** | `/Library/Audio/Plug-Ins/VST3/FabFilter Saturn 2.vst3` | ✅ this one |
| FabFilter Saturn 2 | `…/Components/FabFilter Saturn 2.component` | AU twin (macOS-only) |

### The real parameter surface (Pedalboard-exposed — authoritative)

**956 automatable parameters.** Every parameter — even drive/gain/frequency — is exposed as a `valid_values` list
(a quantized grid), not a free float. Numeric params accept a `setattr` float and **snap to the grid**; string/bool
params take the exact enum value. The map:

**Global (the ones that matter offline):**

| Param | Type | Values | Role |
|---|---|---|---|
| `input_gain` / `output_gain` | enum-num | −36 … +36 dB | I/O trim (**`output_gain` default −1.0** = restored state) |
| `mix` | enum-num | 0 … 100 % | **master dry/wet** (parallel); `mix=0` = bit-exact dry |
| `num_active_bands` | enum | 1 … 6 | how many saturation bands are live |
| `channel_mode` | enum | `Left/Right` · `Mid/Side` | per-band pan/level act on L/R or **M/S** |
| `processing_mode` | enum | `Minimum Phase` · `Linear Phase` | crossover (+HQ) phase mode |
| `high_quality_mode` | enum | `Off` · `Good` · `Superb` | oversampling (Good = 8×, Superb = 32× — Part B) |
| `unrestricted_feedback` | bool | False · True | let feedback self-oscillate past the safe limit |
| `bypass` / `host_bypass` | enum | `Not Bypassed` · `Bypassed` | bypass (bit-exact) |
| `audition_signal` | enum | `Output` · `Side Chain` · `Band 1…6` | solo-monitor a band/SC |

**Per band** (`band_1_…` through `band_6_…`, 17 params each = 102):

| Param | Type | Values | Control |
|---|---|---|---|
| `band_N_style` | enum (28) | Subtle/Clean/Warm/Broken **Tube** · Subtle/Clean/Warm/Old **Tape** · 9 **Amp** · Subtle/Gentle/Heavy **Saturation** · Subtle/Gentle/Warm **Transformer** · Smudge · Breakdown · Foldback · Rectify · Destroy | the distortion algorithm |
| `band_N_drive` | enum-num | 0 … 100 % | how hard the clipping stage is driven |
| `band_N_dynamics` | enum-num | −1 … +1 | bipolar: − = expand/gate (punchy), + = compress (dense) |
| `band_N_feedback_amount` | enum-num | 0 … 100 % | resonant feedback into the band input |
| `band_N_feedback_frequency` | enum-num | 10 … 1000 Hz | ringing pitch of the feedback |
| `band_N_bass` / `_mid` / `_treble` / `_presence` | enum-num | −24 … +24 dB | the post-distortion **Tone** EQ (4 fixed bands) |
| `band_N_mix` | enum-num | 0 … 100 % | per-band dry/wet (per-band parallel); `=0` mutes that band's effect |
| `band_N_level` | enum-num | −inf … +36 dB | per-band output trim |
| `band_N_pan` | enum | L/R balance string | per-band pan (Mid/Side in M/S mode) |
| `band_N_drive_pan` | enum-num | −1 … +1 | pan the *driven* signal (stereo distortion) |
| `band_N_crossover_frequency` | enum-num | 40 … 18000 Hz | the band's crossover |
| `band_N_crossover_slope` | enum | `6` · `12` · `24` · `36` · `48 dB/oct` | crossover slope (**36 dB/oct exists** — resolves a Part-B doubt) |
| `band_N_enabled` | bool | False · True | band on/off |
| `band_N_state` | enum | `Normal` · `Solo` · `Mute` · `Solo (Mute)` | per-band solo/mute |

**Modulation system** (largely a DAW feature — see the headless note): a **50-slot** drag-drop matrix
(`slot_1…50` × source/target/level/invert/bypass; 232 targets) fed by **6 XLFOs** (step-sequencer LFOs, 16 steps
each — `xlfo_*`, 432 params), **6 EGs** (ADSR+delay/hold/range/threshold/trigger), **4 envelope followers**
(`ef_*`, Envelope/Transient mode), **6 XY controllers**, **10 MIDI sources**. The Pedalboard surface exposes
fixed caps (6/6/4/6/10/50) — handy to know vs the marketing "as many as you need."

### Footguns (proven)

1. **A bare load restores the last-saved GUI state, not a neutral default.** Ours came up as the screenshot's
   `Warm Tape` preset (1 band, drive 20, output −1, HQ Off). On the drum loop that restored state already changed
   the tone (max|bare − dry| = 0.29). **You are never starting clean** — set every param, or restore a `dump_state`.
2. **`drive=0` is NOT a bypass.** Even at drive 0 the style colors (Warm Tube @ drive 0 = **+1.7 dB / 2.2 % THD**
   on a 1 kHz sine). The deterministic clean slate is **`mix=0`** or **`bypass="Bypassed"`** (both measured
   max|out − dry| = **0.0e0**). To make one band inert in a multiband preset, use `band_N_mix=0`, not drive 0.
3. **The float dict can't pick a style.** `band_N_style` (and `_crossover_slope`, `_state`, `channel_mode`,
   `processing_mode`, `high_quality_mode`) are **string enums** — `apply-vst-chain`'s float-only `parameters`
   can't set them, and the style *is the sound*. Use the **[[vst-preset]] harness** (`setattr`) for any real move.
4. **Set `dynamics`/`mix`/`output_gain` explicitly** — an unset value silently inherits the restored GUI state
   (same class of bug as Pro-Q 4's inherited `dynamic_range`).

### Drive sweep — Warm Tube, 1 kHz @ −12 dBFS, HQ Superb

| drive | fundamental | H2 (even) | H3 (odd) | H5 | THD |
|---|---|---|---|---|---|
| 0 | −10.3 dBFS | −33 | −49 | −105 | **2.2 %** |
| 20 | −10.3 | −28 | −49 | −95 | 4.0 % |
| 40 | −10.3 | −23 | −47 | −66 | 7.1 % |
| 70 | −10.2 | −27 | **−20** | −44 | 11.5 % |
| 100 | −9.7 | −27 | **−12** | **−20** | **27 %** |

Reads: drive raises THD monotonically; the **fundamental holds ≈ −10.3 dBFS** (drive is roughly output-compensated,
*not* just a volume knob) until it limits at the very top; and the harmonic profile **shifts from even (H2) at low
drive to odd (H3/H5) at high drive** — the classic "warm → gritty" arc. On real material drive also **crushes crest**
(below).

### Style harmonic signatures — drive 50, HQ Superb, 1 kHz probe (the headline table)

| Style | H2 | H3 | H5 | THD | Read |
|---|---|---|---|---|---|
| Subtle Tube | −59 | −51 | −68 | 0.3 % | barely-there |
| Clean Tube | −34 | −31 | −45 | 3.5 % | even ≈ odd, gentle |
| **Warm Tube** | **−22** | −33 | −44 | 8.1 % | **even-dominant = warmth** |
| Broken Tube | −22 | −11 | −16 | 33 % | odd takes over, gritty |
| Clean/Warm Tape | **−136…−145** | −24 | −58…−66 | ~6 % | **odd-ONLY — no 2nd harmonic** |
| Old Tape | −133 | −13 | −27 | 22 % | driven odd, no even |
| American Plexi Amp | −22 | **−5** | −22 | **58 %** | heavy odd amp grit |
| British Rock Amp | −43 | **−6** | −19 | 51 % | odd, scooped 2nd |
| Lead Amp | −23 | **0** | −3 | **132 %** | extreme odd distortion |
| Subtle Saturation | −170 | −57 | −74 | **0.1 %** | cleanest generator |
| Heavy Saturation | −139 | −11 | −17 | 33 % | symmetric odd, dense |
| Warm Transformer | −31 | −20 | −40 | 10 % | mixed even+odd |
| Foldback | (none) | −16 | **+7** | wavefolder | **5th harmonic LOUDER than fundamental** |
| Rectify | — | — | — | — | **fundamental removed → 2k/4k/6k octave-up** (full-wave rectification; crest 21.8) |
| Destroy | −124 | −30 | −51 | 3.3 %* | crush/decimation; *flattens drums to crest ~4, inharmonic mush |

> **Why this matters:** pick the style by the harmonic you want. **Even/warm** → Tube (esp. Warm Tube),
> Transformer. **Odd/edge without 2nd-harmonic mud** → Tape, Saturation, Amps. **Transparent density** → Subtle
> Saturation. **Special FX** → Foldback (metallic wavefold), Rectify (octave-up fuzz), Destroy (lo-fi). This is
> the *measured* version of Part B's (corrected) web claims — and it overrides the naive "tube=even, tape=warm/even"
> lore: **tape here is odd-only.**

### Drum-loop renders (crest / RMS / centroid) — drive crushes transients; parallel & dynamics protect them

| config | crest | RMS dBFS | centroid |
|---|---|---|---|
| dry | 14.63 | −17.72 | 3007 |
| Warm Tape drive 20 | 12.38 | −15.38 | 2871 |
| Warm Tape drive 50 | 8.18 | −16.53 | 2956 |
| Warm Tape drive 80 (full wet) | 5.59 | −18.05 | 3412 |
| **Warm Tape drive 80, `mix`=30 (parallel)** | **12.73** | −18.15 | 3027 |
| Destroy drive 50 | 8.17 | −19.87 | 3896 |

- **Drive crushes crest** (14.6 → 5.6 at drive 80); **the global `mix` is a real parallel path** — pulling it to
  30 % restored crest to 12.7 while keeping the grit. Parallel = how you saturate hard without killing punch.
- **Dynamics knob protects transients when negative:** Warm Tube drive 60 → crest **10.8** (dyn −0.8) / 9.75 (0) /
  **8.0** (+0.8). Negative = open/punchy (backs off on hits), positive = dense/compressed.
- **Tone EQ is a powerful fixed 4-band:** `treble`+12 → centroid 2871 → **4940**; `presence`+12 → 4788;
  `bass`+12 → centroid **1935** *and* +7 dB level (broad low shelf). Use small moves.
- **Multiband is real:** split @700 Hz, drive only the **low** band → crest **13.1** (transients preserved);
  drive only the **high** band → crest **8.6** (the band carrying the transients gets crushed). Saturate lows for
  weight, highs for bite. (Band-energy reads are confounded because saturating a band generates harmonics *above*
  it — judge multiband by crest/centroid, not raw band RMS.)
- **Feedback** adds sustained resonant density tuned by `feedback_frequency`: amount 0→80 raised RMS by **+7.8 dB**
  and collapsed crest 13.3 → 6.7 — a special-effect (ring/howl/sustain), not a glue tool. Use sparingly.
- **HQ changes the render** (it is *not* inert offline): max|Off − Superb| = **0.18** on a hot high-freq signal,
  no added buffer latency. Use Good/Superb when driving hard or high frequencies (aliasing); Superb is heavy CPU.
- **Minimum vs Linear phase** differ (max|Δ| = 1.12; different crossover phase) — Linear for parallel/mastering
  crossover coherence, Minimum (default) otherwise.

### Validated shipped presets (rendered on the Watercolors drum loop)

| Preset | Move | crest | centroid | vs dry |
|---|---|---|---|---|
| `presets/vst/saturn2-drum-bus-warm.json` | 1× Warm Tube drive 24, dyn −0.3, tone warm | 13.77 | 2526 | warmer/darker, +3 dB denser, **punch kept** |
| `presets/vst/saturn2-parallel-smash.json` | 1× British Rock Amp drive 45, `mix`=30 (parallel) | 14.88 | 2989 | grit + density, **transients intact** |
| `presets/vst/saturn2-bass-multiband.json` | 2 bands @110 Hz: sub dry (`mix`=0), highs Warm Tube drive 45 + presence | 12.13 | 3479 | upper harmonics added, **sub clean** |

dry = crest 14.63 / centroid 3007. All three render via `apply_vst_preset.py` (no-iLok, headless).

### How to actually drive it headless

Use **[[vst-preset]]**'s `apply_vst_preset.py` (it `setattr`s every param, strings included). The preset must set
**every** param explicitly (bare load = restored GUI state): `num_active_bands`, and per used band `band_N_enabled`,
`band_N_style`, `band_N_drive`, `band_N_mix`, `band_N_dynamics`, the tone bands, `band_N_level`
(+`band_N_crossover_frequency`/`_slope` for multiband), plus global `mix`, `output_gain`, `channel_mode`,
`processing_mode`, `high_quality_mode`. Make unused bands inert with `band_N_mix=0`. Set `dump_state=true` (via
`apply-vst-chain`) once dialed, then re-render from the opaque `.state` blob for byte-stability.

---

# Part B — how Saturn 2 works (web-research synthesis, adversarially verified, cited)

Released **May 19, 2020** (Saturn 1 was 2012). **Not** a recent plugin like Pro-Q 4 (Dec 2024). Current price
**USD $149** (EUR 129); **no-iLok** (simple license key, up to 3 machines, offline-friendly). Formats today:
VST/VST3, AU, AAX Native, AudioSuite, **CLAP** (CLAP added *post-launch* ≈ late 2022 — not a 2020 launch format).
macOS 10.13+ Apple-Silicon-native. ([product page](https://www.fabfilter.com/products/saturn-2-multiband-distortion-saturation-plug-in),
[press](https://www.fabfilter.com/press/1589878800/fabfilter-releases-fabfilter-saturn-2-distortion-and-saturation-plug-in),
[FAQ/licensing](https://www.fabfilter.com/support/faq))

## 1. What it is + signal flow

A **multiband distortion/saturation** plug-in: run full-band or split into **up to 6 bands**, each processed
independently. **Per-band signal flow:** crossover split (slopes 6/12/24/**36**/48 dB/oct) → **Drive → distortion
style** (with **Feedback** self-feeding the band for resonant ring, tuned by **Feedback Freq**) → **Tone** (fixed
post-distortion EQ) → **Dynamics** (compress right / gate-expand left) → **Level + Pan** → per-band **Mix**.
Bands recombine → global input/output gain, global **Mix**, **channel mode** (L/R or M/S), **Linear-phase** toggle,
**HQ** oversampling. The interactive display is where bands are created (drag crossovers, double-click to type a
frequency); per-band **solo/mute** on hover. ([overview](https://www.fabfilter.com/help/saturn/using/overview),
[band controls](https://www.fabfilter.com/help/saturn/using/bandcontrols),
[display](https://www.fabfilter.com/help/saturn/using/display))

## 2. New in Saturn 2 vs Saturn 1 (verified split)

- **Distortion styles 16 → 28** (FabFilter: "almost doubles… from 16 to 28"). The **12 new** styles are exactly:
  **3 Subtle** (Tube, Tape, Saturation) + **4 Amp** (American Tweed, American Plexi, British Rock, British Pop) +
  **3 Transformer** (Subtle, Gentle, Warm) + **2 FX** (**Foldback, Breakdown**). ([press](https://www.fabfilter.com/press/1589878800/fabfilter-releases-fabfilter-saturn-2-distortion-and-saturation-plug-in),
  [SOS](https://www.soundonsound.com/reviews/fabfilter-saturn-2))
- ⚠️ **Correction (adversarial verify):** of the destructive styles, **only Foldback & Breakdown are new in v2**.
  **Smudge and Rectify are carried over from Saturn 1** (v1's announcement: "time-smear, stretch, crush, **rectify**
  and clip"). **Destroy** is in the v2 menu but is **not** among the 12 documented new styles; its exact v1 lineage
  is unconfirmed — don't claim it's "new in 2." ([Saturn 1 news](https://www.fabfilter.com/news/1331161200/fabfilter-releases-fabfilter-saturn-distortion-plug-in))
- Also new in v2: **Linear-phase** mode; a **2nd HQ tier "Superb" (32×)** (v1 had one 8× tier, now "Good");
  **selectable crossover slopes**; overhauled/visualized modulation (curved EG, EF **Transient** mode, XY **Slider**
  mode, legato MIDI, more targets); resizable/full-screen GPU GUI.
- **Carried over from Saturn 1 (do NOT call new):** up to 6 bands, per-band Dynamics, Mid/Side, the modulation
  engine (XLFO/EG/EF/XY/MIDI + drag-drop matrix), 16-step XLFOs, the 4-band Tone EQ, the interactive display, and
  the **Smudge/Rectify** styles. ([MusicRadar Saturn v1](https://www.musicradar.com/reviews/tech/fabfilter-saturn-544050))

## 3. Controls (detail / ranges)

- **Drive** — "one of the most important parameters… how much the clipping stage is driven," with **automatic
  output-level compensation** (matches our measured ~constant fundamental). No published dB range.
- **Tone (Bass/Mid/Treble/Presence)** — a **fixed** post-distortion EQ "to tweak the harmonics generated by the
  distortion." FabFilter staff: it's **a low shelf (Bass), a high bell (Mid), and two high shelves (Treble,
  Presence)** — frequencies **not published / not sweepable** (common *unofficial* estimates ≈ 50 Hz / 600 Hz /
  5 kHz / 10 kHz — treat as approximate). Range ±24 dB (measured). ([band controls](https://www.fabfilter.com/help/saturn/using/bandcontrols),
  [forum](https://prod.fabfilter.com/forum/topic/8128/saturn-2-how-does-the-tone-controls-work))
- **Dynamics (bipolar)** — knob **right = pumping compression**, **left = gating/expansion**, center off (measured:
  negative preserves transients). **Feedback Amount/Freq** — self-feeds processed audio for resonant ring (the
  "mic near an amp" analogy). **Level** per band to +36 dB; **Pan** acts on Mid/Side in M/S mode.
- **Global:** input/output gain **±36 dB**; master **Mix**; **HQ Off/Good(8×)/Superb(32×)** (Superb = big CPU);
  **Linear vs Minimum phase** — Linear makes **only crossovers + HQ** linear-phase ("more suitable for mastering"),
  *not* the Tone EQ or each style's internal modeling; **channel mode** L/R vs M/S. ([input/output](https://www.fabfilter.com/help/saturn/using/inputoutput))

## 4. The 28 styles by family (sourced character; harmonics = our Part-A measurement)

| Family | Emulates [sourced] | Character (measured Part A) | Use |
|---|---|---|---|
| **Tube** (Subtle/Clean/Warm/Broken) | valve overdrive | even **+** odd; Warm = even-leaning warmth; Broken = gritty | warmth, bus/vocal/bass body |
| **Tape** (Subtle/Clean/Warm/Old) | magnetic tape | **odd-only (no 2nd harmonic)** + soft compression | de-harsh, glue, vintage/lo-fi |
| **Amp** (Tweed/Plexi/British Rock/British Pop/Smooth/Crunchy/Lead/Screaming/Power) | guitar amps | heavy **odd**, soft→hard by gain (50–130 % THD) | re-amp DI, aggressive drum/synth grit |
| **Saturation** (Subtle/Gentle/Heavy) | generic waveshaper | odd, transparent→dense; Subtle = cleanest of all | density/loudness with no "device" tone |
| **Transformer** (Subtle/Gentle/Warm) | iron/transformer | mixed even+odd, low-end weight | low-end weight, console glue |
| **Smudge** *(from v1)* | time-smear/stretch | spectral smear, no clean series | texture, transitions |
| **Breakdown** *(new v2)* | down-pitch + aggressive distortion | inharmonic grime | subby growl, drops, sound design |
| **Foldback** *(new v2)* | wavefolder ("aggressive, very digital clipping") | high-order odd (5th > fundamental) | metallic/digital edge |
| **Rectify** *(from v1)* | rectifier + DC-offset removal + soft clip | **even-rich / octave-up** (fundamental removed) | octave-fuzz, crunch, lo-fi |
| **Destroy** | bit-crush + sample-rate reduction + clip | quantization/aliasing mush, crest ~4 | 8-bit / glitch / extreme |

## 5. Modulation (which sources work offline / headless)

A **50-slot** drag-drop matrix; sources = **XLFO** (LFO or 16-step sequencer; free 0.02–500 Hz or synced 16 bars→1/64),
**EG** (ADSR+delay/hold; MIDI- or audio-threshold-triggered), **Envelope Follower** (Envelope/Transient mode),
**XY/Slider**, **MIDI**. Targets ≈ any param (drive, mix, crossover, tone, feedback, pan…). ([modulation](https://www.fabfilter.com/help/saturn/using/modulation))

| Source | Works in an offline/headless render? |
|---|---|
| **Envelope Follower** | ✅ audio-driven — the one source that reliably modulates a passed-through file |
| EG (audio-threshold) | ✅ (❌ if MIDI-triggered) |
| XLFO free-running | ⚠️ runs, but phase not anchored → not sample-deterministic |
| XLFO tempo-synced | ❌ needs host transport |
| XY / Slider / MIDI | ❌ need a human / DAW automation / MIDI |

**Headless bottom line:** treat Saturn 2 as a **static multiband saturator** for `apply-vst-chain`; if you want
movement that survives offline, use an **Envelope Follower → Drive** (e.g. grit that breathes with the input).
*(This offline-modulation behavior is empirically reasoned, not yet render-verified on this rig.)*

## 6. Recipes (Saturn-specific [S] vs generic-saturation [G]; tune by ear, level-matched)

| Goal | Move |
|---|---|
| **Drum-bus warmth/glue** | [G] Warm Tube/Tape **drive 15–25**, full band; [S] EF **Transient** mode → snare-band drive so it fires only on hits; [S] pull **Dynamics** negative to keep punch. (Shipped: `saturn2-drum-bus-warm.json`.) |
| **Parallel drum smash** | [S] drive hard, blend back with the global/per-band **Mix** (no aux) — Destroy/Rectify/Amp under the clean kit. (Shipped: `saturn2-parallel-smash.json`.) |
| **Bass that translates** | [S] multiband: low band `mix=0` (sub clean), saturate the **mids** (Warm Tube/Amp) + Tone presence so harmonics cut on phones. (Shipped: `saturn2-bass-multiband.json`.) Overlaps [[sub-design]] for the sub itself. |
| **Vocal warmth/presence** | [G] Warm Tube drive 15–25, optional mid-band focus; [S] EF → drive for dynamic dig-in. |
| **Mix-bus glue** | [G] barely-there tube/tape/sat; [S] for mastering enable **Linear phase + Superb (32×)** to minimize crossover smear + aliasing; [S] M/S: warm the Mid, brighten the Side. |
| **Lo-fi / destruction** | [S] Destroy (bitcrush+SR), Foldback (wavefold), Breakdown (down-pitch), Rectify (octave crunch), Smudge (smear); degrade only chosen bands. |
| **Air without raising hiss** | [S] top band (~5–7 kHz up), Clean Tube/Warm Tape **very low drive** + Tone treble/presence → harmonic sheen, not a shelf. Pure-DSP twin: [[excite]]. |
| **Tame harshness** | [G] lower drive / keep 15–25; [S] Warm/Clean Tape on a high band as a soft dynamic de-fizz. Pure-DSP twins: [[de-harsh]] / [[de-ess]]. |

> **Pure-DSP equivalents (no plugin, deterministic):** tube/tape/clip color → `[L] saturate-loop` ([[vst-saturate]]
> generic); band-limited air → `[L] excite-loop` ([[excite]]); multiband density → `[L] multiband-compress`
> ([[multiband-compress]]); sub weight → `drum-prep sub-design` ([[sub-design]]). Reach for Saturn when you want
> a *specific* style, true multiband distortion, the Tone EQ on the harmonics, or the Feedback/modulation FX.

## 7. Pitfalls & gotchas

- **It's a 2020 plugin, not a 2024 one** — don't conflate its feature set with Pro-Q 4. Saturn 1 = 2012, v2 = 2020.
- **Don't trust a bare headless load to be flat** (restores the last GUI state) and **don't drive it via the float
  dict** (can't set the *style* — a string enum) → set everything via the [[vst-preset]] harness or a `dump_state`.
- **`drive=0` ≠ clean** — use `mix=0` / `bypass` for a true dry reference; A/B level-matched (drive auto-comp ≠ LUFS match).
- **Hard styles alias** — raise **HQ** (Good/Superb) for amp/Destroy/Foldback or high-frequency drive.
- **Linear-phase only touches crossovers + HQ**, not the Tone EQ or style modeling — it's not a blanket "phase-perfect."
- **Modulation is mostly a DAW feature** offline — only the Envelope Follower (and audio-triggered EG) reliably render.
- **No-iLok, but loads ≠ renders** — screen with `[[vst-verify]]` / `probe_plugin.py "Saturn 2"` and **measure detail**
  (THD/centroid/crest), then pin the version + persist `dump_state`.

### LOW-CONFIDENCE / unresolved (from the web pass; some resolved by Part A)

- **Tone EQ center frequencies** — not published (≈50/600/5k/10k are user estimates). **Resolved by measurement:**
  bass = broad low shelf, treble/presence = high shelves (centroid moves confirm).
- **Numeric ranges** for Drive %, per-band Mix %, Dynamics, Feedback Hz are GUI-only in the docs — but the
  **Pedalboard `valid_values` grids in Part A are authoritative** (drive 0–100, dynamics −1…+1, feedback freq
  10–1000 Hz, tone ±24 dB).
- **HQ factors 8×/32×** are from FabFilter's pages; we confirmed the *render changes* with HQ but can't measure the
  exact oversampling factor.
- **"Destroy" v1/v2 lineage** unconfirmed (present in v2, not among the 12 documented new styles).
- **Recipe numbers** (drive %/Hz) are tutorial/blog ballpark, not vendor spec.

---

## Sources

FabFilter Saturn 2 product page, press release (May 19 2020) & manual/help (overview, band controls, display,
input/output, modulation, XLFO/EG/EF) · FabFilter FAQ/EULA (no-iLok licensing) · Sound on Sound, MusicRadar
(Saturn v1), PluginBoutique/Andrulian, Sage Audio, Nail The Mix, Magnetic, Loopcloud (technique + Saturn-1-vs-2 +
harmonic analysis). Plus **our own param-surface dump + render/measure results (Part A)** on
`/Library/Audio/Plug-Ins/VST3/FabFilter Saturn 2.vst3` via Pedalboard 0.9.23. Full verified research brief +
per-claim URLs were produced by the `saturn2-research` adversarial-verification workflow.
