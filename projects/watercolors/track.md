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
