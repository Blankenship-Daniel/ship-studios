---
name: in-the-air-tonight
description: "Use when the user wants the Phil Collins 'In the Air Tonight' / Hugh Padgham GATED-REVERB drum sound from a FOLDER of multi-mic drum stems — 'In the Air Tonight drums', 'gated reverb', 'gated snare', 'that huge 80s drum sound', 'Phil Collins drums', 'explosive gated drums', 'big gated drum fill'. EXPLOSIVE / GATED / HUGE — a heavily-compressed room ambience cut off ABRUPTLY by a gate, blended big and WIDE; a NEW axis vs [[fool-in-the-rain]] (room/warm), [[tomorrow-never-knows]] (mono/crush) and [[home-at-last]] (clean/dynamic). Does NOT need room mics — the bus SYNTHESIZES the room. The bus is pure DSP (deterministic); Stage-2 stem colour + optional VST reverb use the `vst` extra; optional GEMINI_API_KEY for the A/B."
argument-hint: <stems-folder> [slug] [bpm]
---

# in-the-air-tonight — Phil Collins "In the Air Tonight" (Padgham gated reverb) drum sound (end to end)

One ordered pipeline that takes a **folder of multi-mic drum stems** and produces the **EXPLOSIVE /
GATED / HUGE "In the Air Tonight" (Padgham) tone** as (a) a finished drum **bus** and (b) drum **loops**.
A NEW axis in the famous-drum series — mirror the [[fool-in-the-rain]] / [[tomorrow-never-knows]] /
[[home-at-last]] anatomy. Its defining trait is the **gated reverb**: a big, slightly dark room ambience
that is **heavily compressed** and then **cut off abruptly by a noise gate** (no decaying tail), blended
big under the dry kit and spread WIDE. Dev-validated 2026-06-04 on a 60 s drum bus.

**User steps → stages:** process stems (Stage 2) · volume-adjust, snare/tom-FORWARD (Stage 3) · EQ
(Stage 2 punchy corrective + Stage 4 present/crack) · the gated-reverb bus + sum (Stage 4: synth reverb →
heavy compression → abrupt gate → wide blend) · create loops (Stage 5). Per repo doctrine: per-stem
**corrective** EQ in Stage 2, **level** balance in Stage 3, **bus tone** in Stage 4 — never EQ to fix a
balance problem ([[mix-balance]]).

## What this is — and is NOT

- It chases the **gated-reverb TONE** (explosive heavily-compressed ambience, an abrupt gated cutoff,
  a big WIDE image), **not** a specific groove. The famous tom fill lives in the source performance.
- **The bus SYNTHESIZES the room** (a deterministic decaying-noise reverb impulse), so it does **NOT need
  room mics** — the inverse of [[fool-in-the-rain]]. A real room channel is redundant here (omit it or keep
  it far down). A snare/tom-forward kit suits the iconic gated-fill sound.
- **All three traits are the point and must not be softened:** EXPLOSIVE = the heavy compression of the
  ambience (the SSL talkback-comp move); GATED = the abrupt close (no decaying tail); HUGE = the wide blend.
- **Deterministic default.** The bus loads **no plugin** on the default path — a seeded synth reverb +
  `compress-loop` + a numpy gate — so a bare invocation is **bit-reproducible** (no UADx non-determinism).
- **Honest nuance:** the gated-reverb sound was *discovered* by engineer Hugh Padgham on Peter Gabriel's
  "Intruder" (1980) when an SSL 4000 talkback/overhead mic — with the console channel's **compressor + noise
  gate** engaged — was left open over the kit, then used on "In the Air Tonight" (1981); the era effect later
  used AMS RMX16 "NonLin" / Lexicon ambience. This chain is an era-appropriate **PROXY of that technique in
  deterministic DSP**, not a model of the literal Townhouse Studios signal path.

## Inputs & setup

- Inputs (prose — **`$ARGUMENTS`** is the whole string): the **stems folder** the user provided (it may
  contain SPACES, e.g. "Ship Studios - Drum Stems" — treat the WHOLE path as ONE argument and QUOTE it in
  every command); an optional **slug** (else slugify the folder name); an optional **BPM** (for Stage 5
  loops). Do NOT rely on positional `$1`/`$2`/`$3` — a spaced path space-splits.
- Prereqs: `uv sync --extra drum-prep` (this repo); in `../stemmy-loops-mcp`: `uv sync --extra vst --extra
  mixing`. The **bus chain is pure DSP** (no plugin); the **`vst` extra** is needed only for the Stage-2 API
  Vision stem colour (`process_stems.py`) and the optional `--reverb-vst`. `GEMINI_API_KEY` only for the
  optional Stage-4b A/B.
- **Run scripts with the stemmy-loops vst venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python`. In a git
  worktree the `../` is WRONG — resolve it to the ABSOLUTE venv path next to the canonical checkout.
- **Always pass ABSOLUTE paths** to `find-loops` / `stemmy-gemini` tools (they resolve relative to the
  server cwd). In a git worktree, `artifacts/`/`projects/` live in the canonical checkout.

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` ([[format-fix]]).
- Baseline-measure each stem (`measure-loudness` + `measure-spectrum` + `check-clipping`); keep the
  third-octave spectra — they drive the Stage-2 plan. Room mics are **optional** (the bus makes its own).

## Stage 1 — phase-align close mics → overheads (gated)

- `uv run --no-sync drum-prep detect <stems-dir>` → confirm roles (FX/reverb returns auto-detect as `fx`,
  excluded; overheads = stereo anchor) → `phase-align` → `phase-aligned/`.
- **Stereo-image gate** (same as [[drum-phase-align]]): drum-prep mono-collapses close mics — lossless only
  if dual-mono; **OH MUST stay stereo** (the kit image; the bus owns the room). See [[drum-stems-warm-loops]]
  Stage 1 for the full gate.

## Stage 2 — process the stems (PUNCHY, DRY, tight)

Author `presets/mix/<slug>-stem-process.plans.json` from the Stage-0 spectra — **use
`presets/mix/in-the-air-tonight-stem-process.plans.json` as the template** (built for `artifacts/drums`;
adapt freqs/gains to the supplied kit). 80s gated rules:

- **Punchy + DRY.** The dry hits must cut THROUGH the exploding ambience, so keep stems tight: controlled
  lows, a present snare/tom **CRACK** (4–6 kHz), and — unlike [[home-at-last]] — **transient snap is ALLOWED**
  (a small positive `shape-bands` transient) so the dry attack is strong and keys the bus gate cleanly.
- **Restrain the hat** (the famous intro is hatless) and **keep the overheads as the kit image, not the
  ambience** — the bus synthesizes the gated room.
- **Room is redundant** (the bus makes it). If a room channel is present, keep it tight and far down, or omit.
- declick OFF (percussive). Run: `$VENV scripts/mix/process_stems.py presets/mix/<slug>-stem-process.plans.json
  <phase-aligned-dir> <kit>/processed-iat`. **GOTCHA:** process_stems always runs the API strip +
  peak-normalizes each stem to −1 dBFS — harmless, Stage 3 re-levels by LUFS ([[stem-process]]).

## Stage 3 — snare/tom-FORWARD balance + sum

Measured-LUFS balance: the **snare + tom fills** are the 80s stars, the kick solid, overheads/hat present
but under the drums (the gated explosion is added at the BUS, not from a room mic). Reuse the targets in
`presets/mix/in-the-air-tonight.json` → build the spec → `$VENV scripts/mix/balance_stems.py <spec.json>` →
`bus_iat_pre.wav`:

| Role | target LUFS | pan | |
|---|---|---|---|
| **snare top** | **−15** | 0.0 | THE STAR (gated snare; full body + crack) |
| tom | −16 | spread | the iconic FILL (if present) — forward |
| kick in | −17 | 0.0 | solid, punchy, controlled |
| overhead | −19 | 0.0 | kit image (stereo); the bus owns the room |
| hi hat | −23 | −0.15 | present but restrained |
| snare bottom | −26 | 0.0 | a touch of wires/snap |
| kick beater | −26 | 0.0 | clean click |
| drum room | −30 | 0.0 | OPTIONAL + redundant — omit (the bus makes the room) |

One global **−6 dBFS** headroom trim (never per-stem). A balance problem is **not** an EQ problem ([[mix-balance]]).

## Stage 4 — In-the-Air-Tonight bus chain (synth reverb → heavy compression → abrupt gate → wide blend)

`$VENV scripts/mix/in_the_air_tonight_bus.py <pre-bus> bus_iat.wav` — **defaults reproduce the approved
signature, bit-for-bit** (params in `presets/mix/in-the-air-tonight.json`):

- **A. HPF 30** (zero-phase) → **B. synth reverb** (a seeded decaying-noise IR convolved on the dry kit =
  a big, slightly dark, WIDE room — deterministic) → **C. heavy compression** (`compress-loop` thresh −30,
  ratio 8, fast attack, auto-makeup — the ambience EXPLODES) → **D. abrupt gate** (keyed off the dry kit
  envelope; opens instantly, HOLDS ~320 ms, then SLAMS shut in 28 ms — no decaying tail) → **E. blend**
  (the gated explosion RMS-matched under the dry, `--wet` 0.7) → **F. present/crack EQ** (low weight +
  4 kHz crack + gentle air, zero-phase) → **G. WIDE** (`adjust-stereo` width 1.4) → −1 dBFS mix bus.
- **Why these, and the do-NOT-fix list:** the reverb is CRUSHED then GATED — the abrupt cutoff IS the sound
  (don't soften the close); width goes **WIDE** (the opposite of [[tomorrow-never-knows]]' mono); the reverb
  is a **deterministic synth IR** by default, NOT a VST, so the signature is reproducible. The gate is derived
  from `scripts/mix/keyed_gate.py` ([[bleed-gate]]); the crush uses `compress-loop` ([[multiband-compress]]
  is the per-band cousin).
- **Tuning knobs:** `--decay-s` (room size), `--reverb-dark` (room brightness), `--gate-hold-ms` (the open
  window — the reverb length you hear), `--gate-release-ms` (keep SHORT for the abrupt slam), `--wet` (blend),
  `--rev-comp-ratio`/`--rev-comp-thresh` (the explosion), `--crack` (snare presence), `--width`, `--no-gate`/
  `--no-comp` (A/B), `--reverb-vst <path>` (a real reverb instead of the synth IR). Expect: **correlation
  DROPS HARD** (~0.5 = WIDE/HUGE), **LUFS UP** (dense exploding ambience at the same peak), **centroid UP**
  (the crack), **crest HIGH** (dry transients punch through). The gated-vs-ungated difference is mostly
  PERCEPTUAL (the abrupt tail) — judge the tail by ear / the Gemini panel.
- **Optional real reverb:** `--reverb-vst <path>` routes a VST reverb (e.g. ValhallaPlate / SSL Native
  FlexVerb) instead of the synth IR — a CREATIVE alternative, **NOT** the locked signature. **load ≠ render**:
  verify it actually processed (a 0.00 change = passthrough) before trusting it ([[vst-reverb]] / [[vst-verify]]).

### Stage 4b — lock the settings (the tuning workflow)

Run `.claude/workflows/in-the-air-tonight.js` (`/workflows`) — it renders chain variants (decay / gate hold
& release / wet blend / width / comp amount) and runs a **parallel Gemini judge panel** scoring each against
the gated-reverb brief (explosive ambience, the abrupt gated cutoff, huge width, dry punch-through). Write the
winner's meters into the preset's `approved_signature_full_kit`. **Gemini hears ~16 kbps MONO → trust the
meters for crest/tilt/centroid/correlation, ears for the gated-tail feel** ([[gemini-audio-understanding]]).
The default path is deterministic (no VST/UADx), so a re-render reproduces the winner exactly.

## Stage 5 — create loops (raw + mastered)

Same as [[loops-to-deliverables]] / [[home-at-last]] Stage 5, on `bus_iat.wav`: structure-trim → **confirm
BPM** (the mandatory checkpoint; `$3` or ask — never guess) → `find-loops` (absolute path, `bpm`,
`bars=[1,2,4,8]`, `separate=false`) → seam → raw (tagged) + mastered (×3 formats, tagged) → `drum-prep
verify-tags` ([[delivery-qc]]). The tagging gotchas are handled in `scripts/loops/build_loops.py` — don't
undo them. **Note:** a gated-reverb bus has hard tails — pick loop points on the gated cutoffs, not mid-tail.

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/phase-aligned/ · stems/processed-iat/
  mix/   bus_iat_pre.wav · bus_iat.wav (FINAL In-the-Air-Tonight bus, peak −1) · ab_*_m.wav
  loops/        raw gated-reverb-bus loops (tagged)
  deliverables/ mastered ×3 formats (tagged)
  track.md      BPM, gated-reverb settings, snare/tom-forward balance, structure
presets/mix/<slug>-stem-process.plans.json
artifacts/<slug>-loops/  (find-loops scratch)
```

## Report to the user

Per-stage before→after metrics; the final In-the-Air-Tonight signature vs the approved (correlation DROPS
HARD = WIDE/HUGE, LUFS UP = exploding ambience, centroid UP = crack, crest HIGH = dry punch-through); the
snare/tom-forward balance table; the confirmed BPM; loop counts + `all_tagged`. It's a **MIX bus** (peak −1,
not mastered) → hand to [[master-track]] for a standalone master.

## Pitfalls

- **Tone, not groove.** Don't expect the famous tom fill without the source performance.
- **Don't soften the gate.** Keep `--gate-release-ms` short — the abrupt cutoff IS the sound. A long release
  turns it into an ordinary reverb.
- **Does NOT need room mics** — the bus synthesizes the gated ambience. A real room channel is redundant; omit
  it (the inverse of [[fool-in-the-rain]]).
- **Keep it WIDE.** Don't narrow toward mono (that's [[tomorrow-never-knows]]); the huge stereo image is core.
- **Deterministic by default** — don't reach for `--reverb-vst` unless you specifically want a real reverb's
  character; the synth-IR path is reproducible and the locked signature. load ≠ render on any VST reverb.
- **Mind the noise floor** — the heavy ambience compression raises any hiss; clean the stems in Stage 2.

## Related
[[fool-in-the-rain]] · [[tomorrow-never-knows]] · [[home-at-last]] · [[format-fix]] · [[drum-phase-align]] · [[stem-process]] · [[mix-balance]] · [[bleed-gate]] · [[multiband-compress]] · [[vst-reverb]] · [[vst-verify]] · [[loops-to-deliverables]] · [[delivery-qc]] · [[gemini-audio-understanding]] · [[master-track]]
