# SSL Native Bus Compressor 2 — field guide: VCA bus glue, drum-bus + parallel, headless

How to drive **SSL Native Bus Compressor 2** (`/Library/Audio/Plug-Ins/VST3/SSL Native Bus Compressor 2.vst3`)
— Solid State Logic's software of the **4000 G-series console quad bus compressor**, the canonical **VCA "mix
glue"** comp. It's the *cohesion/density* counterpart to the console-tone strips
([[api-vision-channel-strip]] / [[kit-bb-a5]] / [[kit-bb-n105]] / [[studer-a800]]) and the transient-design
[[softube-transient-shaper]] — the measured deep-dive behind the [[ssl-bus-compressor-2]] skill and the
plugin-specific specialization of [[vst-compress]].

**Part A** is *measured on this rig* (real Pedalboard param surface + our render results); **Part B** is a
*web-research synthesis, cited* (chiefly SSL's own Bus Compressor 2 User Guide, read page-by-page).

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness / peak / stereo and the crest/LRA that
> prove "glued." Verify every move with `[L] measure-loudness` / `measure-microdynamics`. A comp that "sounds
> glued" but doesn't move crest/LRA/GR is a level illusion ([[gemini-audio-understanding]]).

---

## TL;DR (the headline, measured)

1. **It's a GLUE comp.** Classic recipe = **2:1 / 4:1, slow attack (10–30 ms), AUTO release, 2–4 dB GR**,
   makeup to match. On the Watercolors warm drum bus that lands gentle glue: crest 17.2→16.5, **LRA 2.44→2.07
   (tighter)**, +0.7 LU, true-peak still −0.98 (`ssl-bc2-drum-glue` → `projects/watercolors/mix/ssl_bc2_glue_demo.wav`).
2. **Slow attack preserves transients — measured, the textbook holds here.** At fixed GR, **30 ms passed the
   kick/snare peak +2.4 dB louder than 0.1 ms** (peak −9.0 vs −11.4; crest 19.3 vs 18.2). Use 10–30 ms for
   punch, fast (0.1–3 ms) to clamp. (Contrast [[api-vision-channel-strip]], where "slow = punch" was *false* —
   it's plugin-specific, so measure.)
3. **AUTO release = smooth glue; fixed fast releases PUMP.** AUTO gave crest ~18; fixed **0.1–0.6 s gave
   crest ~21** (more breath/pump). AUTO is the safe default; pick a fixed fast release on purpose for pumping.
4. **Threshold is RELATIVE to input level, not dBFS.** Dial it to the GR, not a number (see the map below).
5. **Tooling gotcha:** `ratio` / `release_s` / `sidechain_hpf_hz` / `oversampling` are **string enums** and
   `comp_bypass`/`external_s_c`/`mix_lock` are **bools** — `apply-vst-chain`'s float dict can't set them.
   Ratio + release are fundamental → use the **[[vst-preset]] harness**.
6. **Renders headless via Pedalboard** (`changed:true`). SSL Native is **iLok/PACE** machine-activated — the
   iLok render-farm landmine ([[vst]]): re-verify on any new machine; a demo/unactivated
   seat may load yet render demo-noise/silence.

---

## Part A — measured on this rig (Pedalboard 0.9.23)

**Loads + renders headless.** `load_plugin(".../SSL Native Bus Compressor 2.vst3")` → `name="SSL Native Bus
Compressor 2"`, `is_effect=True`, renders (`changed:true`).

**Param surface (Pedalboard snake_case — what you set in code/the harness):**

| Param | Type | Range / values (measured) | GUI control |
|---|---|---|---|
| `threshold_db` | float dB | −20 … +20, step 0.1 | THRESHOLD |
| `makeup_gain_db` | float dB | **−5 … +15**, step 0.1 | MAKEUP (GUI labels `0..+`) |
| `attack_ms` | float (stepped) | **{0.1, 0.3, 1, 3, 10, 20, 30}** ms | ATTACK |
| `release_s` | **string enum** | `'0.1' '0.3' '0.4' '0.6' '0.8' '1.2' 'AUTO'` (s) | RELEASE |
| `ratio` | **string enum** | `'1.5:1' '2:1' '3:1' '4:1' '10:1' '20:1' 'X'` | RATIO |
| `sidechain_hpf_hz` | **string enum** | `'OFF'` … `'185.0'` (1001 non-round steps, e.g. `'59.9'`) | S/C HPF |
| `dry_wet_mix` | float % | 0 … 100, step 0.1 (**100 = fully wet**) | MIX |
| `oversampling` | **string enum** | `'OFF' '2x' '4x'` | OVERSAMPLING |
| `comp_bypass` | bool | `False` = IN/engaged, `True` = bypassed | IN button |
| `external_s_c` | bool | external sidechain (needs host routing → **n/a offline**) | EXTERNAL S/C |
| `mix_lock` | bool | lock MIX across preset loads | MIX LOCK |
| `groupsense` | float | 0 … 16777215 (SSL 360 group/sense link — leave 0) | (360 / Plug-in Mixer) |

> **Enum gotcha (the big one).** `[L] apply-vst-chain`'s `parameters` dict is **float-only** — it sets
> `threshold_db` / `makeup_gain_db` / `attack_ms` / `dry_wet_mix` but **NOT** the string enums (`ratio`,
> `release_s`, `sidechain_hpf_hz`, `oversampling`) or the bools (`comp_bypass`, `external_s_c`, `mix_lock`).
> Because **ratio and release are fundamental**, drive BC2 through the **`presets/vst/apply_vst_preset.py`**
> harness ([[vst-preset]]), which `setattr`s every param. Enum strings are exact: `ratio="4:1"`,
> `release_s="AUTO"`, `sidechain_hpf_hz="59.9"` (`'60.0'` is rejected — pull from the plugin's valid list).

### The threshold → GR map (4:1, attack 10 ms, AUTO, makeup 0; source = warm drum bus, −17 LUFS / −1 dBFS peak)

| threshold | +12 | +8 | +4 | 0 | −4 | −8 | −12 |
|---|---|---|---|---|---|---|---|
| GR (≈ peak/RMS pull-down) | 1.2 | 2.7 | **4.6** | 6.7 | 8.9 | 11.0 | 13.1 |

**Threshold is relative to input level, not dBFS** — on this bus ~**+4…+6 gives the musical 3–4 dB glue**. On a
different level the same number gives different GR: gain-stage consistently (harness `input_gain_db`) and re-dial.

### Attack → transient preservation (4:1, threshold −8, AUTO, makeup 0)

| attack | 0.1 | 1 | 3 | 10 | 20 | 30 ms |
|---|---|---|---|---|---|---|
| crest | 18.2 | 18.2 | 18.1 | 18.1 | 18.6 | **19.3** |
| transient peak | −11.4 | −11.4 | −11.4 | −11.1 | −10.1 | **−9.0** |

**Slow attack lets the hit through** (+2.4 dB peak, +1.1 crest from 0.1→30 ms). Fast (0.1–3 ms) clamps it.
The textbook holds for BC2 — but it was *inverted* on the API Vision strip, so always measure.

### Release → glue vs pump (4:1, threshold −8, attack 10, makeup 0)

| release | AUTO | 1.2 | 0.6 | 0.3 | 0.1 s |
|---|---|---|---|---|---|
| crest | **18.1** | 21.0 | 21.4 | 21.4 | 21.3 |

**AUTO = smooth, program-dependent, lowest crest (transparent glue).** Fixed fast releases recover between
hits → crest ~21 (more pump/breath). Choose fixed fast release *on purpose* for an EDM/aggressive pump.

### Parallel via the built-in MIX (10:1-ish heavy wet, threshold −12, attack 3, AUTO)

| MIX | 100% | 75% | 50% | 25% |
|---|---|---|---|---|
| GR | 13.4 | 7.8 | 4.4 | 1.9 |
| peak | −11.5 | −8.3 | −5.1 | **−2.8** |

Smash the wet hard, then blend the **dry** back with MIX → "New York" parallel. As MIX drops the dry
transients return (peak walks back toward source −1.0). 30–50% is the usual blend. No external send needed.

### Sidechain HPF — kick out of the detector (4:1, threshold −4, attack 10, AUTO)

| S/C HPF | OFF | 60 Hz | 120 Hz | 185 Hz |
|---|---|---|---|---|
| GR | 8.9 | 7.8 | 4.6 | 3.0 |
| kick peak through | −9.8 | −9.9 | −8.3 | **−7.1** |

Raising the SC-HPF removes low energy from the **detection** path (audio low end untouched) → less
kick-triggered GR, the kick punches **+2.8 dB** more through, and the bus stops pumping on bass. ~60–120 Hz is
the usual mix-bus setting.

### Oversampling

OFF / 2x / 4x measured **identical** in peak/crest on this material (no audible aliasing at the loop level —
the difference is ultrasonic, on heavy/fast settings). **For offline render leave 2x/4x on** — it's free here
(the manual's PDC/latency caveat only matters in a live DAW). Note our Pedalboard load reported the state at
`4x`; SSL's documented GUI default is OFF.

### Validated glue render (real MCP meters, `[L] measure-loudness`)

`ssl-bc2-drum-glue` (4:1, attack 30, AUTO, threshold +5, makeup +3.5, OS 4x), warm drum bus → demo:

| metric | source | after | Δ |
|---|---|---|---|
| Integrated LUFS | −17.18 | −16.45 | +0.73 |
| Crest (dB) | 17.17 | 16.49 | −0.68 |
| PLR | 16.20 | 15.47 | −0.73 |
| LRA | 2.44 | 2.07 | tighter |
| True-peak dBTP | −0.98 | −0.98 | safe |

Textbook gentle glue: crest down a touch, LRA tighter, slightly louder, peak-safe. → `projects/watercolors/mix/ssl_bc2_glue_demo.wav`.

---

## Part B — how it works (web-research synthesis, cited)

**What it is.** Solid State Logic (Oxford, England). The big VU reads **dB of gain reduction** (0–20) "in the
style of the classic moving-coil meter found on SSL consoles." It models the **4000 G-series console centre-
section bus compressor** — the legendary VCA "glue" that put cohesion on countless mix buses. The core
compression character is unchanged from the hardware/original plug-in; **v2 adds modern controls around it**.

**Version naming (the one thing that looks wrong but isn't):** the *product* is "Bus Compressor 2" but the
*file version* is v1.x (the screenshot reads v1.8.8; SSL's guide shows v1.0.25 historically and v1.8.36
current). **Don't read "v1.8.8" as "the original" — it is Bus Compressor 2.**

**Controls (all confirmed vs SSL's official User Guide):**
- **THRESHOLD** −20…+20 dB — "the level at which gain reduction is introduced." Continuous.
- **MAKEUP** — "a gain stage to compensate for… compression." GUI labels `0..+`; **the Pedalboard param
  range is −5…+15 dB** (measured). SSL doesn't print the numeric ceiling; +15 matches the Waves/hardware-G
  lineage.
- **ATTACK** {.1 .3 1 3 10 20 30} ms, stepped — "response time of the onset of compression." *"The 20 ms
  option has been introduced in Bus Compressor 2"* (hardware had .1/.3/1/3/10/30).
- **RELEASE** {.1 .3 .4 .6 .8 1.2 AUTO} s, stepped — *".4, .8 and 1.2 second options have been introduced in
  Bus Compressor 2."* **AUTO** is the renowned dual-time-constant, program-dependent release (SSL does not
  publish BC2's exact constants; the classic "≈100 ms fast / ≈12 s slow" figures float around unofficially).
- **RATIO** {1.5 2 3 4 10 20 X} — "the degree of compression." *"The 1.5, 3, 10, 20 and X options have been
  introduced in Bus Compressor 2. X is the most aggressive option — greater than 20, but less than infinity."*
  So the hardware set was **2/4/10**; **X is a super-ratio (>20:1, <∞), NOT a literal brickwall limiter.**
- **S/C HPF** OFF…185 Hz — "applies a high-pass filter to the compressor **sidechain**." Detection-only;
  stops bass/kick over-triggering GR and pumping. One of two features SSL calls "not found on the original
  hardware."
- **MIX** DRY…WET — "the blend of processed (wet) and unprocessed (dry)… commonly referred to as parallel
  compression." Built-in parallel; the other "not on the original hardware" feature. **MIX LOCK** excludes MIX
  from the preset system so loading presets doesn't yank your blend.
- **OVERSAMPLING** OFF/2x/4x — internal anti-alias; "when compressing material heavily (e.g. smashing a drum
  bus)… helps reduce unfavourable distortion." Adds DAW delay compensation when on (irrelevant offline).
- **EXTERNAL S/C** — feeds the sidechain from a host send (e.g. a kick to pump the bus). **The key routing is
  done in the DAW header**, so it's effectively **unusable in a headless Pedalboard render** — leave off.
- **PLUG-IN MIXER / 360** (the "360° CONSOLE" button) — opens the SSL 360 Plug-in Mixer; BC2 is 360-enabled
  and controllable from UC1/UF8/UF1 hardware. Irrelevant offline (leave `groupsense`/360 default).
- **IN** — compressor in/out (bypass), linked to the DAW insert bypass; lit orange = engaged.

**What's new in Bus Compressor 2** (vs the original SSL Native Bus Compressor and the G-bus hardware): (1)
2x/4x oversampling, (2) built-in MIX dry/wet for parallel + MIX LOCK, (3) sidechain HPF (OFF–185 Hz), (4)
external sidechain key, (5) SSL 360 / Plug-in Mixer + UC1/UF1 hardware integration, (6) expanded ratios
(adds 1.5/3/20/X to 2/4/10), (7) expanded attack (+20 ms) and release (+.4/.8/1.2 s). **The glue character is
the same** — these are workflow/quality additions, not a new sound.

**The classic recipes (from SSL + the bus-comp literature):**

| Use | Ratio | Attack | Release | GR | Notes |
|---|---|---|---|---|---|
| **Mix-bus glue** (the famous one) | 2:1 or 4:1 | 10–30 ms | AUTO | 2–4 dB | slow attack keeps punch; SC-HPF ~60–90 Hz if bass pumps |
| **Drum-bus glue** | 4:1 | 10–30 ms | AUTO (or .3) | 3–5 dB | the cohesion + density move |
| **Parallel / NY smash** | 10:1 / X | 1–3 ms | .1–.3 | 8–12 dB | then dial MIX 30–50% to restore dry punch |
| **Pump / EDM** | 4:1 | 10 ms | .1 | 4–6 dB | fast fixed release = intentional breath/pump |

**Pitfalls (third-party + reproduced here):** too-fast attack kills drum punch (use 10–30 ms); too much GR or
a fast fixed release **pumps** (use AUTO + 2–4 dB for transparent glue); makeup gain **hides** over-compression
(judge by crest/LRA, not level); it's a **glue stage, not a master** (don't limit here — hand to
[[master-track]]); and offline you can't use EXTERNAL S/C (no host key) and should keep oversampling on.

**Licensing / headless (cited + caveated):** SSL Native uses **iLok/PACE** (machine activation, iLok dongle,
or iLok Cloud; SSL added machine-based iLok licensing in the Native v6.3 release). Machine activation enables
offline headless rendering **on a validly-activated machine** — but the **iLok render-farm landmine** applies:
a fresh/unactivated/demo seat may load yet render demo-noise or silence, and **subscription** seats must
reconnect periodically. The Pedalboard render result above is a first-party empirical test on this Mac (no
external write-up of SSL-Native-through-Pedalboard exists) — **re-verify load+render anywhere else.**

---

## Sources
- **SSL Bus Compressor 2 User Guide (official, primary)** — https://www.solidstatelogic.com/assets/uploads/downloads/support.solidstatelogic.com_Bus_Compressor_2_User_Guide.pdf · https://support.solidstatelogic.com/hc/en-gb/articles/4408670926109-SSL-Bus-Compressor-2-Plug-in-User-Guide
- SSL store (product / price / formats / Apple-Silicon) — https://store.solidstatelogic.com/plug-ins/ssl-native-bus-compressor-2
- SSL 4000 G-Bus hardware lineage (UAD manual) — https://help.uaudio.com/hc/en-us/articles/30847649785748-SSL-4000-G-Bus-Compressor-Manual · https://www.uaudio.com/products/ssl-4000-g-series-bus-compressor
- BC2 new-modes / SC-HPF + Mix review — https://blog.imseankim.com/ssl-native-bus-compressor-2-glue-compression-new-modes-review/ · https://blog.imseankim.com/ssl-g-bus-compressor-plugin-sidechain-hpf-mix-knob-update/
- Classic SSL bus-glue technique — https://www.waves.com/how-to-use-ssl-bus-compressor-classic-mix-glue · https://recordmixandmaster.com/2025-10-the-magic-of-the-ssl-g-series-bus-compressor · https://penny.cool/tips-and-techniques/the-ssl-4000-bus-compressor/
- AUTO-release behavior — https://gearspace.com/board/high-end/66154-ssl-buss-compressor-autorelease.html
- Drum-bus compression — https://unison.audio/drum-bus-compression/ · https://wethesound.io/blogs/infos/how-the-ssl-comp-makes-your-drums-bang · https://www.musicguymixing.com/drum-bus-compression/
- Sidechain-filter / stop mix-bus pumping — https://www.nailthemix.com/how-to-stop-mix-bus-pumping-the-sidechain-filter-hack
- SSL iLok/PACE licensing + machine activation — https://support.solidstatelogic.com/hc/en-gb/articles/7638678976413-iLok-Licensing-and-Activation-FAQ · https://solidstatelogic.com/media/ssl-native-v63-plug-release-adds-machine-based-ilok-licensing-and-new-plug · https://www.sweetwater.com/sweetcare/articles/ssl-native-software-activation-instructions/
- Headless VST3 hosting / Pedalboard — https://spotify.github.io/pedalboard/reference/pedalboard.html · https://deepwiki.com/spotify/pedalboard/3.2-external-plugins-(vst3au) · https://forum.juce.com/t/headless-vst3-host-some-plugins-render-silence/58169
