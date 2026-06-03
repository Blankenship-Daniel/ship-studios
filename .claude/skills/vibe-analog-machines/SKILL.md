---
name: vibe-analog-machines
description: "Use when running the UAD/UADx Vibe Analog Machines (formerly Verve Analog Machines) for fast analog 'vibe' — saturation, warmth, lo-fi tape character, wobble, or preamp grit — on a drum bus, loop, stem, beat, vocal, or mix bus — 'Vibe Analog Machines', 'Verve Analog Machines', 'UAD Vibe', 'add some vibe/character', 'analog saturation/warmth', 'lo-fi / vintage / tape / wobble it', 'sweeten the drums', 'thicken / glow / sputter / distort this', or when you want a one-machine-at-a-time colour box (pick a machine, turn up drive, add warble or tone). The measured, plugin-specific deep-dive of [[vst-saturate]] — a 10-machine (6 tape + 4 preamp) harmonic-saturation + modulation character effect (NOT an EQ, NOT a compressor), grounded in the real 6-param surface + per-machine THD/tonal numbers in docs/vst/vibe-analog-machines.md. Renders headless (UADx native; iLok account, no dongle). A faster/lo-fi cousin of the tape skills [[studer-a800]] / [[ampex-atr-102]] / [[softube-tape]]. Stemmy MCP, the `vst` extra."
---

# vibe-analog-machines — drive the UADx Vibe Analog Machines (measured)

The plugin-specific, measured workflow for the **UADx Vibe Analog Machines**
(`/Library/Audio/Plug-Ins/VST3/uaudio_verve.vst3`). It's UA's analog **saturation/coloration** box: pick one of
**10 modeled "machines"** (the colour-swatch row), set **DRIVE** (the amount), shape with the second knob —
**WARBLE** (tape wow/flutter) on the 6 *tape* machines or **TONE** (brightness) on the 4 *preamp* machines — and trim
the output. **It is harmonic saturation + modulation — NOT an EQ (no bands) and NOT a real compressor** (its
saturation lowers crest = light "glue"). The fast lo-fi/character cousin of the tape emulations [[studer-a800]] /
[[ampex-atr-102]] / [[softube-tape]] and the multiband saturator [[fabfilter-saturn-2]], in the [[vst-saturate]]
family. Full field guide — real surface, the machine map, footguns, recipes, our numbers, history/sources —
[`docs/vst/vibe-analog-machines.md`](../../../docs/vst/vibe-analog-machines.md). This skill is the workflow.

## The governing facts (read first — all measured on this rig, Pedalboard)

1. **Name + binary:** **"Vibe Analog Machines" is the renamed "Verve Analog Machines"** (UA renamed it 2026-04-14; same
   plug-in) — so reviews/manual say "Verve" but mean this, and it ships as **`uaudio_verve.vst3`** (codename `verve`,
   product name "UADx Vibe Analog Machines"). The cut-down **Essentials** = `uaudio_verve_essentials.vst3`.
2. **Renders headless — load `uaudio_verve.vst3`.** `probe_plugin.py` → `RENDERS ✓`; **bypass is sample-accurate to
   dry**. UADx native; needs an **iLok *account*** (software, no dongle) — authorized & verified processing here,
   re-verify elsewhere. Don't load the `UAD …`/`.component`/AU twins (passthrough-offline risk —
   [[uadx-uaudio-build-renders-headless]]).
3. **6 params; `machine` is a STRING enum → use the [[vst-preset]] harness, not `apply-vst-chain`'s float dict**
   (which sets the numerics but silently misses the machine name — the whole point of the plugin).
4. **`param_1` = DRIVE; `param_2` = WARBLE (tape machines) / TONE (preamp machines); `output_trim` = the bipolar −/0/+
   output slider** (clean, perfectly linear ±12 dB). The on-screen far-left "input" element is a **meter**, not a
   host-exposed control — gain-stage with the harness's `input_gain_db`/`output_peak_dbfs`.
5. **The 2nd knob is context-dependent (measured):** on the 6 TAPE machines `param_2` is **WARBLE** — pitch wow/flutter,
   tone/centroid doesn't move, **invisible to the spectrum/crest meters** (audition it). On the 4 PREAMP machines it's
   **TONE** — a big brightness control (centroid ~1200 → 6000+ Hz), no pitch smear. Same slot, two meanings. **Know
   your machine's type before setting `param_2`.**
6. **DRIVE 0 IS NOT BYPASS** — still colours (Sweeten d0 = 0.24 % THD + level). True null = `master_bypass=true`
   (0.000 % THD) or `power=false`. **DRIVE is only ~gain-compensated** (UA says compensated; measured ±a few dB across
   machines + soft-clip eats peak) → normalize / use `output_trim`, **A/B loudness-matched**. **Meters own the tone.**

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]` perceptual tools
  optional (`GEMINI_API_KEY`) for an A/B read.
- Confirm the build: `[L] list-vst-plugins {name_contains:"Vibe"}` (it lives in `uaudio_verve.vst3`). Screen with
  `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "verve"` (expect `RENDERS ✓`). Dump the live
  surface: `… presets/vst/dump_params.py uaudio_verve`; re-characterize: `… scripts/mix/vibe_sweep.py`.
- **It loads ≠ it rendered** — re-measure detail; a 0.00 spectrum/crest delta = the passthrough twin.

## The parameter surface (6 enums — authoritative)

| Param | Values | What it does (measured) |
|---|---|---|
| `machine` | `THICKEN`·`VINTAGIZE`·`OVERDRIVE`·`EDGE`·`SPUTTER`·`GLOW`·`DISTORT`·`SWEETEN`·`WARM`·`FIRE` | the **voicing** (this is the *enum/dump* order — not the GUI gradient order; see the machine map) |
| `param_1` | 0–100 (default **40**) | **DRIVE** — amount of the machine's saturation |
| `param_2` | 0–100 (default **0**) | **WARBLE** (6 tape machines) / **TONE** (4 preamp machines) — one slot, two meanings |
| `output_trim` | −12 … +12 dB (default 0) | clean, linear output level (the −/0/+ slider; global; full version only) |
| `power` | `True`/`False` | unit power (False = true bypass) |
| `master_bypass` | `False`/`True` | plugin bypass (True = true null, 0.000 % THD) |

## The 10 machines — GUI gradient order, cleanest→dirtiest (measured)

| Machine | Type | 2nd knob | On drums / tone (measured) | Reach for it when… |
|---|---|---|---|---|
| **SWEETEN** ★ | tape | Warble | **brighten** (centroid 1593→1725), +air, **crest HELD**; 0.8 % THD | clean sweeten / air (safe default — exciter-like) |
| **EDGE** | preamp (SS) | **Tone** | near-clean @d40; **Tone = brightness tilt** (centroid 1273→6150) | a clean console tone-shaper; subtle crunch when driven |
| **GLOW** | preamp (valve) | **Tone** | subtle valve warmth; **Tone** 1224→5784, low THD | clean tube warmth + a brightness tilt |
| **WARM** ★ | tape | Warble | warmer (→1335 @d65), **keeps air**, crest ↓ (glue); 0.3 % | gentle warm bus colour without going dull |
| **THICKEN** | tape | Warble | **mid body ↑**, **crest UP** (tighter), darker; 4.6 % | midrange weight / "bigger" + tighter |
| **VINTAGIZE** | tape | Warble | **dark, band-limited, mid-forward**; 13.8 % | lo-fi / "old tape" |
| **DISTORT** | preamp (valve) | **Tone** | driven valve; Tone adds brightness + grit (THD 14→45 %) | overt valve distortion w/ a tone control |
| **OVERDRIVE** | tape | Warble | heavy clip, **crest crushed ~7**, harsh top; 40 % | aggressive odd-harmonic tape overdrive |
| **FIRE** | tape | Warble | searing pushed tape, crest crushed; 32 % | extreme tape |
| **SPUTTER** | preamp (transistor) | **Tone** | filthiest ("on the verge of blowing up"); THD 44→94 % | broken/destroyed solid-state grime |

**Tells:** sweeten → centroid UP + crest HELD · warm/dark tape → centroid DOWN + crest down · THICKEN → body + crest UP ·
distortion → crest crushed · **preamp Tone → centroid sweeps 1200↔6000+** (that's how you tell a preamp's 2nd knob is
Tone, not warble — warble doesn't move the centroid). Essentials = the 4 tape machines (Sweeten/Warm/Thicken/Vintagize).

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (centroid + tilt + 5-band) + `[L] measure-loudness` (crest/PLR). Decide the
   job: **sweeten/air** (Sweeten) · **warm/glue** (Warm; or Glow for tube tilt) · **body** (Thicken) · **lo-fi/grit**
   (Vintagize/Sputter/Distort) · **destroy** (Overdrive/Fire) — and whether you want **warble** (tape) or to shape **tone** (preamp).
2. **Pick machine + drive.** Start drive ~40–50: Sweeten/Warm/Glow/Edge stay subtle to ~60 then build; Vintagize/
   Distort/Overdrive/Fire/Sputter are heavy by 40. Then set the 2nd knob: **Warble** (tape, ~20–35 for an audible
   wobble) or **Tone** (preamp, ~50 ≈ neutral, up = brighter/harsher).
3. **Build a preset** (`presets/vst/vibe-*.json`) setting **all 6** params explicitly; apply with the harness:
   `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
   projects/<track>/mix/<stem>_vibe.wav` (it peak-normalizes). `dump_state=true` via `apply-vst-chain` for byte-stable.
4. **Prove it** — re-`measure-spectrum`/`measure-loudness` (match the tell row). **Warble won't show** — confirm by
   ear / `[G] detect-mix-issues`. A 0.00 delta = passthrough twin. A/B loudness-matched ([[level-match]] / `[L] render-ab`).
5. **QC** — `[G] detect-mix-issues` / `mastering-feedback` for over-drive (harsh/fizzy) or too-dark/lo-fi; cross-check
   any mono "dark/harsh" flag vs the meters ([[gemini-mastering-feedback-cross-check]]). It's a colour insert, **not a
   master** — hand off to [[master-track]].

## Move table (measured)

| Goal | Vibe move |
|---|---|
| **Clean sweeten / air on drums** ★ | `SWEETEN`, drive 50 — centroid ↑, +air, crest held (the shipped `vibe-sweeten-drum-glue`). |
| **Warm + glued drum bus** ★ | `WARM`, drive 65 — crest 14.6→12.1, warmer, top gently rolled (the shipped `vibe-warm-drum-bus`; matches [[drum-bus-warm-tight-preference]]; SoS also recommends Warm @ drive ~65 on drums). |
| **Dark tube warmth** | `GLOW`, drive 40–60, **Tone ~30–50** — valve warmth; lower Tone = darker. |
| **Body / weight + tighter** | `THICKEN`, drive 50–70 — low-mid up, crest UP. |
| **Lo-fi / vintage tape wobble** ★ | `VINTAGIZE`, drive 50, **warble 35** — dark/band-limited + audible wow/flutter (the shipped `vibe-lofi-warble`). |
| **Clean console tone-shape** | `EDGE`, drive 40, **Tone** to taste — near-clean brightness tilt; drive up for crunch. |
| **Overt distortion / destroy** | `DISTORT` (valve, has Tone) / `OVERDRIVE`/`FIRE` (tape, has warble) / `SPUTTER` (filthiest); parallel it to keep punch. |
| **Tape wobble on keys/synth** | any **tape** machine + `warble` 20–50 (audition — meter-invisible). |

## Outputs

- `projects/<track>/mix/<stem>_vibe.wav` + the reusable `presets/vst/vibe-*.json` (and `.state` if dumped).

## Reporting to the user

State the machine (+ its type) + drive + warble-or-tone, the before→after **crest / centroid / tilt / target-band
deltas**, that warble (if used) is audible-only / meter-invisible, that it ran headless via `uaudio_verve.vst3`, and
the preset/`.state` path. A/B loudness-matched so "vibe" isn't a level illusion.

## Pitfalls

- **Wrong build = silent passthrough** — load `uaudio_verve.vst3`, not the `UAD …`/`.component`/AU twins.
- **Float dict can't pick the machine** — the `machine` string enum needs the [[vst-preset]] harness.
- **The 2nd knob means Warble on tape / Tone on preamp** — `param_2=80` on a preamp is *bright*, not wobbly.
- **Drive 0 ≠ bypass** — use `master_bypass`/`power` for a true null.
- **Warble is invisible to the meters** — pitch modulation; audition it.
- **Drive's level isn't perfectly compensated + crushes peak on hot machines** — normalize / `output_trim`, A/B level-matched.
- **It's colour, not correction** — no EQ bands (use `[L] apply-eq` / [[fabfilter-pro-q-4]]), no real compressor (use
  [[ssl-bus-compressor-2]] / [[fairchild-660]]); keep off the 2-bus loudness stage ([[master-track]]).
- **Essentials ≠ full** — 4 tape machines, drive only (no warble/tone/output_trim).

## Related

- [`docs/vst/vibe-analog-machines.md`](../../../docs/vst/vibe-analog-machines.md) — the full measured field guide (Part A measured + Part B history/usage, cited)
- [[vst-saturate]] — the generic skill this specializes · [[vst-preset]] — apply enum/all-explicit chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- Tape/warm siblings (proper tape machines): [[studer-a800]] (multitrack, darkens) · [[ampex-atr-102]] (mastering tape) · [[softube-tape]] (3-machine) · [[fabfilter-saturn-2]] (multiband saturator) · console colour [[helios-type-69]] / [[kit-bb-n105]]
- Pure-DSP twins (no plugin, deterministic): tanh/tape/soft-clip colour → `[L] saturate-loop`; air/presence → [[excite]]; EQ → `[L] apply-eq`
- [[mix-check]] (find the problem first) · [[warm-drum-bus]] / [[drum-stems-warm-loops]] (where a warm/lo-fi colour fits) · [[uadx-uaudio-build-renders-headless]] (why the build matters)
