# UADx Vibe Analog Machines — field guide: a 10-"machine" analog saturation + warble/tone box, headless

How to drive the **UADx Vibe Analog Machines** — UA's analog **saturation / coloration** effect: pick one of **10
modeled analog "machines"** (the colour-swatch row), set **DRIVE** (the amount), and shape with the second knob —
**WARBLE** (tape wow/flutter) on the 6 *tape* machines or **TONE** (brightness/colour) on the 4 *preamp* machines —
then trim the output. It is a **harmonic-saturation + modulation colour box — NOT an EQ (no bands) and NOT a real
compressor** (its saturation lowers crest, which reads as light "glue"). The fast lo-fi/character cousin of the
proper tape emulations [[studer-a800]] / [[ampex-atr-102]] / [[softube-tape]] and the multiband saturator
[[fabfilter-saturn-2]], in the [[vst-saturate]] family.

> **The name + binary gotcha (read first):** **"Vibe Analog Machines" is the renamed "Verve Analog Machines"** — the
> *same* plug-in (UA renamed it **2026-04-14**; originally released **2024-04-04** as *Verve*). So **all reviews and
> the manual say "Verve"** but describe this exact plug-in, and the product ships as
> **`/Library/Audio/Plug-Ins/VST3/uaudio_verve.vst3`** — internal codename `verve`, but `load_plugin`/`dump_params`
> report the product name *"UADx Vibe Analog Machines"*. The cut-down **Essentials** edition is
> `uaudio_verve_essentials.vst3`. There is no `uaudio_vibe*`.

**Part A** is *measured on this rig* (the real Pedalboard param surface + our own render/THD/meter results); **Part B**
is a *web-research synthesis, adversarially verified, cited*. Pleasingly, **Part A answers exactly the open questions
Part B couldn't** (does it render headless? the param surface? is the 2nd knob one param meaning Warble/Tone? the
machine enum? per-machine THD?). The skill [[vibe-analog-machines]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the tilt/centroid/crest that
> prove a tonal or saturation move. Verify every move with `[L] measure-spectrum` / `measure-loudness`. A render that
> "sounds" coloured but shows a 0.00 spectrum/crest delta is a **passthrough** (wrong build). **And WARBLE is invisible
> to those meters** (it's pitch modulation) — audition it.

---

## TL;DR (the headline, measured)

1. **Renders headless — load `uaudio_verve.vst3`.** UADx native, `probe_plugin.py` → `RENDERS ✓`, **bypass is
   sample-accurate to dry (Δ = 0.0)**. Needs an **iLok *account*** (software, no dongle) — authorized & verified
   processing here; re-verify on another machine. Don't load the `UAD …`/`.component`/AU twins (the usual UAD
   passthrough-offline risk — [[vst-verify]]).
2. **6 params; the `machine` is a STRING enum → drive it with the [[vst-preset]] harness, not `apply-vst-chain`'s
   float dict** (which sets the numerics but silently misses the machine name — the whole point of the plugin).
3. **`param_1` = DRIVE; `param_2` = WARBLE on the 6 TAPE machines / TONE on the 4 PREAMP machines; `output_trim` =
   the bipolar −/0/+ output slider** (mapped by measurement). DRIVE is the saturation amount; `output_trim` is a
   perfectly **linear, clean** level (±6 trim = ±6 dB exactly).
4. **The second knob is context-dependent (measured):** on tape machines `param_2` is **WARBLE** — pitch modulation,
   the tone/centroid doesn't move; on preamp machines it is **TONE** — a huge brightness control (centroid 1200 → 6000+
   Hz), no pitch smear. Same parameter slot, two meanings, by machine.
5. **DRIVE 0 IS NOT BYPASS** — at `param_1=0` the machine still colours (Sweeten d0 = 0.24 % THD + level). True null =
   `master_bypass=true` (0.000 % THD) or `power=false`.
6. **The 10 machines are 6 tape + 4 preamp on a clean→dirty (blue→red) gradient.** Tape: Sweeten, Warm, Thicken,
   Vintagize, Overdrive, Fire. Preamp: Edge, Glow, Distort, Sputter. UA says **Drive is gain-compensated**; measured,
   level still drifts ±a few dB across machines and soft-clip eats peak → **normalize / use `output_trim`, A/B
   loudness-matched.**

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin(".../uaudio_verve.vst3")` → `name="UADx Vibe Analog Machines"`,
`is_instrument=False`, renders (machine/drive moves change the audio; `master_bypass=true` is bit-identical to dry).
Tested input `artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav` (the drum loop in the plugin's
title bar in the source screenshot) + a 1 kHz tone for THD.

`list-vst-plugins {name_contains:"Vibe"}` → use the VST3 **`uaudio_verve.vst3`** build:

| Name | Path | Use |
|---|---|---|
| **UADx Vibe Analog Machines** | `/Library/Audio/Plug-Ins/VST3/uaudio_verve.vst3` | ✅ this one (renders; 10 machines) |
| UADx Vibe Analog Machines Essentials | `/Library/Audio/Plug-Ins/VST3/uaudio_verve_essentials.vst3` | cut-down build (4 tape machines, drive only) |
| UADx Vibe Analog Machines (AU) | `…/Components/uaudio_verve.component` | AU twin (macOS-only) |
| (any `UAD …` / DSP twin) | `…/Components/…` / `…/Universal Audio/…` | ❌ DSP/passthrough twins (offline) — avoid |

### The real parameter surface (Pedalboard-exposed — authoritative for this build)

**6 parameters, all enums.** Numeric enums (`param_1`, `param_2`, `output_trim`) take an on-grid float via `setattr`;
`machine` takes the exact string; `power`/`master_bypass` are bools.

| Param | Type | Values (grid) | Control / measured behaviour |
|---|---|---|---|
| `machine` | enum (str) | `THICKEN`·`VINTAGIZE`·`OVERDRIVE`·`EDGE`·`SPUTTER`·`GLOW`·`DISTORT`·`SWEETEN`·`WARM`·`FIRE` | the **voicing**. ⚠️ this enum order is the internal/dump order — **not** the GUI gradient order (see the machine map) |
| `param_1` | enum-num | 0–100, 0.1 steps (default **40**) | **DRIVE** — amount of the selected machine's saturation |
| `param_2` | enum-num | 0–100, 0.1 steps (default **0**) | the **second knob**: **WARBLE** (tape machines) / **TONE** (preamp machines) — one slot, two meanings |
| `output_trim` | enum-num | −12 … +12 dB, 0.02 steps (default 0) | the bipolar **−/0/+ output slider** — clean, perfectly **linear** level (global; full version only) |
| `power` | bool | `True`/`False` | unit power (False = true bypass) |
| `master_bypass` | bool | `False`/`True` | plugin bypass (True = true null, 0.000 % THD) |

> **No input gain, no wet/dry, no EQ, no compressor controls.** The far-left on-screen "input" element is a **meter**,
> not a host-exposed fader — gain-stage with the harness's `input_gain_db` / `output_peak_dbfs` instead. `output_trim`
> (the right −/0/+ slider) is the only level control. **Essentials** exposes only `power` / `machine` (4 tape values:
> `THICKEN`/`VINTAGIZE`/`SWEETEN`/`WARM`) / `param_1` (drive) / `master_bypass` — **no warble/tone, no output_trim**.

### The 10 machines — GUI gradient order (cleanest→dirtiest), measured

The swatch row runs blue (clean/cold) → red (dirty/old). Type and the second-knob meaning are **measured** (warble =
pitch-mod, tone steady; tone = centroid swings, no pitch-mod):

| # | Machine | Type | 2nd knob | THD @ drive 40¹ | Harmonics | Tonal character (measured) |
|---|---|---|---|---|---|---|
| 1 | **SWEETEN** ★ | tape | Warble | 0.8 % | odd, near-clean | cleanest; **brightens** (centroid 1593→1725), +air, **crest HELD** — exciter-like |
| 2 | **EDGE** | preamp (SS console) | **Tone** | ~0.01 % | even (blooms w/ drive) | near-clean at d40; **Tone is a big brightness tilt** (centroid 1273→6150 across Tone) |
| 3 | **GLOW** | preamp (valve) | **Tone** | 0.18 % | even | subtle valve warmth; **Tone** centroid 1224→5784, low THD — clean tube tilt |
| 4 | **WARM** ★ | tape | Warble | 0.3 % | odd (clean till ~d60) | warmer (centroid→1335 @d65), **keeps air**, crest down (glue) |
| 5 | **THICKEN** | tape | Warble | 4.6 % | odd (symmetric) | **mid body ↑**, **crest UP** (tighter), darker — density |
| 6 | **VINTAGIZE** | tape | Warble | 13.8 % | odd | **dark, band-limited, mid-forward** — lo-fi/old tape |
| 7 | **DISTORT** | preamp (valve) | **Tone** | 14.4 % | balanced even+odd | driven valve; **Tone** centroid 1429→6587 + THD 14→45 % — bright/dirty |
| 8 | **OVERDRIVE** | tape | Warble | 40.3 % | odd (symmetric) | heavy clip, **crest crushed ~7**, harsh top |
| 9 | **FIRE** | tape | Warble | 32.2 % | odd | searing pushed tape, crest crushed, bright/harsh |
| 10 | **SPUTTER** | preamp (transistor) | **Tone** | 43.6 % | **even** (2nd at −7 dB) | filthiest ("on the verge of blowing up"); **Tone** 1514→7439 + THD 44→94 % |

¹ Tape THD is at `warble 0`; **preamp THD is at `Tone 0`** (their darkest, lowest-harmonic setting) — Tone raises both
brightness *and* (on the dirty preamps) THD. Essentials = the 4 tape machines Sweeten/Warm/Thicken/Vintagize.

**The crest + centroid tell:** *sweeten* → centroid UP + crest HELD · *warm/dark tape* → centroid DOWN + crest down ·
*body* (THICKEN) → low-mid up + crest UP · *distortion* → crest crushed + harmonic top · *preamp Tone* → centroid
sweeps 1200↔6000+. **Warble doesn't move any of these** (audition it). Even-vs-odd is real: the preamps EDGE/GLOW/
SPUTTER + tape THICKEN(no-2nd)… actually the **even-leaning** set is GLOW/EDGE/SPUTTER (+DISTORT balanced); the
**odd-leaning** set is the rest — a useful timbre cue (even = rounder/tube-ish; odd = edgier).

### Footguns (proven on this rig)

1. **The 2nd knob means different things by machine.** `param_2` = **Warble** (pitch wow/flutter) on the 6 tape
   machines, **Tone** (brightness/colour) on the 4 preamp machines. A preset that sets `param_2` assuming "warble" on
   a preamp machine is actually setting **Tone** (e.g. `param_2=80` on GLOW = bright, not wobbly). Know your machine's type.
2. **WARBLE is pitch modulation → invisible to `measure-spectrum`/crest.** Measured: Vintagize warble 0/30/60 on the
   drum loop → **identical** centroid & band energies, constant RMS. On a 1 kHz tone the fundamental-concentration
   collapses 1.00 → 0.85 (w30) → 0.28 (w50) → 0.08 (w100). **Audition it / use a tonal source.** (TONE, by contrast,
   *does* move the centroid — that's how you tell which one a machine has.)
3. **DRIVE 0 ≠ bypass.** `param_1=0` still colours (Sweeten d0 = 0.24 % THD, +level; Δ vs true bypass = 0.35). Only
   `master_bypass=true` (0.000 % THD) or `power=false` is a real null (bit-identical to dry). Compare against a *real*
   bypass, not drive 0.
4. **Drive's level "compensation" is approximate.** UA's manual calls Drive gain-compensated; measured, RMS stays
   *roughly* constant within a machine but the level still drifts ±a few dB across machines (EDGE/GLOW +3–4 dB at high
   Tone, OVERDRIVE −5.5 dB) and soft-clip eats peak on the hot machines. **Normalize / pull `output_trim`, A/B
   loudness-matched** — don't judge by level; judge by THD/crest/centroid.
5. **The `machine` string enum needs the harness.** `apply-vst-chain`'s float-only dict can nudge `param_1`/`param_2`/
   `output_trim` but **cannot set `machine`** — drive it with [[vst-preset]]'s `apply_vst_preset.py` (`setattr`).
6. **Per-machine recall (GUI).** In the GUI, Drive/Warble/Tone are retained *per machine* (switching recalls that
   machine's last values) and only Output is global; for a deterministic render this is moot if you **set every param
   explicitly** (the harness does) — but never assume a value carries across a machine switch.
7. **Wrong build = silent passthrough.** Load `uaudio_verve.vst3`; the `UAD …`/`.component`/AU twins risk passthrough
   offline — a 0.00 delta is the tell ([[vst-verify]]).

### Measured: DRIVE (`param_1`) = the saturation engine

THD of a 1 kHz tone vs drive — each machine has its own curve/onset:

| machine | d0 | d20 | d40 | d60 | d80 | d100 | note |
|---|---|---|---|---|---|---|---|
| **SWEETEN** (tape) | 0.24 % | 0.46 % | 0.78 % | 0.89 % | 1.19 % | 9.98 % | stays clean, only bites at 100 |
| **WARM** (tape) | 0.30 % | 0.29 % | 0.30 % | 2.15 % | 7.52 % | 17.9 % | clean until ~d60, then odd harmonics build |
| **DISTORT** (preamp) | 0.19 % | 5.85 % | 14.4 % | 17.8 % | 19.2 % | 19.7 % | ramps fast, plateaus ~19 % (at Tone 0) |

Clean machines (Sweeten/Warm/Glow/Edge) want 60–100 for obvious colour; the dirty ones (Vintagize/Distort/Overdrive/
Fire/Sputter) are heavy by 40.

### Measured: WARBLE (`param_2`, tape machines) = wow/flutter (pitch modulation)

1 kHz tone, Sweeten drive 40, fundamental concentration (1.0 = pure tone; lower = smeared by pitch wobble):

| warble | 0 | 15 | 30 | 50 | 75 | 100 | RMS |
|---|---|---|---|---|---|---|---|
| concentration | 1.000 | 0.990 | 0.848 | 0.284 | 0.150 | 0.078 | **constant 0.191** |

Constant RMS + a collapsing fundamental = pure pitch modulation, no level/tone change. ~20–35 is a musical, audible
wobble; 50+ gets seasick. **It will not show in any spectrum/loudness meter** — confirm by ear / `[G] detect-mix-issues`.

### Measured: TONE (`param_2`, preamp machines) = brightness/colour

Drive 40, Tone sweep — preamp centroid (drum loop) + THD (1 kHz tone). Tone is a wide brightness tilt:

| preamp | centroid @ Tone 0→50→100 | THD @ Tone 0→100 | note |
|---|---|---|---|
| **EDGE** (SS console) | 1273 → 3107 → 6150 | 0.01 % → 0.02 % | near-clean tone-shaper at d40 |
| **GLOW** (valve) | 1224 → 2914 → 5784 | 0.18 % → 0.27 % | subtle valve warmth + brightness |
| **DISTORT** (valve) | 1429 → 3435 → 6587 | 14.4 % → 45 % | driven valve; Tone adds brightness *and* grit |
| **SPUTTER** (transistor) | 1514 → 3848 → 7439 | 44 % → 94 % | filthiest; Tone pushes it further over |

So on a preamp machine **Tone ≈ 50 is roughly neutral**, 0 = dark, 100 = bright/harsh. (My earlier "GLOW/EDGE/SPUTTER
are the darkest machines" reading was an artifact of measuring them at Tone 0 — at Tone 50 they're neutral-to-bright.)

### Measured: `output_trim` = clean, linear output level

Sweeten d0, 1 kHz tone — `output_trim` −12/−6/0/+6/+12 → RMS −27.0/−21.0/−15.0/−9.0/−3.0 dBFS: **exactly ±6 dB per ±6
trim, tone unchanged.** A clean post-gain (the right −/0/+ slider), not a drive control.

### Measured: the three shipped presets (via the real `apply_vst_preset.py` harness + `[L]` meters)

All peak-normalized to −1 dBFS by the harness (read **crest / centroid / tilt** for the honest move, not LUFS):

| metric (`[L]` meters) | dry | `vibe-sweeten-drum-glue` (SWEETEN d50) | `vibe-warm-drum-bus` (WARM d65) | `vibe-lofi-warble` (VINTAGIZE d50 w35) |
|---|---|---|---|---|
| crest factor (dB) | 14.63 | **14.75** (held — clean) | **12.09** (−2.5, glue) | **12.82** (−1.8) |
| spectral centroid (Hz) | 1593 | **1725** (brighter) | **1335** (warmer) | **1078** (dark) |
| spectral tilt (dB/oct) | −2.71 | −2.62 | −3.34 | −3.57 |
| 5 k / 10 k (rel dB) | −21.4 / −28.8 | −19.9 / −27.5 (+air) | −20.3 / −32.3 (top gently rolled) | −20.9 / −44.5 (top gutted) |
| true-peak (dBTP) | −3.07 | −0.99 | −0.97 | −0.99 |

- **`vibe-sweeten-drum-glue`** — Sweeten d50: an **exciter-like clean brighten** (centroid up, +air, crest held).
- **`vibe-warm-drum-bus`** — Warm d65: warm + glued, crest down 2.5, top *gently* rolled (matches [[warm-drum-bus]];
  and, independently, **SoS recommends "Warm @ Drive ~65 % on drums"** — Part B). The truer "warm bus" (keeps air).
- **`vibe-lofi-warble`** — Vintagize d50 + warble 35: dark/band-limited lo-fi **plus** tape wobble (the warble is
  audible-only; the table can't show it).

**The crest direction is the proof:** colour/glue **lowers** crest; a clean sweeten **holds** it.

### How to drive it headless

Use **[[vst-preset]]**'s `apply_vst_preset.py` (`setattr`s every param, the `machine` string included), all 6 params
explicit. `presets/vst/vibe-*.json` are ready:
`../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
projects/<track>/mix/<stem>_vibe.wav`. Dump the live surface with `presets/vst/dump_params.py uaudio_verve`;
re-characterize with `scripts/mix/vibe_sweep.py`; set `dump_state=true` (via `apply-vst-chain`) for a byte-stable re-render.

---

# Part B — how the Vibe Analog Machines works (web-research synthesis, adversarially verified, cited)

> Graded by adversarial verdict; 40 claims supported/refined, 0 refuted. Where the installed plugin's measured surface
> (Part A) differs, **Part A wins for what renders** — and Part A empirically answers Part B's open questions.

## 1. What it is + the name fact

- **A native analog *saturation / coloration* plug-in** — not an EQ, compressor, or instrument. A bank of **10
  UA-designed "tone machines"** (tape-recorder and tube/solid-state preamp emulations) adding harmonic warmth, grit,
  and — on tape models — wow/flutter. UA: *"Explore ten retro-futuristic tone machines, packed with analog magic"* ·
  *"Shape tones quickly with simple controls like drive, tone, and tape warble"* · *"Give kicks, snares, and synths
  gritty tape textures or add tube warmth to vocals, guitar, bass, or your entire mix."* [SUPPORTED]
- **Vibe == Verve (the load-bearing fact).** UA **renamed Verve Analog Machines → Vibe Analog Machines on
  2026-04-14** ("only affects the product name … features, functionality, and sonics are unchanged"). It originally
  **released 2024-04-04 as Verve**. So **all the in-depth reviews + the manual carry the "Verve" name** but describe
  this exact plug-in, and the binary keeps the `verve` codename. [SUPPORTED]
- **Mental model** (Tape Op): roughly *"a two-knob hybrid mashup of UA's Thermionic Culture Vulture and a Studer A800"*
  — a *feel*, not a literal model list.

## 2. Platforms / licensing / DSP-vs-native

- **UADx = UA's native (CPU) line** — runs on macOS/Windows **with NO UA hardware** (no Apollo, no UAD-2 DSP); it
  **cannot** run on UA DSP. Formats: **VST3, AU (macOS), AAX**, + UA's LUNA; macOS build is **Universal 2** (Intel +
  Apple Silicon); **macOS Big Sur 11 minimum** (the "10.15" figure on some aggregators is stale). [SUPPORTED]
- **Requires an iLok *account*** (software) — a physical iLok dongle is supported but **not required**; 3 activations.
  "No UA hardware" does **not** waive the iLok-account requirement; an unauthorized machine fails/passes through.
  [SUPPORTED] → this is the build family that processes headless in Pedalboard (Part A confirms it renders here).
- **Pricing is time-dependent** — launched $199 list / $99 intro; aggregators currently snapshot ~$99 (promo vs reset
  unclear). Latest version ~1.1.0. *Don't hardcode a price.*

## 3. The 10 machines — 6 tape + 4 preamp, on a clean→dirty gradient

Verified order, **cleanest (blue) → filthiest (red)**, with the type split confirmed by measurement (Part A):

`Sweeten · Edge · Glow · Warm · Thicken · Vintagize · Distort · Overdrive · Fire · Sputter`

| # | Machine | Type | UA/review character |
|---|---|---|---|
| 1 | Sweeten | **Tape** | cleanest; studio-tape gloss/warmth, gently overdrivable (the screenshot's selected machine) |
| 2 | Edge | **Preamp** (solid-state console) | *"subtle crunch created by gentle harmonics"* (UA manual) — subtle, not heavy |
| 3 | Glow | **Preamp** (valve) | *"subtle warmth created by gentle harmonics"* (UA manual) |
| 4 | Warm | **Tape** | vintage studio-tape warmth, warmer/older than Sweeten |
| 5 | Thicken | **Tape** | tape recorded ~½ century ago; density/thickening |
| 6 | Vintagize | **Tape** | older-recording vintage tape character |
| 7 | Distort | **Preamp** (valve) | a driving valve preamp |
| 8 | Overdrive | **Tape** | tape pushed past its limits / "fuzzy tape" |
| 9 | Fire | **Tape** | *"searing analogue tape"* pushed hard |
| 10 | Sputter | **Preamp** (transistor) | filthiest — *"a transistor preamp on the verge of blowing up"* (solid-state, **not** valve) |

- **Tape (6):** Sweeten, Warm, Thicken, Vintagize, Overdrive, Fire → controls **Drive + Warble**.
- **Preamp (4):** Edge, Glow, Distort, Sputter → controls **Drive + Tone**.
- **No named hardware.** Tape Op: *"none of these machines are modeled after any specific piece of hardware."* Never
  attribute a specific Ampex/Studer/Neve unit. The on-screen 3D renders are **decorative** (tape reels spin; preamps
  show a reactive signal light); the **"ST9" reel label is stylised/fictional**. The screenshot's 11th circular
  element is the **"i" info button**, not an 11th machine (10 machines confirmed).

## 4. Controls (cross-check Part A for what renders)

| Control | What it does (verified) |
|---|---|
| **Machine selector** (colour swatches, blue→red) | one coloured button per machine; or arrow-step / shuttle the central graphic. Colour = character (bluer cleaner, redder dirtier). It IS the selector, not an intensity knob. |
| **Drive** | the intensity knob on **every** machine (and the only control in Essentials). UA: **gain-compensated** (Part A: only approximately). |
| **Warble** (tape only) | tape **wow & flutter**, **free-running / not tempo-synced**; "substantial degrees" available. Not an EQ. |
| **Tone** (preamp only) | the preamp models' **EQ/colour** control — "invaluable for tailoring the effect for a mix," but can introduce **harsh highs** if pushed. Same slot Warble occupies on tape models; a machine shows one *or* the other. |
| **Output level** (bipolar −/0/+ slider) | **±12 dB output trim, global, full version only** — the plug-in's only level control. |
| **Input** (far-left) | **metering only** — no input-gain control. |
| **Preset dropdown** | task-named presets sorted by category/keyword (e.g. "Vocal Butter", "Drum Bus 60s Bounced", "Acoustic Sizzle"). |
| toolbar IN / A·B / COPY·PASTE / palette / "…" | standard UADx host chrome. |
| **No wet/dry / mix** | confirmed absent — parallel = the DAW insert's wet/dry, or zero Warble to avoid phasing. |

## 5. How engineers use it (reviews)

| Source | Starting moves |
|---|---|
| Sound on Sound | **Warm @ Drive ~65 % on drums** (≡ our `vibe-warm-drum-bus`); Sweeten low-Drive + moderate Warble on vocals; reach for **Tone** (preamp machines) to fit the effect in a busy mix (mind harsh highs). |
| Mix Online | **Warm on vocals**; **Thicken on the drum bus** (a softer "1176-all-buttons"); **Glow on kick**; **Vintagize / Edge on snare or DI bass**. |
| Tape Op | pick a swatch "spiciness," then **audition neighbouring colours**; grab task-named presets; Warble is untimed (a feature). |
| UA copy | gritty tape on kicks/snares/synths; tube warmth on vocals/guitar/bass/whole mix; pop, hip-hop, lo-fi, electronic, rock, experimental. |

## 6. Pitfalls / gotchas (Part B + Part A)

- **"Verve" sources ≠ a different product** — same plug-in, old name; rename was **2026-04-14**, not the 2024 launch.
- **No wet/dry, no input gain; Output is the only level control (±12 dB, global, full version only).**
- **Don't judge a render by loudness** (Drive is ~gain-compensated) — measure THD/crest/centroid (Part A).
- **Edge & Glow are *subtle*** harmonic machines (don't over-describe as heavy distortion); **Sputter is transistor,
  not valve**; the order is Sweeten·**Edge·Glow**·Warm… (Edge/Glow are #2/#3).
- **Headless control mechanics (answered by Part A):** load `uaudio_verve.vst3`; the `machine` string enum needs the
  [[vst-preset]] harness; the 2nd knob is **Warble on tape / Tone on preamp**; Drive 0 ≠ bypass.

> **Pure-DSP equivalents (no plugin, deterministic):** tanh/tape/soft-clip colour → `[L] saturate-loop`; air/presence
> → [[excite]]; proper tape warmth → [[studer-a800]] / [[ampex-atr-102]] / [[softube-tape]]; multiband saturation →
> [[fabfilter-saturn-2]]. Reach for Vibe when you want *its* fast one-machine "vibe" character + the tape **warble**
> specifically.

---

## Sources

UA — Vibe Analog Machines + Essentials product pages; the "Verve is now Vibe" rename note (2026-04-14), the Vibe
Analog Machines manual + FAQ, the UADx-native & system-requirements + iLok-activation help pages (several 403-gated,
quoted via search index); the 2024-04-04 Verve launch press release · Sound on Sound — *UA Vibe Analog Machines*
review + the 2024 Verve launch news · Mix Online — *Verve Analog Machines* real-world review · Tape Op — *Verve (now
Vibe) Analog Machines* review · MusicRadar — *Vibe Analog Machines* review + launch news · KVR — UADx Vibe Analog
Machines listing · Sweetwater / Gearnews — listings. Plus **our own param-surface dump + render/THD/meter results
(Part A)** on `/Library/Audio/Plug-Ins/VST3/uaudio_verve.vst3` via Pedalboard.
