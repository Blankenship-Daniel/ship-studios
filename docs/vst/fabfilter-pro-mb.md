# FabFilter Pro-MB — field guide: 6-band multiband dynamics (comp/expand, up/down), headless

How to drive **FabFilter Pro-MB** (`/Library/Audio/Plug-Ins/VST3/FabFilter Pro-MB.vst3`) — a **6-band multiband
dynamics** processor that does **compression AND expansion, downward AND upward**, on *dynamic* (movable)
crossover bands, each with its own side-chain (Band/Free, internal/external), Mid/Side operation, and three phase
modes. It's the **band-split / dynamic-EQ** member of [[vst-compress]] / [[multiband-compress]] — the multiband
counterpart to the parametric [[fabfilter-pro-q-4]] (Pro-Q's dynamic EQ has *no* band-split) and to the broadband
glue comps [[fairchild-660]] / [[ssl-bus-compressor-2]]. **Part A** is *measured on this rig* (the real Pedalboard
param surface + our own render results); **Part B** is a *web-research synthesis, adversarially verified, cited*
(FabFilter's own docs + reviews). The skill [[fabfilter-pro-mb]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/peak/stereo/crest and the tilt/centroid/
> band-ratios that prove a move. Verify every Pro-MB move with `[L] measure-spectrum` / `measure-loudness` (+
> `measure-stereo` for M/S). A band that "sounds" engaged but shows a 0.00 spectrum delta is a no-op (range 0, or
> a disabled band).

---

## TL;DR (the headline, measured)

1. **It renders headless AND it's no-iLok** — uniquely safe here. Pro-MB loads + processes through Pedalboard
   0.9.23 (probe: pushing `output_level` moved the audio Δ 2.44; **156 params**). FabFilter uses a **simple
   license key, no iLok/PACE/UAD dongle**, so like [[fabfilter-pro-q-4]] it is a *clean* render-farm candidate
   (unlike the [[vst]] iLok/UAD landmines). Use the **VST3** path (an AU `.component` twin is
   also installed).
2. **A bare load is a TRUE passthrough — the OPPOSITE of Pro-Q.** All 6 band slots default to `Unused`; a fresh
   `load_plugin` measured **0.0000 dB** band-energy deviation vs the input. So **you do NOT flatten Pro-MB**
   (Pro-Q restores its last GUI curve and *must* be flattened — Pro-MB does not). Just `Enabled` the bands you want.
3. **RANGE is the master "amount" knob — set it NONZERO or the band is inert.** Measured: a band `Enabled`,
   `threshold=-35`, `ratio=4.00:1`, but **`range=0`** rendered **bit-for-bit identical to dry**. `band_N_range`
   (−30…+30 dB) is the *maximum gain change*; `threshold`/`ratio` only shape *how* it gets there. The #1 Pro-MB
   footgun: a fully-dialed threshold/ratio with `range=0` does **nothing**.
4. **`apply-vst-chain`'s float dict can't drive it; the standout behaviors all measure.** All 156 params are
   Pedalboard `valid_values` enums — the float dict set `band_1_range/threshold/crossover` but returned
   **`changed:false`** (the band stayed `Unused`; `band_1_state` is a *string* enum it can't set). Use the
   **[[vst-preset]]** harness. The four quadrants all render: Compression −range ducked **5 kHz by 8.5 dB** while
   leaving the **lows at 0.00 dB** (true band-split); Expansion +range **added +5.6 dB presence + 1.4 crest**
   (upward expansion = a dynamic exciter). **Meters own it** — read centroid/tilt/band-ratios/crest.

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `pedalboard.load_plugin("…/FabFilter Pro-MB.vst3")` → `name="Pro-MB"`,
`is_instrument=False`, renders (a configured band changes the audio; an all-`Unused` instance == input).
Tested with **Pedalboard 0.9.23**, input `artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav`
(the file from the GUI screenshot, `Pro-MB/4-watercolors_drums_104bpm_8bar_a`).

`list-vst-plugins {name_contains:"Pro-MB"}` returns two entries — **use the VST3**:

| Name | Path | Use |
|---|---|---|
| **FabFilter Pro-MB** | `/Library/Audio/Plug-Ins/VST3/FabFilter Pro-MB.vst3` | ✅ this one |
| FabFilter Pro-MB | `…/Components/FabFilter Pro-MB.component` | AU twin (macOS-only) |

### The real parameter surface (Pedalboard-exposed — authoritative)

**156 automatable parameters: 6 bands × 21 params + 30 globals.** Every parameter is exposed as a Pedalboard
**`valid_values` list** (a quantized grid), not a free `min/max` float. Numeric params accept a `setattr` float
and **snap to the grid**; string/bool params take the exact enum value.

**Per-band params** (`band_1_…` through `band_6_…`):

| Param | Type | Values (grid) | Control |
|---|---|---|---|
| `band_N_state` | enum | `Disabled` · `Enabled` · `Unused` | **the band slot** (default `Unused` = passthrough; set `Enabled` to process) |
| `band_N_low_crossover` | enum-num | 30 … 30000 Hz (log) | band's **lower** edge |
| `band_N_low_slope` | enum | `6.0 dB/oct` … `48.0 dB/oct` (default 24) | lower-edge filter slope |
| `band_N_high_crossover` | enum-num | 30 … 30000 Hz (default 30000) | band's **upper** edge |
| `band_N_high_slope` | enum | `6.0 dB/oct` … `48.0 dB/oct` (default 24) | upper-edge slope |
| `band_N_dynamics_mode` | enum | `Compression` · `Expansion` | which way the dynamics work |
| `band_N_threshold` | enum-num | −90 … 0 dB (default −18) | where the dynamics engage |
| **`band_N_range`** | enum-num | **−30 … +30 dB (default 0)** | **the master amount: max gain change. 0 = inert. sign sets up/down** |
| `band_N_ratio` | enum | `1.00:1` … `100.00:1` (string, default `4.00:1`) | ratio (string enum → harness only) |
| `band_N_attack` | enum-num | 0 … 100 (default 20) | attack — **a 0–100 % percentage, NOT ms** (program-/frequency-dependent; see Part B §4) |
| `band_N_release` | enum-num | 0 … 100 (default 20) | release — **a 0–100 % percentage, NOT ms** (program-/frequency-dependent) |
| `band_N_knee` | enum-num | 0 … 48 dB (default 24) | knee width (default = wide/soft) |
| `band_N_lookahead` | enum-num | 0 … 20 ms (default 1.0) | per-band lookahead (gated by global `lookahead_enabled`) |
| `band_N_level` | enum-num | −30 … +30 dB (default 0) | per-band output / make-up gain |
| `band_N_pan` | enum | `Mid: x / Side: y` grid | per-band Mid/Side pan |
| `band_N_side_chain_filtering` | enum | `Band` · `Free` | trigger from the band itself vs a free SC filter |
| `band_N_side_chain_low_frequency` | enum-num | 30 … 30000 Hz | SC low-cut (when `Free`) |
| `band_N_side_chain_high_frequency` | enum-num | 30 … 30000 Hz | SC high-cut (when `Free`) |
| `band_N_side_chain_input` | enum | `Plug-in Input` · `External Input` | internal vs external trigger |
| `band_N_stereo_link` | enum | `0%` … `100%` (+ `100%, X% Mid-only`) | L/R (or M/S) link amount |
| `band_N_stereo_link_mode` | enum | `Mid` · `Side` | operate on Mid or Side |
| `band_N_solo_mute_state` | enum | `Normal` · `Solo` · `Mute` · `Solo (Mute)` | per-band solo/mute |

**Global params** (30):

| Param | Type | Values | Role |
|---|---|---|---|
| `processing_mode` | enum | `Linear Phase` · **`Dynamic Phase`** · `Minimum Phase` (default Dynamic) | phase/latency mode |
| `oversampling` | enum | `Off` · `2x` · `4x` | anti-alias the dynamics |
| `lookahead_enabled` | bool | `False` · `True` (default True) | global lookahead enable |
| `mix` | enum-num | 0 … 200 % (default 100) | **global wet/dry — < 100 = parallel** |
| `expert_mode` | bool | `False` · `True` | reveal the full per-band control set in the GUI |
| `input_level` / `output_level` | enum-num | −inf … +36 dB | I/O gain |
| `input_pan` / `output_pan` | enum | `Left: x / Right: y` grid | I/O pan |
| `audition_side_chain` | enum | `Off` · `Band 1…6` | solo-listen a band's side-chain |
| `bypass` / `host_bypass` | enum | `Not Bypassed` · `Bypassed` | bypass |
| `display_range` | enum-num | 3 · 6 · 12 · 30 dB | GUI scale |
| `analyzer*` | mixed | `Off/Pre/Post/Pre+Post`, resolution, speed, tilt, freeze, `analyzer_side_chain` | spectrum analyzer (incl. the `Pre+Post+SC` from the screenshot) |
| `midi_state`, `internal`, `midi_cc`, `pitch_bend`, `channel_pressure` | — | — | MIDI-learn plumbing (ignore) |

### The four quadrants — `dynamics_mode` × sign of `range` (measured)

The crux of Pro-MB. A single band over **3–9 kHz** on the drum loop (level-matched plugin output, lows shown to
prove band-split):

| Mode + range | What it is | Measured Δ (3–9 kHz band, vs dry) | Lows |
|---|---|---|---|
| **Compression, −range** | downward comp — duck the loud part | `−12`: 5 kHz **−6.0**, 4 kHz −5.1, presence −3.2, crest −0.26 · `−24/8:1`: 5 kHz **−8.5**, 4 kHz −7.1, presence −4.2 | **0.00** |
| **Compression, +range** | upward comp — lift the quiet part toward the loud (density) | raises the band's low-level passages (subtle on already-dense drums) | 0.00 |
| **Expansion, +range** | **upward expansion** — boost the loud part (dynamic exciter/air) | `+12`: presence **+5.6**, 5 kHz +7.4, 4 kHz +6.8, **crest +1.4** | 0.00 |
| **Expansion, −range** | downward expansion / gate — reduce *below* threshold | acts only where the band dips below threshold → on busy drums you must set the **threshold up into the quiet** (see below) | 0.00 |

**Downward-expansion threshold is inverted (a teaching gotcha).** `Expansion, range −12, threshold −35` on the
loud 3–9 kHz band = **0.00 dB no-op** — the band never falls below −35, so the expander never engages. Raise the
threshold into the signal's quieter passages and it bites: `thr −12 / range −18` → presence **−1.0**, air −1.3;
full-band `thr −12 / range −24` → low −0.3, **crest +0.18, RMS −0.18** (tightening the tails). Opposite intuition
from compression — for a downward expander the threshold sits *above* what you want to push down.

**Band-split is real** (the difference from a fixed-crossover MB comp and from Pro-Q's parametric dynamic EQ): a
Compression band on **30–150 Hz** moved **sub −6.0 / low −4.5** and **everything above 0.00**, while raising crest
**+2.55** (tightened the boom, peaks kept). Each band only touches between its own crossovers; the gaps pass
unprocessed.

### Four footguns (proven)

1. **Range 0 = silent no-op.** A band `Enabled` with `threshold −35` + `ratio 4:1` but `range 0` == the dry input.
   `range` is the master amount — **always set it nonzero**.
2. **Bare load is a true passthrough — do NOT flatten.** All 6 bands default `Unused` (measured 0.0000 dB vs
   input). Unlike Pro-Q (which restores its last GUI curve), a fresh Pro-MB is genuinely clean — just enable your
   bands. (You *can* set a band's state to `Disabled` to park it without losing its settings; `Unused` is the
   never-touched default.)
3. **`apply-vst-chain`'s float dict can't enable a band.** Setting `band_1_range=-24, band_1_threshold=-35,
   band_1_low_crossover=3000, band_1_high_crossover=9000` via the tool reported `parameters_set` for all four but
   **`changed:false`** (RMS −17.7222 → −17.7222) — the band stayed `Unused`, and the float dict can't set
   `band_1_state` / `dynamics_mode` / `ratio` / the slopes / `processing_mode` (string enums). **Use the preset
   harness for any real Pro-MB move.**
4. **Expansion threshold is inverted** (see the quadrant section) — a downward expander only acts below threshold;
   set the threshold up into the quiet or it never engages.

### How to actually drive it headless

Use **[[vst-preset]]**'s `apply_vst_preset.py` (it `setattr`s every param, strings included). Per band set
`band_N_state="Enabled"`, the crossovers + slopes, `dynamics_mode`, `threshold`, **a nonzero `range`**, `ratio`,
and (optionally) `attack`/`release`/`knee`/`lookahead`/`level`; plus globals `processing_mode`, `mix`,
`oversampling`. No flatten step is needed (passthrough default). Set `dump_state=true` (via `apply-vst-chain`)
once you like it, then re-render from the opaque `.state` blob for byte-stability. Inspect the surface any time
with `presets/vst/dump_params.py "Pro-MB"`.

### Measured result — the shipped de-harsh preset

`presets/vst/fabfilter-promb-drum-deharsh.json` (one band, 3–9 kHz / 24 dB-oct edges / Compression / threshold
−30 / **range −9** / 4:1 / knee 12 / Dynamic Phase), applied to the Watercolors drum loop via the harness
(output level-matched to the dry at −3 dBFS peak), measured with `[L] measure-spectrum`:

| third-octave / metric | dry | de-harsh | Δ |
|---|---|---|---|
| 500 Hz | −23.47 | −23.47 | **0.00** (below the band — untouched) |
| 1 kHz | −26.53 | −26.58 | −0.05 (untouched) |
| 2.5 kHz | −24.77 | −26.30 | −1.53 |
| 3.15 kHz | −24.09 | −26.84 | −2.75 |
| 4 kHz | −22.90 | −26.91 | **−4.01** |
| **5 kHz** | −21.38 | −26.10 | **−4.72** (the harsh peak) |
| 6.3 kHz | −22.06 | −26.62 | **−4.56** |
| 8 kHz | −25.94 | −29.45 | −3.51 |
| spectral centroid | 1593 Hz | 1506 Hz | −87 (top tamed) |
| spectral tilt | −2.71 | −3.01 | steeper (less harsh) |
| high-mid band-ratio | 0.0113 | 0.0052 | presence energy ~halved |

The single band ducked the **3–9 kHz presence by ~4–5 dB on its peaks** while **everything below 1 kHz stayed
within 0.05 dB** — the surgical, band-split dynamic de-harsh a static cut can't do without dulling the steady top.
The 3-band `presets/vst/fabfilter-promb-drum-multiband-glue.json` adds gentle Compression on the lows (30–120 Hz)
and low-mid box (200–600 Hz) for bus glue — each band moves only its own zone.

### Other isolation findings

- **Parallel `mix`**: the same de-harsh at `mix=50` halved the duck (presence −4.2 → −2.7 dB) — global `mix`
  (0–200 %) is true parallel/dry-wet, cheaper than softening each band's range.
- **Phase modes** (same −18 dB comp on 3–9 kHz): magnitude is **near-identical** across Dynamic / Minimum /
  Linear (presence −4.0 / −3.9 / −3.8; crest 14.30 / 14.19 / 14.19) — choose by **phase coherence / latency /
  pre-ring**, not tone. Dynamic Phase (default) is the transient-safe **zero-latency** pick for drums (with
  lookahead + oversampling off — but the stock instance ships `lookahead_enabled=True` + 1 ms per-band lookahead,
  so it is *not* truly zero-latency until you disable lookahead); Linear only for parallel/phase-critical sums (it
  pre-rings transients); Minimum for lowest latency but "virtually unusable for mastering" except at 6 dB/oct.
  (Mechanism — and the fact that **Dynamic Phase shipped with Pro-MB at its 2013 launch and only *later* propagated
  to Pro-Q 4** — is in Part B §3.)

---

# Part B — How Pro-MB Works (web-research synthesis, adversarially verified, cited)

> **Reading this section.** Everything below is FabFilter-doc-grounded and cross-checked against our own ground-truth render surface: the Pedalboard 0.9.23 parameter dump of `/Library/Audio/Plug-Ins/VST3/FabFilter Pro-MB.vst3` (156 params, **renders headless**). Where a researched claim was corrected, downgraded, or refuted during verification, the corrected version is used and the confidence is noted inline. Numeric *defaults* and the exact param value-strings come from the dump (FabFilter's docs rarely print them); the dump and the docs do not contradict each other anywhere material.

---

## 1. What Pro-MB is — identity, history, version, format, licensing

**FabFilter Pro-MB is a multiband *dynamics* processor** — not just a multiband compressor. Per FabFilter's own description it does "compression, limiting, expansion, upward compression, and gating across multiple frequency bands," with up to **six bands** ([product page](https://www.fabfilter.com/products/pro-mb-multiband-compressor-plug-in); [About Pro-MB](https://www.fabfilter.com/help/pro-mb)). The six-band ceiling is confirmed verbatim ("Up to six processing bands, freely placed anywhere in the spectrum") and matches the dump exactly: `band_1..band_6`, each `band_N_state = {Disabled, Enabled, Unused}` (default `Unused`). There is no seventh slot — six is a hard ceiling, not a soft default. *(Confidence: high.)*

**The defining identity choice — "think bands, not crossovers."** A classic multiband splits the *whole* spectrum into contiguous crossover slices. Pro-MB instead lets you place free-floating bands only where you want to act, leaving the rest of the spectrum untouched. FabFilter: "Instead of conventionally splitting the entire spectrum with crossovers, Pro-MB enables you to directly create a new band at the frequency range you want to work on… The interactive multiband display clearly shows that the rest of the spectrum stays untouched" ([product page](https://www.fabfilter.com/products/pro-mb-multiband-compressor-plug-in)). The `Unused` default state in the dump *is* this model — a band slot does not exist until you place it. Bands can still be **snapped** together to share a crossover and build a traditional contiguous split if you want one. This free-placement framing is why Pro-MB reads as a dynamic EQ rather than a 3/4/5-band comp (see §7). *(Note: it is overstated to call Pro-MB simply "a true band-splitting multiband" — in its default Dynamic Phase mode the signal "is not actually split into bands"; true crossover band-splitting is only the Minimum/Linear Phase modes. Our measured frequency-isolation still holds audibly in Dynamic Phase. Confidence: high.)*

**History / version.** Released **17 October 2013** ([FabFilter press release](https://www.fabfilter.com/press/1382002200/fabfilter-releases-fabfilter-pro-mb-multiband-dynamics-plug-in); corroborated by [Production Expert, 2013-10-17](https://www.production-expert.com/home-page/2013/10/17/fabfilter-release-new-pro-mb-multiband-dynamics-plug-in.html)). Launch price was EUR 169 / USD 229 / GBP 139; current price is **USD $199** ([shop, USD](https://www.fabfilter.com/shop/pro-mb-multiband-compressor-plug-in?currency=USD)). Pro-MB has never had a major-version bump — it remains a **1.x** product (legacy downloads show e.g. 1.17/1.19), receiving only maintenance/compatibility updates over its life. **The exact current build number is not published by FabFilter on any public page — flagged, not invented** (the live build is in your FabFilter account/download area). *(Confidence on the 2013 date: high. On "no current build number published": high.)*

**Format.** At launch: VST, VST3, AU, AAX, RTAS, AudioSuite. Current product/shop pages list **VST · VST3 · AU · CLAP · AAX · AudioSuite** — i.e. **CLAP added post-launch, RTAS dropped** ([product page](https://www.fabfilter.com/products/pro-mb-multiband-compressor-plug-in)). 64-bit only; macOS 10.13+ (Intel or Apple Silicon native). Our rig loads the **VST3** build, which the dump confirms renders headless.

**Licensing — a clean win for headless/render-farm use.** Pro-MB uses a **simple copy-paste software license key — NO iLok, NO hardware dongle**: "No, our plug-ins don't need an iLok. Instead, we use a fairly simple license key system" ([FAQ](https://www.fabfilter.com/support/faq); [license help](https://www.fabfilter.com/help/pro-mb/purchase/license)). **Offline activation is supported** — download the installer + key on a connected machine, move both via USB, paste the key, no internet required ([activate](https://www.fabfilter.com/activate)). A single license runs on **up to 3 computers** (Windows/macOS, sole user), with self-service Deauthorize to move between machines. This matches our existing Pro-Q 4 finding (same vendor, no-PACE key scheme) and makes Pro-MB a **low-risk headless citizen** — no iLok/PACE render-farm landmine. *(Confidence: high.)*

---

## 2. The band & dynamics model — the four quadrants, threshold/ratio/knee, dynamic vs fixed crossovers

This is the conceptual heart of the plugin, and the part most people get wrong.

**Two controls pick one of four behaviors.** FabFilter, verbatim: "FabFilter Pro-MB can apply any kind of dynamics processing per band, using the **Dynamics Mode buttons in combination with the Range knob.** When the Dynamics Mode is set to Compress, use either a **negative or positive range** to apply **downward (normal) or upward** compression. The same applies to Expand mode" ([basic band controls](https://www.fabfilter.com/help/pro-mb/using/basicbandcontrols)). The dump exposes exactly this surface: per-band `dynamics_mode = {Compression, Expansion}` and a **bipolar** `range = −30..+30 dB` (default 0). *(All four behaviors confirmed verbatim. Confidence: high.)*

| Quadrant | Mode + Range sign | Acts on | Behavior (FabFilter, verbatim sense) |
|---|---|---|---|
| **Downward compression** ("normal" comp) | Compress + **negative** Range | **above** threshold → cut | "the dynamic range is reduced by attenuating peaks that exceed the specified threshold" |
| **Upward compression** | Compress + **positive** Range | **below** threshold → boost | "adds gain as soon as the level drops below the threshold… reduces the dynamic range from the noise floor up" — adds loudness/body, leaves transients |
| **Downward expansion** (→ gating) | Expand + **negative** Range | **below** threshold → cut | "attenuated as soon as it drops below the threshold… higher ratio/range values → gating" |
| **Upward expansion** (transient enhance) | Expand + **positive** Range | **above** threshold → boost | "adds gain as soon as the signal exceeds the threshold, emphasizing the peaks… enhance transients (e.g. increase the impact of a snare)" |

**The clean mental model:** *Mode* (Compress/Expand) chooses whether the band *reduces* or *increases* dynamic range; *Range sign* chooses gain **down (−)** or **up (+)**. Together they pick the quadrant. The threshold trigger direction (above vs below) is **derived** from mode+range, not a separate control: "Whether the band triggers on signals above or below the threshold depends on both the Range parameter and the current dynamics mode." *(This is exactly why our measured `Expansion, range −12, threshold −35` on a loud band was a no-op — downward expansion acts **below** threshold, so the threshold must sit up in the quiet passages.)*

> ⚠️ **Quadrant authority — a corrected source.** The **Sage Audio** explainer garbles two of the four quadrants (it internally mislabels downward expansion vs upward expansion). **Trust the FabFilter manual quadrant table above, not Sage's prose.** Sage is fine as general technique color only. *(Confidence: high.)*

**Range vs Threshold vs Ratio — exactly how they interact.**

- **Threshold** = the comparison level (dump: −90..0 dB, **default −18**). It sets *where* the boundary sits; mode+range sign set *which side* is active.
- **Ratio** = the transfer-curve *slope* — it **scales** the effect. "at a ratio of 4:1, three of every four dB above the threshold will be attenuated" (dump: `ratio "1.00:1".."100.00:1"`, **default "4.00:1"** — note the default means **you must change it** if you want 2:1 glue).
- **Range** = the **cap** on total gain change, *and* the direction selector. Verbatim: "the Range knob **limits the final amount of compression or expansion rather than scaling it.**" Ratio scales; **Range clamps.**

> ⚠️ **"Range = 0 does nothing" — verified *partly* (corrected version applied).** It is *true* that at Range = 0 dB the maximum permitted gain change is zero, so the band is inert regardless of Threshold/Ratio (our measured bit-exact passthrough). The precise framing: Range = 0 is **not a dedicated "off"** — it is the **neutral zero-crossing of a bipolar direction-and-magnitude knob** (a band is genuinely parked via its *state* = `Disabled`). The load-bearing takeaway is unchanged: **a freshly placed/enabled band with default threshold/ratio but `range = 0` produces no audible change** — the #1 headless footgun. Always set `range` (with sign) explicitly. *(Confidence: high.)*

> 🔎 **One refinement on the upward modes (FabFilter staff):** in positive-range modes "the range not only limits the amount of expansion, but also scales the amplification" — i.e. positive Range additionally *scales*, not purely *caps*, the added gain ([FabFilter forum](https://prod.fabfilter.com/forum/topic/2746/)). This changes *how* upward modes feel, not *which* four behaviors exist. *(Confidence: high.)*

**Knee** sets hard↔soft response around the threshold; the manual is qualitative, the dump supplies the numbers: `knee = 0..48 dB`, **default 24** (a fairly soft default, one reason the stock band is gentle). *(Confidence: high.)*

**Dynamic crossovers vs fixed multiband.** Each band has its **own** low and high crossover (dump: `low_crossover`/`high_crossover` 30..30000 Hz) with **per-crossover variable slopes 6–48 dB/oct** (dump: `low_slope`/`high_slope` 6.0..48.0, **default 24**). Two free band-edges per band = a placed region, not a contiguous slice. The full 6–48 slope range is available **only in Dynamic and Linear Phase modes**; in Minimum Phase, steep slopes impose audible static phase shift and FabFilter recommends 6 dB/oct throughout. **Honest flag:** FabFilter docs do **not** confirm whether two independent bands may freely *overlap* the same frequency range (they document snap-to-share-crossover and "rest of spectrum untouched," not overlap) — treat free overlap as **unconfirmed**. *(Confidence on slopes/crossovers: high. On overlap: low/unconfirmed.)*

---

## 3. Processing modes + oversampling

All three modes answer one question: *how is the signal split into bands before dynamics are applied?* The difference is entirely crossover topology → phase, latency, pre-ringing.

| Mode | Latency | Pre-ringing | Phase behavior | FabFilter's note |
|---|---|---|---|---|
| **Dynamic Phase** *(default)* | **Zero** (with lookahead + OS off) | **None** | Flat/linear phase when **idle**; phase shifts **only** when a band actually changes gain, in proportion to that change. Avoids Minimum Phase's *static* crossover shift. | "by far the most transparent mode, suitable for both mastering and mixing… chosen as the default" |
| **Linear Phase** | "quite a bit of extra latency" (high) | **Possible** (inevitable side-effect of linear-phase FIR) | Guaranteed flat phase after split+sum, even at any crossover setting | transparent but latent; best when phase coherence across crossovers must be *guaranteed* |
| **Minimum Phase** | **Zero** extra | **None** (causal) | **Static** phase changes at every crossover, **always on** (worse at steep slopes) | "virtually unusable for mastering" — *except* with **6 dB/oct slopes throughout**, which stays clean |

Dump: `processing_mode = {Linear Phase, Dynamic Phase, Minimum Phase}`, **default Dynamic Phase** — exact match. Our magnitude measurements across the three modes were near-identical, which is expected: the modes differ in *phase/latency/pre-ring*, not in the gain a band applies. *(Confidence: high.)*

> ⚠️ **Dynamic Phase claim — verified *partly* (corrected version applied).** Two precisions: (a) it is **zero-latency, not merely "low-latency"** ("features zero latency operation"); (b) it does **not** "avoid all phase shift" — it is phase-**flat at rest** and introduces *gain-coupled* phase shift only while actively processing. It is strictly better than Minimum Phase's always-on static shift, not phase-shift-free in absolute terms. **Version:** Dynamic Phase shipped in **Pro-MB 1.0 at launch (Oct 2013)** — it was developed exclusively for Pro-MB and headlined the launch press release, *not* added later. (The confusion is that it has since propagated to other FabFilter plug-ins, e.g. Pro-Q 4.) *(Confidence: high.)*

**Latency budget** = processing mode + lookahead + oversampling. Verbatim: "If lookahead is disabled, oversampling is turned off, and the processing mode is set to Dynamic Phase or Minimum Phase, FabFilter Pro-MB works without any latency. When lookahead is enabled, the latency will be 20 ms, plus possible additional latency for Linear Phase processing and oversampling" ([processing mode](https://www.fabfilter.com/help/pro-mb/using/processingmode)). **Headless footgun:** the dump default is `lookahead_enabled = True` with per-band `lookahead = 1.0 ms`, so a stock instance is **not truly zero-latency even in Dynamic Phase** — set `lookahead_enabled = False` + `oversampling = Off` + Dynamic/Minimum Phase for genuine zero latency. (Offline in Pedalboard, latency is compensated, so it costs render buffer, not sync — but it still governs Linear-Phase pre-ring.)

**Oversampling** (dump: `{Off, 2x, 4x}`; product page "up to 4× linear-phase oversampling"): runs the dynamics internally at 2×/4× to reduce aliasing from aggressive gain changes and improve HF response. **Nuance:** FabFilter scopes the HF-response benefit to **Minimum Phase and Dynamic Phase** — Linear Phase already has excellent HF response, so for Linear Phase oversampling buys *anti-aliasing*, not HF correction. Turn it up "when the compression or expansion is more aggressive… lower Attack and Release and/or higher Ratio and Range." For offline renders (no real-time CPU constraint), **2×/4× is cheap insurance on aggressive bands.** *(Confidence: high.)*

---

## 4. Controls — attack/release (the real story), lookahead, knee, Mix, level, expert mode

> ⚠️ **Attack/Release in milliseconds — the claim was REFUTED. Corrected version applied.** The premise that there is a "real min/max in ms" is **false**: Pro-MB does **not** expose attack/release in milliseconds at all, by design. The 0–100 values are literally **percentages**, not a normalization of a hidden ms range. FabFilter, verbatim: "The Attack knob shows a percentage value from 0% to 100%, **because actual attack times are very program dependent, and even depend on the placement of the band in the frequency spectrum**" — identically for Release; the feature list calls these "**Intelligent, highly program- and frequency-dependent attack and release curves**." The same % maps to different real ms depending on content *and* on the band's center frequency (a low band runs slower than a high band at the same %). **There is no published ms figure for 0% or 100%, and none was invented.** Functional guidance only: below ~50% = faster (transient control, limiting/gating); above ~50% = slower (leveling). The dump confirms independently: `attack`/`release` exposed as **0..100, default 20** (= 20%), **no ms units**. **You cannot set attack/release in ms via `apply-vst-chain` — only the 0–100 value, same as the GUI.** *(Confidence: high.)*

**Lookahead** is the *only* genuine ms control in this area: "start reacting up to **20 ms** before gain change is actually detected" (dump: per-band `lookahead = 0..20 ms`, **default 1.0**; global `lookahead_enabled`, default True). Use it so a fast attack catches transients cleanly without ultra-fast attack distortion; **disable it for zero-latency renders.**

**Knee** — `0..48 dB`, default 24 (soft↔hard; 0 = hard, 48 = very soft). Soften for de-essing/leveling, harden for snappy gating.

**Mix (global parallel/dry-wet).** Dump: `mix = 0..200%`, default 100. FabFilter: "The Mix slider enables you to mix between the dry and processed signals, scaling the overall dynamic and static gain changes for all bands… **Because the Mix slider ranges from 0% to 200%, you can also choose to increase overall gain processing instead of fading it out!**" ([output options](https://www.fabfilter.com/help/pro-mb/using/outputoptions)). **Precision:** 0–100% is a true dry/processed blend (classic parallel below 100%, which our `mix=50` render confirmed — it halved the duck); **100–200% does NOT add more dry signal — it *scales the per-band gain changes up* (to 2× at 200%)**, i.e. intensifies processing rather than widening the blend. It is global, whole-plugin (the per-band parallel-style move is upward compression, §2). *(Confidence: high.)*

**Level / pan.** Per-band: `level = −30..+30 dB` (makeup/band balance) and a **Mid/Side** pan ring (`pan = {Mid, Side}` — **mid/side, NOT L/R**). Global: `input_level`/`output_level = −inf..+36 dB` with **L/R** `input_pan`/`output_pan` (an alternative to moving every band's threshold). **Note the contrast:** per-band pan is M/S; global I/O pan is L/R. *(Confidence: high.)*

**Expert mode** (`expert_mode`, default False) is a global toggle that *reveals* the per-band side-chain triggering + stereo-linking + audition controls (off by default → bands trigger on their own input). **Headless nuance:** the dump surfaces every per-band SC/stereo param *unconditionally* (Pedalboard automation surfacing) even with `expert_mode = False` — so you can set them via state without flipping Expert, but set `expert_mode = True` if you want a human to *see* them in a re-opened GUI. *(Confidence: high.)*

---

## 5. Side-chain (Band/Free, internal/external) + stereo (M/S, stereo link)

**Per-band side-chain (Expert mode).**
- **Band vs Free filtering** (dump: `side_chain_filtering = {Band, Free}` + `side_chain_low_frequency`/`side_chain_high_frequency`): **Band** (default) triggers on the band's own crossover slice; **Free** decouples detection from processing — the band still compresses its own region but *listens* to a separately chosen frequency window. FabFilter's tip: "When triggering on a very specific frequency, choosing a very narrow range in **Free** mode often works better than the default Band mode." *(Capability: high; "adaptive filter" internals: low/marketing.)*
- **Internal vs External input** (dump: `side_chain_input = {Plug-in Input, External Input}`, per band): `In` = normal plug-in input; `Ext` = external key. **Shared-bus caveat:** there is exactly **one** external SC bus — all bands set to External share the same external source. **Headless caveat (flagged, expected-not-proven):** external SC routing is host-side; offline in Pedalboard there is generally no SC bus to feed, so `External Input` will likely see silence → **keep `side_chain_input = Plug-in Input` for headless renders**; use **Free-mode in-plugin triggering** as the headless-safe substitute. *(Host behavior: high; "inert offline": medium — verify by render.)*
- **Audition** (dump: global `audition_side_chain = {Off, Band 1..6}`): listens to one band's *filtered + stereo-linked trigger signal* (distinct from `analyzer_side_chain`, which is display-only). **Headless footgun:** if left on a band, the render outputs the *trigger* signal, not the processed audio — **assert `audition_side_chain = Off` before any real render.**

**Stereo & Mid/Side.**

> ⚠️ **"Bands can operate in Left/Right or Mid/Side" — verified *partly* (corrected version applied).** Pro-MB has **no per-band L/R operating mode.** M/S lives entirely on the per-band **Stereo Link** slider + **Stereo Link Mode** toggle:
> - **0%..100%** = stereo *linking* of the trigger: 0% = channels processed independently, 100% = identical gain reduction on both (image preserved).
> - **Drag past 100%** → the band processes **Mid-only** or **Side-only** content; the small **Stereo Link Mode** button picks which (`stereo_link_mode = {Mid, Side}` — **never Left/Right**).
> The dump confirms precisely: `stereo_link = "0%..100%"` then an extended `"100%, X% Mid-only"` region, and `stereo_link_mode = {Mid, Side}` — there is **no Left or Right value anywhere in the 156-param surface**. The dump's odd-looking `"100%, X% Mid-only"` string is exactly the documented drag-past-100% behavior, not a bug. The separate per-band `pan = {Mid, Side}` ring is *output* M/S panning, not an L/R operating mode either. *(Confidence: high.)*

The full per-band detection chain: **input select (In/Ext) → SC filter (Band/Free) → stereo link/channel select → Threshold detection.**

---

## 6. Practical recipes

Concrete starting numbers. **All map to literal dump params except attack/release**, which are **0–100 *intent* values, not ms** (calibrate by render — the realized ms is program/frequency-dependent). Every band needs `band_N_state = Enabled` **and a signed `range`** to do anything, and **`ratio` must be set explicitly** (default is 4:1, not the values below).

| Task | Mode + key params | Starting numbers |
|---|---|---|
| **De-ess** | Compression, downward (`range` neg), narrow band; soft-ish knee; little lookahead | band ~5–10 kHz (Band, or Free for tighter trigger), `range −1..−2`, `ratio "2.00:1"`, fast attack/release, `lookahead` ~3–5 ms. Keep range *small* — over-ranging dulls the whole top. |
| **Multiband / bus glue** | Single broadband band, gentle Compression downward | `range −2..−3`, `ratio "2.00:1"` (1.5:1–max 4:1), threshold catching peaks only, mid-slow attack / fast release, ~1–2 dB GR. `processing_mode = Dynamic Phase`. |
| **Dynamic-EQ: resonance / mud** | Compression downward, narrow band, **Free** trigger | band ~200–500 Hz, `side_chain_filtering = Free` tight around the offender, `range −2..−4`, `ratio "3.00:1"`. |
| **Dynamic-EQ: boom (bass)** | Compression downward, low band | band ~40–120 Hz, `range −2..−4`, `ratio "2.00:1".."4.00:1"`, medium attack/release. Sub variant: ~20–60 Hz, slow-ish attack (keep impact)/fast release, `stereo_link_mode = Mid` (sub is mono). |
| **Bass control / dynamic mono-low** | Side-only Compression on a low band | low band high-crossover ~100–130 Hz, `stereo_link_mode = Side` (into the extension), downward `range`, **`processing_mode = Linear Phase`** for clean low-end mono. *(Synthesis of side-only capability + standard mono-bass goal — flag.)* |
| **M/S (preserve image / width)** | Mid-only or Side-only band | Preserve center: `stereo_link_mode = Mid` on the band covering the centered element. Dynamic width: `stereo_link_mode = Side` on a high band, upward expansion to widen only when already wide. |
| **Upward compression (density)** | Compression, **positive** `range` | `range +2..+6`, `ratio "1.50:1"`, soft knee, threshold *above* the quiet detail to lift. ⚠️ raises everything below threshold incl. hiss. |
| **Downward expansion (tighten / gate)** | Expansion, **negative** `range`, threshold UP into the quiet | tighten `range −6..−20`; deeper + higher ratio = gating; fast attack, release tuned to the decay. Per-band → gate only the noisy region. |

*(Hz / dB-range / ratio / mode values are literal dump params; ms-style guidance is intent. Confidence: high on the param mappings; medium on the specific engineer-consensus numbers, which are starting points, not spec.)*

---

## 7. Pro-MB vs Pro-Q 4 dynamic EQ vs Pro-C 2 — when to use which

> ⚠️ **The classic "Pro-MB beats Pro-Q for de-essing because Pro-Q has no attack/release" is OBSOLETE.** Pro-Q **4 added adjustable attack and release** on dynamic-EQ bands ([[fabfilter-pro-q-4]]). The old reason is largely moot. *(Confidence: high.)*

**Architecture.** Dynamic EQ = one parametric filter whose gain moves, keyed off a band-limited version of the input. Multiband comp = band split → per-band compressor → recombine. The real distinction now is **control depth and Q**, *not* band-split-vs-not (Pro-Q's dynamic bands are band-limited too, and Pro-MB's default Dynamic Phase doesn't truly split):

- **Pro-Q 4 (dynamic EQ / Spectral Dynamics):** surgical, **much tighter minimum Q**, transparent, EQ-native workflow; now *also* has adjustable attack/release (but fixed ratio/knee, no lookahead). **First reach for tonal/EQ problems** — notch a single resonance, de-ess with a tight bell, tame a *moving* harsh frequency.
- **Pro-MB:** when you need genuine **compressor** behavior in a band — explicit **ratio, deeper knee, lookahead up to 20 ms, adjustable crossover slopes 6–48 dB/oct**, plus **expansion/gating, upward compression, per-band M/S, and free/external side-chain.** Broader minimum Q. The tool when "tame this region" becomes "compress/expand this region like a compressor." Keep it on Dynamic Phase for transparency.
- **Pro-C 2:** a **broadband (single-band)** character compressor with styles (Clean/Classic/Opto/Vocal/Mastering/Bus/Punch/Pumping), SC EQ, lookahead. For **glue/leveling/character/parallel on a whole source.** "Pro-C is for individual sounds, Pro-MB is for mixed sounds to adjust balance."

| Need | Tool |
|---|---|
| Surgical, transparent, narrow-Q tonal fix; moving resonance | **[[fabfilter-pro-q-4]]** (Pro-Q 4) |
| Compressor behavior on a *band*: ratio/knee/lookahead, gate, upward comp, per-band M/S, free/ext SC | **Pro-MB** (this skill) |
| Broadband glue / leveling / character / parallel on a whole source | **Pro-C 2** ([[vst-compress]]) / [[fairchild-660]] / [[ssl-bus-compressor-2]] |

*(Confidence: high.)*

---

## 8. Pitfalls & gotchas

1. **A band does nothing at the defaults.** All slots ship `Unused`; even an `Enabled` band with default threshold/ratio but **`range = 0` is a bit-exact passthrough** (measured). Set `band_N_state = Enabled` **and a signed `range`** per band. *(High.)*
2. **`ratio` defaults to "4.00:1" — every recipe assumes you change it.** Set it explicitly in your preset JSON. *(High.)*
3. **Attack/Release are 0–100% percentages, not ms — and there is no published ms mapping.** Calibrate by isolation render; the same % differs by band frequency and material. *(High — refuted the ms premise.)*
4. **`audition_side_chain` must be `Off` for a real render** — otherwise you bounce the trigger signal, not the processed audio. *(High.)*
5. **Default instance is not zero-latency.** `lookahead_enabled = True` + 1.0 ms per-band lookahead by default; for true zero latency set `lookahead_enabled = False` + `oversampling = Off` + Dynamic/Minimum Phase. *(High.)*
6. **External side-chain is DAW-only / likely inert headless** — keep `side_chain_input = Plug-in Input` and trigger via **Free** mode offline. Verify with a render before trusting it. *(Medium — expected, not proven.)*
7. **Per-band pan is Mid/Side, not L/R; global I/O pan is L/R.** There is **no per-band L/R operating mode** at all — M/S is the Stereo Link slider past 100%. *(High.)*
8. **Enum-heavy surface → use the preset/state harness, not the float dict.** `band_N_state`, `dynamics_mode`, `ratio` (string "4.00:1"), `pan`, `side_chain_filtering`, `side_chain_input`, `stereo_link`, `stereo_link_mode`, `processing_mode`, `oversampling`, `audition_side_chain` are string/enum params. An `apply-vst-chain` float dict silently sets the numeric ones and **misses every string enum** (measured `changed:false`). Drive Pro-MB via the **[[vst-preset]]** harness / `state_path`, setting `range`, `dynamics_mode`, and `ratio` explicitly on every band. Verify with [[vst-verify]]. *(High.)*
9. **Minimum Phase is "virtually unusable for mastering" except at 6 dB/oct slopes throughout.** For mastering use Dynamic Phase (default) or Linear Phase. *(High.)*
10. **`Unused` ≠ `Disabled`.** Unused = never created (the free-placement default); Disabled = a created band turned off. *(High.)*

---

## Sources

FabFilter official (authoritative): product page <https://www.fabfilter.com/products/pro-mb-multiband-compressor-plug-in> · About/help ToC <https://www.fabfilter.com/help/pro-mb> · Basic band controls <https://www.fabfilter.com/help/pro-mb/using/basicbandcontrols> · Expert band controls <https://www.fabfilter.com/help/pro-mb/using/expertbandcontrols> · Processing mode <https://www.fabfilter.com/help/pro-mb/using/processingmode> · Oversampling <https://www.fabfilter.com/help/pro-mb/using/oversampling> · Input/output options (Mix) <https://www.fabfilter.com/help/pro-mb/using/outputoptions> · External side chaining <https://www.fabfilter.com/help/pro-mb/support/externalsidechaining> · License key <https://www.fabfilter.com/help/pro-mb/purchase/license> · Press release (2013-10-17) <https://www.fabfilter.com/press/1382002200/fabfilter-releases-fabfilter-pro-mb-multiband-dynamics-plug-in> · Shop (USD price) <https://www.fabfilter.com/shop/pro-mb-multiband-compressor-plug-in?currency=USD> · FAQ (no-iLok / 3-computer licensing) <https://www.fabfilter.com/support/faq> · Activate (offline) <https://www.fabfilter.com/activate> · PDF manual <https://www.fabfilter.com/downloads/pdf/help/ffpromb-manual.pdf> · FabFilter forum (upward-range scaling) <https://prod.fabfilter.com/forum/topic/2746/>. Reputable third-party (technique/opinion): Sound on Sound <https://www.soundonsound.com/reviews/fabfilter-pro-mb> · Tape Op <https://tapeop.com/reviews/gear/101/pro-mb-plug-in> · Production Expert (post-production use) <https://www.production-expert.com/production-expert-1/using-fabfilter-pro-mb-in-post-production> · The Pro Audio Files <https://theproaudiofiles.com/review-fabfilter-pro-mb-multiband-compressor/>. Flagged ERRONEOUS on the four quadrants (general technique only): Sage Audio <https://www.sageaudio.com/articles/everything-you-need-to-know-about-fabfilter-mb>. **Ground truth:** our own Pedalboard 0.9.23 parameter dump + render/measure results (Part A) on `/Library/Audio/Plug-Ins/VST3/FabFilter Pro-MB.vst3`.
