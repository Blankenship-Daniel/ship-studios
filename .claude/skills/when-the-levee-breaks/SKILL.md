---
name: when-the-levee-breaks
description: "Use when the user wants the Led Zeppelin 'When the Levee Breaks' / Bonham / Headley Grange stairwell drum sound from a FOLDER of multi-mic drum stems (which want ROOM and/or overhead mics) — 'When the Levee Breaks drums', 'Bonham stairwell', 'distant mic drums', 'crushed cavernous Bonham', 'breathing compressed drums', 'that Levee break sound', 'Binson echo drums'. DISTANT-AMBIENT / breathing-CRUSH / DARK / cavernous / NARROW — the two-distant-mic stairwell, the OPPOSITE technique to [[fool-in-the-rain]] (warm room as a wide layer); also distinct from [[tomorrow-never-knows]] (mono/dark close crush), [[home-at-last]], [[in-the-air-tonight]] and [[back-in-black]]. Local DSP + the stemmy MCP servers; needs the `vst` extra + optional GEMINI_API_KEY (perceptual A/B)."
argument-hint: <stems-folder> [slug] [bpm]
---

# when-the-levee-breaks — Led Zeppelin "When the Levee Breaks" (Bonham stairwell) drum sound (end to end)

One ordered pipeline that takes a **folder of multi-mic drum stems** and produces the **DISTANT-AMBIENT /
breathing-CRUSH / DARK / cavernous "When the Levee Breaks" tone** as (a) a finished drum **bus** and (b)
drum **loops**. A SECOND Bonham axis — but the **OPPOSITE technique** to [[fool-in-the-rain]]: that recipe
is the warm room as a *layer* of a full multi-mic kit (wide, clean SSL glue, big-but-open); **this** is the
two-DISTANT-MIC CRUSH — only the stairwell ambience IS the kit, aggressively compressed so it breathes/pumps,
dark and cavernous, narrower. Dev-validated 2026-06-04 on a 60 s drum bus.

**User steps → stages:** process stems (Stage 2) · volume-adjust, room/overhead-FORWARD (Stage 3) · EQ
(Stage 2 dark corrective + Stage 4 dark tilt) · the crush bus + sum (Stage 4: Distressor → dbx 160 → Studer
15 IPS → Binson echo → dark → narrow) · create loops (Stage 5). Per repo doctrine: per-stem **corrective**
EQ in Stage 2, **level** balance in Stage 3, **bus tone** in Stage 4 — never EQ to fix a balance problem
([[mix-balance]]).

## What this is — and is NOT

- It chases the **TONE** (distant ambience, aggressive breathing crush, dark/cavernous, narrower), **not** a
  groove. The iconic Bonham groove lives in the source performance.
- **The DISTANT mics are the sound.** Balance the **room and/or overheads FORWARD** and the close mics far
  down — if there are no room/overhead mics you cannot make the distant-ambience character (the close mics
  alone are too dry/tight).
- **vs [[fool-in-the-rain]] (the key contrast):** FITR = warm room as a wide LAYER, clean SSL glue, big-but-
  OPEN, crest held wide. Levee = two-distant-mic CRUSH, aggressive comp (crest DOWN, breathing/pump),
  DARK/cavernous, NARROWER. Pick by whether you want warm-open (FITR) or dark-crushed (Levee).
- **AGGRESSIVE crush, not clean glue.** The Distressor 10:1 + dbx pump genuinely reduce crest (the Helios
  F760 "breathing"). **DARK** — 15 IPS fat tape + a high-shelf cut remove the air. Do not brighten/widen.
- **The Binson echo is deterministic numpy** (a multi-tap, HF-damped slap), not a VST — the headless UADx
  Galaxy/EP-34 tape echo isn't render-verified here ([[vst-delay]]; **load ≠ render**). Tune with `--echo-*`.
- **Honest nuance:** Bonham played at the bottom of Headley Grange's three-storey stairwell; engineer Andy
  Johns captured the kit with just TWO Beyerdynamic M160 ribbons at the top (the only mics), amplified/
  compressed through a Helios console (a pair of Helios F760 comp/limiters set aggressively for the
  "breathing"), with a Binson Echorec on the mix (1970–71). So **Distressor + dbx 160 + Studer 15 IPS + a
  numpy Binson echo** is an era-appropriate **PROXY for the tone**, not the literal Headley Grange path.

## Inputs & setup

- Inputs (prose — **`$ARGUMENTS`** is the whole string): the **stems folder** the user provided (it may
  contain SPACES — treat the WHOLE path as ONE argument and QUOTE it everywhere); an optional **slug** (else
  slugify the folder name); an optional **BPM** (for Stage 5 loops). Do NOT rely on positional `$1`/`$2`/`$3`.
- Prereqs: `uv sync --extra drum-prep` (this repo); in `../stemmy-loops-mcp`: `uv sync --extra vst --extra
  mixing`. `uaudio_distressor.vst3` + `uaudio_dbx_160.vst3` + `uaudio_studer_a800.vst3` installed/authorized
  (the `uaudio_*` builds render headless; never the `UAD ….component` twins). The Binson echo is pure numpy.
  `GEMINI_API_KEY` only for the optional Stage-4b A/B.
- **Run scripts with the stemmy-loops vst venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python`. In a git
  worktree the `../` is WRONG — resolve it to the ABSOLUTE venv path next to the canonical checkout.
- **Always pass ABSOLUTE paths** to `find-loops` / `stemmy-gemini` tools (they resolve relative to the
  server cwd). In a git worktree, `artifacts/`/`projects/` live in the canonical checkout.

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` ([[format-fix]]).
- Baseline-measure each stem (`measure-loudness` + `measure-spectrum` + `check-clipping`); keep the
  third-octave spectra. **Confirm there's a room and/or overhead pair** — they are the kit here.

## Stage 1 — phase-align close mics → overheads (gated)

- `uv run --no-sync drum-prep detect <stems-dir>` → confirm roles (room + overheads = the distant pair, the
  star; close mics support) → `phase-align` → `phase-aligned/`.
- **Stereo-image gate** (same as [[drum-phase-align]]): drum-prep mono-collapses close mics — lossless only
  if dual-mono; **OH/room MUST stay stereo** (the distant image). See [[drum-stems-warm-loops]] Stage 1.

## Stage 2 — process the stems (DARK, distant-forward)

Author `presets/mix/<slug>-stem-process.plans.json` from the Stage-0 spectra — **use
`presets/mix/when-the-levee-breaks-stem-process.plans.json` as the template** (built for `artifacts/drums`;
adapt freqs/gains to the supplied kit). Levee rules:

- **Room/overheads dominate, dark + full.** Fill the low-mid body, roll the top a touch (the bus darkens
  further), heavier room compression for the breathing.
- **Close mics SUPPORT, dark, far down.** No bright beater click, no bright snare crack — the distant mics
  own the kick/snare in a damp cavern; darken the close mics' tops and balance them low.
- **No air anywhere** (the inverse of [[home-at-last]]).
- declick OFF (percussive). Run: `$VENV scripts/mix/process_stems.py presets/mix/<slug>-stem-process.plans.json
  <phase-aligned-dir> <kit>/processed-levee`. **GOTCHA:** process_stems always runs the API strip +
  peak-normalizes each stem to −1 dBFS — harmless, Stage 3 re-levels by LUFS ([[stem-process]]).

## Stage 3 — room/overhead-FORWARD balance + sum

Measured-LUFS balance: the room/overheads (the stairwell ambience) ARE the kit and lead the balance; the
close mics support far down (same room-forward emphasis as [[fool-in-the-rain]] — but the bus then CRUSHES
it dark). Reuse the targets in `presets/mix/when-the-levee-breaks.json` → build the spec → `$VENV
scripts/mix/balance_stems.py <spec.json>` → `bus_levee_pre.wav`:

| Role | target LUFS | pan | |
|---|---|---|---|
| **drum room** | **−15** | 0.0 | THE STAR (if present) — the distant stairwell ambience |
| overhead | −16 | 0.0 | the distant pair; leads with no room channel (stereo) |
| kick in | −19 | 0.0 | supportive low thud — far down |
| snare top | −19 | 0.0 | supportive backbeat — far down |
| hi hat | −26 | −0.1 | minimal (the ambience owns the cymbals) |
| snare bottom | −28 | 0.0 | a faint touch of wires |
| kick beater | −28 | 0.0 | a faint click |

One global **−6 dBFS** headroom trim (never per-stem). A balance problem is **not** an EQ problem ([[mix-balance]]).

## Stage 4 — When-the-Levee-Breaks bus chain (Distressor → dbx 160 → Studer 15 IPS → Binson echo → dark → narrow)

`$VENV scripts/mix/when_the_levee_breaks_bus.py <pre-bus> bus_levee.wav` — **defaults reproduce the approved
signature** (params in `presets/mix/when-the-levee-breaks.json`):

- **A. HPF 35** (subsonic, zero-phase) → **B. Distressor** (10:1, Dist 2, input 8, attack 4/release 2 = the
  aggressive Helios F760 'breathing' crush — crest DOWN, pump) → **C. dbx 160** (4:1 VCA pump/cohesion) →
  **D. Studer 15 IPS** (dark FAT tape, repro_hf 1.5 = cavernous low-mid weight, darkened top) → **E. Binson
  echo** (numpy multi-tap HF-damped slap = the cavern) → **F. dark tilt EQ** (low weight + low-mid thump +
  high-shelf CUT) → **G. NARROW** (`adjust-stereo` width 0.6) → −1 dBFS mix bus.
- **Why these, and the do-NOT-fix list (vs [[fool-in-the-rain]]):** AGGRESSIVE crush (Distressor) not clean
  SSL glue (crest DOWN, breathing); DARK (15 IPS + high-shelf cut) not warm-open (remove the air); NARROWER
  (the distant-mic image) not the wide warm room; a Binson-style ECHO adds the cavern (FITR has none). See
  [[distressor]] / [[dbx-160]] / [[studer-a800]] / [[vst-delay]].
- **Tuning knobs:** `--dist-ratio`/`--dist-input` (the crush/breathing), `--dbx-thresh` (pump),
  `--ips`/`--repro-hf`/`--tape-in` (dark fat tape), `--echo-time`/`--echo-feedback`/`--echo-mix`/`--echo-damp`
  (the cavern), `--dark` (high-shelf cut), `--width`, `--no-dist`/`--no-echo`/etc. Expect: **crest DOWN**
  (breathing crush), **centroid DOWN + tilt darker** (cavernous), **correlation UP** (narrower). Judge the
  DIRECTION (crest down, dark, narrow, cavernous).

### Stage 4b — lock the settings (the tuning workflow)

Run `.claude/workflows/when-the-levee-breaks.js` (`/workflows`) — it renders chain variants (Distressor
crush · dbx pump · 15-vs-30 IPS · echo amount · dark/narrow) and runs a **parallel Gemini judge panel**
scoring each against the Levee brief (distant ambience, breathing crush, dark/cavernous, the echo, narrow).
Write the winner's meters into the preset's `approved_signature_full_kit`. **Gemini hears ~16 kbps MONO →
trust the meters for crest/tilt/centroid/correlation, ears for feel** ([[gemini-audio-understanding]]). The
Distressor/dbx/Studer are UADx (non-deterministic across the concurrent renders; the numpy echo is
deterministic) — confirm the winner's locked meters with a **sequential** re-render.

## Stage 5 — create loops (raw + mastered)

Same as [[loops-to-deliverables]] / [[home-at-last]] Stage 5, on `bus_levee.wav`: structure-trim → **confirm
BPM** (the mandatory checkpoint; `$3` or ask — never guess) → `find-loops` (absolute path, `bpm`,
`bars=[1,2,4,8]`, `separate=false`) → seam → raw (tagged) + mastered (×3 formats, tagged) → `drum-prep
verify-tags` ([[delivery-qc]]). The tagging gotchas are handled in `scripts/loops/build_loops.py`. The Levee
break is a classic sampling source — a 1/2/4-bar loop or one-shot pack suits it.

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/phase-aligned/ · stems/processed-levee/
  mix/   bus_levee_pre.wav · bus_levee.wav (FINAL When-the-Levee-Breaks bus, peak −1) · ab_*_m.wav
  loops/        raw Levee-bus loops (tagged)
  deliverables/ mastered ×3 formats (tagged)
  track.md      BPM, Levee settings, room/overhead-forward balance, structure
presets/mix/<slug>-stem-process.plans.json
artifacts/<slug>-loops/  (find-loops scratch)
```

## Report to the user

Per-stage before→after metrics; the final Levee signature vs the approved (crest DOWN = breathing crush,
centroid DOWN/tilt darker = dark cavern, correlation UP = narrower); the room/overhead-forward balance table;
the confirmed BPM; loop counts + `all_tagged`. It's a **MIX bus** (peak −1, not mastered) → hand to
[[master-track]] for a standalone master.

## Pitfalls

- **Tone, not groove.** Don't expect the Bonham feel without the source performance.
- **Needs distant mics.** No room/overhead pair → you can't make the distant-ambience character; this is the
  one trait the close mics alone can't fake.
- **Crush, don't glue.** The Distressor genuinely lowers crest (breathing); if crest stays high you under-
  drove it. (The OPPOSITE of [[fool-in-the-rain]]'s crest-holding glue.)
- **Dark, not warm-open.** Keep the air rolled off; don't brighten (that un-caverns it) and don't widen
  (that's the warm room).
- **Two Bonham recipes** — pick Levee for dark-distant-crush, [[fool-in-the-rain]] for warm-wide-room. They
  are deliberately different axes.
- **Honest proxy** — the Distressor/dbx/Studer/numpy-echo chain chases the tone, not the literal Headley Grange path.
- **UADx non-determinism** in the tuning workflow (concurrent renders) — trust a sequential re-render for the locked meters.

## Related
[[fool-in-the-rain]] · [[tomorrow-never-knows]] · [[home-at-last]] · [[in-the-air-tonight]] · [[back-in-black]] · [[format-fix]] · [[drum-phase-align]] · [[stem-process]] · [[mix-balance]] · [[distressor]] · [[dbx-160]] · [[studer-a800]] · [[vst-delay]] · [[loops-to-deliverables]] · [[delivery-qc]] · [[gemini-audio-understanding]] · [[master-track]]
