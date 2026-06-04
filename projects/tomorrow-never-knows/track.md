# tomorrow-never-knows — drum bus

**Source:** `~/Desktop/Drum STEMS/` (8 mono/stereo AIFs, 262 s full performance) → `stems/` (48k/24 WAV).
**Recipe:** `[[tomorrow-never-knows]]` — The Beatles "Tomorrow Never Knows" (Ringo / Geoff Emerick, 1966) drum tone: heavily-compressed, DARK/lo-fi/saturated, MONO/narrow. The opposite axis from `[[fool-in-the-rain]]`.
**Kit note:** NO toms and NO snare-reverb return; HAS a hi-hat → ran the recipe's **no-toms fallback** balance (kick + snare forward) with an added dark hi-hat.

- **BPM:** _TBD_ (not yet supplied — required before Stage 5 loops; never guessed).
- **Key/root:** n/a (drums).
- **Target platform / LUFS / ceiling:** _TBD_ (bus is a MIX bus, peak −1, NOT mastered).

## Pipeline run (2026-06-03)

| Stage | What | Output |
|---|---|---|
| 0 | afconvert → 48k/24; energy-scan (whole 262 s active) | `stems/*.wav` |
| 1 | merge OH L/R → stereo `overheads.wav`; phase-align (snare-top phase flip −0.24→+0.63 fixed) | `stems/phase-aligned/` |
| 2 | per-stem DARK process (HPF + de-box + de-harsh + API Vision colour) | `stems/processed-tnk/` |
| 3 | no-toms-fallback measured-LUFS balance, −6 dBFS headroom | `mix/bus_tnk_pre.wav` |
| 4b | tuning workflow (7-variant sweep + Gemini judge panel) on a 30 s window | `mix/tnk-variants/` |
| 4 | **final full bus**, winning flags, sequential render | `mix/bus_tnk.wav` |

## Locked chain (winning tuning)

`tomorrow_never_knows_bus.py --la3a --vibe --repro-hf 0.5 --tape-in 4 --dark -8`

Fairchild 660 (colour) → LA-3A (opto LIMIT) → Studer A800 15 IPS (dark/hot tape) → **Vibe VINTAGIZE** (the key lo-fi darkener + grit) → dark EQ (high-shelf −8 @ 8k) → width 0.35 mono → peak −1.

## Balance (no-toms fallback, measured LUFS → target)

| stem | target LUFS | pan |
|---|---|---|
| kick in | −16 | 0.0 |
| snare top | −17 | −0.05 |
| overheads (stereo) | −22 | 0.0 |
| drum room (stereo) | −22 | 0.0 |
| kick beater | −26 | 0.0 |
| snare bottom | −30 | −0.05 |
| hi-hat | −32 | −0.20 |

## Final signature (full bus, pre → after)

| meter | pre-bus | **bus_tnk** | target |
|---|---|---|---|
| centroid | 4140 | **1481 Hz** | DOWN (dark) ✓ |
| tilt | −1.94 | **−4.36 dB/oct** | more negative (dark) ✓ |
| crest | 26.1 | **17.7 dB** | DOWN (pump) — at the headless mix-bus ceiling |
| L-R corr | 0.917 | **0.980** | UP toward 1 (mono) ✓ |
| LUFS-I | −29.8 | **−16.2** | (peak −1, mix bus) |

Gemini perceptual confirm: *"perfectly hits the TNK brief — dark, fat, intentionally lo-fi without devolving into a murky blur; kick + snare legible; perfect mono image."*

## Notes / next steps

- **Tone nailed; pump at the recipe ceiling.** crest 17.7 matches the recipe's documented "~17 with --la3a" — the headless Fairchild colours rather than crushes. The full 1966 *slam/breathing* is an aggressive **mastering** step (`[[master-track]]` with an aggressive limiter / Distressor), NOT a mix-bus move.
- **Workflow caveat:** UADx plugins render NON-deterministically under the tuning workflow's concurrency (2/7 Vibe variants failed; reported winner meters didn't reproduce). Final bus was rendered **sequentially** (deterministic). See `presets/mix/tomorrow-never-knows.json` → `approved_signature_desktop_kit`.
- **This is the TONE, not Ringo's hypnotic tom GROOVE** — that lives in the performance.
- Prior 60 s dev scratch (a different 366 s source) archived in `_prev-366s-source/`.

## Outputs
```
stems/ (48k/24) · stems/phase-aligned/ · stems/processed-tnk/
mix/ bus_tnk_pre.wav · bus_tnk.wav (FINAL, peak −1) · tnk-variants/
presets/mix/tomorrow-never-knows-desktop-stem-process.plans.json
presets/mix/tomorrow-never-knows.json (approved_signature_desktop_kit)
```
