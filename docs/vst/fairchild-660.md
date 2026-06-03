# UADx Fairchild 660 — field guide: variable-mu tube COLOR + glue, headless

How to drive the **UADx Fairchild 660** (`/Library/Audio/Plug-Ins/VST3/uaudio_fairchild_660.vst3`) — Universal
Audio's model of the **Fairchild Model 660 variable-mu (vari-mu) tube compressor-limiter**, the late-1950s
"holy grail" leveler. It's the **tube COLOR + glue** counterpart to the VCA glue of [[ssl-bus-compressor-2]],
the console-tone strips ([[api-vision-channel-strip]] / [[kit-bb-a5]] / [[kit-bb-n105]] / [[ssl-4k-e]]) and
the mastering-tape [[ampex-atr-102]] / [[studer-a800]] — the measured deep-dive behind the [[fairchild-660]]
skill and the plugin-specific specialization of [[vst-compress]].

**Part A** is *measured on this rig* (real Pedalboard param surface + our render results); **Part B** is a
*web-research synthesis, cited* (UA's Fairchild Tube Limiter Collection manual + the hardware literature).

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness / peak / stereo and the crest / LRA /
> spectrum that prove "color, not crush." Verify every move with `[L] measure-loudness` /
> `measure-microdynamics` / `measure-spectrum`. A "fatter" feel that doesn't move crest / low-mid ratio is a
> level illusion ([[gemini-audio-understanding]]).

---

## TL;DR (the headline, measured)

1. **It COLORS more than it crushes.** On this 660 the **crest factor stays ~17–19 dB across the entire
   input/threshold range** — it levels RMS and **thickens the low-mids** without clamping transients. Validated
   gentle move on the Watercolors warm drum bus (`fc660-drum-color`): **crest 17.17→16.90, LRA 2.44→1.84,
   low-mid energy ratio 0.179→0.188, low-band punch HELD (27.15→27.19), +0.27 LU, true-peak −0.99.**
2. **No ratio / attack / release knob.** Sculpt with **INPUT** (drive), **THRESH**, and **TIME_CONST**.
   **INPUT drives both GR *and* harmonic color** — it's a tone box even at 1–3 dB GR.
3. **TIME CONSTANT (1–6) is the transient/density control.** Measured crest on the drum bus: **tc4 = most
   open/punchy (18.2)**, **tc1 = tightest (15.4)**, **tc5/6 = program-dependent auto (denser here, ~15–17)**.
4. **THRESHOLD: higher `thresh` value = MORE GR** (measured — opposite to some hardware-dial lore; dial to the
   meter, see the reconciliation note). **SC FILTER** raises output +4.7 dB to 250 Hz (lows out of the detector).
   **HR (headroom)** is an operating-level trim: low value = hotter/more GR, high value = cleaner/more open.
5. **MIX = built-in parallel** (100 = wet). **660 = MONO** (dual-mono on a stereo bus); **670 = stereo /
   lateral-vertical (M/S)** — prefer the 670 for a true stereo mix.
6. **Tooling gotcha:** **all 12 params are enums** (numeric *and* string) → `apply-vst-chain`'s float-only
   dict can't set them reliably → use the **[[vst-preset]] harness**.
7. **Renders headless via the `uaudio_*.vst3` UADx native build** (`changed:true`). The
   `/Components/UAD Fairchild 660.component` twin **passes audio through** offline — never load it.

---

## Part A — measured on this rig (Pedalboard 0.9.23)

**Loads + processes headless.** `load_plugin(".../uaudio_fairchild_660.vst3")` → `name="UADx Fairchild 660
Compressor"`, renders (`changed:true`, large measured deltas). UADx native is the **perpetual / no-iLok**
lineage (like [[ampex-atr-102]] / Pultec) — but re-verify `changed:true` on a new machine. **Load the
`uaudio_*.vst3` build, not the `/Components/UAD Fairchild 660.component` twin** (passthrough offline →
[[vst-verify]] / [[vst]]).

**Param surface (Pedalboard snake_case — what you set in code/the harness). All 12 are ENUMs:**

| Param | Type | Range / values (measured) | GUI control |
|---|---|---|---|
| `meter` | enum str | `'In' 'GR' 'Out'` (display only — no audio effect) | IN / GR / OUT switch |
| `input` | enum num | `-inf, -48 … 0.0` dB (2 dB steps), **default −14** | INPUT GAIN |
| `thresh` | enum num | `0.0 … 10.0` (0.1 step), **default 5** | THRESHOLD |
| `time_const` | enum num | `1 … 6`, **default 1*** | TIME CONSTANT |
| `sc_filt` | enum str | `'Off'`, `'20 Hz' … '500 Hz'` (non-uniform steps), **default Off** | SIDECHAIN FILTER |
| `bal` | enum num | `-10 … +10` (0.1), **default 0** | BAL (bias balance) |
| `dc_thr` | enum num | `0 … 10` (0.1), **default 7.5** | DC THRES. (CAL / OWR) |
| `output` | enum num | `-20 … +20` dB (0.1), **default 0** | OUTPUT |
| `mix` | enum num | `0 … 100` % (1), **default 100** (100 = wet) | MIX |
| `headroom` | enum num | `{4, 8, 12, 16, 20, 24, 28}` dB, **default 16** | HR |
| `power` | bool | `False / True`, default **True** | ON |
| `master_bypass` | bool | `False / True`, default **False** | (host bypass) |

> ***Default note:** Pedalboard reported `time_const` default **1.0** for the 660 (the 670 twin reports 5.0);
> UA's documented GUI default is **Position 5**. Set it explicitly.
>
> **Enum gotcha (the big one).** `[L] apply-vst-chain`'s `parameters` dict is **float-only** — it can't set
> the string enums (`meter`, `sc_filt`) or the bools, and snaps numerics unpredictably. **Drive this through
> `presets/vst/apply_vst_preset.py`** ([[vst-preset]]), which `setattr`s every param and snaps numeric
> targets to the nearest valid value (so `sc_filt="60 Hz"` and `time_const=4.0` land exactly).

### Drive map — `input` → level + crest + color (tc 4, thresh 5, HR 16; 20 s drum-bus excerpt, raw float, no trim)

| input (dB) | −14 | −10 | −6 | −2 | 0 |
|---|---|---|---|---|---|
| RMS dBFS | −19.6 | −17.3 | −16.0 | −15.2 | **−14.9** |
| crest | 18.0 | 17.6 | 17.7 | 18.5 | **18.9** |

Driving `input` from −14→0 (**+14 dB in**) raised RMS only **+4.7 dB** — i.e. ~9 dB got absorbed as gain
reduction — yet **crest stayed ~18** and the **low-mid energy ratio rose 0.173→0.211** (centroid 1834→1854 Hz,
HF unchanged). That is the signature: **input adds level + low-mid harmonic body, not transient clamping.**
At `input` 0 the raw render hit **+3.95 dBTP** — gain-stage with `output` / HR (the harness peak-trims to −1).

### Threshold map — `thresh` → gain reduction (input −4, tc 4)

| thresh | 2 | 4 | 6 | 8 |
|---|---|---|---|---|
| RMS dBFS | −9.7 | −13.9 | −16.0 | **−25.2** |
| crest | 18.5 | 17.8 | 18.3 | 18.9 |

**Higher `thresh` value = MORE gain reduction** (RMS drops ~15 dB from thresh 2→8). Crest stays ~18 — again,
it levels without crushing transients.

> **⚠️ Measured-vs-lore reconciliation (threshold direction).** The hardware/literature describes the
> THRESHOLD *control* the opposite way ("lower threshold = more compression; higher dial number = less" — see
> Part B). The **Pedalboard `thresh` enum evidently maps inverted to the GUI dial**: measured, **higher
> `thresh` value = more GR**. When driving via the harness, **trust the meter and this table, not the dial
> number.** Dial `thresh` to the GR you want; re-check on different-level material (threshold is relative to
> input level).

### Time Constant map — the transient/density control (input −4, thresh 5)

| time_const | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| crest | **15.4** | 16.1 | 17.0 | **18.2** | 16.7 | 15.4 |

**This is the knob that moves transients.** `tc4` (release ~5 s) is **the most open/punchy** position (crest
18.2; low-band block-crest *rose* 17.1→19.5 — kick punch kept). `tc1` (fastest, release 0.3 s) is **the
tightest/most controlled** (crest 15.4, true-peak +1.8 confirmed via `measure-loudness`). `tc5/tc6` are the
**program-dependent AUTO-release** positions (a fast first stage + a long secondary release) — denser on this
busy material (~15–17). **Pick tc4 to keep punch, tc1 to clamp, tc5/6 for breathing auto-release glue.**

### Sidechain Filter map — `sc_filt` (detector low-cut only; input −2, thresh 4, tc 4)

| sc_filt | Off | 60 Hz | 120 Hz | 250 Hz |
|---|---|---|---|---|
| RMS dBFS | −13.5 | −11.7 | −10.5 | **−8.8** |

Raising the SC filter removes low energy from the **detector** (audio low end untouched) → less kick/bass-
triggered GR → output rises **+4.7 dB by 250 Hz** and the low end punches through instead of pumping the bus.
**~60–120 Hz** is the usual setting. Values are non-uniform strings (`'60 Hz'`, `'120 Hz'`…) — the harness
snaps numeric targets to the nearest valid string.

### Headroom map — `headroom` / HR (operating-level trim; input −4, thresh 5, tc 4)

| HR (dB) | 8 | 16 | 24 |
|---|---|---|---|
| RMS dBFS | −10.3 | −15.6 | **−22.5** |
| crest | 17.8 | 18.2 | **19.9** |

HR sets how hard the model is driven. **Higher HR value = more headroom = cleaner / less GR** (HR 24 → quieter,
crest up to 19.9); **lower HR value = less headroom = hotter / more drive + GR** (HR 8 → +5 dB louder, denser).
Default 16 is neutral. Use HR to set how hard it runs without re-dialing `input`.

### Parallel MIX map — `mix` (built-in parallel; input 0, thresh 2, tc 2)

| MIX % | 100 | 75 | 50 | 25 |
|---|---|---|---|---|
| RMS dBFS | −7.4 | −9.2 | −11.4 | −14.5 |

`mix` blends the wet under the dry (100 = fully wet); as it drops, the level (and dry transients) walk back
toward source. For a true New-York smash, **crush the wet hard first** (hot input + high thresh + fast tc),
*then* blend down — that's `fc660-parallel-smash` below.

### The color signature (spectrum, full warm drum bus: source → `fc660-drum-color`)

| band ratio | low (0–) | **low-mid** | mid | high-mid | high | centroid Hz |
|---|---|---|---|---|---|---|
| source | 0.792 | 0.179 | 0.0117 | 0.0123 | 0.0047 | 1747 |
| after | 0.784 | **0.188** | 0.0125 | 0.0116 | 0.0044 | 1756 |

Energy moves **out of the sub/low and up into the low-mids (≈200–400 Hz body)** with HF essentially unchanged —
**warmth/thickness, not brightness.** That's the vari-mu "weight / larger-than-life" character, measured.

### Validated renders (real MCP meters, full warm drum bus → `projects/watercolors/mix/`)

Source: **−17.18 LUFS · crest 17.17 · true-peak −0.98 · LRA 2.44 · low-band punch 27.15.**

| preset | key settings | LUFS (Δ) | crest | TP dBTP | LRA | character |
|---|---|---|---|---|---|---|
| **fc660-drum-color** ★ | in −6 · th 6 · **tc 4** · sc 60 Hz | −16.91 (+0.27) | 16.90 | −0.99 | **1.84** | low-mids thicken (0.179→0.188), **punch held** (27.19) |
| **fc660-bus-glue** | in −8 · th 5 · **tc 5** · sc 90 Hz | −16.57 (+0.61) | 16.52 | −0.99 | 1.84 | program-dependent auto, gentle cohesion |
| **fc660-parallel-smash** | in 0 · th 8 · **tc 1** · **mix 40** · HR 12 | −15.37 (+1.81) | **15.34** | −0.98 | 2.27 | bigger/denser (low-band punch 27.15→24.9), dry blend keeps attack |

Textbook vari-mu: gentle color + leveling, crest roughly held, LRA tighter, low end thickened, true-peak safe.
A/B loudness-matched (it adds level + harmonics) — `[L] render-ab` / [[level-match]].

---

## Part B — how it works (web-research synthesis, cited)

> Compiled from manufacturer and hardware documentation plus engineering write-ups. The authoritative UAD
> source (the *Fairchild Tube Limiter Collection Manual*, help.uaudio.com) returned **HTTP 403 to automated
> fetch**, so its exact numeric tables were reconstructed/cross-checked against UA's press release, the
> MusicRadar hands-on review, and multiple hardware-manual transcriptions. This is a **modeled,
> non-deterministic tube/transformer plugin** — treat every harmonic/GR figure as plugin-version-dependent and
> verify on-rig with [[vst-verify]] before trusting it on a release.

### What it is

The **Fairchild Model 660** is a single-channel **variable-mu (vari-mu) vacuum-tube compressor-limiter**,
designed by **Rein Narma** (early 1950s) and built by the **Fairchild Recording Equipment Corporation** (Long
Island, NY); the productized 660 shipped in **1959**. Roughly **800 units** were made.

**Vari-mu = the tube *is* the gain-reduction element.** No VCA, opto, or FET — gain reduction is performed by
**remote-cutoff valves whose own gain falls as a sidechain-derived DC control voltage raises their grid bias**
toward cutoff. Because gain reduction and harmonic color come from the *same* stage, the device:

- Has an **inherently soft, program-dependent knee** — a sliding ratio of roughly **~1:1–2:1 on quiet peaks
  climbing to ~20:1 (and as a hard peak limiter ~30:1) on loud input** — set by the threshold controls, not a
  ratio knob. **Max useful GR ≈ 20 dB** (the vari-mu ceiling).
- **Colors even at 0 dB gain reduction** — the Input Gain control sits *ahead of the tubes*, so driving the
  input hits the gain-varying tube harder and adds harmonic "glow" independent of how much it's compressing.
  Many engineers run it at **1–3 dB GR purely for tone/glue**.
- Has a **very fast attack** (full limiting in ~0.1 ms) and was **the first limiter with automatic, program-
  dependent release** (Time-Constant positions 5–6).

**660 = mono, 670 = stereo.** The **660 is single-channel**; its controls match one channel of the 670, but UA
modeled them independently and they're sonically distinct (different threshold behavior, total gain, distortion
structure). The **670 is a dual-channel** unit that can run as two independent limiters, **dual-mono**, **linked
stereo (L/R)**, or in **lateral/vertical (LAT/VERT = Mid/Side)** mode — letting it compress the mono center
independently of the stereo sides. The **670 has ~20 tubes** (eight 6386 vari-mu dual-triodes) + 11
transformers; the **660 uses ~half the tube count** and has **~8 dB more available gain**. (`uaudio_fairchild_670.vst3`
adds the `agc_matrix` `L-R`/`L-V` + `sc_link`/`ctrl_link` enums — verified in the param dump.)

UA's **Fairchild Tube Limiter Collection** models the complete electronic path (tubes *and* transformers),
captured from **Ocean Way Recording's "golden-reference" hardware** (hence the DC-Threshold "OWR" mark). It
ships **UADx native** titles (the `uaudio_*.vst3` build, which renders headless here) and legacy **UAD-2 DSP**
twins (the `/Components/UAD …` build — **passthrough offline, do not use**). **670 Legacy** omits the
transformer modeling and lacks HR / Sidechain Filter / Mix.

### Controls

UA states all controls are the original hardware controls **except** the digital-only additions (**Output,
Controls Link, Sidechain Filter, Mix, Headroom**), plus a re-purposed VU meter.

| Control | Origin | What it does |
|---|---|---|
| **Input Gain** | original | Stepped attenuator **ahead of the tubes** — the primary **"amount" *and* "color"** control: more input = more GR *and* more harmonic distortion. Default −14 dB ≈ unity. |
| **Threshold** | original | Where GR begins. Hardware lore: clockwise / lower threshold = more compression, higher dial number = less. **(⚠️ measured: the Pedalboard `thresh` enum runs the *other* way — higher value = more GR; see Part A. Trust the meter.)** |
| **Time Constant (1–6)** | original | Selects a *paired* attack+release preset (table below). 1–4 fixed (fast→slow); **5–6 program-dependent auto-release.** The only time control. |
| **DC Threshold (CAL / OWR)** | original (rear-panel on the hardware) | Sets **ratio + knee width together**: CW → lower ratio / broader-softer knee. **CAL** = factory default; **OWR** = the Ocean Way unit's setting. |
| **BAL — Balance** | original | Trims the channel's **bias-current balance** (transient "thud"). Default = calibrated; **do not automate.** |
| **HR — Headroom** | UA-added | Sets the **internal operating reference level** (how hard the tubes are driven); 4–28 dB, default 16. **Higher dB value = more headroom = less GR/color; lower value = more drive = more GR + "good" distortion** (matches Part A's measured map). No "Auto"; **do not automate.** |
| **Sidechain Filter** | UA-added | Low-cut on the **detector only — does NOT filter the audio.** Stops bass/kick over-triggering GR / pumping. OFF…500 Hz. |
| **MIX** | UA-added | **Built-in parallel** dry/wet (0 = dry, 100 = wet). |
| **OUTPUT** | UA-added | Clean, uncolored makeup / level-match gain (±20 dB). |
| **Meter switch (IN / GR / OUT)** | re-purposed | **GR** = gain reduction in dB (calibrated); IN/OUT are relative, **uncalibrated.** |
| **AGC matrix + SC/Controls Link** *(670 only)* | original mod / UA | Sets the four 670 stereo modes (L-R vs Lat/Vert × linked/unlinked). **Absent on the 660.** |

### The Time Constant table

A single 6-position switch sets attack *and* release as fixed pairs (1–4) or **fixed-attack + automatic,
program-dependent release** (5–6). Below are the **UAD manual's published values**; UA explicitly notes "the
actual measured times are a bit different, but the overall trend is the same" — i.e. **nominal, ordinal
figures, not the model's literal measured times. Choose by ear (and by the Part A crest map), not by the
printed digits.**

| Pos | Attack | Release | Use |
|---|---|---|---|
| **1** | 0.2 ms | 0.3 s | Fastest release. Percussion / aggressive / parallel drums / transient control. |
| **2** | 0.2 ms | 0.8 s | Plucked strings, fast bass. |
| **3** | 0.4 ms | 2 s | Vocals, mixed program; common "glue." |
| **4** | 0.8 ms *(disputed: some sources 0.4 ms)* | 5 s | Slowest fixed release; transparent bus/glue. **Most open/punchy in Part A.** |
| **5** *(default)* | 0.2 ms *(disputed)* | auto, 2-stage: ~2 s peaks → ~10 s sustained | First auto-release position. |
| **6** | 0.4 ms *(disputed)* | auto, 3-stage: ~0.3 s peaks → ~10 s → ~25 s sustained | Most program-adaptive; "invisible glue." |

**Disputes:** the **release column is well-settled** (0.3/0.8/2/5 s; Pos 5 two-stage, Pos 6 three-stage). The
**attack column genuinely diverges** — Pos 4 (UAD/SoS 0.8 ms vs others 0.4 ms), and Pos 5↔6 attack values are
**swapped between the UAD manual and the SoS/original-manual reading**. This doc uses the **UAD-manual attack
figures** (0.2/0.2/0.4/0.8/0.2/0.4 ms) since it documents the UAD plugin; either way every attack is
sub-millisecond, and a GroupDIY RC analysis suggests the original manual's printed times are internally
inconsistent — **treat the table as relative (1 = fastest → 6 = slowest/most adaptive).**

### Technique & recipes

The Fairchild is a **glue/color/leveling stage, not a brickwall limiter** — mix *into* it; use a real limiter
for peaks. (Targets below are the classic web recipes; the validated Part-A presets translate them to this rig.)

| Goal | Time Constant | Target GR | Key knobs |
|---|---|---|---|
| Color / vibe only | 4–6 | 1–3 dB | Input up, threshold for tone, **MIX 100%** |
| Vocal sheen / leveling (mono) | 1–3 | 1–3 dB | drive Input, trim OUTPUT; opt. MIX ~80–90% |
| Parallel drum smash | 1 | 6–10 dB | Input high, more GR, **SC filter ~80–120 Hz**, **MIX ~40–50%** |
| Mix-bus glue | 5–6 | 1–3 dB | gentle GR, raise HR so it kisses peaks |
| Master glue (670, linked) | 6 | 1–2 dB | HR high, kiss the peaks |
| Bass weight (mono) | 5 | 3–6 dB | higher ratio via DC Threshold, makeup up |
| Stereo mix M/S (670) | 5–6 | 1–3 dB | **Lat/Vert**: compress LAT (mid), open VERT (side) |

**670 stereo modes** (670-only): `L-R`+Linked = **Stereo L/R** (equal GR, no image shift — the safe default
for stereo glue); `L-R`+Unlinked = **Dual-Mono** (one-sided ducking shifts the image — avoid for stereo);
`Lat/Vert` = **Mid/Side**. **The 660 has none of these — it's mono** (and runs linked dual-mono on a stereo bus
in Pedalboard).

### Pitfalls

- **It colors and adds level even at low/zero GR — always A/B at matched loudness** ([[level-match]] /
  `render-ab`). Both tube drive and OUTPUT raise apparent level; "louder" ≠ "better."
- **No ratio knob** — sculpt with Input + Threshold + Time Constant (+ DC Threshold for knee/ratio feel).
- **Input drives GR *and* color** — trade Input↑/Threshold to hold GR while dialing color.
- **Too-fast a Time Constant on bass-heavy program pumps / "sucks the life out"** — use slower positions
  (4–6) or sub-buses; engage the **Sidechain Filter (~80–120 Hz)** so the kick/bass stop over-triggering.
- **HR (lower value = hotter/more GR) and threshold (param: higher value = more GR) are the two most
  misread controls** — both confirmed in Part A; dial to the meter. Don't automate HR or BAL.
- **Plugin ≠ hardware:** Mix / Sidechain Filter / HR / Output / Link are digital-only; IN/OUT meters are
  uncalibrated; time-constant digits are nominal. **Load the `uaudio_*.vst3` native build**, not the passthrough
  legacy twin. **Every param is an enum/bool → use the preset / `state_path` harness, not the float dict.**
- **Stereo bus on the 660** — it's a mono unit; for true stereo / M-S use the **670**.
- It's a **color/glue stage, not a master** — hand off to [[master-track]] for loudness/limiting.

## Sources

- https://help.uaudio.com/hc/en-us/articles/13293388042900-Fairchild-Tube-Limiter-Collection-Manual — **UAD Fairchild Tube Limiter Collection Manual** (authoritative plugin source; 403 to automated fetch, cross-checked via snippets + the sources below)
- https://www.uaudio.com/blogs/press/fairchild-collection · https://www.uaudio.com/uad-plugins/compressors-limiters/fairchild-tube-limiter-collection.html — UA press / product
- https://www.musicradar.com/reviews/tech/universal-audio-fairchild-tube-limiter-plug-in-collection-594971 · https://www.musicradar.com/how-to/mixes-fairchild-compression — MusicRadar review + technique
- https://www.soundonsound.com/reviews/fairchild-660-670 — Sound on Sound, Fairchild 660 & 670
- https://en.wikipedia.org/wiki/Fairchild_660 · https://www.historyofrecording.com/Fairchild_660.html — Fairchild 660 history/spec
- https://www.telefunken-elektroakustik.com/product/fairchild-660/ — Telefunken 660 reissue spec
- https://vintageking.com/fairchild-660-670-compressor-limiter · https://blog.native-instruments.com/fairchild-compressor/ — overviews
- https://blog.mixanalog.com/fairchild-670-tutorial · https://penny.cool/tips-and-techniques/the-fairchild-670-compressor/ — technique deep-dives
- https://goldmidi.com/community/resources/fairchild-670-compressors-attack-and-release-times.49/ · https://justproaudio.net/fairchild-670/ — time-constant tables
- https://groupdiy.com/threads/problem-with-fairchild-660-670-original-manual-data.40623/ — manual-data dispute (RC analysis)
- https://gearspace.com/board/so-much-gear-so-little-time/661249-what-sonical-difference-between-fairchild-660-fairchild-670-a.html · https://gearspace.com/board/so-much-gear-so-little-time/157433-what-does-lat-vert-switch-670-do.html — 660-vs-670 / Lat-Vert
- Headless VST3 hosting / Pedalboard — https://spotify.github.io/pedalboard/reference/pedalboard.html
