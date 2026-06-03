---
name: ampex-atr-102
description: "Use when running the UAD/UADx Ampex ATR-102 Master Tape for 2-bus / mastering / mixdown tape glue, warmth, and 'gloss' on a stereo mix, drum bus, or master — 'Ampex ATR-102', 'master tape', 'tape on the 2-bus / mix bus', 'tape glue on the mix', 'tape mastering', 'glossy 2-track tape', 'mastering tape machine', or when you want the smooth mastering-tape character (vs the punchier Studer A800). The measured, plugin-specific deep-dive of [[vst-saturate]] / [[vst-master]] — grounded in the real 30-param surface + isolation/harmonic numbers in docs/vst/ampex-atr-102.md. Stemmy MCP, the `vst` extra. UADx native (no iLok)."
---

# ampex-atr-102 — drive the UAD Ampex ATR-102 master tape (measured)

The plugin-specific, measured version of [[vst-saturate]] / [[vst-master]] for the **UAD/UADx Ampex ATR-102
Master Tape** (`uaudio_ampex_atr-102_tape.vst3`) — the **2-track ¼/½/1″ mastering & mixdown** machine, the
smooth/glossy counterpart to the punchier multitrack **[[studer-a800]]**. Full field guide — real 30-param
surface, the levers, harmonic theory, recipes, decision table, our own isolation/sweep/harmonic numbers —
lives in [`docs/vst/ampex-atr-102.md`](../../../docs/vst/ampex-atr-102.md). This skill is the workflow; pull
the doc for the *why* and the settings tables.

## The governing facts (read first)

1. **It's the 2-track MASTERING deck, not a multitrack.** Extra levers the A800 lacks: per-channel
   **Record level** (= the drive) / **Reproduce level** (= makeup), an **output Transformer** toggle, **tape
   WIDTH** (1/4 · 1/2 · 1″), and modeled **crosstalk / wow&flutter**. Reach for it on a **2-bus, stereo
   mixdown, or master**; for punchy drum/multitrack tracking the A800 is usually the pick.
2. **The "gloss" is the TRANSFORMER (even/2nd harmonics); the tape is ODD (3rd).** Measured on a drum bus:
   transformer **OFF → centroid −751** (much darker) vs **−395** with it ON — the transformer adds ~356 Hz of
   top back. A 1 kHz sine probe confirms it: transformer adds **+15 dB of 2nd harmonic** (H2 −70→−55) while
   the odd 3rd (the tape) is unchanged. So the ATR's character = **tape's odd 3rd + transformer's even 2nd**,
   a richer blend than the A800. **Driven hard the odd stack climbs (3rd→5th→7th) = harshness; cure = less
   Record level**, not EQ.
3. **−12 dBFS = 0 VU.** **Record level** drives the tape (saturates *and* raises level); **Reproduce** is
   make-up; **Auto Gain** compensates output. A −18-referenced feed under-drives ~6 dB; a near-0 mix slams it.
   In the preset harness the drive is `input_gain_db`. **Always A/B loudness-matched** — meters own this
   (Gemini hears ~16 kbps mono, can't judge the head bump / true-peak / width).
4. **WIDTH × SPEED is the signature combo (measured):** **15 IPS = warm/full** (wider tape → *darker*);
   **30 IPS = bright/tight** (wider tape → *leaner, tighter low end*, band-low 0.63→0.53). **1″ + 30 IPS =
   the most hi-fi mastering format** (open top, controlled bottom, ~transparent dynamics); **1/2″ + 15 IPS =
   warm mixdown**. NAB/CCIR is **AES-locked (inert) at 30 IPS**.
5. **Verify with meters:** `[L] measure-spectrum` (centroid/tilt — harshness proxies), `measure-loudness` /
   `measure-microdynamics` (crest/PLR = the glue), `check-clipping` (Record drive pushes true-peak).

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- The **`uaudio_ampex_atr-102_tape.vst3`** build (UADx native — renders headless, **no iLok**). The
  `UAD Ampex ATR-102.component`/twin **passes audio through** offline — never use it. Confirm with
  `[L] list-vst-plugins {name_contains:"ampex"}`. (Probe-tip: the param-response probe gives a *false*
  PASSTHROUGH if it toggles `auto_gain`; it really renders — set `repro_hf_eq=0` or push Record level to confirm.)
- Enum/float/bool params (`ips='30 IPS'`, `tape_type='456'`, `cal_level=6.0`, `head_width='1'`,
  `emphasis_eq='NAB'`, `transformer=True`, `wow_flutter=False`, `auto_cal=True`, per-channel `l_/r_*` levels &
  EQ) → set via the **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`); `apply-vst-chain`'s
  `parameters` dict is float-only and can't gain-stage or set the enums/bools.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (centroid/tilt) + `[L] measure-loudness` (crest/PLR). The "before."
2. **Gain-stage** — set `input_gain_db` so peaks land near 0 VU (≈ −12 dBFS). Too quiet = no tape; too hot = slammed.
3. **Pick the starting point** by goal (see the doc §decision-table; ready presets in `presets/vst/`):
   - **Transparent master / 2-bus polish:** `path=REPRO · ips=30 IPS · tape=456 · cal=6.0 · head_width=1 ·
     transformer=True · wow_flutter/crosstalk/hiss=False · auto_cal=True`, light drive → **`ampex-atr-master-glue.json`**
     (tight low + open top, crest ~untouched).
   - **Warm fuller mixdown:** `15 IPS · 456 · 6.0 · head_width=1/2 · NAB · transformer=True`, more drive →
     **`ampex-atr-warm-2bus.json`** (centroid −395, ~2.6 dB tape compression).
   - **Drum-bus glue/color (smooth):** `15 IPS · 456 · 1/2 · NAB`, drive to ~3–4 dB crest drop →
     **`ampex-atr-drum-glue.json`** (the ATR/mastering-deck counterpart to the A800 `tight-70s-*` punch presets).
   - **Tame harshness:** **`repro_hf_eq` down** (strongest — −2134 centroid at 0) > **less Record drive** >
     **over-`bias`** > **wider tape**. (`hf_eq` is the *record* brightness card — a brightener, NOT a de-harsher.)
   - **Lean a boomy bottom:** **`repro_lf_eq` down** (default 9.7 = full lows) or go **30 IPS / wider tape**.
4. **Drive to taste** — raise `input_gain_db`/Record until you see only **~1–2 dB crest drop** for a master
   (more for drum glue); **stop the moment the top spits** (rising 3rd harmonic = new harshness). Trim output
   (`output_peak_dbfs`, or Reproduce / Auto Gain) to gain-match.
5. **Apply** — via [[vst-preset]] (`apply_vst_preset.py <preset.json> <in.wav> <out.wav>`) so enums + gain-stage
   are honored. **Assert `auto_cal:true` with the FULL speed/tape/cal/width set** (a partial set that only
   changes `ips` leaves repro-EQ mis-calibrated for the old speed — measured ~−800 Hz darker at 30 IPS).
   Output → `projects/<track>/mix/` (or `masters/` staging — but the ATR is a color insert, **not** the limiter).
6. **Verify** — re-measure. Confirm the move is what you intended (transparent polish vs warm darkening vs
   glue), that crest didn't collapse (tape glue ≠ squash), and `check-clipping` (Record drive pushes true-peak).
   If too dull, **don't** add `hf_eq`/HF record card — lighten drive, widen the tape, or go 30 IPS.

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset JSON (`dump_state` for byte-exact re-render).
- Ready-made presets: `presets/vst/ampex-atr-{master-glue,warm-2bus,drum-glue}.json` (measured signatures inside).
- The `vintage-1960s.json` chain (Pultec → Fairchild 670 → **Ampex ATR-102**) is a fuller example use.

## Reporting to the user

State the key ATR settings (path/IPS/tape/cal/**width**/transformer/Record-drive), the before→after
**centroid / tilt / crest**, that it ran **headless (UADx, no iLok)**, and — when relevant — whether the
top came from the **transformer (even gloss)** vs the tape darkening. A/B with `[L] render-ab`
(loudness-matched) so taste isn't a level illusion.

## Pitfalls

- **It's a color insert, not a limiter** — master loudness/ceiling still belong to `render-mastered` ([[master-track]]).
- **30 IPS ≠ simply brighter-everywhere** — it brightens *and* tightens the low (wider tape leans it further);
  15 IPS is the warm/full speed. **NAB/CCIR is inert at 30 IPS** (AES-locked).
- **Width matters and interacts with speed** — don't treat 1/4/1/2/1″ as cosmetic. 1″ = tightest/most hi-fi.
- **Re-assert Auto Cal** after any tape/speed/cal/width change (mirror the A800) or the EQ stays mis-aligned.
- **wow&flutter / crosstalk are ON by default** — turn them OFF for a clean master; ON for vintage vibe.
  **Hiss/Hum OFF** by default; **extra latency** from upsampling.
- **Tape can't do surgery** — a real sibilance hotspot or harsh imbalance wants `[L] de-ess` /
  `[L] suppress-resonances` / `[[mix-balance]]`, not tape. Tape is glue + tilt + harmonic color only.
- **Don't blame the tape for harshness** — isolate & measure; driven odd-harmonics or an upstream EQ are the
  usual cause (the cure for tape harshness is **less Record drive**).

## Related

- [`docs/vst/ampex-atr-102.md`](../../../docs/vst/ampex-atr-102.md) — the full measured field guide (levers, harmonic probe, decision table)
- [[studer-a800]] — the **multitrack/punchy** UAD tape sibling (this is the **2-track/mastering/glossy** one) · compare before picking
- [[vst-saturate]] — generic tape/harmonic-color skill this specializes · [[vst-master]] — 2-bus master-chain context · [[vst-preset]] — apply enum/gain-staged chains
- [[vst-verify]] — prove the build renders (responds to params) before trusting it · [[vst-shootout]] — render ATR setting variants & judge to a winner
- [[finalize-mix]] — the pure-DSP glue stage a tape insert lives in · [[master-track]] — the limiter/compliance stage the ATR feeds
- [[gemini-audio-understanding]] — why meters (not Gemini) own loudness/peak/stereo for tape moves
