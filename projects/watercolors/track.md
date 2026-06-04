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

## Files
- `mix/bus_warm.wav` — FINAL warm/tight drum bus (mix bus, peak −1; **not mastered** → [[master-track]] for loudness).
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
