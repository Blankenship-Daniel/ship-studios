---
name: la-3a
description: "Use when running the UADx Teletronix LA-3A for solid-state opto leveling / glue / parallel 'smash' on a drum bus, electric guitar, vocal, bass, room mics, or any source that wants smooth program-dependent leveling with a touch of grit — 'LA-3A', 'Teletronix', 'opto compressor on the guitar/drums', 'audio leveler', 'parallel-compress the drums with the LA-3A', 'level this vocal', 'that aggressive opto sound'. The measured, plugin-specific deep-dive of [[vst-compress]] — a solid-state electro-optical (T4) compressor that LEVELS (reduces crest, unlike the crest-holding tube [[fairchild-660]]) and colors with ODD/3rd-harmonic grit, grounded in the real 8-enum-param Pedalboard surface + peak-reduction / comp-vs-limit / HF-emphasis / parallel render numbers in docs/vst/la-3a.md. Stemmy MCP, the `vst` extra."
argument-hint: <wav-or-bus> [goal: drum-glue|bus-level|parallel|guitar|vocal]
---

# la-3a — drive the UADx Teletronix LA-3A (measured)

The plugin-specific, measured version of [[vst-compress]] for the **UADx Teletronix LA-3A**
(`/Library/Audio/Plug-Ins/VST3/uaudio_la3a.vst3`) — Universal Audio's model of the **Teletronix LA-3A
Audio Leveler**, the 1969 **solid-state electro-optical (T4)** successor to the tube LA-2A. It is the
**solid-state opto LEVELER** counterpart to the tube COLOR of [[fairchild-660]] and the VCA glue of
[[ssl-bus-compressor-2]] — faster and more aggressive than an LA-2A, smoother and less colored than an
1176. Full field guide — param surface, the peak-reduction / comp-vs-limit / HF-emphasis maps, the
harmonic signature, recipes, pitfalls, sources — lives in
[`docs/vst/la-3a.md`](../../../docs/vst/la-3a.md). This skill is the workflow.

## The governing facts (read first — all measured on this rig)

1. **It is a REAL leveler — it reduces crest** (the opposite of the crest-holding tube [[fairchild-660]]).
   On the Watercolors warm drum bus, pushing **Peak Reduction** dropped crest 17.2→14.2 at pr 4 (~3 dB GR)
   and →12.8 at pr 6 (~11 dB). It levels transients; that's the point.
2. **No ratio / attack / release knobs.** It's an opto with **program-dependent attack/release**. You sculpt
   with **PEAK REDUCTION** (amount/threshold), **COMP/LIM** (gentle vs hard), **HF EMPHASIS** (the drum
   control), **GAIN** (clean makeup), and **MIX** (parallel).
3. **PEAK REDUCTION has a DEAD ZONE at the bottom** (pr 0–2 = no gain reduction on this material); it bites
   from ~pr 3–4 up. More PR = more GR + lower crest + **lower output** → make up with **GAIN**.
4. **HF EMPHASIS (0–100, default 0) is the signature control — and it runs the way you'd want, not the way
   the name suggests.** Raising it **takes the low end out of the detector** so the kick/bass stop driving
   gain reduction: hf 0 = full-range detection = **most GR, darkest, most pumped**; hf 35–100 = **less GR,
   crest recovers (12.8→15.7), the kick punches through, and the balance tilts UP into low-mid body +
   presence** (it's the LA-3A's built-in sidechain HPF). On drums, **raise HF to keep punch**; leave it at 0
   for dense, dark, pumped leveling (great as the crushed layer in parallel).
5. **COMP vs LIM: Limit clamps harder and slightly darker** than Comp at the same Peak Reduction (lower
   crest, lower peak, lower centroid). Comp = gentle leveling; Limit = firmer/limiting.
6. **It colors with ODD / 3rd-harmonic solid-state grit, NOT even-harmonic tube warmth.** Measured on a
   1 kHz tone: H3 dominant (~−48 dB), H2/H4 at the noise floor; **~0 % THD until it's actually compressing,
   then ~0.37 %.** Clean-ish — cleaner than the tube [[fairchild-660]] / [[pultec-eqp-1a]]. **Engaged-flat
   (pr 0) is clean** except the makeup gain (not a colored passthrough).
7. **GAIN is perfectly clean makeup** (~4.9 dB per unit, zero tone change). **MIX is built-in parallel**
   (0 = dry, 100 = wet) and **blends AFTER the makeup gain** — so for a parallel smash you must drive GAIN
   up or the crushed (quiet) wet adds nothing.
8. **Tooling:** 8 params, **all enums**. `peak_reduction` / `gain` / `hf_emphasis` / `mix` are numeric (the
   `apply-vst-chain` float dict can set those), but **`comp_limit` and `meter` are STRING enums the float
   dict can't set** → drive it through the **[[vst-preset]] harness** (`presets/vst/apply_vst_preset.py`,
   which `setattr`s every param) whenever you need Limit mode (which you usually do).
9. **It adds level + color → always A/B at matched loudness** ([[level-match]] / `render-ab`). **LA-3A = MONO
   unit** (runs linked dual-mono on a stereo bus). It's a leveling/glue stage, **not** a master — hand off to
   [[master-track]].

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **Load the `uaudio_la3a.vst3` UADx native build** — it **renders headless & processes offline**
  (`RENDERS ✓` here). The `/Library/Audio/Plug-Ins/Components/UAD Teletronix LA-3A.component` twin is the
  legacy UAD-2 build and **passes audio through unprocessed** offline — never use it ([[vst-verify]] /
  [[vst]]). UADx native is the no-iLok-dongle perpetual lineage, but re-verify
  `RENDERS ✓` on a new machine.
- Balance the bus first ([[mix-balance]]); hand the leveled/glued result to [[master-track]] — this is a
  leveling/glue stage, **not** a master/limiter.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` (crest / LRA / PLR / true-peak) + `[L] measure-microdynamics`
   (per-band block-crest + punch) + `[L] measure-spectrum` (centroid + low/low-mid ratio). The "before."
2. **Pick the move** from the table below. Decide Comp vs Limit, how much Peak Reduction, and — on drums —
   how much HF EMPHASIS (raise it to keep the kick punching).
3. **Apply via the preset harness** (so `comp_limit`/`meter` land):
   `…/stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py presets/vst/la3a-*.json <in> <out>`.
   Ready-made: **`la3a-drum-glue`** (validated ★), **`la3a-bus-level`**, **`la3a-parallel-smash`**.
4. **Dial it to the result:** more PEAK REDUCTION = more leveling (watch crest fall); **COMP→LIMIT** to grab
   harder; **raise HF EMPHASIS** if the kick pumps / it gets dark; **GAIN** for makeup; **MIX** down (and
   GAIN up) for parallel. Re-measure after each change.
5. **Prove it** — re-`measure-loudness` / `measure-microdynamics` / `measure-spectrum`: expect **crest down**
   (leveling), **LRA tighter**, denser LUFS at the same peak, and — if HF was raised — **low-mid/presence up**
   (more body/forward), not darker. **A/B loudness-matched** (`[L] render-ab` / [[level-match]]) so "denser"
   isn't just "louder."
6. **QC** — `[G] detect-mix-issues` (genre/intent set) to catch pumping (too much GR / hf too low on a
   bass-heavy bus) or a dull/over-leveled bus; reconcile any mono "dull/dynamics" flag against the stereo
   meters ([[gemini-audio-understanding]]).

## Recipes (measured starting points — re-dial to your level)

| Goal | comp/lim | peak_reduction | hf_emphasis | mix | gain | Preset |
|---|---|---|---|---|---|---|
| **Drum glue** (keep punch) ★ | Comp | **4.5** | **35** | 100 | 5 | `la3a-drum-glue` |
| **Firm bus leveling** (in-your-face) | **Limit** | 6 | 20 | 100 | 5 | `la3a-bus-level` |
| **Parallel drum smash** | **Limit** | **9** | **0** | **45** | **9.5** | `la3a-parallel-smash` |
| **Electric guitar** (the classic) | Comp/Limit | 4–6 | 0–30 | 100 | makeup | (recipe) |
| **Lead vocal leveling** (mono src) | Comp | 3–5 | 0–20 | 100 | makeup | (recipe) |
| **Bass** (mono src) | Comp | 4–6 | 0 | 100 | makeup | (recipe) |
| **Room / overheads crush** | Limit | 6–9 | 0 | 100 | makeup | (recipe) |

★ the validated gentle glue (`presets/vst/la3a-drum-glue.json` → `projects/watercolors/mix/la3a_drum-glue_demo.wav`).
**PEAK REDUCTION** 0–10 (dead zone ~0–2; bites from 3–4; more = more GR + lower crest, make up with GAIN).
**COMP/LIM** Comp=gentle, Limit=harder/darker. **HF EMPHASIS** 0–100 (raise to keep lows off the detector →
less pump, more punch + brightness). **GAIN** 0–10 clean makeup (~4.9 dB/unit). **MIX** 0–100 (parallel;
blends after makeup, so raise GAIN when you blend down). Leave `power` on, `master_bypass` off; the harness
peak-trims to −1 dBFS so loudness-match before judging.

## Reporting to the user

State the settings (comp/limit · peak reduction · HF emphasis · mix), before→after **crest / LRA / true-peak**
+ the LUFS gain at matched peak (density) and any tonal shift (low-mid/presence up if HF raised), that it ran
headless via the `uaudio_la3a.vst3` build, and that the character is **solid-state opto leveling + odd/3rd-
harmonic grit** (not tube warmth, not crest-holding color). A/B loudness-matched so "denser" isn't "louder."

## Pitfalls

- **Wrong build = passthrough** — the `/Components/UAD Teletronix LA-3A.component` (legacy UAD-2) twin passes
  audio through offline. Load `uaudio_la3a.vst3`; verify `RENDERS ✓` + measure *detail* ([[vst-verify]]).
- **`comp_limit` / `meter` are string enums** — `apply-vst-chain`'s float dict can't set them (you'd be stuck
  in Comp). Use the [[vst-preset]] harness for any Limit-mode or metered recipe.
- **Peak Reduction below ~3 does nothing** (dead zone) — if you hear no change, it's under threshold; push it up.
- **Bass-heavy bus pumps at hf 0** — the low end is hammering the detector; **raise HF EMPHASIS** (20–50) so
  the kick stops triggering GR (the LA-3A's built-in sidechain HPF).
- **Parallel did nothing?** MIX blends after makeup — **raise GAIN** so the crushed wet is loud enough to hear
  when you blend it back.
- **It levels + colors → louder & a bit gritty** — A/B at matched loudness; don't mistake added level for "better."
- **Mono unit** — it's dual-mono on a stereo bus (fine for drum/instrument buses; for true stereo glue reach
  for [[ssl-bus-compressor-2]] or a stereo comp).
- **It's not a master** — leveling/glue stage; hand off to [[master-track]] for loudness/limiting.

## Related

- [`docs/vst/la-3a.md`](../../../docs/vst/la-3a.md) — the full measured field guide (Part A measured + Part B cited)
- [[vst-compress]] — the generic compressor skill this specializes · [[fairchild-660]] — tube COLOR sibling (holds crest, even-harmonic) vs the LA-3A's LEVELING (drops crest, odd-harmonic) · [[dbx-160]] — clean feed-forward true-RMS VCA that ADDS punch (RAISES crest) on drums, the opposite of the LA-3A's leveling · [[ssl-bus-compressor-2]] — VCA stereo glue
- [[vst-preset]] — apply enum chains (required for Limit mode) · [[vst-verify]] — prove the build renders · [[vst-shootout]] — judge setting variants
- [[finalize-mix]] / [[stem-master]] — stages this fits · [[drum-punch]] — pure-DSP transient design (no plugin) · [[multiband-compress]] — band-split dynamics
- [[gemini-audio-understanding]] — why meters (not Gemini mono) own crest/GR
