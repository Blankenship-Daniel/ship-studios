---
name: home-at-last
description: "Use when the user wants the Steely Dan 'Home at Last' / Aja / Bernard Purdie shuffle drum sound from a FOLDER of multi-mic drum stems — 'Home at Last drums', 'Aja drum sound', 'Purdie shuffle drum tone', 'Steely Dan drums', 'clean hi-fi studio drums', 'preserve the ghost-note dynamics'. CLEAN/hi-fi, DYNAMIC (crest preserved), tight-round low, silky top, natural width — the third axis vs [[fool-in-the-rain]] (room/warm-dark) and [[tomorrow-never-knows]] (crush/dark/mono), and unlike Bonham it does NOT need room mics. Local DSP + the stemmy MCP servers; needs the `vst` extra (Pultec/Manley/Studer) + optional GEMINI_API_KEY."
argument-hint: <stems-folder> [slug] [bpm]
---

# home-at-last — Steely Dan "Home at Last" (Aja / Purdie shuffle) drum sound (end to end)

One ordered pipeline that takes a **folder of multi-mic drum stems** and produces the **clean / hi-fi,
warm-but-detailed, DYNAMIC "Home at Last" (Aja) tone** as (a) a finished drum **bus** and (b) drum **loops**.
The THIRD axis in the series — mirror the [[fool-in-the-rain]] / [[tomorrow-never-knows]] anatomy. Its defining
trait is **preserved DYNAMICS**: the snare ghost-note shuffle stays alive (crest held/up), never crushed.
Dev-validated 2026-06-03 on a 45 s `artifacts/drums` clip (a bright, hyper-dynamic, non-Aja stress kit).

**User steps → stages:** process stems (Stage 2) · volume-adjust, snare/kit-FORWARD (Stage 3) · EQ (Stage 2
clean corrective + Stage 4 Pultec tone) · use the VST plugins + sum (Stage 4: Pultec → Manley → Studer 30 IPS)
· create loops (Stage 5). Per repo doctrine: per-stem **corrective** EQ in Stage 2, **level** balance in Stage 3,
**tonal colour** at the bus in Stage 4 — never EQ to fix a balance problem ([[mix-balance]]).

## What this is — and is NOT

- It chases the **TONE/feel** (clean/hi-fi detail, warm-but-detailed, **DYNAMIC** with the ghost-note contrast
  intact, tight/round controlled low end, silky extended top, natural balanced width), **not** Bernard Purdie's
  performed half-time shuffle **GROOVE** — the groove + the whisper-quiet ghost-note placement live in the source.
- **Dynamics are the point.** The chain *preserves* the dynamic range that keeps the quiet ghost notes audible
  against the full-volume backbeat. Crest must **hold or rise** — if it collapses you erased the very thing the
  shuffle is built on.
- It does **NOT need room mics** (the OPPOSITE of [[fool-in-the-rain]]): the documented Aja drum captures were
  close-mic'd, and this recipe treats it as a close-mic'd kit. A room channel, if present, is used **minimally**
  for tasteful depth — omit it for the most authentic close-mic Aja sound.
- **Honest nuance:** Aja (1977, prod. Gary Katz) won the 1978 Best-Engineered Grammy shared by Roger Nichols
  (exec engineer), Bill Schnee, Elliot Scheiner & Al Schmitt (don't attribute one per-track engineer). Core
  tracking was at Producers' Workshop to a 2″ Stephens machine **at 30 IPS** through a home-made console with a
  **passive Langevin EQ (NOT a Pultec)**. The documented close-mic-only kit (**no room mics, no drum
  compression, "a little EQ"**) is from the Steve Gadd **TITLE-TRACK** session — "Home at Last" (a separate
  Purdie session) has **no comparable documentation, so don't over-claim the exact path**. So **Pultec EQP-1A +
  Manley Variable Mu + Studer A800 30 IPS** is an era-appropriate **PROXY for the tone**, not Aja's literal
  signal path. (Wendel was a Gaucho-era sampler — not on Aja.)

## Inputs & setup

- **`$1` = stems folder**; **`$2` = slug** (optional; else slugify the folder name); **`$3` = BPM** (optional, for Stage 5 loops).
- Prereqs: `uv sync --extra drum-prep` (this repo); in `../stemmy-loops-mcp`: `uv sync --extra vst --extra mixing`. UADx `uaudio_pultec_eqp-1a.vst3` + `uaudio_manley_variable_mu.vst3` + `uaudio_studer_a800.vst3` installed/authorized (the `uaudio_*` builds render headless; never the `UAD ….component` twins). `GEMINI_API_KEY` only for the optional Stage-4b A/B.
- **Run scripts with the stemmy-loops vst venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python`. `drum-prep` via `uv run --no-sync drum-prep`.
- **Always pass ABSOLUTE paths** to `find-loops` / `stemmy-gemini` tools (they resolve relative to the server cwd). In a git worktree, `artifacts/`/`projects/` live in the canonical checkout.

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` ([[format-fix]]; `afconvert -d LEI24 -f WAVE`).
- Baseline-measure each stem (`measure-loudness` + `measure-spectrum` + `check-clipping`); keep the third-octave spectra — they drive the Stage-2 plan. Room mics are **optional** here (Aja used none).

## Stage 1 — phase-align close mics → overheads (gated)

- `uv run --no-sync drum-prep detect <stems-dir>` → confirm roles (FX/reverb returns auto-detect as `fx`, excluded; overheads = stereo anchor; room polarity-only). → `phase-align` → `phase-aligned/`.
- **Stereo-image gate** (same as [[drum-phase-align]]): drum-prep mono-collapses close mics — lossless only if dual-mono; **OH MUST stay stereo** (the clean kit image). See [[drum-stems-warm-loops]] Stage 1 for the full gate.

## Stage 2 — process the stems (CLEAN, DETAILED, dynamics-preserving)

Author `presets/mix/<slug>-stem-process.plans.json` from the Stage-0 spectra — **use
`presets/mix/home-at-last-stem-process.plans.json` as the template** (built for `artifacts/drums`; adapt
freqs/gains to the supplied kit). Aja rules differ from both siblings:

- **CLEAN + detailed.** Gentle de-box (keep warmth), gentle de-harsh on bright stems (Aja is **never** harsh).
  Unlike Bonham/TNK ("NO air anywhere"), Home at Last is the one recipe that **allows a touch of clean top detail**
  — a small high-shelf on the overheads + a crack bell on the snare + a sizzle lift on the hat — but **guarded by a
  5–7 kHz de-harsh** and modest (the kit has a noise floor; a broad bright shelf would raise hiss, [[de-harsh]]).
- **Protect the dynamics.** **No gating** and **no transient snap** on the snare (the ghost-note + backbeat
  contrast IS the shuffle), and keep the API console comp **ratios LOW** (level gently, don't crush).
- **Room is OPTIONAL + minimal** (Aja had none). If present, tighten it (higher HPF, control the low buildup) — it
  adds depth, it is **not** the star (the inverse of [[fool-in-the-rain]]).
- declick OFF (percussive). Run: `$VENV scripts/mix/process_stems.py presets/mix/<slug>-stem-process.plans.json <phase-aligned-dir> <kit>/processed-hal`. **GOTCHA:** process_stems always runs the API strip + peak-normalizes each stem to −1 dBFS — harmless, Stage 3 re-levels by LUFS ([[stem-process]]).

## Stage 3 — CLEAN snare/kit-FORWARD balance + sum

Measured-LUFS balance: the **snare** (the shuffle's ghost-note star) is forward, the kick tight & supportive, the
hat present + detailed, the overheads a clean kit image, the room minimal. Reuse the targets in
`presets/mix/home-at-last.json` → build the spec → `$VENV scripts/mix/balance_stems.py <spec.json>` → `bus_hal_pre.wav`:

| Role | target LUFS | pan | |
|---|---|---|---|
| **snare top** | **−16** | −0.05 | THE STAR (ghost-note shuffle; NOT gated) |
| kick in | −17 | 0.0 | tight, round, supportive |
| overhead | −18 | 0.0 | clean detailed kit image (stereo) |
| hi hat | −21 | −0.15 | present + smooth + detailed |
| snare bottom | −26 | −0.05 | a clean touch of wires |
| kick beater | −26 | 0.0 | clean click |
| drum room | −24 | 0.0 | OPTIONAL — minimal depth (omit for authentic Aja) |

One global **−6 dBFS** headroom trim (never per-stem). A balance problem is **not** an EQ problem ([[mix-balance]]).

## Stage 4 — Home-at-Last bus chain (Pultec → Manley → Studer 30 IPS → polish → natural width)

`$VENV scripts/mix/home_at_last_bus.py <pre-bus> bus_hal.wav` — **defaults reproduce the approved signature**
(params in `presets/mix/home-at-last.json`):

- **A. HPF 30** (gentle subsonic, zero-phase — keep the round low end) → **B. Pultec EQP-1A** (LOW-END TRICK
  60 CPS B5/A4 = big-but-tight round bottom + low-mid scoop; AIR-WITHOUT-FIZZ 16 KCS boost q8 + 5 KCS atten = silky
  top, harshness shaved) → **C. Manley Variable Mu** (Comp, thresh 5, slow attack 3, Med recovery, HP-SC In, input 6
  — CLEAN tube glue that LEVELS macro-dynamics yet **keeps transients**; crest holds/rises) → **D. Studer A800
  @ 30 IPS NAB** (repro_hf 5 = detailed top, gentle drive — tight CONTROLLED warmth) → **E. zero-phase polish**
  (low_shelf +0.5@100, bell −1@400 de-box, bell −1@3k smoothness guard, high_shelf +0.5@12k clean sheen) →
  **F. natural width** (default 1.0 = no-op) → −1 dBFS mix bus.
- **Why these, and the do-NOT-fix list:** 30 IPS (not 15) moves the head-bump UP for a FLATTER/controlled low end
  (15 IPS BLOOMS = Bonham); Manley stays in **COMP not LIMIT** with a slow attack so crest doesn't collapse (the
  shuffle IS its dynamics); width **stays 1.0** — do not narrow (TNK) or hyper-widen (room). The Pultec colours via
  CURVES not drive (~0.01% THD). See [[pultec-eqp-1a]] / [[manley-variable-mu]] / [[studer-a800]].
- **Tuning knobs:** `--mu-thresh` (glue; lower = more, but watch crest), `--mu-attack` (keep low for dynamics),
  `--pul-lf-boost`/`--pul-lf-atten` (low weight/tightness), `--pul-hf-boost`/`--pul-hf-atten` (air vs de-fizz),
  `--repro-hf` (top detail), `--tape-in` (warmth), `--ips`, `--width`, `--no-pultec`/`--no-manley`/`--no-tape`.
  Expect: **crest HELD/high** (dynamics — the signature), **centroid HELD** (top detail kept, ~no darkening),
  tilt gently warm (~−2), correlation NATURAL (~0.95, far from TNK's mono ~0.99). **Crest is content-dependent**;
  on a hyper-dynamic kit it stays high — judge the DIRECTION (crest stays high, centroid held, tilt gently warm).

### Stage 4b — lock the settings (the tuning workflow)

Run `.claude/workflows/home-at-last.js` (`/workflows`) — it renders chain variants (Pultec air/low amounts ·
Manley threshold/attack · 30-vs-15 IPS · tape drive · ±detail) and runs a **parallel Gemini judge panel** scoring
each against the Aja brief (clean/hi-fi detail, preserved ghost-note dynamics, warm-silky-no-harsh top, tight-round
low, natural width). Write the winner's meters into the preset's `approved_signature_full_kit`. **Gemini hears
~16 kbps MONO → trust the meters for crest/tilt/centroid/correlation, ears for feel** ([[gemini-audio-understanding]]).
The tuning workflow renders **concurrently** — UADx is non-deterministic across concurrent renders, so confirm the
winner's locked meters with a **sequential** re-render.

## Stage 5 — create loops (raw + mastered)

Same as [[loops-to-deliverables]] / [[fool-in-the-rain]] Stage 5, on `bus_hal.wav`: structure-trim → **confirm BPM**
(the mandatory checkpoint; `$3` or ask — never guess) → `find-loops` (absolute path, `bpm`, `bars=[1,2,4,8]`,
`separate=false`) → seam → raw (tagged) + mastered (**gentle, crest-preserving** — don't squash the dynamics; ×3
formats, tagged) → `drum-prep verify-tags` ([[delivery-qc]]). The tagging gotchas are handled in
`scripts/loops/build_loops.py` — don't undo them.

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/phase-aligned/ · stems/processed-hal/
  mix/   bus_hal_pre.wav · bus_hal.wav (FINAL Home-at-Last bus, peak −1) · ab_*_m.wav
  loops/        raw Home-at-Last-bus loops (tagged)
  deliverables/ mastered ×3 formats (tagged)
  track.md      BPM, Home-at-Last settings, clean balance, structure
presets/mix/<slug>-stem-process.plans.json
artifacts/<slug>-loops/  (find-loops scratch)
```

## Report to the user

Per-stage before→after metrics; the final Home-at-Last signature vs the approved (crest HELD/high = dynamics
preserved, centroid HELD = top detail kept, tilt gently warm, correlation natural); the snare/kit-forward balance
table; the confirmed BPM; loop counts + `all_tagged`. It's a **MIX bus** (peak −1, not mastered) → hand to
[[master-track]] for a standalone master.

## Pitfalls

- **Tone, not groove.** Don't expect the shuffle feel without Purdie's performance.
- **Do NOT crush.** Manley stays in COMP + slow attack; no gating/transient-snap; gentle loop mastering. If crest
  collapses, the ghost-note contrast is gone — back the threshold off.
- **Does NOT need room mics** — the documented Aja captures were close-mic'd; keep any room channel minimal (or omit). Don't make it room-forward (that's [[fool-in-the-rain]]).
- **Keep it detailed, not dark and not bright.** 30 IPS + repro_hf 5 keep the top; the air is via the Pultec's
  air-WITHOUT-fizz (3–8 kHz shaved), not a bright shelf. Don't narrow toward mono (that's [[tomorrow-never-knows]]).
- **Honest proxy** — the Pultec/Manley/Studer chain chases the tone, not Aja's literal Langevin-console signal path.
- **UADx non-determinism** in the tuning workflow (concurrent renders) — trust a sequential re-render for the locked meters.

## Related
[[fool-in-the-rain]] · [[tomorrow-never-knows]] · [[format-fix]] · [[drum-phase-align]] · [[stem-process]] · [[mix-balance]] · [[pultec-eqp-1a]] · [[manley-variable-mu]] · [[studer-a800]] · [[de-harsh]] · [[drum-stems-warm-loops]] · [[loops-to-deliverables]] · [[delivery-qc]] · [[gemini-audio-understanding]] · [[master-track]]
