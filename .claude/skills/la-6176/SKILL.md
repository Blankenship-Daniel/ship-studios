---
name: la-6176
description: "Use when running the UAD/UADx LA-6176 Signature Channel Strip — a complete one-pass console channel (610 tube preamp + 2-band EQ + a switchable 1176-OR-LA-2A compressor) — on a vocal, bass, guitar, drum bus, or any source: 'LA-6176', '6176 channel strip', 'UA channel strip on the vocal', '610 preamp + 1176', 'put the LA-2A / 1176 on this', 'that Coldplay/Adele vocal chain', 'tube preamp + compressor in one', or when you want to pick FET-fast (1176) vs opto-smooth (LA-2A) compression in one strip. The measured, plugin-specific deep-dive of [[vst-channel-strip]] (preamp+EQ+comp, with a real compressor unlike [[helios-type-69]]) — grounded in the real 26-enum-param surface + isolation/THD/dynamics numbers in docs/vst/la-6176.md. Stemmy MCP, the `vst` extra. UADx native (no iLok)."
---

# la-6176 — drive the UADx LA-6176 Signature Channel Strip (measured)

The plugin-specific, measured workflow for the **UADx LA-6176 Signature Channel Strip**
(`/Library/Audio/Plug-Ins/VST3/uaudio_la_6176.vst3`) — UA's **Bill Putnam Jr. Signature Edition** of the hardware
**6176** (a **610 tube/transformer preamp + 1176 FET compressor**), with the plug-in's headline addition: a
**dynamics MODE switch** that makes the compressor either the **fast 1176** or the **slow, gentle LA-2A**. So it's a
**preamp + 2-band EQ + two-flavour compressor** in one pass — the all-in-one console-channel member of
[[vst-channel-strip]] *with a real compressor* (unlike the EQ-only [[helios-type-69]]). Full field guide — real param
surface, footguns, recipes, our numbers, sources — [`docs/vst/la-6176.md`](../../../docs/vst/la-6176.md). This skill
is the workflow.

## The governing facts (read first — all measured on this rig)

1. **Renders headless — use the `uaudio_` build.** `uaudio_la_6176.vst3` loads + processes (UADx native, **no iLok**).
   The `UAD LA-6176 Channel Strip.component` is the UAD-2/Apollo **passthrough** twin — never load it
   ([[uadx-uaudio-build-renders-headless]]). `probe_plugin.py` *passes* here (it has a numeric output knob), but a
   bare-load render is **NOT a clean reference** — see #2.
2. **A bare load already compresses.** Default = `Dyn In` + 1176 @ input 3 / 8:1 / mix 10 (~5 dB GR; default-load
   crest 14.6 → 12.3). For a clean A/B set `dyn_bypass:"Dyn Byp"` + `eq_bypass:"EQ Byp"` (or `master_bypass:true`,
   which nulls perfectly). **Always loudness-match the A/B.**
3. **Preamp: Line/Hi-Z are line-level; Mic is a high-gain MIC pre (footgun + heavy-colour path).** Line g0 = 0.24 %
   THD (clean) → Line g+10 = 3.5 % (H2/even-harmonic tube warmth, crest 14.2→11.3). **Mic on a line-level stem ≈
   40 % THD** (crest → ~5) — it expects −40…−60 dBFS. **Use Line/Hi-Z on stems; reach for Mic only as deliberate
   saturation** with `input_pad:"-15 dB"` (the pad acts **on the Mic stage only** — inert on Line) + `input_gain:-10`.
   **Hi-Z ≡ Line** offline; the impedance options are an Apollo/Unison feature (tone-inert in native use).
4. **EQ = two broad SHELVES, gain ~1:1, symmetric.** LOW corner 70/100/200 (higher reaches up into the body); HIGH
   corner 4.5k/7k/10k (lower = broader, reaches down). `±9` set → `±~5–6`. `cut_filter:"75Hz"` is a separate HPF
   (rumble; crest up, brighter). **EQ sits BEFORE the compressor** — a low boost *drives more GR* (proven: +8.1 dB
   shelf → only +1.16 dB out through the 8:1 comp).
5. **Dynamics — the contrast IS the plugin (`dyn_mode`).** **1176** (FET, fast): crest **falls** with input/ratio;
   `1176_atk`/`1176_rel` = **0 slow → 10 fast** (atk10 catches transients crest→11.0, atk0 lets them through →14.8);
   **ALL** = all-buttons crush + level/aggression jump + ~4× THD; `1176_sc_filt` HPFs the *detector*; `1176_mix` =
   **parallel** (0 = dry, 10 = full wet). **LA-2A** (opto, slow, program-dependent, **no time knobs**): on drums it
   **RAISES crest** (pk3→13.6, pk9→18.2 — punch-glue); clamps sustained sources hard; `la2a_ratio` Comp/Limit. The
   **inactive mode's controls go inert**, so each block is self-contained.
6. **All 26 params are enums → drive it with the [[vst-preset]] harness, not `apply-vst-chain`'s float dict.** The
   character/mode switches are string enums and the dynamics knobs are **digit-prefixed** (`1176_atk`…) — both need
   `setattr`. **Meters own it** (Gemini hears mono): read crest / centroid / tilt / THD, not vibes.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]` perceptual tools
  (optional, `GEMINI_API_KEY`) for an A/B read.
- Confirm the build: `[L] list-vst-plugins {name_contains:"6176"}` → take the **`uaudio_la_6176.vst3`** path. Dump
  the live surface any time: `../stemmy-loops-mcp/.venv/bin/python presets/vst/dump_params.py uaudio_la_6176`.
- **It loads ≠ it rendered** — re-measure detail after (a 0.00 spectrum/crest delta = the `.component` twin loaded).

## The parameter surface (26 enums — authoritative; full table in the doc)

- **610 preamp:** `input_select` (`(Mic) 500`·`(Mic) 2.0k`·`Line`·`(Hi-Z) 47k`·`(Hi-Z) 2.2M`) · `input_pad`
  (Off·`-15 dB`, Mic-stage only) · `input_gain` (−10…+10, 5 dB steps = the GAIN/drive) · `polarity` · `cut_filter`
  (Off·75Hz HPF) · `level` (0–10 output fader).
- **610 EQ:** `eq_lo_freq` (70·100·200) · `eq_lo_gain` (±9, 1.5 steps) · `eq_hi_freq` (4500·7000·10000) ·
  `eq_hi_gain` (±9) · `eq_bypass` (EQ In·EQ Byp).
- **Dynamics:** `dyn_mode` (**1176·LA2A**) · `dyn_bypass` (Dyn In·Dyn Byp). **1176:** `1176_input` (drive/threshold)
  · `1176_output` (makeup) · `1176_ratio` (1:1·4:1·8:1·12:1·20:1·**ALL**) · `1176_atk`/`1176_rel` (0 slow→10 fast) ·
  `1176_sc_filt` (detector HPF) · `1176_mix` (parallel, 0 dry→10 wet). **LA-2A:** `la2a_ratio` (Comp·Limit) ·
  `la2a_pk_red` (peak reduction) · `la2a_gain` (makeup).
- **Global:** `meter` (Preamp·GR·Out, cosmetic) · `power` · `master_bypass` (the only true null).

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness`
   (crest/PLR). The "before" column. Decide the job: **vocal/instrument channel**, **drum glue (punchy 1176 vs smooth
   LA-2A)**, **bus glue**, or **colour/saturation**.
2. **Pick the path.** Line (clean → gentle warmth via `input_gain`); Mic only for deliberate heavy saturation (pad +
   `input_gain -10`). Add `cut_filter:"75Hz"` for rumble on close-mic'd sources.
3. **Dial the EQ** (broad shelves): low corner 70/100/200, high corner 4.5k/7k/10k, `±` gain. Remember EQ → comp, so
   a boost drives more GR.
4. **Pick the compressor by feel.** `dyn_mode:"1176"` to *grab*/punch (set `1176_input` for GR, ratio 4:1 gentle →
   ALL aggressive, attack low to keep punch / high to tame, `1176_mix` < 10 for parallel). `dyn_mode:"LA2A"` to
   *level* smoothly (Comp/Limit, `la2a_pk_red` for amount) — on drums this *raises* crest (punch-glue).
5. **Build a preset** (`presets/vst/la6176-*.json`) setting **all 26** params explicitly (so the inert mode + bypass
   states are deterministic), and apply with the harness: `../stemmy-loops-mcp/.venv/bin/python
   presets/vst/apply_vst_preset.py <preset.json> <in> projects/<track>/mix/<stem>_la6176.wav` (it `setattr`s string +
   digit-prefixed enums and peak-normalizes, absorbing the drive/makeup level). Set `dump_state=true` via
   `apply-vst-chain` once dialed for a byte-stable re-render.
6. **Prove it** — re-`measure-spectrum`/`measure-loudness`. **Preamp drive / 1176 → crest DOWN** (+ harmonics, low
   fill); **LA-2A on drums / clean EQ / HPF → crest UP**; centroid/tilt move with the shelves. A 0.00 delta =
   passthrough twin. A/B loudness-matched ([[level-match]] / `[L] render-ab`).
7. **QC** — `[G] detect-mix-issues` / `mastering-feedback` (genre/intent set) for over-drive (harsh/distorted),
   over-compression (pumping/lifeless), or sibilance (the strip has no de-esser → follow with [[de-ess]]). Cross-check
   any mono "dark/harsh" flag against the meters ([[gemini-mastering-feedback-cross-check]]). It's a per-track/bus
   colour+EQ+comp insert, **not** a master — hand the result to [[master-track]] for loudness.

## Move table (measured)

| Goal | LA-6176 move |
|---|---|
| **Warm + tight drum bus** ★ | `Line`, `input_gain 5` (1.5 % tube warmth), low 100 +3 / hi 10k +1.5, parallel **1176** 4:1 input 4 atk 2 mix 6 `sc_filt` on → crest 14.6→12.1, centroid ↓, low ↑ (the shipped `la6176-warm-drum-glue` preset). |
| **Punchy drum glue (opto)** | `Line`, hi 7k +3, **LA-2A** Comp pk 6 → crest 14.6→16.1 (transients preserved, sustain leveled — `la6176-la2a-drum-punch`). |
| **Vocal channel** ★ | `Line`, `cut_filter 75Hz`, hi 10k +3 air, **LA-2A** Comp pk 4 (smooth leveling) — the classic 6176 vocal chain (`la6176-vocal-strip`). Aggressive vocal: **1176** 4:1, input 4, fast attack. |
| **Aggressive drum smash** | **1176** ratio **ALL**, high `1176_input`, blend via `1176_mix` ~4–5 (parallel) — gritty, pumping room crush. |
| **Bus glue** | **LA-2A** Comp low pk (transparent), or **1176** 4:1 slow attack + parallel mix. |
| **Bass / DI** | `(Hi-Z) 47k` (active) / `2.2M` (passive); low 100 weight; **LA-2A** for even sustain or **1176** 4:1 to tame peaks. |
| **Heavy tube colour** | `(Mic) 500`, `input_pad -15`, `input_gain -10`→0 (deliberate saturation; pad off / gain up = more). |
| **Tighten lows / rumble** | `cut_filter 75Hz` + low shelf cut (e.g. lo 100 −3). |

## Outputs

- `projects/<track>/mix/<stem>_la6176.wav` + the reusable `presets/vst/la6176-*.json` (and `.state` if dumped).

## Reporting to the user

State the path (Line/Mic + gain, EQ moves), **which compressor mode** (1176 vs LA-2A) and its settings, the
before→after **crest / centroid / tilt / target-band deltas** (crest direction = the tell: 1176/drive down, LA-2A on
drums up), that it ran headless via the `uaudio_` build, and the preset/`.state` path. A/B loudness-matched so
"better" isn't a level/crest illusion.

## Pitfalls

- **Wrong build = silent passthrough** — load `uaudio_la_6176.vst3`, not the `UAD …Channel Strip.component` twin.
- **Bare load ≠ neutral** — it's already compressing (~5 dB GR); bypass dyn/EQ or `master_bypass` for a clean A/B.
- **Mic path on a line-level stem distorts hard** (~40 % THD) — use Line/Hi-Z, or pad + `input_gain -10` if you want it.
- **Float dict can't drive the character** — string switches (`input_select`/`dyn_mode`/`1176_ratio`/`la2a_ratio`/…)
  + the digit-prefixed `1176_*` need the [[vst-preset]] harness.
- **EQ feeds the compressor** — a low-shelf boost drives more GR; commit or make level back post-comp.
- **1176 attack/release are 0=slow→10=fast**; **ALL** jumps level + distorts (loudness-match); **LA-2A has no time
  knobs** (program-dependent — "more" = `la2a_pk_red`).
- **No de-esser** — sibilance after air → [[de-ess]]. It's a channel insert, **not** mastering ([[master-track]]).

## Related

- [`docs/vst/la-6176.md`](../../../docs/vst/la-6176.md) — the full measured field guide (Part A measured + Part B history/usage, cited)
- [[vst-channel-strip]] (the generic skill this specializes) · [[vst-compress]] (its compressor side) · [[vst-eq]] /
  [[vst-saturate]] (its EQ / preamp-drive sides) · [[vst-preset]] (apply enum/all-explicit chains) · [[vst-verify]]
  (prove the build renders) · [[vst-chain]] (the backbone) · [[vst]] (index/doctrine)
- Channel-strip siblings: [[helios-type-69]] (warm British, preamp+EQ, no comp) · [[ssl-4k-e]] / [[ssl-native-channel-strip-2]]
  (clean British) · [[api-vision-channel-strip]] / [[kit-bb-a5]] (punchy API) · [[kit-bb-n105]] / [[kit-bb-n73]] (Neve)
- Compressor siblings (when you want the comp alone): [[la-3a]] (solid-state opto) · [[fairchild-660]] (tube color comp) ·
  [[ssl-bus-compressor-2]] (VCA bus glue)
- Pure-DSP twins (no plugin): FET-style grab → `[L] compress-loop`; tube/transformer colour → `[L] saturate-loop`;
  surgical/tilt EQ → `[L] apply-eq`; air → [[excite]]
- [[mix-check]] (find the problems first) · [[warm-drum-bus]] / [[drum-stems-warm-loops]] (where a warm console colour fits) ·
  [[uadx-uaudio-build-renders-headless]] (why the build matters)
