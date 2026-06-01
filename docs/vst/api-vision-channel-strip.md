# UAD API Vision Channel Strip — field guide: tight, punchy, forward drums without harshness

How to drive the UAD/UADx **API Vision Channel Strip** (`uaudio_api_vision_channel_strip.vst3`) — the
American-console counterpart to the Neve/Studer tape sound. **Part A** is *measured on this rig* (the real
param surface + isolation numbers from our own renders); **Part B** is a *web-research synthesis* (cited).
The skill [[api-vision-channel-strip]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo and the crest that proves
> "punch." Verify with `[L] measure-loudness` / `measure-spectrum` / `measure-microdynamics` / `check-clipping`.
> Driving the input raises level *and* true-peak — re-measure after every change, A/B loudness-matched.

---

## TL;DR (the headline, measured)

1. **"Slow attack = punch" is FALSE here.** Across detector modes, **Medium (18 ms) attack maximized crest**
   (FB/Medium 31.3), **Slow (75 ms) gave the *least*** (FB 28.6 / FF 27.9) — opposite of the textbook. The
   comp adds punch at every setting (all ≫ dry 25.0), but the attack knob is **non-monotonic and
   topology/material-dependent — measure crest, don't assume.**
2. **The strip is clean at unity — color lives in the modules.** All modules off ≈ no change (centroid
   4266→4130, crest +0.4). The "API color" comes from driving the **212L** and engaging the EQ/comp, not an
   always-on saturation.
3. **Keep the 550 top flat for un-harsh punch.** In our shootout, EQ boosts at 5 k/10 k pushed centroid
   +535/+714 (the same hi-mid harshness the Neve added); the winner used **low thump + de-box + NO top
   boost** (centroid +244, tilt stayed warm). API forwardness lives at 2–5 kHz — and proportional-Q makes a
   big boost there auto-narrow into a sharp peak.
4. **Punch comes from the comp envelope, not EQ.** 215 HPF tightens, 225 comp (Medium attack, 3–6 dB GR)
   punches, 550 adds weight + de-box. Dry is from the source.

---

# Part A — measured on this rig

Probe: `uaudio_api_vision_channel_strip.vst3` via Pedalboard, processing
`projects/drums-kit/mix/bus_70s_balanced.wav` (60 s dry, measured-balanced drum bus) at +6 dB input gain,
peak-normalized before measuring so only **spectral shape / crest** is compared.

### The real parameter surface (Pedalboard-exposed — authoritative)

Six API modules in series. Default flow: **212 input → 215 filters → 235 gate → 225 comp → 550/560 EQ → out.**
Every module has an `_on` switch (**all off by default** → near-passthrough).

| Module / param | Values *(default)* | Role |
|---|---|---|
| **212 input** `input_select` | `Line` · `Mic` *(Line)* | input stage |
| `line_gain` | 0 … 12 dB *(0)* | **Line drive** into the 2520/transformers (color) |
| `mic_gain` | 30 … 65 dB *(40.5)* | Mic drive (Unison preamp) |
| `pad` / `phase` | bool / `Normal`·`Inverted` | −20 dB pad / polarity |
| `cut_filter` | `Off` · `50 Hz` *(Off)* | quick LF cut |
| **215 filter** `215_hp_filter` | 12 … 596 Hz *(12)* | **high-pass corner** (tighten sub; 12 = off) |
| `215_lp_filter` | 643 Hz … 40.8 k *(40.8 k)* | low-pass corner (40.8 k = off) |
| `215_dyn_sc` / `215_on` | bool | route 215 to the **dynamics detector** / engage |
| **235 gate** `235_thresh` | 35 … −47 *(−47)* | gate/expander threshold |
| `235_depth` | 0 … 80 dB *(80)* | attenuation depth (non-linear) |
| `235_attack` | `Normal` (25 ms) · `Fast` (100 µs) | gate attack |
| `235_release` | 50 ms … 3.00 s *(0.50 s)* | gate release |
| `235_r_h` / `235_g_e` / `235_on` | `Release`·`Hold` / `Gate`·`Expand` / bool | hold (80s gated drums) / mode / engage |
| **225 comp** `225_thresh` | 13 … −18 *(13)* | threshold (lower = more GR) |
| `225_ratio` | 1.0 … `Limit` *(4.0)* | ratio |
| `225_attack` | `Fast` (2 ms) · `Medium` (18 ms) · `Slow` (75 ms) *(Medium)* | **attack (see crest map below)** |
| `225_release` | 50 ms … 3.00 s *(0.50 s)* | release |
| `225_knee` / `225_type` / `225_on` | `Soft`·`Hard` / `Old (FB)`·`New (FF)` / bool | knee / **feedback vs feedforward** / engage |
| **550 EQ** (4-band, proportional-Q, gain ±12 in **2/4/6/9/12** steps) | | **no Q knob — gain IS the Q** |
| `550_lf_freq` / `_gain` / `_filter` | {30,40,50,100,200,300,400} / ±12 / `Shelf`·`Peak` | low band |
| `550_lmf_freq` / `_gain` | {75,150,180,240,500,700,1000} / ±12 | low-mid (bell only) |
| `550_hmf_freq` / `_gain` | {800,1500,3000,5000,8000,10000,12500} / ±12 | hi-mid (bell only) |
| `550_hf_freq` / `_gain` / `_filter` | {2500,5000,7000,10000,12500,15000,20000} / ±12 / `Shelf`·`Peak` | high band |
| **560 graphic** `560_31hz` … `560_16khz` | ±12 each | 10-band graphic (alt to 550; `eq_type`) |
| **routing** `eq_type` / `eq_on` | `550L`·`560L` / bool | which EQ / engage |
| `eq_predyn` / `eq_dyn_sc` / `sc_link` | bool | EQ **before** dynamics / EQ→detector / link L-R detector |
| `level` / `power` / `master_bypass` | −∞…+9 dB / bool / bool | output |

> **5 kHz lives in BOTH `550_hmf` and `550_hf`** — boosting it in both double-stacks the harsh zone. The
> 215 HP/LP labels are swapped in some reviews; identify by range (12–596 Hz = high-pass).

### Console color at unity (all modules off)

| | crest | tilt | centroid |
|---|---|---|---|
| dry (no plugin) | 25.0 | −2.69 | 4266 |
| strip, all modules off | 25.4 | −2.68 | 4130 |

**Near-transparent at unity** — confirms UA's "low settings benign." The character is opt-in (drive the
212, engage the modules). API's color is **2nd-order (even) harmonic** + transformer push — *not* tape's odd/3rd.

### 225 comp: attack × detector-type → crest (the punch map)

Comp-only, thresh −10, 4:1, release 0.10 s, HPF 50, peak-normalized. **Crest = punch proxy; dry = 25.0.**

| `225_type` | Fast (2 ms) | Medium (18 ms) | Slow (75 ms) |
|---|---|---|---|
| **Old (FB)** | 29.7 | **31.3** | 28.6 |
| **New (FF)** | 29.9 | 30.0 | 27.9 |

Every cell ≫ dry → the comp **is** the punch. But **Medium attack wins, Slow loses** — the "slow attack
passes transients" rule did not hold on this material in either mode. **Always measure crest vs attack.**

### 550-EQ shootout on the dry bus (which is tight/dry/punchy without harshness?)

215 HPF 50 + 225 comp (Slow, −10, 4:1, FB) + 550 EQ, width 0.92, peak-normalized:

| variant | crest | tilt | centroid | corr | read |
|---|---|---|---|---|---|
| dry balanced | 25.0 | −2.69 | 4266 | 0.962 | source |
| v1 eq-forward (LF+4, HMF+2@5k, HF+2@10k) | 26.5 | −2.17 | 4801 (+535) | 0.971 | **bright/harsh** |
| **v2 comp-punch (LF+3, LMF−2, flat top)** | **28.1** | −2.49 | **4510 (+244)** | **0.975** | **winner** |
| v3 balanced (LF+3, HMF+1.5@5k, HF+1.5@12.5k) | 27.9 | −2.00 | 4980 (+714) | brightest |

**v2 won all three axes** — punchiest (crest), tightest (corr), least harsh (smallest centroid rise, warm
tilt). The top-boosting variants re-created the Neve's hi-mid harshness. → preset `tight-70s-api.json`.

> Note: v2 uses **Slow** attack (calmest); by the crest map above, **Medium** attack would be punchier
> (~31 comp-only) but more aggressive. Try it if you want more slam — and re-measure.

### Presets (`presets/vst/`)

- `tight-70s-api.json` — the v2 winner: 215 HPF 50, 225 (−10, 4:1, Slow, 0.10 s, FB), 550 LF +3 @100 peak +
  LMF −2 @500, **flat top**, width 0.92. Tight/dry/punchy, neutral top.

---

# Part B — how the console works (web-research synthesis, cited)

## 1. What it is / the "API sound"

The UAD **API Vision Channel Strip** models the channel modules of the modern **API Vision** console
(introduced ~2003, all built on the 2520 op-amp); the *circuits* descend from API's 1970s all-discrete desks
(chiefly the **2488** "LA sound" console on much of '70s American rock). Six modules in series: **212L**
preamp, **215L** sweep filters, **235L** gate/expander, **225L** compressor/limiter, and a selectable
**550L** 4-band parametric *or* **560L** 10-band graphic EQ (UA manual; SoS).

- **2520 discrete op-amp** — 9-transistor, fully discrete (not an IC), in every API console since 1968 (Saul
  Walker). >110 dB open-loop gain, ~40 kHz bandwidth, high output drive (>7.75 V RMS into 75 Ω) → transients
  clip *later* than IC op-amps = API's fast-transient handling (2520 datasheet, 1972).
- **Color = low-order distortion.** Rated 0.2% THD; predominantly **2nd-order** harmonic — a measurable,
  deliberate signature.
- **Transformers** — the 2520 drives API I/O transformers; UA modeled "their saturation behaviour when
  pushed hard." This thickens drums/bass with level.
- **Proportional-Q EQ** (Walker, 1969) — bandwidth narrows automatically as boost/cut increases; **no Q knob**.
- **THRUST** — API's equal-energy-per-octave sidechain — is on the **2500 bus comp, NOT the 225L strip comp**.

**API vs Neve vs SSL:** API = **fast / punchy / forward / aggressive** (sharp transients, exposed mids, low
end stays defined under compression — the US-rock/drum console). Neve = warmer/slower/more saturated. SSL =
cleaner/clinical (the bus-comp "glue").

> **Lineage caveat:** modern Vision module set, vintage circuit roots — don't call it a 1970s console. Many
> "API records" used custom DeMedio/Heider desks (API cards + Jensen transformers), not stock API.

## 2. The modules & signal flow

```
212L preamp → 215L filters → 235L gate → 225L compressor → 550L / 560L EQ → out
```

So by default **dynamics process the un-EQ'd signal**, gate is **before** comp, filter is first.

- **212L preamp** — 2520 + transformers. Line/Mic, gain (Mic 30–65 dB), 20 dB pad, polarity. The
  **weight/attitude** drive (clean → growly → clipping), not a tone control.
- **215L filters** (passive, gentle slopes) — **HP 12–596 Hz**, **LP 643 Hz–40.8 kHz** (defaults = off). A
  contour tool, not brick-wall. Has its own **SC** button.
- **235L gate/expander** — gate or 1:2 expand; threshold, **Depth 0…−80 dB** (non-linear), Attack Normal
  25 ms / Fast 100 µs, Release 50 ms–3 s, **Release/Hold** for 80s gated drums.
- **225L comp/limiter** — Ratio 1:1…∞ (def 4:1); Attack **Fast 2 ms / Medium 18 ms / Slow 75 ms** (def
  Medium); Release variable (def 0.5 s); Knee **Soft/Hard**; **Type Old (feedback) / New (feed-forward)**.
- **550L EQ** — 4-band parametric (=550B), proportional-Q, ±12 dB; LF & HF bell↔shelf; LMF & HMF bell only.
- **560L EQ** — 10-band graphic (alt via EQ Type), proportional-Q, ±12 dB/octave band.

**Routing:** **PREDYN** moves EQ before the dynamics (EQ *into* the comp). **DYN SC** pulls the 215/EQ out of
the **audio** path and into the **detector** (frequency-conscious comp/gate; the audio passes flat). **SC
Link** ties L/R detectors — **use on any stereo drum bus.**

## 3. The key levers (per drum-shaping module)

**215L HPF (12 dB/oct):** strips sub/rumble before gate+comp. Bus ~30–45 Hz (set a touch higher than a
24 dB/oct DAW filter for the same tighten); snare top ~80–120 Hz; hat/OH ~200–400 Hz. *Harsh/wrong:*
over-cutting thins the kick, and can starve the gate detector of the kick thump — set HPF first, re-check the
gate opens.

**225L comp:** the engine of API punch. *Punchy/tight:* **New (FF)** for clean modern control or **Old (FB)**
for vintage glue; ratio 3:1–4:1; Knee Hard for slam; Release ~0.1–0.2 s; target **3–6 dB GR**. Attack is a
3-step switch — *measure crest across the three* (Part A: Medium often beats Slow). *Harsh/dull:* Hard knee +
Fast attack + high ratio clamps the transient → duller, not punchier; "more GR ≠ more punch." No THRUST here
(use 215 SC + sidechain HPF to stop kick over-triggering).

**550L EQ (proportional-Q):** **gain is your Q.** *Punchy:* kick +4–6 @ 50–100, de-box −3/−4 @ 400, beater
click +6–8 @ 5–7 k (big boost auto-narrows to a focused click); snare body +2–3 @ 200, crack +2–4 @ 1.5–5 k,
air shelf @ 12.5 k. **Small moves (2–4 dB) broad/musical; big (9–12) surgical.** *Harsh:* **2–5 kHz is where
snap AND harshness live** — a 9–12 dB boost there auto-narrows into a brittle peak; 5 kHz is in **both** HMF
and HF (don't double-stack).

**560L graphic:** broad whole-spectrum shaping (31 Hz–16 kHz octaves, ±12). *Punchy:* pull 250/500 down a few
dB to de-clutter; nudge 8 k/16 k for air; small 63 Hz lift + 250 dip = gentle smile. *Wrong:* not for
surgical notches (use the 550); stacked boosts add level fast — gain-match.

## 4. Recipes

**4a. Tight/dry/punchy drum bus:** 212 subtle drive (pad if it slams); 215 HPF ~40 Hz; 235 expander
Depth −6…−12, Fast attack, ~150–300 ms, **SC Link on**; 225 **New, Hard, 3:1–4:1, attack measured (Medium
often punchiest), ~0.1–0.2 s, 3–6 dB GR**; 560 post-comp +2–4 @ 2–4 k for aggression, small 63–125 lift, dip
250 if muddy.

**4b. Gentle bus glue:** 212 clean; 215 HPF ~30 Hz; 235 off; 225 **Old, Soft, 2:1, Medium, 0.3–0.5 s,
2–3 dB GR**; 550 small +2–4 @ 100 + HF shelf for air.

**4c. API punch WITHOUT 2–5 kHz harshness:** drive the 212 for color not loudness (back off when 2–4 k gets
brittle); get punch from the **comp envelope, not EQ**; **cut box (−3/−4 @ 400–500) instead of boosting
highs**; keep presence boosts ≤2–4 dB (proportional-Q stays wide); never boost 5 k in both HMF+HF;
sidechain-tame the kick (215 SC + HPF detector); loudness-match before judging.

## 5. Why API can sound harsh (and what to move)

1. **The 2–5 kHz presence push** — snap and harshness share this band; over-exposes resonances on toms/kick.
   *Fix:* presence boosts ≤2–4 dB; prefer a modest **cut** (auto-broad); don't stack 5 kHz.
2. **Op-amp/preamp drive** — 212 goes clean → growly → clipping; on bright transient drums this stacks edge.
   *Fix:* drive = color, not loudness; back the input off; use the 20 dB pad.
3. **550 mid bands + proportional-Q** — your *protection at small gains*, a *trap at large gains* (9–12 dB in
   2–5 k auto-narrows into a sharp peak). *Fix:* **gain is your only Q** — small for musical, big only for an
   intentional accent. Cuts in the harsh band stay broad → de-harshing with a gentle cut is forgiving.

## 6. Pitfalls & gotchas

- **No THRUST on the 225L** (it's a 2500 feature) — approximate with 215 SC + sidechain HPF.
- **No Q knob anywhere** (proportional-Q); 550 freqs/gains are **stepped** (gain 0/2/4/6/9/12; the 6→9 jump
  is large + narrowing).
- **It's the 4-band 550L (=550B)**, not the 3-band 550A; only LF/HF are bell/shelf-switchable.
- **Default flow is dynamics-BEFORE-EQ** — to EQ into the comp, engage **PREDYN**.
- **SC buttons remove the module from the AUDIO path** — if the EQ SC LED is lit you hear *no EQ on output*
  (it's steering the detector). Easy to mistake for a broken EQ.
- **Presets don't carry your level** — re-set the 235 + 225 thresholds to your track level after recall.
- **A gate fixes level/bleed, not tone**; the 215 HPF + 550 do tone.
- **Slow-attack trades level for transient** → higher true-peak, lower GR — verify with `measure-microdynamics`,
  not Gemini. And on this strip **Medium often out-punches Slow by crest** — measure.
- **Loudness-match before any A/B** — drive + boosts raise level; "better" is often just "louder."
- **Spec caveats:** 2520 slew rate is unverified secondary data; reliable = 0.2% THD, >110 dB open-loop;
  help.uaudio.com 403s direct fetch — confirm exact ms/dB against the live plugin.

## 7. Decision table

| Goal | 215 HPF | 225 (Type / Ratio / Attack / Release / GR) | 550 moves |
|---|---|---|---|
| Tight/dry/punchy bus | ~40 Hz | New / 3:1–4:1 / **measure (Med often)** / 0.1–0.2 s / 3–6 dB | de-box −4 @400; small +2–4 @100; flat top |
| Gentle glue | ~30 Hz | Old / 2:1 / Medium / 0.3–0.5 s / 2–3 dB | +2–4 @100; HF shelf air |
| Max slam | ~40 Hz | New / 4:1 / measure / 0.1 s / Hard / 3–6 dB | +6–8 @7 k click (let Q narrow) |
| Punch kick | ~30–45 Hz | New / 4:1 / measure / 0.1–0.2 s / 3–6 dB | +4–6 @50–100, **−4 @400**, +6–8 @5–7 k |
| Snare crack | 80–120 Hz | slow-ish + fast release, ~4:1, modest GR | +2–3 @200, +2–4 @1.5–5 k, shelf @12.5 k |
| OH de-clutter | 200–400 Hz | light | **560**: pull 250/500 down a few dB |
| De-harsh | — | back off 212 drive | **modest cut** 2.5–5 k; boosts ≤4 dB; don't stack 5 k |
| Stop kick pumping bus | 215 **SC** + HPF detector | New / 4:1 / Medium / 0.1–0.2 s / 3–6 dB | (audio EQ unaffected by SC) |
| 80s gated snare | per-mic HPF | gate not comp | 235 **Hold**, Fast (100 µs), deep Depth |
| EQ into comp | first | (any) | engage **PREDYN** |

> Pure-DSP approximation (no VST): emulate THRUST by sidechain-shaping before `[L] compress-loop`; push
> 2nd-order color with `[L] saturate-loop`; place 550-grid bells/shelves with `[L] apply-eq`; verify punch
> (crest/PLR) with `[L] measure-microdynamics`.

---

## Sources

UA API Vision Channel Strip manual + product page · Sound on Sound (UA API Vision review; "What does the API
2500 Thrust do?") · API 2520 datasheet (1972) · apiaudio.com (550A/2500) · Waves "API 550 or 560" · Sweetwater
console history · Gearspace (API for drums; NAB vs CCIR) · Nail The Mix / Penny Cool / iZotope / Production
Expert. Plus **our own isolation/sweep/shootout measurements** (Part A) on `uaudio_api_vision_channel_strip.vst3`.
