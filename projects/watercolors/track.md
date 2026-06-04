# Watercolors — drum stems

Source: `~/Desktop/Watercolors - Drum Stems/` (5 stems, 48 kHz/24-bit stereo AIFF).
Processed via the **[[drum-stems-warm-loops]]** pipeline on 2026-06-03.

- **BPM:** 104 (user-confirmed; auto-detect was octave/phase-ambiguous).
- **Structure:** drums play **0–58 s**, then session silence (60 s+ = −62…−73 dBFS). The final bus is trimmed to 60 s. (Gemini's "spoken-word voiceover at 1:01" was a mono-downmix hallucination of the near-silent tail.)
- **Kit:** Kick (kick_in, dual-mono), Snare (snare_top, dual-mono), Drum Overheads (stereo anchor, carries hats/cymbals — no separate hat mic), Drum Room (stereo ambience), Snare Reverb (**FX return**).

## Decisions
- **Phase-align:** kick/snare → OH (delays 213 / 111 smp; corr −0.28→+0.46, −0.33→+0.56). Dual-mono close mics mono-collapsed losslessly; OH/Room stereo preserved.
- **Per-stem (`presets/mix/watercolors-stem-process.plans.json`):** HPF only on kick (clean) & snare (70 Hz); OH HPF 110 + de-box −2 @400; Room HPF 120 + de-box −1.5 @400. No de-box on snare (250–400 already −10 dB → would only brighten). declick OFF.
- **Warm balance:** kick −16 / snare −18 / OH −22 / room −26 / reverb −30 LUFS, −6 dBFS headroom.
- **Warm bus:** `warm_bus.py --hs-gain -2 --repro-hf 3` (this kit is darker — fewer cymbals + OH down). FINAL **dry** (reverb dropped): Gemini A/B + meters agreed the reverb added low-mid wash that loosened the tight low end. Signature: tilt −2.67 / corr 0.975 / crest 19.5 (centroid 2480, darker than the 2880 reference but on-tilt = appropriately warm).
- **Loops:** 104 BPM, bars [1,2,4,8] → 8 loops. RAW (warm character, ~−20 LUFS) in `loops/`; MASTERED gently to −15 LUFS (crest preserved) ×3 formats in `deliverables/`. All tagged.

## Variant — dry / tight / punchy (2026-06-03)

A contrasting flavor off the **same `stems/processed/`** source. Where the warm bus is tape + tilt
(dark, glued), this is a **forward American-console** sound: dry, tight, attack-forward.

- **Dry balance** (`mix/balance_punchy.spec.json`): BOTH ambience sources out (Drum Room **and** Snare
  Reverb) — vs the warm "dry" which kept the room. Close mics forward: **kick −16 · snare −17 · OH −23**
  (snare +1 / OH −1 LU vs warm so the close-mic attack dominates, not the cymbal/room wash). 60 s, −6 dBFS.
- **Tone chain** (`scripts/mix/punchy_bus.py`, bare defaults reproduce the approved bus): HPF 35 →
  `shape_bands` GENTLE transient lift (kick 0.35 / snare 0.20 / cymbal 0.10) → **UAD API Vision Channel
  Strip** (215 HPF @50 tighten · 225 comp, Old (FB), thresh −10 ratio 4 = the punch · 550 EQ: +3 @100
  thump, −2 @500 box-clean, **no top boost**) → width 0.95 → −1 dBFS.
- **The punch is the 225 comp, not EQ/shaper.** Attack tested Fast/Medium/Slow: **Medium maxes crest**
  (25.8 vs Slow 24.5 vs Fast 23.1 — confirms [[api-vision-channel-strip]], refutes tight-70s-api's
  "Slow=punch"), BUT Medium's harder envelope pumped up this live kit's **noise-floor hiss** (in the gaps/
  tail) + slight kick box (`detect-mix-issues` flagged both; meters showed 0 clipping). So **Slow** was
  kept — verified clean, crest 24.5 still ≫ warm's 17.2. First pass over-shaped (mid 0.40/hi 0.30) →
  meter-grounded `detect-mix-issues` flagged a clicky/spitty snare ("excessive transient shaping"; meters
  showed 0 clipping → tone defect, not level). Easing to 0.20/0.10 cleared it with ~no crest loss
  (24.7→24.5) — the comp owned the punch. Verified **clean** by `detect-mix-issues` (0 defects).
- **Candidate shootout:** v1 (API-only) vs v2 (heavy shape, harsh) vs v2b (eased shape) vs v3 (OH −21,
  brighter). Gemini A/B (loudness-matched) + meters chose **v2b** — driest, punchy-but-musical, tightest
  (corr 0.985); v3's louder OH read harsh/wetter (defeats "dry").
- **Signature (vs warm):** centroid **2386** (warm 1747) · tilt **−1.99** (−2.67) · crest **24.5** (17.2) ·
  PLR **22.6** (16.2) · corr **0.985** (0.975) · LUFS −23.6 · TP −0.99 · 0 clipped. Brighter, drier,
  much punchier, tighter — exactly the intended contrast.

## Master (2026-06-03) — both buses mastered to a stereo bus

Both mix buses mastered via `render-mastered` (HPF 30 → no added transient → limiter, −1 dBTP), target chosen
by a **per-bus Gemini judge-panel shootout** (`warm-bus-shootout` workflow, criteria punch/clean/balance,
meter-grounded). FX stayed **dry** (honoring the prior A/B).

- **Warm → −14 LUFS** (`masters/watercolors_drums_warm_master.wav`). Panel winner (24/30 vs 23/23 for −16/−15).
  Limiter near-transparent here: crest 17.2→**13.9**, THD **0.57 dB**, 0 clipped, TP −1.08. **Spotify/YouTube/
  Tidal fully compliant** (−14 exactly); Apple turns it down 2 dB. The Spotify-ready master.
- **Punchy → −18 LUFS** (`masters/watercolors_drums_punchy_master.wav`). **Overrode** the panel's loudness-biased
  −16/−14 tie: this bus's identity is crest 24.5, and at −16 the limiter crushes it to 17.3 + adds **3.5 dB** THD
  that mono Gemini can't hear (cross-check rule). −18 keeps crest **19.1**. **Dynamics-first**: TP-limited at
  −1.08 so streaming can only lift it +0.08 dB → plays ~4 LU quieter than warm. Best used in-mix, not as a
  loudness-competitive standalone. (`shootout/punchy_m16.wav` exists if a louder cut is wanted.)
- Variants: `masters/shootout/{warm,punchy}_m{14,15,16,18}.wav`.
- **Deliverables:** `deliverables/masters/` — each master × {44.1/16, 48/24, 96/24}, tagged (BPM 104; 16-bit via
  sidecar only — `tag-deliverable` upconverts to 24-bit, so distribution re-exported `tag=false` + kept the sidecar).

## Files
- `mix/bus_warm.wav` — FINAL warm/tight drum bus (mix bus, peak −1; mastered → `masters/…_warm_master.wav`).
- `mix/bus_warm_dry.wav` (full untrimmed) · `mix/bus_warm_withfx.wav` + `mix/ab_*_m.wav` (the A/B that chose dry).
- `mix/bus_punchy.wav` — FINAL **dry/tight/punchy** variant (mix bus, peak −1; not mastered). `mix/bus_punchy_pre.wav` = its dry balance pre-tone. Recipe: `scripts/mix/punchy_bus.py` + `mix/balance_punchy.spec.json`.
- `loops/` (8 raw) · `deliverables/` (24 = 8 × {44.1/16, 48/24, 96/24}) — **warm-bus** loops. (Punchy loop pack not yet cut — say the word.)

## Per-stem Pro-Q 4 EQ + Pro-L 2 (2026-06-03) — from the RAW desktop stems

User asked to EQ each raw stem with **Pro-Q 4** then limit each with **Pro-L 2** (goal: cleanup +
sweeten). Operated on the original `~/Desktop/Watercolors - Drum Stems/` AIFFs (NOT the warm/punchy
busses above). Both stages **faithful** (EQ balance-preserving / no peak-norm; limiter owns the −1 dBTP
ceiling). Ran headless via the loops `vst` venv (`apply-vst-chain` MCP not connected in this worktree).

- **Pro-Q 4** (Natural Phase, Clean) — presets `presets/vst/watercolors-<stem>-proq4.json`
  (flatten-first, every band explicit): Kick HPF 35 / −3 box @350 / +3.5 click @3.8k · Snare HPF 90 /
  +body @200 / −3 box @350 / +crack @4k / +sheen @10k · Overheads HPF 150 / de-box 250+400 / +2.5 air @9k
  / **dynamic** (not spectral — pre-ring) de-harsh @6k, **−5 dB out trim** (air lifts cymbal peaks to
  +3.4 dBFS) · Room HPF 100 / −box @400 / +top @8k / spectral de-harsh @5.5k · Snare Reverb HPF 200 /
  −box @250 / +sheen @8k / HC 16k.
- **Pro-L 2** (Transparent / −1.0 dBTP / TP on / 4× / dither off, `gain +4`) via
  `presets/vst/fabfilter-prol2-streaming-master.state` + `artifacts/watercolors-eq/faithful_prol2.py`.
  Gentle: loud stems ~1–2 dB GR, ambience returns pass through. All ≤ −1.02 dBTP.

| Stem | source LUFS/TP | EQ'd | EQ+limited |
|---|---|---|---|
| Kick | −19.3 / −1.7 | −19.5 / −3.1 | **−16.5 / −1.02** |
| Snare | −23.2 / −2.6 | −22.7 / −2.5 | **−19.7 / −1.02** |
| Overheads | −18.7 / −0.1 | −26.2 / −1.6 | **−23.8 / −1.02** |
| Room | −32.5 / −9.4 | −34.2 / −11.7 | **−31.3 / −8.7** |
| Snare Reverb | −33.3 / −15.7 | −36.9 / −19.3 | **−33.9 / −16.3** |

Outputs: `mix/<stem>_proq4.wav` (EQ only) + `mix/<stem>_proq4_prol2.wav` (EQ + limited). OH trimmed −5 dB
for the air boost → sits lower in the kit now; rebalance to taste. (LUFS-I is pulled down by the silent
60 s+ tail — the active 0–58 s section reads hotter.)

### Mix → master of the EQ+limited stems

- **Mix** (`drum-prep mix`, **punchy / audience / subtle verb**): kick 0 · snare −1 · OH −2 (anchor) ·
  room −12 · snare-reverb FX −19 (vs OH). Bus `mix/drums-mix-punchy-audience.wav` — peak −1.00 / −0.99 dBTP,
  LUFS −21.4, crest 24.5, tilt −3.76. Flat unity sum (no glue/limiting).
- **Master** (user: **loud / hard-hitting ~−11 LUFS**): light master EQ (`presets/vst/watercolors-drumbus-mastereq.json`
  — HPF 28 + 1.5 dB air @12k) → **Pro-L 2 Punchy, −1.0 dBTP, TP on, 16× OS, gain +19** (via
  `artifacts/watercolors-eq/faithful_prol2.py`, faithful). Result `masters/drums-master-loud.wav`:
  **−10.88 LUFS-I / −1.01 dBTP**, crest 24.5→**13.3** (heavy limiting, accepted), tilt −3.29, 48k/24-bit, dither off.
  (Gain→loudness flattened hard: +13→−13.3, +16→−12.05, +19→−10.88.) For 44.1/16 distribution, dither at export.

## Variant — Bonham "Fool In The Rain" (2026-06-03)

The room-DOMINANT, warm/dark, breathing **John Bonham** flavor via the [[fool-in-the-rain]] skill — the
opposite axis from the warm-tight and punchy buses: here the **room/overheads are the loudest layer** (the
room IS the reverb), 15 IPS tape **blooms** the lows (vs 30 IPS tightening them), and the snare reverb is
KEPT as ambience (vs dropped on the warm bus).

- **Per-stem** (`presets/mix/watercolors-fitr-stem-process.plans.json` → `stems/processed-fitr/`): GENTLE +
  warmth-preserving. Room **HPF only 45** (keep the low weight; warm used 120) + −1.5 @200; OH HPF 110 + −2
  @200 (kick-bleed); Snare HPF 70, NO de-box, dynamic 4.5-7k de-harsh (it's the one bright element); Kick HPF
  30, keep the 58 Hz sub. **No air anywhere**, and **zero low-mid cuts in the API color EQ** on room/OH (those
  scoop the warmth). Snare Reverb (FX) cleaned with HPF 150 to kill the low-mid wash that loosened the warm bus.
- **Room-forward balance** (`mix/bus_fitr_pre.wav`): Room **−16** (star) · OH −18 · Kick −20 · Snare −21 ·
  Snare Reverb −26 (ambience), −6 dBFS headroom, 60 s.
- **Bus chain** (`scripts/mix/fool_in_the_rain_bus.py`): HPF 35 → Helios Type 69 (Mic g40/pad−20, 700 Hz +3,
  no air) → Studer A800 **15 IPS** NAB (repro-hf **3** — this kit is already dark) → SSL Bus Comp 2 → zero-phase
  polish → −1 dBFS.
- **Gemini tuning panel** (`.claude/workflows/fool-in-the-rain.js` logic, run MCP-free via the gemini venv —
  the worktree session has no stemmy-gemini MCP): 5+4 variants over two rounds. **Winner = `glue_fast`**
  (`--repro-hf 3 --ssl-thresh -18 --ssl-attack 3 --ssl-makeup 5`). Key reads: Gemini scores were noisy
  run-to-run (more_glue 36→25) so only recurring notes were weighted; its "too dry / no room" verdict is a
  **mono-downmix artifact** (it can't hear the wide stereo room — corr 0.84 confirms it's there), so that was
  NOT chased; the meter-backed "more glue" note WAS — a faster SSL attack genuinely bit the peaky bus
  (crest 25.9→24.7) without the mud that `glue_fast_hot` flagged. Variants kept in `mix/fitr_shootout/`.
- **Signature** (`mix/bus_fitr.wav`, the winner): centroid **2154** (source 2673) · tilt **−2.31** (−1.62) ·
  crest **24.7** (27.6) · corr **0.836** (wide room preserved — vs warm 0.975 / punchy 0.985) · LUFS −23.0.
  Warm/dark, room-forward, breathing — exactly the Bonham brief. MIX bus (peak −1, not mastered).
- **Files:** `mix/bus_fitr.wav` (FINAL) · `mix/bus_fitr_pre.wav` (room-forward balance) · `mix/bus_fitr_dry.wav`
  (no-reverb alt) · `mix/fitr_shootout/` (9 tuning variants) · `presets/mix/watercolors-fitr-stem-process.plans.json`.
- **Loops:** 104 BPM, bars [1,2,4] → **7 raw** (`watercolors_bonham_drums_*`, ~−26 LUFS, crest 20-23, in `loops/`)
  + **21 mastered** (−15/−16 LUFS, crest 13-15, ×3 formats in `deliverables/`). All tagged — sidecars + in-WAV
  RIFF LIST/INFO on every file, 16-bit distribution stays PCM_16 with the embedded tag. find-loops scratch in
  `artifacts/watercolors-fitr-loops/`. (8-bar skipped — the 58 s performance is too short.)
- **Spotify master** (`masters/watercolors_drums_bonham_master.wav`, via [[master-track]], meter-driven —
  Gemini is mono-deaf to loudness/TP so it was not consulted): target shootout −14/−15/−16. The source is so
  peaky (crest 24.7) that −14 and −15 land identically (plays −14.7, crest 16.3); −16 keeps crest 18.0 but
  plays 1.6 LU quieter. **Picked −14 / −1.0 dBTP** = `render-mastered` (HPF 30, no added transient, 48k/24).
  Result: **−14.7 LUFS-I · −1.02 dBTP · crest 16.3** (from 24.7 — still more dynamic than the warm master's
  13.9). `check-streaming-targets`: **Spotify ✓ (plays −14.6) · YouTube ✓ · Tidal ✓**; Apple plays it −1.3 dB
  down (its −16 target — like the warm master, not a defect). Dynamics-first alt kept at
  `masters/shootout/bonham_m16.wav` (−16, crest 18, Apple-optimal). **Deliverables:** `deliverables/masters/`
  — `watercolors_drums_bonham_master.{distribution_44k_16, production_48k_24, master_96k_24}.wav`, all tagged
  (BPM 104; export-deliverables tag=true wrote NO tags here, so re-tagged via the build_loops _tag_16/_tag_24
  splice — 16-bit stays PCM_16 with the in-WAV LIST chunk).
