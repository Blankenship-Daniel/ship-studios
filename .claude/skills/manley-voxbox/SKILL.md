---
name: manley-voxbox
description: "Use when running the UAD/UADx Manley VOXBOX Channel Strip for an all-tube VOCAL channel, or for smooth tube colour + opto compression + passive Pultec EQ + de-essing on vocals, bass, acoustic, drums, or a bus — 'Manley VOXBOX', 'VOXBOX', 'tube vocal channel strip', 'put the VOXBOX on the vocal', 'that Manley tube sound', 'opto comp + Pultec EQ + de-ess in one box', 'smooth hi-fi tube channel'. The measured, plugin-specific deep-dive of [[vst-channel-strip]] — a 4-block tube strip (tube pre + passive electro-optical compressor + passive MEQ-5-style 3-band EQ + de-esser/opto-limiter), grounded in the real 25-enum-param Pedalboard surface + isolation/THD/comp/EQ/de-ess render numbers in docs/vst/manley-voxbox.md. The SMOOTH/OPEN tube counterpart to the clean [[ssl-native-channel-strip-2]] and punchy [[api-vision-channel-strip]] / [[kit-bb-a5]]. Renders headless (UADx native, no dongle here). Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: vocal|drum-glue|bus-glue|colour|level|air|de-box|de-ess|limit]
---

# manley-voxbox — drive the UADx Manley VOXBOX Channel Strip (measured)

The plugin-specific, measured workflow for the **UADx Manley VOXBOX Channel Strip**
(`/Library/Audio/Plug-Ins/VST3/uaudio_manley_voxbox.vst3`) — UA's model of the **Manley Laboratories VOXBOX** (1998),
a mono **all-tube** "reference channel strip" and the most celebrated **vocal channel** ever built. Four blocks in one:
a **tube mic/line preamp**, a **passive electro-optical compressor**, a **passive Pultec-style (MEQ-5-derived) 3-band
EQ**, and a **de-esser / opto limiter**, plus an output transformer. It's the **smooth, open, "hi-fi" tube** member of
[[vst-channel-strip]] — the only deep-dive of ours with comp *and* EQ *and* de-ess in one box. Full field guide — real
param surface, footguns, recipes, our numbers, sources — [`docs/vst/manley-voxbox.md`](../../../docs/vst/manley-voxbox.md).
This skill is the workflow.

## The governing facts (read first — all measured on this rig, Pedalboard 0.9.23)

1. **Renders headless — use the `uaudio_` build.** `uaudio_manley_voxbox.vst3` loads + processes (UADx native). The
   `UAD Manley VOXBOX.component` twin is the **passthrough** offline build — never load it
   ([[vst-verify]]). UADx native = no DSP/iLok dongle for the render here.
2. **The audio path is NOT the GUI layout.** Internal flow is **INPUT → COMPRESSOR → tube PREAMP → EQ → DE-ESS/LIMITER
   → OUTPUT** — the **compressor is FIRST** (it clamps transients before the first tube), and it's **fixed**. So `input`
   feeds the comp *and* the tube.
3. **`input` + `gain` + Mic = the tube drive/colour.** Line in3 g40 = **0.002 %** THD (clean); Mic in6 g50 = **5 %**;
   Mic in10 g60 = **67 %**, **even-harmonic** (H2 −4.9 dB). **Mic saturates ~10–20 dB sooner than Line.** On drums the
   drive lowers crest *and* **BRIGHTENS** as it distorts (centroid rises). `input` is an attenuator (higher = hotter).
4. **The opto compressor RAISES crest** on transient material (it levels the body, leaves transients): drum loop crest
   14.6 → 19.5. It's a smooth **program-dependent opto** leveller (nominal "3:1", *not* a fixed ratio) — not a grabber.
   **`comp_thresh` is RELATIVE TO `input`, and HIGHER number = MORE GR.** **Slow attack = transients pass; Fast = control.**
5. **The Pultec EQ dials are nonlinear 0–10, not dB** (action is 5–10): `lo_peak` 10 ≈ +10.5 dB, `hi_peak` 10 ≈ +8.6 dB
   (a **bell**), `mid_dip` 10 ≈ −11.7 dB. **PEAK-DIP-PEAK only** — LOW boost / MID cut / HIGH boost; no low/high cut, no
   mid boost, no Q. **`hi_peak_freq` has 11 values incl. 2 kHz** (GUI label hides it).
6. **De-ess ducks the selected band (3K/6K/9K/12K); the 5th position `Limit` is a smooth opto 10:1 limiter** (pulls
   peaks, crest ↓ — not a fast brickwall). Higher `de_ess_thr` = more; it acts only where there's energy at the freq.
7. **All 25 params are enums → drive it with the [[vst-preset]] harness, not `apply-vst-chain`'s float dict.** The
   string switches (`source_select`=Mic, `low_cut`, `comp_byp`/`eq_byp`/`de_ess_byp`, `comp_attack`/`comp_rel`,
   `de_ess_sel`, `sc_link`, `transformer_byp`, `meter`) are the character controls and can't be set float-only. The
   output transformer (`transformer_byp`) is **near-transparent** here. `sc_link` is a **stereo** link (inert in mono).
   **Meters own it** (Gemini hears mono).

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]` perceptual tools
  (optional, `GEMINI_API_KEY`) for an A/B read.
- Confirm the build: `[L] list-vst-plugins {name_contains:"VOXBOX"}` → take the **`uaudio_manley_voxbox.vst3`** path.
  Screen with `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "voxbox"` (expect `RENDERS ✓`). Dump the
  live surface any time: `… presets/vst/dump_params.py uaudio_manley_voxbox`.
- **It loads ≠ it rendered** — always re-measure detail after (a 0.00 spectrum/crest delta = the `.component` passthrough twin).

## The parameter surface (25 enums — see the doc for the full table)

Numeric enums (settable via float on-grid): `input` 0–10 · `gain` 40/45/50/55/60 · `comp_thresh` 0–10 · `lo_peak`/
`mid_dip`/`hi_peak` 0–10 (mid is negative) · the three `*_freq` · `de_ess_thr` 0–10 · `output` −60…+12 · `phase` 0/180.
**String enums (harness only):** `source_select` Line/Mic · `low_cut` Off/80/120 · `sc_link` Sep/Link · `comp_byp`
Byp/In · `comp_attack` Fast…Slow · `comp_rel` Slow…Fast · `eq_byp` Byp/In · `de_ess_byp` Byp/In · `de_ess_sel`
3K/6K/9K/12K/Limit · `meter` GR/In/Pre Out/Out/DS · `transformer_byp` Byp/In · `power`/`master_bypass`.
Freq grids: LOW 20–1000 · MID 200–7000 · HIGH **1500/2000/3000/4000/5000/6400/8000/10000/12000/16000/20000**.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid) + `[L] measure-loudness` (crest/PLR). The
   "before" column. Decide the job: **vocal channel** (full chain), **tube drum/bus colour + leveling**, or **gentle
   bus tone + peak control**.
2. **Pick the path.** *Colour/glue:* `source_select="Mic"`, push `input`/`gain` (in4 g50 ≈ moderate). *Clean:*
   `source_select="Line"`, low `input`/`gain` (in3 g40 ≈ 0.002 % THD).
3. **Set the compressor.** `comp_byp="In"`; raise `comp_thresh` (and/or `input`) until the GR is what you want —
   remember higher number = more, relative to input. **Vocals:** Medium/Med-Slow, ~3 dB GR. **Drums:** Medium opens
   transients (crest ↑); Fast attack to control. **Bass:** Med Fast.
4. **Dial the EQ** (`eq_byp="In"`). LOW PEAK @70–200 for weight/chest, HI PEAK @10–16k for air (both bells, 0–10
   nonlinear), MID DIP @500–1.5k to de-box/de-honk (cut-only). Remember the dial action is 5–10.
5. **De-ess / limit** (`de_ess_byp="In"`). `de_ess_sel` 6K (typical sibilance) / 3K (chesty) / 9–12K (bright) + raise
   `de_ess_thr`; or `de_ess_sel="Limit"` for smooth wideband peak control on a bus.
6. **Build a preset** (`presets/vst/voxbox-*.json`) setting **all 25** params explicitly, and apply with the harness:
   `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
   projects/<track>/mix/<stem>_voxbox.wav` (it `setattr`s string enums and peak-normalizes, absorbing the drive/no-make-up
   level). Set `dump_state=true` via `apply-vst-chain` once dialed for a byte-stable re-render.
7. **Prove it** — re-`measure-spectrum`/`measure-loudness`. **Comp/colour → crest UP** (optical leveling opens
   transients) or DOWN under heavy drive; **`Limit` → crest DOWN** (peak control); EQ moves centroid/tilt. A 0.00 delta
   = passthrough twin. A/B loudness-matched ([[level-match]] / `[L] render-ab`).
8. **QC** — `[G] detect-mix-issues` / `mastering-feedback` (genre/intent set) for over-drive or over-de-ess; cross-check
   any mono "harsh/dull" flag against the meters ([[gemini-audio-understanding]]). It's a per-track/bus
   insert, not a master — hand the result to [[master-track]] for loudness.

## Move table (measured)

| Goal | VOXBOX move |
|---|---|
| **Vocal channel** ★ | `Mic`, in3 g50, `low_cut 80`, comp In thr~9 Med/Med-Slow (~3 dB GR), EQ lo 3@100 / mid −3@700 / hi 5@12k, de-ess 6K (shipped `voxbox-vocal-channel`). |
| **Warm tube drum bus** ★ | `Mic`, in4 g50, comp In thr8 Med/Med, EQ lo 5@70 / hi 5@10k / mid −3@500 → crest 14.6→19.5 (opens transients), darker/rounder (shipped `voxbox-drum-glue`). |
| **Gentle bus tone + peak control** | `Line`, in4 g40, light comp, Pultec smile (lo 3@50 / hi 4@16k), `de_ess_sel Limit` thr5 → crest 14.6→12.8, +4 dB denser (shipped `voxbox-bus-tube-glue`). |
| **More tube colour** | `Mic`, raise `input`/`gain` (in6 g50 ≈ 5 % THD; in10 g60 = nuclear) — even-harmonic, brightens as it drives. |
| **Smooth leveling (vocal/bass)** | comp Medium/Med-Slow (bass: Med Fast), ~3 dB GR; Slow atk + Slow rel = fader-ride. |
| **Open transients (drums)** | comp Medium/Slow attack (lets transients pass → crest ↑). |
| **Add air** | HI PEAK 4–6 @10–16k (broad bell); de-ess if it spits. |
| **De-box / de-honk** | MID DIP −3…−6 @500–1k (cut-only bell). |
| **Add weight/chest** | LOW PEAK 4–6 @70–150 (boost bell) — or push the Mic drive. |
| **Tame sibilance** | `de_ess_byp In`, `de_ess_sel` 6K (or 3/9/12K), raise `de_ess_thr`; watch the `DS` meter. |
| **Catch peaks (bus)** | `de_ess_sel Limit`, raise `de_ess_thr` (smooth opto, not a brickwall). |

## Outputs

- `projects/<track>/mix/<stem>_voxbox.wav` + the reusable `presets/vst/voxbox-*.json` (and `.state` if dumped).

## Reporting to the user

State the path (Line clean vs Mic-driven + input/gain), which blocks are engaged (comp thr/attack/release + GR, the EQ
moves, de-ess band or Limit), the before→after **crest / centroid / tilt / target-band deltas** (crest UP = optical
leveling / comp; crest DOWN = the Limit mode or heavy drive), that it ran headless via the `uaudio_` build, and the
preset/`.state` path. A/B loudness-matched so warmth isn't a level illusion.

## Pitfalls

- **Wrong build = silent passthrough** — load `uaudio_manley_voxbox.vst3`, not the `UAD Manley VOXBOX.component` twin.
- **Float dict can't drive it** — the string switches (Mic/HPF/the In engages/attack/release/de-ess-band/transformer) need the [[vst-preset]] harness.
- **Thresholds are "backwards"** — higher `comp_thresh`/`de_ess_thr` = more, and `comp_thresh` is relative to `input` (drive). A quiet input + low threshold number = no action.
- **No comp make-up gain** — recover level with `input`/`gain`/`output` (the harness normalizes for you).
- **EQ is PEAK-DIP-PEAK** (no low/high cut, no mid boost, no Q) and the 0–10 dials are nonlinear (action 5–10); the **HI band has a 2 kHz position** the GUI hides.
- **`Limit` is a smooth opto limiter, not a brickwall** — no ceiling/true-peak; hand off to [[master-track]] / [[fabfilter-pro-l-2]] for the real limiter.
- **`sc_link` is a STEREO link**, not comp↔de-ess; inert in mono. **The output transformer is subtle** here.
- It's a per-track/bus tube channel, **not** mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/manley-voxbox.md`](../../../docs/vst/manley-voxbox.md) — the full measured field guide (Part A measured + Part B history/usage, cited)
- [[vst-channel-strip]] — the generic skill this specializes · [[vst-eq]] / [[vst-compress]] / [[vst-de-ess]] / [[vst-saturate]] — its per-block generic cousins ·
  [[vst-preset]] — apply enum/all-explicit chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- Channel-strip siblings: [[ssl-native-channel-strip-2]] / [[ssl-4k-e]] (clean British) · [[api-vision-channel-strip]] / [[kit-bb-a5]] (punchy API) · [[kit-bb-n105]] / [[kit-bb-n73]] (Neve, warm) · [[helios-type-69]] (warm British pre+EQ, no comp)
- Tube cousins: [[fairchild-660]] (vari-mu tube comp) · [[studer-a800]] / [[ampex-atr-102]] (tape warmth)
- Pure-DSP twins (no plugin): opto/tube colour → `[L] saturate-loop`; leveling → `[L] compress-loop`; de-ess → [[de-ess]]; air → [[excite]]; surgical/tilt EQ + weight → `[L] apply-eq`
- [[mix-check]] (find the problems first) · [[vst-verify]] (why the build matters)
