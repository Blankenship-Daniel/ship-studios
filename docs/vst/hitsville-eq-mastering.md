# UADx Hitsville EQ Mastering — field guide: the Motown disk-mastering / M-S EQ (measured)

How to drive the **UADx Hitsville EQ Mastering** (`/Library/Audio/Plug-Ins/VST3/uaudio_hitsville_eq_mastering.vst3`)
— Universal Audio's model of the **custom Motown / Hitsville U.S.A. disk-mastering equalizer**, a **passive,
inductor-based (LC), proportional-Q graphic EQ** with **7 fixed bands per channel**, a half-speed frequency
set, the fixed **"Motown Filters,"** and — UA's own addition — a **Mid/Side mode**. It's a **broad, musical,
"colour" mastering EQ**, the opposite of a surgical parametric. **Part A** is *measured on this rig* (the real
Pedalboard param surface + our isolation/curve/M-S render numbers); **Part B** is a *web-research synthesis*
(cited). The skill [[hitsville-eq-mastering]] is the measured workflow over this doc.

> **It's the MASTERING version (stereo / M-S / half-speed), not the channel "Hitsville EQ."** The collection
> ships two EQs + a reverb. Three installed builds carry "Hitsville EQ": `uaudio_hitsville_eq.vst3` (the
> Studio/channel 7-band EQ → [[hitsville-eq]]), **`uaudio_hitsville_eq_mastering.vst3` (this one — dual LEFT/MID + RIGHT/SIDE
> sections, the FILTER + MID/SIDE + 1/2-SPEED switches)**, and `uaudio_hitsville_chambers.vst3` (the reverb).
> Point the skill at the **`_mastering`** `.vst3`.

> **Repo caveat:** Gemini hears ~16 kbps mono → **meters own** loudness/peak/stereo. This is a stereo/M-S EQ,
> so the **stereo meter matters most**: verify with `[L] measure-spectrum` (tilt / band ratios / centroid),
> `[L] measure-stereo` (correlation / per-band width / mono-sum loss) and `[L] measure-loudness`.

---

## TL;DR (the headline, measured)

1. **It renders headless ✓ — but only the UADx `uaudio_*.vst3` build.** A real band boost moved the signal
   (max-abs Δ 0.445 vs flat); the `UAD Hitsville EQ Mastering.component` twin passes audio through. ⚠️ Our
   generic `probe_plugin.py` auto-reports it "PASSTHROUGH" because it pushes the first param it finds
   (`l1_gain`) to its **minimum (0 = flat = no-op)** — a false negative. Confirm with a real **boost**, not the
   auto-probe.
2. **The 0–8 knob is NOT dB, and boost ≠ cut.** Measured, a single band at amount **8** gives only **≈ +5 dB
   (Peak)** / **≈ −3 dB (Dip)** — gentle and **asymmetric**, ~**0.6 dB per step**, and **bands interact**
   (passive). Dial broad, stack bands; don't expect "+8 = +8 dB."
3. **`speed` is INERT headless — set the per-band `lN_freq` instead.** Flipping the global `left_speed`/
   `right_speed` to `'1/2'` did **not** move a band's center (848 Hz stayed 848); setting `l4_freq=400.0`
   **did** move it (measured center ≈ 414 Hz — the nominal enum value lands on the nearest band of the set,
   not exactly 400). The seven `lN_freq` two-value enums are the real frequency control.
4. **All 53 params are enums, and the string ones don't set via the float dict.** `apply-vst-chain` can pass the
   float-valued enums (`lN_gain`, `lN_freq`, `left/right_gain`) but **silently drops** the strings (`lN_dip_pk`,
   `ctrl_link`, `filter`, `mid_side`, `*_byp`, `*_speed`). **Use the [[vst-preset]] harness** for any real patch.
5. **M-S is the standout** — and it's a *spectral* width tool: our M-S preset pushed **low-band width −30 → −33 dB
   (tighter, mono-er bass)** while widening **high-mid −17.4 → −14.3** and **high −19.8 → −15.3 dB**, correlation
   still safe (0.981 → 0.986). **M-S needs `ctrl_link='Unlink'`.**
6. **FILTER = the fixed "Motown Filters"** (4-position): HP ≈ **70 Hz**, LP ≈ **15 kHz**, Band-Pass = both. No
   sweepable corner exists; it applies to **both channels** regardless of LINK. Measured: −5 dB @63 / −34 @31
   (HP), −30 dB @16k (LP).

---

# Part A — measured on this rig

Probe: `uaudio_hitsville_eq_mastering.vst3` via Pedalboard. **Band ID / curve / filter** on reproducible pink
noise (−12 dBFS RMS, FFT delta vs flat). **M-S / character / preset validation** on
`projects/watercolors/mix/bus_punchy_pre.wav` (the same 60 s dry, measured-balanced drum bus the other
per-plugin docs use), peak-normalized to −1 dBFS so only **spectral shape / stereo width** is compared.
Headline numbers are the repo meters (`[L] measure-spectrum` / `measure-stereo` / `measure-loudness`). Probe
scripts: `/tmp/hitsville_probe*.py` (provenance); param-dump: `presets/vst/dump_params.py`.

### The real parameter surface (Pedalboard-exposed — authoritative; **53 params, EVERY one an enum**)

GUI layout: two stacked sections — **top = LEFT/MID (`l*`)**, **bottom = RIGHT/SIDE (`r*`)** — plus a global
footer. Each section = 7 EQ bands + a section bypass + a 1/2-speed switch + an output trim. The label of each
section ("LEFT" vs "MID", "RIGHT" vs "SIDE") tracks the `mid_side` mode.

| GUI control | Param(s) | Values *(default)* | Role |
|---|---|---|---|
| **Per band ×7** (top) | `l1`…`l7` `_gain` | `0.0 … 8.0` (9 steps) *(0)* | **amount** (Dip/Peak direction; **measured ≈ +5/−3 dB at 8**) |
| | `l1`…`l7` `_dip_pk` | **`Dip` · `Peak`** | **Dip = cut, Peak = boost** at the band freq |
| | `l1`…`l7` `_freq` | two-value enum (see table) | **band center** — the REAL freq control (`speed` is inert) |
| LEFT/MID bypass | `left_byp` | `Out` · `In` *(In)* | section engage (`Out` = EQ bypassed, still "colored bypass") |
| LEFT/MID 1/2 speed | `left_speed` | `1/2` · `Normal` *(Normal)* | GUI macro — **does NOT move the render** (set `lN_freq`) |
| LEFT/MID trim | `left_gain` | `−8 … +8` *(0)* | per-channel output makeup |
| **Per band ×7** (bottom) | `r1`…`r7` `_gain`/`_dip_pk`/`_freq` | as above | RIGHT/SIDE bands |
| RIGHT/SIDE bypass/speed/trim | `right_byp` / `right_speed` / `right_gain` | as above | RIGHT/SIDE section |
| CONTROLS LINK | `ctrl_link` | `Unlink` · `Link` *(Link)* | **Link mirrors the top channel onto both** (measured) |
| FILTER | `filter` | `Off` · `High Pass` · `Low Pass` · `Band Pass` *(Off)* | the **fixed Motown Filters** (70 Hz / 15 kHz) |
| MID/SIDE | `mid_side` | `L-R` · `M-S` *(L-R)* | processing mode (**M-S needs Unlink**) |
| POWER | `power` | `True` · `False` *(True)* | plugin on/off (true null) |
| (header IN/bypass) | `master_bypass` | `False` · `True` *(False)* | full bypass (true null) |

**Band frequencies (the two-value `lN_freq`/`rN_freq` enum):**

| Band | Role | NORMAL (Hz) | 1/2 SPEED (Hz) | Measured center @ +8 (Normal) | Shape (measured) |
|---|---|---|---|---|---|
| 1 | Sub-bass | **50** | 25 | 50.5 | broad **bell** (peaks at 50, falls off below) |
| 2 | Bass | **130** | 65 | 133 | broad bell |
| 3 | Lo-mid | **320** | 160 | 332 | broad bell |
| 4 | Mid | **800** | 400 | 848 | broad bell (~2-octave wide) |
| 5 | Hi-mid | **2000** | 1000 | 2126 | broad bell |
| 6 | Treble | **5000** | 2500 | 5130 | broad bell |
| 7 | Brilliance | **12500** | 6250 | 13393 | **high shelf / air** (still +4 dB @16k) |

> Bands are **proportional-Q** (auto-wide at gentle settings, narrower at extremes) and **overlap / interact** —
> the passive-LC reality. The lowest band is a focused **bell**, not an infinite low shelf; the top band acts as
> an **air shelf**. Half-speed band 1 (`l1_freq=25.0`) centers ≈ **25 Hz** (deep sub bump).

### ⚠ The headless gotchas (measured — read before scripting)

1. **`apply-vst-chain`'s float dict can't set the string enums.** It passes `lN_gain` / `lN_freq` / `*_gain`
   (floats) but **silently drops** `lN_dip_pk`, `ctrl_link`, `filter`, `mid_side`, `*_byp`, `*_speed` — so a
   "Dip" you asked for never engages and you get a boost (or nothing). Build with the **[[vst-preset]] harness**
   (`presets/vst/apply_vst_preset.py`, `setattr` handles every enum). `parameters_set` is **not** proof it took.
2. **The 1/2-SPEED switch is inert in a headless render.** `left_speed='1/2'` left band 4 at 848 Hz; only
   `l4_freq=400.0` moved it (→ 414 Hz). **Set the per-band `lN_freq` directly** to pick normal vs half — don't
   touch `*_speed`.
3. **The generic render-probe lies here.** `probe_plugin.py` picks `l1_gain` and pushes it to its **minimum (0)**
   = a no-op, so it prints "PASSTHROUGH ✗". The plugin **does** render — verify with a real boost / a `_dip_pk`
   flip, not the auto-probe.
4. **LINK mirrors; M-S needs Unlink.** With `ctrl_link='Link'`, setting only the LEFT bands changed **both**
   channels (low +6.85 dB on L *and* R). For a reproducible patch use **`Unlink` + set both sections explicitly**;
   M-S only works **unlinked** (and the GUI "Auto Solo" centering doesn't apply offline — dial by the meter).

### Amount knob → realized gain (band 5 @ 2 kHz, Peak; FFT-Δ vs flat)

| amount | 1 | 2 | 4 | 6 | 8 |
|---|---|---|---|---|---|
| Peak (+dB) | +0.52 | +1.13 | +2.40 | +3.72 | **+4.95** |

≈ **0.6 dB/step**, maxing ≈ **+5 dB** at 8. Across all 7 bands, **Peak @8 ≈ +4.5…+5.0 dB**, **Dip @8 ≈ −3.0…−3.1 dB**
— the boost/cut **asymmetry is universal** (a passive-EQ signature). The "8" on the knob is an *amount step*, not dB.

### Curve shapes (amount 8, FFT-Δ dB vs flat — proves bell vs shelf)

| | below | center | above |
|---|---|---|---|
| **Band 1 @50** | +0.9 @20 · +2.5 @31 | **+4.7 @50** | +3.6 @63 · +2.3 @80 · +0.8 @125 → **bell** |
| **Band 4 @800** | +2.1 @500 · +3.4 @630 | **+4.6 @800** | +4.2 @1k · +2.9 @1.25k · +1.0 @2k → **~2-oct bell** |
| **Band 7 @12.5k** | +1.4 @6.3k · +2.3 @8k | **+4.7 @12.5k** | **+4.1 @16k · +2.8 @20k** → **air shelf** |
| Band 1 @25 (½-speed) | +3.9 @20 | **+4.8 @25** | +4.0 @31 · +2.5 @40 → deep sub bell |

### Filter = the fixed "Motown Filters" (FFT-Δ dB vs flat; applies to BOTH channels)

| mode | @31 | @63 | @125 | @4k | @8k | @16k | reading |
|---|---|---|---|---|---|---|---|
| **High Pass** | −34 | −5.2 | +0.3 | 0 | 0 | 0 | HPF, corner ≈ **70 Hz**, steep |
| **Low Pass** | 0 | 0 | 0 | −0.3 | ~0 | **−30** | LPF, corner ≈ **14–15 kHz** |
| **Band Pass** | −34 | −5.2 | +0.3 | −0.3 | ~0 | −34 | = HP + LP together |

No sweepable filter frequency is exposed — the corners are the fixed 70 Hz / 15 kHz Motown Filters.

### Character at unity & the M-S behaviour (watercolors drum bus, peak-normalized −1)

| state | crest (dB) | note |
|---|---|---|
| dry | 21.57 | source |
| EQ engaged, all bands 0 | 21.67 | **near-transparent** (Δcrest +0.10; residual −31 dBFS — a faint passive imprint, not a null) |
| `master_bypass=True` / `power=False` | 21.57 | **true null** (bit-identical to dry) |

**Stereo / M-S** — `hitsville-ms-master-width` vs dry (`[L] measure-stereo`):

| metric | dry | M-S preset | read |
|---|---|---|---|
| correlation | 0.981 | **0.986** | still mono-safe |
| width **low** | −30.0 | **−33.1** | bass tighter / more mono |
| width **high-mid** | −17.4 | **−14.3** | top wider |
| width **high** | −19.8 | **−15.3** | air wider |
| worst mono-sum loss | 0.63 | 0.80 dB | acceptable |

**Tonal presets** — `[L] measure-spectrum` vs dry (band ratios / centroid):

| preset | low | low-mid | high | centroid (Hz) | read |
|---|---|---|---|---|---|
| dry | 0.589 | 0.327 | 0.0130 | 2223 | source |
| **motown-master** | **0.722** | 0.207 | **0.0167** | 2388 | fuller lows + more air, still musical (crest 21.6→19.8 = low sustain densifies) |
| **drum-bus-weight** | 0.627 | 0.301 | 0.0159 | 2350 | low body + de-honk @800 + sheen |

### Presets (`presets/vst/`)

- **`hitsville-motown-master.json`** — L/R "Motown" master curve: 50 Pk3 + 130 Pk2 + 320 Dip2 + 5k Pk2 + 12.5k Pk2.
- **`hitsville-ms-master-width.json`** — M-S: tighten lows (Mid 50 Pk2 / Side 130 Dip2), widen top (Side 5k Pk3 / 12.5k Pk3) + Mid 320 Dip2 / 2k Pk1.
- **`hitsville-drum-bus-weight.json`** — L/R drum sweetening: 130 Pk3 + 800 Dip2 + 5k Pk2 + 12.5k Pk1.

Apply with `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in> <out>`.

---

# Part B — how the EQ / plugin works (web-research synthesis, cited)

## 1. What it is — the Motown / Hitsville mastering EQ

Universal Audio's **Hitsville EQ Collection** (announced **May 2022**, UAD software v10.1; ~**$299**) is the
**only EQ officially licensed by Hitsville U.S.A. / the Motown Museum.** It models the **custom passive EQs built
in-house by Motown's chief technician Mike McLean** (joined Motown Jan 1961). McLean based the design on the
**Langevin EQ 252A** passive graphic EQ (Arthur C. Davis), rebuilt with better switching and a **dual
full-/half-speed center-frequency set**. The collection is two EQs + a reverb: the **Hitsville EQ** (Studio/channel,
7-band, with onboard makeup gain and a 3-way IN/OUT/OFF → [[hitsville-eq]]) and the **Hitsville Mastering EQ** (this one — stereo,
**Mid/Side**, half-speed, the Motown Filters). UA modeled what it believes is the **only still-functioning
Hitsville Mastering EQ** (only ~6 were ever built; ~46 of the channel version), with vintage units supplied by
engineer **Michael Brauer** and the Motown Museum. It shaped "the Motown Sound" — Supremes, Stevie Wonder,
Jackson 5, Marvin Gaye.

The originals are **passive LC designs** (UTC/Freed transformers, makeup amps, real **band interaction**, internal
clipped-filter distortion — all modeled). The Mastering EQ fed Motown's disk-cutting chain (a **Neumann AM131
lathe** + Studer C37 tape). **Mid/Side is the one feature NOT on the hardware** — UA's addition (the original was
L/R only).

> **Two displays, not serial numbers.** The "130 / 131" panels read "Motown Engineering Dept." for vibe; they are
> **not** unit serials — "130" echoes the **130 Hz Bass band** and **AM131** was the Neumann cutting lathe. Don't
> cite "#130/#131 units."

## 2. The EQ — 7 fixed bands, Dip/Peak, half-speed

- **7 fixed bands per channel** at **50 / 130 / 320 / 800 / 2000 / 5000 / 12500 Hz** (NORMAL). You **commit to a
  band and turn its knob** — frequencies are **not** sweepable (it's a graphic EQ).
- **DIP/PEAK** per band: **Dip = cut, Peak = boost** at that frequency. The gain knob is a **stepped rotary**;
  UA documents the range as **±8 dB in 1 dB steps** (Dip up to −8, Peak up to +8). *Our measurement of the
  realized single-band curve peak is gentler/asymmetric — see Part A; the knob value is an amount step, the
  audible curve depends on band interaction + proportional Q.*
- **Bands overlap (~1.5-octave) with proportional Q** → **broad, musical curves, not surgical notches.** This is
  a **passive inductor graphic EQ** in the lineage of the Langevin 252A — **not a Pultec** (no continuously
  variable freq, no simultaneous boost+cut trick).
- **1/2 SPEED** halves every band's center (50→25, 320→160, 800→400, 2000→1000 …), recreating **half-speed disk
  mastering**: at Motown the engineer EQ'd at speed, then ran tape + lathe + EQ all at half speed to cut hotter,
  punchier lacquers. In the plugin it's a tonal choice — pick it for **lower band centers** (deeper bass control,
  a different curve family). It can be toggled per band by clicking a band's frequency label; the global switch
  resets the per-band marks. *(See the Part A gotcha: in a headless render, set `lN_freq` — the global switch is
  inert.)*

## 3. Channel controls — trims, bypass, LINK, MID/SIDE

- **Channel Gain** (top "Left/Mid", bottom "Right/Side"): **±8 dB output makeup per channel.**
- **IN/OUT** per channel: IN = EQ engaged; **OUT = EQ bypassed but audio still runs through the transformer/amp
  model** ("colored bypass"). (The Mastering EQ has only IN/OUT; the channel Hitsville adds OFF.)
- **CONTROLS LINK**: links/unlinks the two channels; **unlinked→linked makes the top channel win** (mirrors onto
  both — Part A confirms).
- **MID/SIDE vs LEFT/RIGHT**: a global mode switch turning the channel pair into **L/R** (top = left, bottom =
  right) or **M/S** (top = mid/center, bottom = side). **M/S is effective only when unlinked**; an **Auto Solo**
  momentarily centers/solos the channel you're tweaking in the GUI. M/S on a master = the plugin's headline move:
  **warm mono bass in the Mid, lush wide highs in the Side.**

## 4. FILTER, POWER

- **FILTER** ("Motown Filters", 4-position): Off / **70 Hz high-pass** / **15 kHz low-pass** / **70 Hz + 15 kHz
  band-pass.** Steep elliptical filters (off the cutting lathe) that "tighten subgroups in a pleasing way."
  **Applies to both channels** regardless of LINK. Part A confirms ≈70 Hz / ≈14–15 kHz corners.
- **POWER**: plug-in bypass / A-B (the header IN button is equivalent). Lower CPU when off.

## 5. Concrete usage moves (reviewer/manual; the half-speed points are the deeper neighbours)

- **Motown low end (Tozzoli's "low cream"):** Peak **65 Hz** (or 50/130 at full speed) with a touch of Dip at
  **25 Hz** → weight on the master without flubbiness.
- **Tape-smooth top:** add **12.5 kHz** on the L/R bus *and* engage the **15 kHz LP** filter to mimic tape's
  rolled-off, smooth high end.
- **Forward (e.g. guitars/leads):** **Dip 5 kHz**, nudge **2 kHz** up, add a few dB Channel Gain — forward, not harsh.
- **Warmth + air together:** boost **12.5 kHz** (air) and **130 Hz** (warmth).
- **M/S 2-bus glue / width:** the standout — boost kick/snare fundamental in the **Mid**, lift cymbal/tom highs in
  the **Side** to widen; keep the bass mono in the Mid. "Adds substance, grit, and width."
- **Subgroup tightening:** the steep 70 Hz / 15 kHz filters clean drum/instrument groups musically.
- **Drive it:** it "takes a surprising amount of input gain and distorts quite nicely" — push the input for
  harmonic colour; even with a section's EQ OUT, the transformer/amp model is a musical **colored bypass**.

## 6. Format / authorization

- **Two builds:** **UADx native** (CPU, macOS/Windows, **no UA hardware**) and **UAD/DSP** (Apollo / Accelerator).
  For this offline pipeline, **load the UADx `uaudio_hitsville_eq_mastering.vst3`** (renders headless — Part A);
  the **`UAD Hitsville EQ Mastering.component`** twin passes audio through unprocessed offline.
- **Formats:** VST3 / AU / AAX / VST (macOS + Windows). **AU is macOS-only** — prefer the VST3 path.
- **Auth:** UADx native is managed via an **iLok account (no dongle required).** iLok/PACE plugins are render-farm
  landmines — Part A verifies load+render *on this Mac*; **re-verify on any other machine.**

## 7. Pitfalls & gotchas

- **String enums don't set via the float dict** (`*_dip_pk`, `mid_side`, `ctrl_link`, `filter`, `*_byp`,
  `*_speed`) — use the harness; `parameters_set` ≠ "it took."
- **`*_speed` is inert headless** — set `lN_freq` to pick normal vs half-speed.
- **The auto render-probe false-flags it PASSTHROUGH** (it nulls `l1_gain`) — verify with a real boost.
- **"8" is not 8 dB** — realized ≈ +5/−3 dB at max, asymmetric; bands interact. Dial broad, stack bands.
- **M/S needs Unlink**; Auto-Solo is GUI-only — dial by `measure-stereo`.
- **It's an EQ, not dynamics** — adding lows lowers crest (denser), it adds no punch/glue (use [[drum-punch]] /
  a comp). Master/limit afterward in [[master-track]] — never here.
- **iLok/PACE** — re-verify load+render on any new machine.

## 8. Decision table

| Goal | Mode | Moves (band Dip/Peak amount) | Filter |
|---|---|---|---|
| Motown master tone | L-R | 50 Pk3 + 130 Pk2 + 320 Dip2 + 5k Pk2 + 12.5k Pk2 | Off (or HP for tight sub) |
| Mono-tight lows + wide air (master) | **M-S** | Mid: 50 Pk2 / 320 Dip2 / 2k Pk1 · Side: 130 Dip2 / 5k Pk3 / 12.5k Pk3 | Off |
| Drum-bus sweetening | L-R | 130 Pk3 + 800 Dip2 + 5k Pk2 + 12.5k Pk1 | HP (70 Hz) to tighten |
| Tape-smooth top | L-R | 12.5k Pk2–3 | **LP (15 kHz)** |
| Deep sub control | L-R | band 1 `freq=25` (½-speed) Pk/Dip 2–3 | HP |
| Subgroup tighten | L-R | (taste) | HP / LP / BP |

> **Pure-DSP approximation (no VST):** place these broad bells/shelf with `[L] apply-eq` (low Q ≈ 0.7, 50/130/
> 320/800/2k/5k bells + a 12.5k shelf, gains ≈ ±2–5 dB); do the M/S "tight lows / wide top" with `[L] adjust-stereo`
> (bass mono-maker + M/S width) ± a Side-only air shelf; the 70/15k filters with `apply-eq` HPF/LPF. Verify with
> `[L] measure-spectrum` / `measure-stereo`.

---

## Sources

Universal Audio — *Hitsville EQ Collection* product page + *Hitsville EQ / Hitsville Mastering EQ* manual
(help.uaudio.com), UA blog "The Story of the Motown / Hitsville EQ" · Motown Museum partnership press · Mix /
SOS / Production Expert / pro-audio reviews of the Hitsville EQ Collection · Acme Audio MTEQ-1 + Kazrog True 252
(independent Langevin-252A-lineage recreations) · interviews referencing Mike McLean / Motown Engineering Dept. /
the Neumann AM131 lathe. Plus **our own render-probe / param-dump / isolation / curve / M-S / preset-validation
measurements** (Part A) on `uaudio_hitsville_eq_mastering.vst3`.
