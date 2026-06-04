---
name: back-in-black
description: "Use when the user wants the AC/DC 'Back in Black' / Mutt Lange / Tony Platt drum sound from a FOLDER of multi-mic drum stems — 'Back in Black drums', 'AC/DC drum sound', 'tight punchy dry rock drums', 'arena rock drums', 'Phil Rudd drum tone', 'big dry rock kit', 'punchy not dark drums'. TIGHT / PUNCHY / DRY / PRESENT — low-tuned, controlled, upfront drums with strong transients and a present (never dark) top, minimal effects; a NEW axis vs [[fool-in-the-rain]] (room/warm), [[tomorrow-never-knows]] (mono/crush), [[home-at-last]] (clean/dynamic) and [[in-the-air-tonight]] (gated/huge). Local DSP + the stemmy MCP servers; needs the `vst` extra + optional GEMINI_API_KEY (perceptual A/B)."
argument-hint: <stems-folder> [slug] [bpm]
---

# back-in-black — AC/DC "Back in Black" (Mutt Lange / Tony Platt) drum sound (end to end)

One ordered pipeline that takes a **folder of multi-mic drum stems** and produces the **TIGHT / PUNCHY /
DRY / PRESENT "Back in Black" arena-rock tone** as (a) a finished drum **bus** and (b) drum **loops**. A
NEW axis in the famous-drum series — mirror the [[fool-in-the-rain]] / [[tomorrow-never-knows]] /
[[home-at-last]] anatomy. Its defining trait is **punch + dryness**: low-tuned, controlled, upfront drums
with strong transients (crest UP) and a present top, captured "dry and compact" with minimal effects.
Dev-validated 2026-06-04 on a 60 s drum bus.

**User steps → stages:** process stems (Stage 2) · volume-adjust, kick/snare-FORWARD (Stage 3) · EQ
(Stage 2 punchy corrective + Stage 4 console weight/presence) · the punchy bus + sum (Stage 4: Transient
Shaper → SSL 4K E → dbx 160) · create loops (Stage 5). Per repo doctrine: per-stem **corrective** EQ in
Stage 2, **level** balance in Stage 3, **bus tone** in Stage 4 — never EQ to fix a balance problem
([[mix-balance]]).

## What this is — and is NOT

- It chases the **TONE/feel** (tight, punchy, dry, present, controlled arena rock), **not** an AC/DC groove.
- **DRY/compact.** No tape, no reverb, no echo ("AC/DC didn't like to hear any effects"). Do **not** add a
  Studer/tape darkening stage (that's [[fool-in-the-rain]] / [[tomorrow-never-knows]]) or ambience (that's
  [[in-the-air-tonight]]). Keep any room channel minimal or omit it.
- **PRESENT, not dark.** The top is pushed a touch (a high-shelf BOOST), the **inverse** of TNK's dark cut.
- **PUNCH is the point.** The SSL comp runs FAST attack **OUT** (slow) so transients pass and crest goes
  **UP**; the dbx 160 at 4:1 **raises** crest on drums; the Transient Shaper adds attack. Don't over-glue —
  if crest collapses you've lost the punch ([[drum-punch]]).
- **Honest nuance:** "Back in Black" (1980) was tracked at Compass Point (Nassau) by engineer Tony Platt
  with producer "Mutt" Lange. Platt hunted a room "sweet spot" where the snare sounded biggest/snappiest;
  the kit was low-tuned/muffled, the **overheads carried most of the texture**, the snare ran through an
  Eventide H910 (detuned ~93), and the capture was deliberately dry/compact with minimal effects. So
  **Softube Transient Shaper + SSL 4K E + dbx 160** is an era-appropriate **PROXY for the tone**, not the
  literal Compass Point signal path (the snare H910 detune is a pitch effect, not modeled here).

## Inputs & setup

- Inputs (prose — **`$ARGUMENTS`** is the whole string): the **stems folder** the user provided (it may
  contain SPACES — treat the WHOLE path as ONE argument and QUOTE it everywhere); an optional **slug** (else
  slugify the folder name); an optional **BPM** (for Stage 5 loops). Do NOT rely on positional `$1`/`$2`/`$3`.
- Prereqs: `uv sync --extra drum-prep` (this repo); in `../stemmy-loops-mcp`: `uv sync --extra vst --extra
  mixing`. `Transient Shaper.vst3` (Softube) + `SSL 4K E.vst3` + `uaudio_dbx_160.vst3` installed/authorized
  (the `uaudio_*` build renders headless; never the `UAD ….component` twin). `GEMINI_API_KEY` only for the
  optional Stage-4b A/B.
- **Run scripts with the stemmy-loops vst venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python`. In a git
  worktree the `../` is WRONG — resolve it to the ABSOLUTE venv path next to the canonical checkout.
- **Always pass ABSOLUTE paths** to `find-loops` / `stemmy-gemini` tools (they resolve relative to the
  server cwd). In a git worktree, `artifacts/`/`projects/` live in the canonical checkout.

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` ([[format-fix]]).
- Baseline-measure each stem (`measure-loudness` + `measure-spectrum` + `check-clipping`); keep the
  third-octave spectra — they drive the Stage-2 plan.

## Stage 1 — phase-align close mics → overheads (gated)

- `uv run --no-sync drum-prep detect <stems-dir>` → confirm roles (overheads = stereo anchor; they carry
  most of the texture here) → `phase-align` → `phase-aligned/`.
- **Stereo-image gate** (same as [[drum-phase-align]]): drum-prep mono-collapses close mics — lossless only
  if dual-mono; **OH MUST stay stereo**. See [[drum-stems-warm-loops]] Stage 1 for the full gate.

## Stage 2 — process the stems (PUNCHY, DRY, tight, PRESENT)

Author `presets/mix/<slug>-stem-process.plans.json` from the Stage-0 spectra — **use
`presets/mix/back-in-black-stem-process.plans.json` as the template** (built for `artifacts/drums`; adapt
freqs/gains to the supplied kit). Back-in-Black rules:

- **Tight + punchy.** Low-tuned but controlled lows (firm de-box, no mud), a present snare/tom **CRACK**,
  and — like [[in-the-air-tonight]], unlike [[home-at-last]] — **transient snap is ALLOWED** (a small
  positive `shape-bands` transient) because the punch is the point.
- **Overheads carry the texture** (Platt) — keep them present, not buried, with a present-but-smooth top.
- **PRESENT top, not dark** (the inverse of TNK): a modest high-shelf detail, de-harsh-guarded.
- **Room is minimal/dry** — keep it tight and far down, or omit (Back in Black is compact).
- declick OFF (percussive). Run: `$VENV scripts/mix/process_stems.py presets/mix/<slug>-stem-process.plans.json
  <phase-aligned-dir> <kit>/processed-bib`. **GOTCHA:** process_stems always runs the API strip +
  peak-normalizes each stem to −1 dBFS — harmless, Stage 3 re-levels by LUFS ([[stem-process]]).

## Stage 3 — kick/snare-FORWARD balance + sum

Measured-LUFS balance: kick + snare upfront and punchy, the overheads carrying most of the texture, the hat
present, the room minimal. Reuse the targets in `presets/mix/back-in-black.json` → build the spec → `$VENV
scripts/mix/balance_stems.py <spec.json>` → `bus_bib_pre.wav`:

| Role | target LUFS | pan | |
|---|---|---|---|
| **snare top** | **−15** | 0.0 | THE backbeat — punchy, cracking, present |
| kick in | −15.5 | 0.0 | tight, low-tuned, controlled, PUNCHY |
| overhead | −17 | 0.0 | carries MOST of the texture (stereo) |
| tom | −18 | spread | present punchy fills (if present) |
| hi hat | −21 | −0.15 | present, tight rock hat |
| snare bottom | −26 | 0.0 | a touch of wires/snap |
| kick beater | −25 | 0.0 | defined click |
| drum room | −28 | 0.0 | OPTIONAL + MINIMAL (dry — omit or far down) |

One global **−6 dBFS** headroom trim (never per-stem). A balance problem is **not** an EQ problem ([[mix-balance]]).

## Stage 4 — Back-in-Black bus chain (Transient Shaper → SSL 4K E → dbx 160 → present EQ → natural width)

`$VENV scripts/mix/back_in_black_bus.py <pre-bus> bus_bib.wav` — **defaults reproduce the approved
signature** (params in `presets/mix/back-in-black.json`):

- **A. HPF 35** (tight subsonic, zero-phase) → **B. Softube Transient Shaper** (PUNCH +2 WIDE SLOW = snare
  crack; SUSTAIN −2 on the LOW band, xover 700 = tighten the kick/snare boom, cymbals keep decay) → **C. SSL
  4K E** (Black EQ: LF bell +3 @80 weight, −2 @450 de-box, +1.5 @3k presence, +1.5 @10k shelf PRESENT top;
  comp 4:1 @ −16, **FAST attack OUT** = transients pass = crest UP = punch) → **D. dbx 160** (4:1, −26 light
  = a few dB VCA punch/cohesion — raises crest on drums) → **E. PRESENT zero-phase EQ** (weight + de-box
  guard + snap + present high-shelf BOOST) → **F. natural width** (default 1.0 = no-op) → −1 dBFS mix bus.
- **Why these, and the do-NOT-fix list:** DRY — no tape/reverb (Bonham/TNK/gated moves are wrong here);
  PRESENT not dark (the top BOOST is the inverse of TNK's cut); the SSL comp FAST attack **OUT** is the
  measured punchier (higher-crest) setting (do not engage FAST); natural width (don't narrow toward mono).
  See [[softube-transient-shaper]] / [[ssl-4k-e]] / [[dbx-160]].
- **Tuning knobs:** `--ts-punch`/`--ts-sustain` (attack vs tighten), `--ssl-colour` (Black/Brown/Orange),
  `--ssl-lf`/`--ssl-debox`/`--ssl-pres`/`--ssl-air` (console tone), `--ssl-thresh`/`--ssl-ratio`/`--ssl-fast`
  (punch), `--dbx-ratio`/`--dbx-thresh` (VCA punch), `--present` (top), `--width`, `--no-ts`/`--no-ssl`/
  `--no-dbx`. Expect: **crest UP** (punch — the signature), **centroid up / tilt held** (present, not dark),
  **correlation NATURAL** (not narrowed). Crest is content-dependent; judge the DIRECTION (crest UP, present
  top, natural width, dry).

### Stage 4b — lock the settings (the tuning workflow)

Run `.claude/workflows/back-in-black.js` (`/workflows`) — it renders chain variants (Transient Shaper punch ·
SSL colour/threshold/FAST · dbx ratio · present-top amount) and runs a **parallel Gemini judge panel**
scoring each against the Back-in-Black brief (tight, punchy, dry, present-not-dark, natural width). Write the
winner's meters into the preset's `approved_signature_full_kit`. **Gemini hears ~16 kbps MONO → trust the
meters for crest/tilt/centroid/correlation, ears for feel** ([[gemini-audio-understanding]]). The tuning
workflow renders **concurrently** — UADx (SSL/dbx) is non-deterministic across concurrent renders, so confirm
the winner's locked meters with a **sequential** re-render.

## Stage 5 — create loops (raw + mastered)

Same as [[loops-to-deliverables]] / [[home-at-last]] Stage 5, on `bus_bib.wav`: structure-trim → **confirm
BPM** (the mandatory checkpoint; `$3` or ask — never guess) → `find-loops` (absolute path, `bpm`,
`bars=[1,2,4,8]`, `separate=false`) → seam → raw (tagged) + mastered (×3 formats, tagged) → `drum-prep
verify-tags` ([[delivery-qc]]). The tagging gotchas are handled in `scripts/loops/build_loops.py`.

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/phase-aligned/ · stems/processed-bib/
  mix/   bus_bib_pre.wav · bus_bib.wav (FINAL Back-in-Black bus, peak −1) · ab_*_m.wav
  loops/        raw Back-in-Black-bus loops (tagged)
  deliverables/ mastered ×3 formats (tagged)
  track.md      BPM, Back-in-Black settings, kick/snare-forward balance, structure
presets/mix/<slug>-stem-process.plans.json
artifacts/<slug>-loops/  (find-loops scratch)
```

## Report to the user

Per-stage before→after metrics; the final Back-in-Black signature vs the approved (crest UP = punch,
centroid up/tilt held = present not dark, correlation natural, dry); the kick/snare-forward balance table;
the confirmed BPM; loop counts + `all_tagged`. It's a **MIX bus** (peak −1, not mastered) → hand to
[[master-track]] for a standalone master.

## Pitfalls

- **Tone, not groove.** Don't expect the AC/DC feel without the source performance.
- **Keep it DRY.** No tape, no reverb, no echo. Adding a Studer/ambience stage breaks the axis.
- **Don't over-glue.** The SSL comp FAST attack stays OUT and the dbx threshold light so crest goes UP — if
  crest collapses you've squashed the punch ([[drum-punch]]).
- **Present, not dark.** Push the top a touch; don't roll it off (that's [[tomorrow-never-knows]]).
- **Natural width.** Don't narrow toward mono (TNK) or hyper-widen (room/gated).
- **Honest proxy** — the Transient-Shaper/SSL/dbx chain chases the tone, not the literal Compass Point path.
- **UADx non-determinism** in the tuning workflow (concurrent renders) — trust a sequential re-render for the locked meters.

## Related
[[fool-in-the-rain]] · [[tomorrow-never-knows]] · [[home-at-last]] · [[in-the-air-tonight]] · [[format-fix]] · [[drum-phase-align]] · [[stem-process]] · [[mix-balance]] · [[softube-transient-shaper]] · [[ssl-4k-e]] · [[dbx-160]] · [[drum-punch]] · [[loops-to-deliverables]] · [[delivery-qc]] · [[gemini-audio-understanding]] · [[master-track]]
