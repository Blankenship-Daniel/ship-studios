# FabFilter Pro-L 2 — field guide: true-peak brickwall limiter, headless

How to drive **FabFilter Pro-L 2** (`/Library/Audio/Plug-Ins/VST3/FabFilter Pro-L 2.vst3`) — a professional
**true-peak brickwall limiter / loudness maximizer**, the **final** stage of a master. It's the VST limiter of
the [[vst-master]] suite and the boutique alternative to the pure-DSP limiter inside `[L] render-mastered`.
**Part A** is *measured on this rig* (the real Pedalboard param surface + our own render/meter results); **Part
B** is a *web-research synthesis, adversarially verified, cited* (FabFilter's own docs + reviews). The skill
[[fabfilter-pro-l-2]] is the measured workflow over this doc.

> **Repo caveat:** Gemini hears ~16 kbps mono — **meters own** loudness/true-peak/crest, which is *exactly* what
> a limiter is judged on. Verify every render with `[L] measure-loudness` (LUFS-I + 4×-oversampled dBTP + crest)
> and `[G] check-streaming-targets`. Never judge a limiter by ear without loudness-matching ([[level-match]]).

---

## TL;DR (the headline, measured)

1. **It limits correctly headless and it's no-iLok.** Pro-L 2 loads + renders through Pedalboard; FabFilter uses
   a **simple license key (no iLok/dongle, offline-activatable, 3 machines)**, so like Pro-Q 4 it's a clean
   render-farm candidate. Driving the **`gain`** slider in (+0→+12) holds the peak at the ceiling while **crest
   falls 14.6 → 8.1** — real loudness maximization. Use the **VST3** path.
2. **True Peak Limiting is the streaming-compliance control (measured).** At +9 gain, ceiling −1.0:
   **TP on → −1.018 dBTP (compliant)**; **TP off → −0.984 dBTP (OVER the −1.0 target)** even though sample-peak
   was −0.99. Sample-peak limiting leaks inter-sample peaks; **turn TP on for any dBTP delivery.**
3. **A limiter OWNS the ceiling — render it faithfully.** The `presets/vst/apply_vst_preset.py` harness
   *peak-normalizes its output* (to `output_peak_dbfs`), which re-scales the limiter and pushes true-peak back
   over the ceiling — **do not use it for Pro-L 2.** Use **`[L] apply-vst-chain`** (writes the plugin output
   unchanged) with a saved **`.state`** blob for the enums + a per-track **`gain`** override. Verified faithful:
   state-driven render held **−1.018 dBTP** ✓.
4. **8 styles, measurably different at matched gain.** Crest @ +9 gain (lower = denser/louder): **Aggressive
   9.49** (densest) · Transparent 9.88 · Dynamic 9.93 · Allround 9.95 · **Bus / Punchy 9.97** · **Safe 10.37** ·
   **Modern 10.56** (most dynamic-preserving, the v2 default). Meters rank *density*; "pump/glue" is perceptual.

---

# Part A — measured on this rig (Pedalboard)

**Loads + renders headless.** `load_plugin("…/FabFilter Pro-L 2.vst3")` → `name="Pro-L 2"`, `is_instrument=False`,
renders. Tested with **Pedalboard 0.9.23**, input `artifacts/watercolors-loops/seam/watercolors_drums_104bpm_8bar_a.wav`.
Both a **VST3** and an AU `.component` are installed — **use the VST3**.

### The real parameter surface (Pedalboard-exposed — authoritative)

**37 parameters, almost all exposed as `valid_values` enums.** Numeric params (gain, output_level, lookahead,
attack, release, channel_link_*) take a `setattr` float / the `apply-vst-chain` float dict; the **string/bool
enums** (style, oversampling, dithering, true_peak_limiting, noise_shaping, filter_dc_offset…) **cannot** be set
by the float dict — use a `.state` blob or a Pedalboard `setattr` script.

| Param | Type | Values | Role |
|---|---|---|---|
| `gain` | num | 0 … 30 dB | **the loudness driver** — lowers the limit threshold + adds output gain at once |
| `output_level` | num | −30 … 0 dB | **the ceiling** (reads **dBTP** when True Peak Limiting is on) |
| `style` | enum | `Transparent`,`Punchy`,`Dynamic`,`Allround`,`Aggressive`,`Modern`,`Bus`,`Safe` | limiting algorithm (8) |
| `lookahead` | num | 0 … 5 ms | the fast **transient** limiting stage |
| `attack` | num | 0 … 10 | the slower **release-envelope** stage (attack side) |
| `release` | num | 0 … 10 | release-envelope time |
| `channel_link_transients` | num | 0 … 100 % | stereo link of the transient stage |
| `channel_link_release` | num | 0 … 100 % | stereo link of the release stage |
| `channel_link_center` / `_lfe` | enum | `Excluded` · `Included` | surround link scope |
| `true_peak_limiting` | bool | False · True | **cap inter-sample/true peaks at the ceiling** (~+5 ms latency) |
| `oversampling` | enum | `Off`,`2x`,`4x`,`8x`,`16x`,`32x` | anti-alias / inter-sample accuracy (4x good; 16x/32x for offline masters) |
| `dithering` | enum | `Off`,`16`,`18`,`20`,`22`,`24 Bits` | output dither bit depth |
| `noise_shaping` | enum | `None`,`Basic`,`Optimized`,`Weighted` | dither noise-shaping |
| `filter_dc_offset` | bool | False · True | remove DC bias |
| `side_chain_triggering` | bool | False · True | external SC (stem mastering) |
| `unity_gain` | bool | False · True | auto-set output to inverse of gain (level-matched audition) |
| `audition_limiting` | bool | False · True | **delta-listen** — hear only the gain reduction |
| `output_level` lock / `lock_output` | enum | `Unlocked` · `Locked` | keep ceiling on preset change |
| `true_peak_metering` | enum | `Show Sample Peaks` · `Show True Peaks` | meter mode |
| `meter_scale` | enum | `-16/-32/-48 dB`, `K-12/K-14/K-20`, `Loudness` | meter scale (Loudness = the LUFS meter) |
| `loudness_time_scale` | enum | `Momentary` · `Short Term` · `Integrated` | LUFS window (LRA shows only on Integrated) |
| `loudness_meter_target` | num | −60 … 0 LUFS | the integrated target line (e.g. −14) |
| `display_mode` | enum | `Slow Down`,`Fast`,`Slow`,`Infinite`,`Off` | **5** display modes (the metering animation) |
| `bypass` / `show_advanced` / `loudness_recording` / `loudness_auto_reset` … | enum/bool | | UI / meter plumbing |

> Like Pro-Q 4, **a bare load restores FabFilter's last-saved GUI state** (ours came up exactly as the
> screenshot: style=`Bus`, oversampling=`32x`, ceiling −1.0, dither `24 Bits`, TP on). So set every relevant
> param explicitly (a `.state` blob) for a reproducible render — don't trust the restored defaults.

### It limits — gain sweep (Transparent, ceiling −1, TP on, 4× OS)

| `gain` | peak dBFS | RMS dBFS | crest |
|---|---|---|---|
| +0 | −4.08 | −18.71 | 14.63 (below ceiling → not yet limiting) |
| +3 | −1.08 | −15.71 | 14.63 (just reaching ceiling) |
| +6 | −1.02 | −12.92 | 11.90 |
| +9 | −1.02 | −10.90 | 9.88 |
| +12 | −1.02 | −9.12 | 8.10 |

Peak pins to the −1 ceiling once engaged; RMS rises and **crest collapses** with gain = the limiter doing its job.

### True Peak Limiting — the compliance proof (faithful render, +9, ceiling −1.0)

| | integrated LUFS | **true-peak dBTP** | sample-peak |
|---|---|---|---|
| **TP on** | −10.38 | **−1.018** ✓ (under −1.0) | −1.024 |
| TP off | −10.36 | **−0.984** ✗ (over −1.0) | −0.990 |

Same loudness, same sample-peak ≈ −1.0 — but **TP off lets the inter-sample true-peak overshoot the target**.
The gap is small on this loop (~0.03 dB) and grows on brighter/denser material. **TP on for any −1.0 dBTP master.**

### Style crest map (@ +9 gain, ceiling −1, 4× OS — density ranking)

| style | crest | RMS | character (manual) |
|---|---|---|---|
| **Aggressive** | **9.49** | −10.49 | densest/loudest — near-clipping, hot |
| Transparent | 9.88 | −10.90 | clean, no pumping/color |
| Dynamic | 9.93 | −10.92 | enhances transients before limiting |
| Allround | 9.95 | −10.98 | balanced loudness vs transparency |
| Bus | 9.97 | −10.99 | non-transparent glue/pump (the screenshot's pick for drums) |
| Punchy | 9.97 | −10.99 | most apparent, a little vibey pump |
| Safe | 10.37 | −11.39 | distortion-free at all costs, not loudness — **Lookahead/Attack/Release/Channel-Link are fixed** (non-adjustable on this style) |
| **Modern** | **10.56** | −11.57 | most dynamic-preserving — the v2 default "best for all" |

Meters rank **density** (Aggressive squashes most; Modern/Safe keep the most transient); the *pumping/glue feel*
that separates e.g. Bus from Transparent is perceptual and partly invisible to a crest number — A/B by ear,
loudness-matched, when style "feel" matters.

> **Safe is special:** its time controls (Lookahead / Attack / Release / Channel Linking) are **not user-adjustable**
> — Safe runs its own fixed, distortion-avoiding envelope (Sound on Sound). Setting `lookahead`/`attack`/`release`
> on a Safe-style `.state` is a no-op; pick another style if you need to dial the envelope.

### The render path (faithful — a limiter owns the ceiling)

`presets/vst/apply_vst_preset.py` **renormalizes its output** to `output_peak_dbfs` — for a limiter this
re-scales the careful ceiling and pushes true-peak back over target. **Use `[L] apply-vst-chain` instead** (it
writes the plugin output unchanged). The enums (style/OS/TP/dither) ride a **`.state`** blob; override the one
per-track knob, `gain`, via the float `parameters` (applied *after* `state_path`):

```
apply-vst-chain {path:<in>, out_path:<out>, plugins:[{
  plugin_path:"/Library/Audio/Plug-Ins/VST3/FabFilter Pro-L 2.vst3",
  state_path:"presets/vst/fabfilter-prol2-streaming-master.state",
  parameters:{gain:<dB>} }]}
```

Verified: state (`Transparent`/−1.0/TP on/4× OS/dither off) + `gain:9` → **−1.018 dBTP** ✓, `state_loaded:true`.
Shipped: `presets/vst/fabfilter-prol2-streaming-master.{state,json}`. **Regenerate the `.state` with a `process()`
flush:** set the params via `setattr`, then **process a buffer before reading `p.raw_state`** — FabFilter only
commits param changes into `raw_state` on the next process call, so dumping immediately after `setattr` silently
captures the *restored* state, not your config (a real bug we hit: the first blob shipped as Bus/32×/24-bit).
Reload the blob into a fresh instance and introspect to confirm before committing (string enums aren't reachable
by the float dict, so the `.state` is the only way to carry style/OS/dither).

---

# Part B — how Pro-L 2 works (web-research synthesis, adversarially verified, cited)

Released **5 December 2017** as the successor to Pro-L 1 (both co-exist in a session; the 4 original algorithms
are reported to sound identical to v1 at the same settings — user-reported, not a FabFilter spec). Formats: VST,
VST3, **CLAP**, AU, AAX Native, AudioSuite. Licensing: **no iLok**, simple key, offline activation, up to 3
machines; **plugin-only** (no desktop standalone; the iOS "Pro-L 2" is an AUv3 app — App Store / FabFilter forum).

## 1. What's new in Pro-L 2 vs Pro-L 1

- **4 new limiting algorithms** (8 total): **Modern** (new default, "best for all"), **Aggressive** (max
  loudness — EDM/rock/dance), **Bus** (deliberately non-transparent glue/pump — drums & individual tracks),
  **Safe** (distortion-free at all costs, *not* aimed at loudness). The 4 carried over: Transparent, Punchy,
  Dynamic, Allround.
- **Extensive LUFS loudness metering** — Momentary / Short-Term / Integrated, ITU-R BS.1770-4 + EBU R128 (also
  ATSC A/85, TR-B32). SoS calls it the headline new visual element of v2.
- **True-peak metering + dedicated True Peak Limiting mode** (ITU-R BS.1770; MFiT-suitable) — guarantees output
  true-peaks stay at/under the Output Level ceiling.
- **High linear-phase oversampling** (up to **32×** current spec), **immersive/surround** (up to 9.1.6 Dolby
  Atmos with smart channel linking), **external side-chain** (stem mastering), **DC-offset filter**, **dither +
  3 noise-shaping modes**, **Unity Gain**, **Audition (delta) Limiting**, A/B, multiple display modes.

## 2. Controls (what each does)

- **Gain** — the one loudness control: simultaneously lowers the limiting threshold and raises output gain, so
  turning it up = louder + more limiting.
- **Output Level** — the **ceiling** (default 0.0 dB; reads **dBTP** when True Peak Limiting is on).
- **Style** — the 8 algorithms (above). Pick by density-vs-transparency + material.
- **Lookahead** (0–5 ms) — feeds the fast **transient** limiting stage. **Attack / Release** — the slower
  release-envelope stage. The two stages interact: shorter/faster = louder but more distortion; longer/slower =
  cleaner but more pumping. Per-style defaults are well-tuned — usually leave them.
- **Channel Linking** — independent **Transient** and **Release** link knobs (and surround scoping). Lower link
  = wider image but allows L/R level drift; higher = more solid centre.
- **True Peak Limiting** (on/off, ~+5 ms latency); **Oversampling** (4× realtime default; **16×/32× for offline
  renders** per FabFilter; 4× + ≥0.1 ms lookahead keeps inter-sample peaks within ~0.1 dB); **DC Offset filter**;
  **Dithering** + 3 noise-shaping; **Unity Gain** (auto output = −gain, for level-matched audition); **Audition
  Limiting** (delta-listen the gain reduction); **Lock Output**.

## 3. Metering & loudness

- **Meter Scale → `Loudness`** turns on the LUFS meter (other scales: fixed dB, K-12/14/20). **Loudness Time
  Scale**: Momentary / Short-Term / **Integrated** (LRA shows only on Integrated). ITU-R BS.1770-4, always gated.
- **Loudness Meter Target** presets −9 / −14 / −23 / −24 LUFS (+ Custom). Workflow: raise **Gain** until
  Integrated sits within ±1 LU of target.
- **True-peak meter** (ITU-R BS.1770 / EBU R128, MFiT-suitable); the read-out switches dB→**dBTP** when True Peak
  Limiting is on. The main meter shows input, output (RMS + peak), and gain reduction at once. Pause / Reset /
  Auto-Reset.

## 4. Mastering technique (verified starting points)

1. Place Pro-L 2 **last** in the chain (after EQ/comp/saturation). Enable **True Peak Limiting** + the loudness
   meter (Integrated).
2. Set **Output Level** to the platform ceiling: **−1.0 dBTP** (EBU R128 / Spotify / YouTube / Apple), **−2.0
   dBTP** (ATSC A/85 broadcast). Streaming-safe default: −1.0 dBTP.
3. Pick a **style**: Transparent/Modern for clean masters; Allround general; Aggressive for max-loud EDM/rock;
   **Bus** for a drum bus or a single track; Safe when distortion-free matters more than loudness.
4. Raise **Gain** to the integrated **LUFS target** (±1 LU). Rule of thumb: a light streaming master often needs
   only **~1 dB gain reduction** for −14 LUFS; competitive/CD wants several dB more (watch distortion/pump).
5. **Oversampling** 4× (or 16×/32× for a final offline bounce). **Dither LAST**, at the **final bit depth**
   (16 Bits for 44.1/16 distribution), with a noise-shaping mode — and only if Pro-L 2 is the file-writing stage.
6. **A/B loudness-matched** (Unity Gain or Audition) so "louder" doesn't masquerade as "better."

## 5. Pitfalls & gotchas

- **Sample-peak ≠ true-peak.** Without True Peak Limiting, inter-sample peaks overshoot the ceiling (measured
  −0.984 vs −1.0). Turn it on for any dBTP delivery.
- **Don't post-normalize a limiter render** — it defeats the true-peak ceiling. Render faithfully (apply-vst-chain),
  not via the renormalizing preset harness.
- **Dither once, at the end, at the final depth.** Two dithers (Pro-L 2 *and* the delivery stage) = double noise.
  Keep Pro-L 2's dither **Off** if a later stage (`export-deliverables`/`render-mastered`) does the final dither.
- **A bare headless load restores the last GUI state** — set everything explicitly (a `.state`).
- **Loudness is per-track** — the gain to hit −14 LUFS depends on the source; measure → set gain → re-measure.
- **No-iLok, but loads ≠ renders** — screen a new install with `[[vst-verify]]` / `probe_plugin.py "Pro-L 2"` and
  **measure dBTP/LUFS** after.
- **Mono vs stereo LUFS** — a dual-mono file reads ~3 LU quieter than the same as stereo; measure the real
  delivery format.

> **Pure-DSP alternative (no plugin, deterministic):** `[L] render-mastered` (HPF→transient→EQ→normalize→
> **limiter**→dither, auto-targets LUFS + ceiling) and the [[master-track]] pipeline. Reach for Pro-L 2 when you
> want its 8 styles, best-in-class true-peak limiting, or its metering; use `render-mastered` for a hands-off,
> reproducible target. Either way, verify with `[L] measure-loudness` + `[G] check-streaming-targets`.

---

## Sources

FabFilter Pro-L 2 product page, release news (5 Dec 2017), and help/manual pages (overview, advanced settings /
styles, true-peak limiting, oversampling, metering, dithering) · Sound on Sound (Pro-L 2 review) · Sage Audio,
Production Expert (technique) · FabFilter FAQ (no-iLok licensing) · Apple App Store (Pro-L 2 iOS AUv3). Plus
**our own param-surface dump + render/meter results (Part A)** on
`/Library/Audio/Plug-Ins/VST3/FabFilter Pro-L 2.vst3` via Pedalboard 0.9.23.
