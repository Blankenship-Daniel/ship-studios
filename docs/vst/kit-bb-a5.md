# KIT Plugins BB A5 — field guide: the Blackbird API Legacy console strip, headless

How to drive the **KIT Plugins BB A5** (`KIT BB A5.vst3`) — a channel-strip emulation of the **API
Legacy consoles at Blackbird Studio** (Nashville). It's the **forward / punchy "American console"**
character, a sibling to the UAD API strip ([[api-vision-channel-strip]]) and the contrast to the
warm Neve/tape direction ([[studer-a800]]). **Part A** is *measured on this rig* (real param surface
+ isolation numbers from our own renders); **Part B** is a *web-research synthesis* (cited). The skill
[[kit-bb-a5]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the crest that
> proves "punch." Verify with `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` /
> `check-clipping`. Driving the input raises level *and* true-peak — re-measure after every change,
> A/B loudness-matched.

> **iLok/PACE plugin — verified-headless on THIS machine, a risk elsewhere.** BB A5 is iLok/PACE
> protected (CLAUDE.md's "render-farm landmine" class). **We empirically confirmed it loads, renders,
> and responds to params under Pedalboard here** (machine/USB-authorized). It is *not* a hard block —
> iLok validates programmatically at load, no GUI — but it is a non-deterministic dependency: if the
> authorization drifts, re-screen with `[[vst-verify]]` before trusting a render. **Never run an
> unlicensed/trial instance unattended** — trial state pops a GUI challenge or degrades the output.

---

## TL;DR (the headline, measured)

1. **MIC is the colored/driven path; LINE is cleaner** — counterintuitive but **measured + confirmed
   by the maker.** `pre_amp_source="Mic Mode"` + `pre_amp_gain` is the main color engine (even+odd
   harmonics; H3 rises −64→−14 dB as gain 0→100). `Line Mode` adds only a level-driven 3rd harmonic.
2. **The "input knob" is DRIVE, not level.** Color/glue comes from *driving a stage*: Mic-pre gain
   (strongest), or hitting the channel amp with hot `input_trim` / a pushed `master_fader` (3rd
   harmonic, level-driven). `output_trim`, `master_fader` (in MSTR-BUSS mode) and Line `pre_amp_gain`
   are **clean** make-up.
3. **MSTR BUSS makes it CLEANER here — opposite of the marketing.** Engaging `master_bus` drove every
   harmonic to ≤ −150 dB on a single render. Use it for a **transparent EQ pass**; for grit, leave it
   OFF and drive Mic/the fader. (The hardware master-buss amp only saturates under hot bus-summing
   levels a single file won't reach — see §5.)
4. **Keep the top modest.** Like every API EQ, BB A5 is proportional-Q (no Q knob): a big 2–5 kHz boost
   auto-narrows into a brittle peak, and 2–5 kHz is where API snap *and* harshness live. Get punch from
   **low weight + de-box**, air from a small high shelf — not a fat presence boost.
5. **Three EQ modules:** `eq_choice` = **55A** (API 550A, 3-band) · **55L** (API 550L, 4-band) ·
   **56L** (API 560L, 10-band graphic). All ±12 dB, proportional-Q.

---

# Part A — measured on this rig

Probe rig: `KIT BB A5.vst3` via Pedalboard (the stemmy-loops `vst` venv), processing
`artifacts/watercolors-loops/master/watercolors_drums_104bpm_8bar_a.wav` (48 kHz, 18.5 s drum loop),
peak-normalized before measuring so only **spectral shape / crest** is compared. Harmonic numbers from
a 1 kHz sine probe. (Scripts: `/tmp/kit_bb_a5_*.py` in the build session.)

### The real parameter surface (Pedalboard-exposed — authoritative, 46 params)

Single API channel in series: **input/preamp → HP/LP filters → 3-band EQ (selectable module) → fader →
master-buss → out.** Everything Pedalboard sees is an **enum** (incl. the gains/freqs) — so
`apply-vst-chain`'s float-only dict **cannot set the string enums** (`pre_amp_source`, `eq_choice`,
the `*_type` shelf bools); use the **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`,
`setattr`) or a `dump_state` blob.

| Param | Values *(default)* | Role |
|---|---|---|
| `pre_amp_source` | `Mic Mode` · `Line Mode` *(Mic)* | **Mic = colored/driven, Line = cleaner** |
| `pre_amp_gain` | 0 … 100 *(0)* | **preamp DRIVE** (color in Mic mode; ~inert for color in Line) |
| `pre_amp_pad` | bool *(F)* | **−20 dB** pad (tame a hot source → clean) |
| `polarity` | bool *(F)* | polarity invert (Ø) |
| `high_pass_filter` | `Off`, `20 Hz` … `600 Hz` *(Off)* | input HPF, 6 dB/oct |
| `low_pass_filter` | `300 Hz` … `20.0 kHz`, `Off` *(Off)* | input LPF, 12 dB/oct |
| `eq_on_off` | bool *(T)* | engage the EQ section |
| `eq_choice` | `55A` · `55L` · `56L` *(55A)* | **which EQ module** (550A / 550L / 560L) |
| `55a_{low,mid,high}_filter_{gain,frequency}` | gain ±12 (0.1) / stepped freqs | 550A 3-band |
| `55a_{low,high}_filter_type` | bool | low/high **bell↔shelf** |
| `55a_fltr` | bool *(F)* | 550A **band-limit filter** (cuts <50 Hz, >15 kHz) — 55A only |
| `55a_continuous_gain` | bool *(T)* | STEPPED-EQ-GAIN: T = continuous gain (set any dB) |
| `55l_{low,low_mid,high_mid,high}_filter_{gain,frequency}` | gain ±12 / stepped | 550L 4-band |
| `55l_{low,high}_filter_type` + `55l_continuous_gain` | bool | bell↔shelf / continuous gain |
| `56l_{31hz…16khz}_gain` | ±12 each (10 bands) | 560L graphic: 31/63/125/250/500/1k/2k/4k/8k/16k |
| `master_fader` | −96 … +10 dB *(0)* | channel fader; **drives the channel amp when pushed** |
| `master_bus` | bool *(F)* | **MSTR BUSS** — *cleaner* here (see §below), NOT a 2-bus mode |
| `hum` / `hum_level` | bool / `1·2·3` | analog 60 Hz hum + level |
| `input_trim` / `output_trim` | ±36 dB *(0)* | clean trims (`input_trim` hot **drives** the channel amp) |
| `bypass` | bool | — |

> **Not Pedalboard-exposed:** HUM LINK (links instances — irrelevant headless), Auto-Gain,
> Oversampling Low/Med/High (the render uses the plugin default OS — drive hard with mild
> aliasing caution), A/B, GUI options. **Stepped freqs match the hardware** — HF `2.5/5/7/10/12.5/15/20 k`,
> LF `30/40/50/100/200/300/400`, 55A MF `200/400/600/800/1.5k/3k/5k`, 55L hi-mid `800…12.5k` /
> lo-mid `75…1000`.

### Color at unity (drum loop, peak-normalized) + the harmonic floor

| | crest | centroid | tilt |
|---|---|---|---|
| dry (no plugin) | 11.6 | 180 | −3.30 |
| strip, EQ off, Mic g0 | 12.2 | 181 | −3.29 |
| strip, EQ off, Line g0 | 11.9 | 179 | −3.30 |

**Tonally near-transparent at unity** — but a 1 kHz sine reveals a **faint always-on harmonic floor**
(Mic: H2 −64 / H3 −63 dB; Line: H3 −62, *no* H2 ≈ −152). So unlike the UAD API Vision (which measured
truly clean at unity), BB A5 prints a subtle fixed analog color (~0.08 % THD) even flat — Mic adds 2nd
*and* 3rd, Line only 3rd.

### Drive → harmonic map (how to add color), 1 kHz @ −12 dBFS unless noted

| setting | H2 | H3 | H5 | read |
|---|---|---|---|---|
| Mic, gain 0 | −64 | −63 | — | faint floor (even+odd) |
| Mic, gain 25 | −47 | −59 | — | subtle 2nd-harm warmth |
| Mic, gain 50 | −34 | −34 | −55 | even **and** odd, musical |
| Mic, gain 75 | −37 | **−19** | −29 | odd-dominant grit |
| Mic, gain 100 | −42 | **−14** | −21 | hard console drive (3rd/5th) |
| Line, gain any | −152 | −62 | — | **pre_amp_gain inert in Line** |
| Line, hot in (−3 dBFS) | — | −44 | −86 | channel amp = **level-driven 3rd** |
| Line, fader +10 (in 0 dBFS) | — | **−25** | −46 | **the fader drives the channel amp** |
| `input_trim` +24 | — | −25 | −46 | hot input drives the channel amp |
| **MSTR BUSS on** (any fader/level) | ≤−150 | ≤−150 | ≤−150 | **clean — defeats the grit** |

**Takeaways:** color ranks **Mic+gain (strongest, even+odd) > hot input_trim / fader-up (3rd, level-
driven) > Line/output_trim/MSTR-BUSS (clean).** Drum-loop drive cross-check: `input_trim +18` (out −18)
took crest **11.6 → 8.0** and centroid **180 → 201** — the channel amp compresses transients + brightens
as you push it.

### MSTR BUSS (the gotcha — measured)

Toggling `master_bus=true` drove **every** harmonic to ≤ −150 dB regardless of fader/input level,
while in channel mode (`master_bus=false`) the fader pushed H3 to −25. **On a single moderate-level
render, MSTR BUSS is the *clean* path, not added glue.** Use it when you want the **console EQ +
frequency response without harmonic grit** (transparent EQ, or a 2-bus where per-channel distortion
isn't wanted). For grit, leave it OFF and drive Mic / the fader. (Marketing says it inserts the
master-buss amp's saturation — true on hardware under hot bus summing, but not reached by one file. §5.)

### EQ modules — all three confirmed working (drum loop, peak-normalized)

| variant | crest | centroid | tilt | what moved |
|---|---|---|---|---|
| dry | 11.6 | 180 | −3.30 | — |
| **55A** low-shelf +6@100, hi-shelf +3@12.5k | 11.4 | 139 | −3.58 | broad low lift (shelf), warmer |
| **55L** low+4@100(bell), lo-mid−3@500, hi-mid+3@5k, hi+3@15k(shelf) | 12.9 | 249 | −2.82 | weight + de-box + presence + air |
| **56L** 63+3, 250−2, 4k+2, 8k+3 (graphic) | 13.0 | 248 | −2.81 | smile curve |

`*_filter_type`: **false = bell, true = shelf** (low shelf @100 dumped centroid 180→139; high shelf
lifts air). Proportional-Q — *gain is the Q*. Hum floor on silence: off ≈ −400 dBFS, **L1/L2/L3 =
−108 / −103 / −98 dBFS** mains hum — inaudible on a loud bus, only matters on exposed/quiet material.

### The drum preset (measured) → `presets/vst/blackbird-a5-drums.json`

Mic g35 + 55L (low +4@100 bell · lo-mid −3@500 · hi-mid +1.5@5k · hi +2.5@12.5k shelf) + HPF 40, MSTR
BUSS off, hum off. Proven via the MCP meters (dry → processed):

| | tilt | centroid | low | low-mid | high | low-band crest |
|---|---|---|---|---|---|---|
| dry | −2.63 | 1603 | .79 | .18 | .0045 | 14.4 |
| preset | **−2.23** | **1776** | **.86** | **.12** | **.0067** | **11.2** |

→ more weight, **de-boxed** low-mid, more air/forward tilt, with light low-end glue (crest 14.4→11.2)
while presence/air crest stays up. A forward "American console" drum bus from one box. For more
aggression, switch to **Line + fader +10 + input_trim ~6** (channel-amp smash, crest ~8 — re-measure).

### Verify it still renders (run before trusting it)

```bash
../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "KIT BB A5"   # expect RENDERS ✓
```

---

# Part B — how the console works (web-research synthesis, cited)

## 1. What it is / the "A5"

BB A5 is a **channel-strip plugin** from **KIT Plugins**, made in an officially licensed collaboration
with **John McBride at Blackbird Studio** (Nashville). It models the **API Legacy consoles** in
Blackbird's **Studios B and D** — the 212L-style channel preamp, three switchable API EQs, and the API
master-buss output amp — captured with KIT's **Full Range Modeling** (10 Hz–96 kHz). **"BB" = Blackbird.**
**"A5" is not documented** — "A" is generally read as API, but no source explains the digit; the modeled
desks are in Studios B/D, so it does *not* map to an "A room." **Don't assert a specific expansion.**

- Released ~late Aug 2023; ~$150–200; **VST3 / AU / AAX**, macOS Universal 2 (Apple-Silicon native).
- Part of KIT's Blackbird "BB" line: **N73** (Neve 1073), **N105** (Neve 8078), **F66/F67** (Fairchild
  660/670), **Chamber A**, **Mo-Q**. The three EQs also sell standalone as **BB 55A / 55L / 56L**.

## 2. The modules & signal flow

```
input/preamp (212L) → HP/LP filters → 3-band EQ (55A / 55L / 56L) → fader → master-buss amp → out
```

- **PRE MIC/LINE** — Mic engages the modeled preamp drive (transformer-type saturation/compression);
  **Line disables that drive** → cleaner. (Matches Part A.)
- **Input knob** — preamp **drive/sensitivity**, not a clean trim; **Auto-Gain** holds output level so
  you hear color not loudness; a **Continuous/Stepped** option overrides the detented gain steps.
- **PAD** −20 dB · **Phase** polarity invert.
- **HI-PASS** 6 dB/oct ~20–600 Hz · **LO-PASS** 12 dB/oct ~300 Hz–20 kHz (KIT page; the UI label may
  read 1k–20k — Part A confirms the Pedalboard range is 300 Hz–20 kHz).
- **EQ** — 55A/55L/56L buttons (default 55A); HF/MF/LF blue stepped freq knobs + grey ±12 dB; **H/F &
  L/F** = high/low **shelf** toggles; **STEPPED EQ GAIN** = stepped↔continuous gain (55A/55L); **FLTR**
  = the 550A band-limit filter (<50 Hz, >15 kHz), 55A only.
- **FADER** −96…+10 dB; drives the master-buss amp. **MSTR BUSS** inserts the console master-buss amp
  (intended subtle sat/comp "glue"), **not** a 2-bus mode — but see Part A §MSTR BUSS for the measured
  reality (clean on a single render).
- **ANALOG HUM** ~60 Hz mains hum + **LEVEL** 1–3 + **HUM LINK** (ties hum across instances).
- **In/Out trims** — clean make-up/calibration; **VU IN/OUT** calibrated −18 dBFS = 0 VU.

## 3. The EQ modules — 55A vs 55L vs 56L

All API 550-family **proportional-Q** (no manual Q — bandwidth narrows as boost/cut increases), ±12 dB.

| Module | Models | Bands | Notable |
|---|---|---|---|
| **55A** | API **550A** | 3-band (1 mid bell) | adds the **FLTR** band-limit (<50 Hz/>15 kHz); outer bands bell/shelf; *default view* |
| **55L** | API **550L** (4-band, 550B family) | 4-band (lo-mid + hi-mid) | no band-limit; most flexible — separate mud (lo-mid) from honk (hi-mid) |
| **56L** | API **560L** | 10-band graphic | octave bands 31 Hz–16 kHz, ±12 dB; proportional-Q |

Stepped freqs (match the param dump): **HF** 2.5/5/7/10/12.5/15/20 k · **LF** 30/40/50/100/200/300/400 ·
**55A MF** 200/400/600/800/1.5k/3k/5k · **55L hi-mid** 800/1.5k/3k/5k/8k/10k/12.5k · **55L lo-mid**
75/150/180/240/500/700/1000 · **56L** 31/63/125/250/500/1k/2k/4k/8k/16k.

## 4. Sonic character & best uses

The API Legacy character is **punchy, aggressive, mid-forward** — "less dense and edgier than the
British (Neve) sound," can get "deliciously aggressive." Reviewer/maker-endorsed sources: **drums** are
the headline (56L "killer on the bass drum"; 550-style snare punch; bus weight ~100 Hz + air shelf),
also **bass, electric guitar, snare, vocals**. In this repo it's the **forward/punchy American-console**
option — the contrast to the warm Studer/Neve tape direction, a sibling to [[api-vision-channel-strip]].

## 5. Licensing / headless-render implications

- **iLok / PACE.** Free iLok account + iLok License Manager required; **2 activations**; targets =
  **iLok Cloud / iLok USB (gen 2-3) / Machine activation**. iLok validates **programmatically at load
  (no GUI)** — so a properly-authorized instance **loads & renders headless** (we confirmed it here).
- **Risk, not a hard block** (the CLAUDE.md "landmine" class): **Cloud** needs persistent internet + a
  GUI-opened session → avoid on an isolated box; on an airgapped host PACE pings `activation.paceap.com:443`
  (block it to bound load latency); **Machine activation can drift** with hardware/driver changes; iLok
  VST3s are documented to occasionally hang at plugin scan/init. **Prefer Machine activation or a
  connected iLok USB; keep the PACE daemon running; verify load *and* render on the box.**
- **Never run unlicensed/trial unattended** — trial pops a GUI activation challenge or degrades output
  (periodic silence/noise), poisoning a render. (Pedalboard compatibility for KIT was undocumented
  online — we verified it empirically; re-screen with [[vst-verify]] if anything changes.)

## 6. Pitfalls & gotchas

- **MIC = colored, LINE = clean** (backwards from intuition). For console grit you want **Mic**.
- **MSTR BUSS is the *clean* mode here**, not glue — flip it on for a transparent EQ pass, off for grit.
- **No Q knob** (proportional-Q) — gain is the Q; a big 2–5 kHz boost auto-narrows into a brittle peak.
- **5 kHz lives in 55L hi-mid *and* the 56L** — don't double-stack the harsh zone.
- **`apply-vst-chain` can't set the string enums** (Mic/Line, 55A/L, shelf bools) → use [[vst-preset]].
- **`pre_amp_gain` is inert for color in Line mode** — drive via Mic gain, or hot `input_trim`/fader.
- **Mic gain jumps level** — peak-trim the output (the preset harness does) and re-check `check-clipping`.
- **Hum/Oversampling**: leave `hum` off for clean renders; OS isn't param-exposed (default OS used).
- **iLok** — verify it renders; never trust an unlicensed instance.

## 7. Decision table

| Goal | source/pre | EQ module + moves | other |
|---|---|---|---|
| Forward/punchy drum bus | Mic g~35 (color+glue) | **55L**: +4@100 bell, −3@500, +1.5@5k, +2.5@12.5k shelf | HPF 40; MSTR BUSS off → `blackbird-a5-drums.json` |
| Aggressive "smash" | Line + fader +10 + input_trim ~6 | 55L low + de-box, flat top | crest drops ~8 — re-measure |
| Clean console EQ (no grit) | Line (or Mic + pad) | any module | **MSTR BUSS on** (defeats grit) |
| Kick punch + HF def | Mic g~30 | **56L**: +63, small −250, +4k/+8k | watch top (harsh) |
| Snare crack | Mic g~30, HPF 80–120 | **55A/55L**: +200 body, ≤+2 @1.5–5k, air shelf | proportional-Q narrows the boost |
| De-box / de-mud | Line | **55L** lo-mid **cut** −3/−4 @ 300–500 | cuts auto-broaden (forgiving) |
| Tame harsh top | back off Mic gain | **modest cut** 2.5–5 k (≤4 dB) | don't stack 5 k across hi-mid+56L |
| 60s-room vibe | Mic g~50 | 56L gentle smile | `hum` L1 + LPF ~12–15 k |

> Pure-DSP fallback (no VST): place 550-grid bells/shelves with `[L] apply-eq`; push odd-harmonic
> color with `[L] saturate-loop`; verify punch (crest/PLR) with `[L] measure-microdynamics`.

---

## Sources

KIT Plugins — BB A5 / BB 55A / BB 55L / BB 56L / Blackbird bundle product pages · Sound on Sound (BB A5
launch) · Recording Magazine (Dec 2023 review — module freqs, FLTR, stepped gain) · Mix (Product of the
Week — MSTR BUSS, VU) · Magnetic Magazine (Blackbird partnership) · Waves "API 550 or 560" (proportional-Q,
550A/550B/560 lineage) · KVR (activation, conflicting) · Sweetwater SweetCare (KIT activation) · iLok
help (Cloud/ILM/licenses FAQ) · Spotify Pedalboard compatibility · Wikipedia (Blackbird Studio). Plus
**our own param-dump + isolation/drive/EQ/MSTR-BUSS/preset measurements** (Part A) on `KIT BB A5.vst3`.
