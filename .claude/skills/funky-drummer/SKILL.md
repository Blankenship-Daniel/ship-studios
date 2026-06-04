---
name: funky-drummer
description: "Use when the user wants the James Brown 'Funky Drummer' / Clyde Stubblefield drum sound from a FOLDER of multi-mic drum stems — 'Funky Drummer drums', 'Clyde Stubblefield break', 'the most sampled breakbeat', 'dry vintage funk drums', 'James Brown drum sound', 'breakbeat drum tone', 'sample-ready funk break'. DRY / TIGHT / VINTAGE-FUNK / MONO-ish / MID-FORWARD — a dry, tight, mid-forward kit, band-limited and narrow, sample-ready; a NEW axis vs [[fool-in-the-rain]] (room/warm), [[tomorrow-never-knows]] (mono/crush/dark), [[home-at-last]] (clean/dynamic), [[in-the-air-tonight]] (gated/huge) and [[back-in-black]] (present/arena). Local DSP + the stemmy MCP servers; needs the `vst` extra + optional GEMINI_API_KEY (perceptual A/B)."
argument-hint: <stems-folder> [slug] [bpm]
---

# funky-drummer — James Brown "Funky Drummer" (Clyde Stubblefield) drum sound (end to end)

One ordered pipeline that takes a **folder of multi-mic drum stems** and produces the **DRY / TIGHT /
VINTAGE-FUNK / MONO-ish / MID-FORWARD "Funky Drummer" tone** as (a) a finished drum **bus** and (b) drum
**loops** — the natural source for a breakbeat loop/one-shot pack. A NEW axis in the famous-drum series —
mirror the [[fool-in-the-rain]] / [[tomorrow-never-knows]] / [[home-at-last]] anatomy. Its defining traits
are **dry, tight, mid-forward and narrow** (band-limited, sample-ready). Dev-validated 2026-06-04 on a 60 s
drum bus.

**User steps → stages:** process stems (Stage 2) · volume-adjust, snare/kick-FORWARD (Stage 3) · EQ (Stage 2
mid-forward corrective + Stage 4 console/midrange tone + band-limit) · the funk bus + sum (Stage 4: API
Vision → Pultec MEQ-5 → dbx 160 → Pultec HLF-3C → narrow) · create loops (Stage 5). Per repo doctrine:
per-stem **corrective** EQ in Stage 2, **level** balance in Stage 3, **bus tone** in Stage 4 — never EQ to
fix a balance problem ([[mix-balance]]).

## What this is — and is NOT

- It chases the **TONE** (dry, tight, mid-forward, band-limited, narrow, sample-ready), **not** the groove —
  Clyde Stubblefield's 8-bar break lives in the source performance.
- **MID-FORWARD is the point.** Both the API EQ and the Pultec MEQ-5 **boost** the mids (200/700/3k). Do
  **not** scoop the mids — the funk presence is the midrange.
- **BAND-LIMITED.** The Pultec HLF-3C cuts the sub AND the very top (10 KCS) for the vintage, sample-ready
  bandwidth. Do **not** restore full-range air/sub (that would un-vintage it). Brighter take: raise the high-cut.
- **MONO-ish / NARROW** (width ~0.45) — the 1969 image is narrow, like [[tomorrow-never-knows]] and the
  **opposite** of [[in-the-air-tonight]]'s wide. Do **not** widen.
- **DRY** — tape is OFF by default (`--tape` adds a touch of vintage 15 IPS warmth); no reverb/echo.
- **Honest nuance:** "Funky Drummer" was cut at King Studios, Cincinnati (1969-11-20); the famous 8-bar
  unaccompanied break is Clyde Stubblefield's (uncredited — he received no songwriter credit or sampling
  royalties), popularized as a sample from the mid-1980s and now on 1000+ records. So **API Vision + Pultec
  MEQ-5 + dbx 160 + Pultec HLF-3C** is an era-appropriate **PROXY for the tone**, not the literal King
  Studios signal path.

## Inputs & setup

- Inputs (prose — **`$ARGUMENTS`** is the whole string): the **stems folder** the user provided (it may
  contain SPACES — treat the WHOLE path as ONE argument and QUOTE it everywhere); an optional **slug** (else
  slugify the folder name); an optional **BPM** (for Stage 5 loops). Do NOT rely on positional `$1`/`$2`/`$3`.
- Prereqs: `uv sync --extra drum-prep` (this repo); in `../stemmy-loops-mcp`: `uv sync --extra vst --extra
  mixing`. `uaudio_api_vision_channel_strip.vst3` + `uaudio_pultec_meq-5.vst3` + `uaudio_dbx_160.vst3` +
  `uaudio_pultec_hlf-3c.vst3` installed/authorized (the `uaudio_*` builds render headless; never the `UAD
  ….component` twins). `GEMINI_API_KEY` only for the optional Stage-4b A/B.
- **Run scripts with the stemmy-loops vst venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python`. In a git
  worktree the `../` is WRONG — resolve it to the ABSOLUTE venv path next to the canonical checkout.
- **Always pass ABSOLUTE paths** to `find-loops` / `stemmy-gemini` tools (they resolve relative to the
  server cwd). In a git worktree, `artifacts/`/`projects/` live in the canonical checkout.

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` ([[format-fix]]).
- Baseline-measure each stem (`measure-loudness` + `measure-spectrum` + `check-clipping`); keep the
  third-octave spectra — they drive the Stage-2 plan.

## Stage 1 — phase-align close mics → overheads (gated)

- `uv run --no-sync drum-prep detect <stems-dir>` → confirm roles (overheads = stereo anchor; narrowed at
  the bus) → `phase-align` → `phase-aligned/`.
- **Stereo-image gate** (same as [[drum-phase-align]]): drum-prep mono-collapses close mics — lossless only
  if dual-mono; **OH MUST stay stereo** before the bus narrows it. See [[drum-stems-warm-loops]] Stage 1.

## Stage 2 — process the stems (DRY, TIGHT, MID-FORWARD)

Author `presets/mix/<slug>-stem-process.plans.json` from the Stage-0 spectra — **use
`presets/mix/funky-drummer-stem-process.plans.json` as the template** (built for `artifacts/drums`; adapt
freqs/gains to the supplied kit). Funky-Drummer rules:

- **Tight + dry.** Controlled lows, defined-not-clicky kick, a snappy snare; a small positive `shape-bands`
  transient keeps the funk pocket snap (the ghost-note attack).
- **MID-FORWARD** (the inverse of a scooped mix): keep/boost the snare bark (~900 Hz) and presence (~3–4 kHz);
  the hat is **present** (the funky 16ths are a defining element) but tight, not splashy.
- **Restrained, vintage top** — the bus band-limits the very top, so don't add a bright air shelf here.
- **Room is minimal** — the break is dry/mono; keep it tight and far down, or omit.
- declick OFF (percussive). Run: `$VENV scripts/mix/process_stems.py presets/mix/<slug>-stem-process.plans.json
  <phase-aligned-dir> <kit>/processed-funky`. **GOTCHA:** process_stems always runs the API strip +
  peak-normalizes each stem to −1 dBFS — harmless, Stage 3 re-levels by LUFS ([[stem-process]]).

## Stage 3 — snare/kick-FORWARD balance + sum

Measured-LUFS balance: the snare + kick drive the break, the hat present (the funk 16ths), overheads a
controlled mono-ish image, room minimal. Reuse the targets in `presets/mix/funky-drummer.json` → build the
spec → `$VENV scripts/mix/balance_stems.py <spec.json>` → `bus_funky_pre.wav`:

| Role | target LUFS | pan | |
|---|---|---|---|
| **snare top** | **−15** | 0.0 | THE funk backbeat + ghost notes (snappy, mid-forward) |
| kick in | −16 | 0.0 | tight, dry, punchy (the pocket) |
| hi hat | −19 | −0.1 | PRESENT (the funky 16ths), tight |
| overhead | −20 | 0.0 | controlled image (stereo; narrowed at the bus) |
| snare bottom | −26 | 0.0 | a touch of wires/ghost-note snap |
| kick beater | −26 | 0.0 | clean click |
| drum room | −30 | 0.0 | OPTIONAL + MINIMAL (dry/mono — omit or far down) |

One global **−6 dBFS** headroom trim (never per-stem). A balance problem is **not** an EQ problem ([[mix-balance]]).

## Stage 4 — Funky-Drummer bus chain (API Vision → Pultec MEQ-5 → dbx 160 → Pultec HLF-3C → narrow)

`$VENV scripts/mix/funky_drummer_bus.py <pre-bus> bus_funky.wav` — **defaults reproduce the approved
signature** (params in `presets/mix/funky-drummer.json`):

- **A. HPF 35** (subsonic, zero-phase) → **B. API Vision** (New(FF) 4:1 forward console punch + a mid-forward
  EQ: +2 @100, +2 @700, +2 @3k) → **C. Pultec MEQ-5** (passive midrange: +3 @200 body, −3 @500 de-box, +4 @3k
  presence/attack) → **D. dbx 160** (4:1, −22 = the tight VCA KNOCK; raises crest on drums) → **E. (opt)
  Studer 15 IPS** (`--tape`, OFF by default) → **F. Pultec HLF-3C** (band-LIMIT: 50 CPS low-cut + 10 KCS
  high-cut = the vintage/sample-ready bandwidth) → **G. light EQ** (weight + snap) → **H. NARROW** (`adjust-stereo`
  width 0.45) → −1 dBFS mix bus.
- **Why these, and the do-NOT-fix list:** MID-FORWARD (the API + MEQ-5 BOOST the mids — don't scoop);
  BAND-LIMITED (the HLF-3C cuts sub + top — don't restore full-range air/sub); MONO-ish (narrow, the opposite
  of [[in-the-air-tonight]]); DRY (tape off by default). See [[api-vision-channel-strip]] / [[pultec-meq-5]] /
  [[dbx-160]] / [[pultec-hlf-3c]].
- **Tuning knobs:** `--api-comp-ratio`/`--api-comp-thresh` (punch), `--api-lmf`/`--api-hmf` (mid lift),
  `--meq-lm`/`--meq-dip`/`--meq-hm` (the passive midrange), `--dbx-ratio`/`--dbx-thresh` (knock),
  `--hlf-highcut` (10 KCS dark vs 15 KCS brighter), `--tape` (vintage warmth), `--width`, `--no-*`. Expect:
  **crest UP** (the knock), **centroid DOWN** + tilt slightly warmer (band-limited vintage top),
  **correlation UP toward mono** (narrow). Judge the DIRECTION (crest up, band-limited top, narrow image).

### Stage 4b — lock the settings (the tuning workflow)

Run `.claude/workflows/funky-drummer.js` (`/workflows`) — it renders chain variants (API/MEQ mid amounts ·
dbx knock · HLF-3C high-cut · width · ±tape) and runs a **parallel Gemini judge panel** scoring each against
the Funky-Drummer brief (dry, tight knock, mid-forward, vintage band-limit, narrow). Write the winner's
meters into the preset's `approved_signature_full_kit`. **Gemini hears ~16 kbps MONO → trust the meters for
crest/tilt/centroid/correlation, ears for feel** ([[gemini-audio-understanding]]). The tuning workflow
renders **concurrently** — UADx is non-deterministic across concurrent renders, so confirm the winner's
locked meters with a **sequential** re-render.

## Stage 5 — create loops (raw + mastered) / a breakbeat pack

Same as [[loops-to-deliverables]] / [[home-at-last]] Stage 5, on `bus_funky.wav`: structure-trim → **confirm
BPM** (the mandatory checkpoint; `$3` or ask — never guess) → `find-loops` (absolute path, `bpm`,
`bars=[1,2,4,8]`, `separate=false`) → seam → raw (tagged) + mastered (×3 formats, tagged) → `drum-prep
verify-tags` ([[delivery-qc]]). The tagging gotchas are handled in `scripts/loops/build_loops.py`. **This
recipe is the natural source for a breakbeat pack** — for the individual hits use [[slice-oneshots]], and for
a sellable multi-format pack use [[sample-pack]].

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/phase-aligned/ · stems/processed-funky/
  mix/   bus_funky_pre.wav · bus_funky.wav (FINAL Funky-Drummer bus, peak −1) · ab_*_m.wav
  loops/        raw Funky-Drummer-bus loops (tagged)
  deliverables/ mastered ×3 formats (tagged)
  track.md      BPM, Funky-Drummer settings, snare/kick-forward balance, structure
presets/mix/<slug>-stem-process.plans.json
artifacts/<slug>-loops/  (find-loops scratch)
```

## Report to the user

Per-stage before→after metrics; the final Funky-Drummer signature vs the approved (crest UP = knock, centroid
DOWN = band-limited vintage top, correlation UP = narrow); the snare/kick-forward balance table; the confirmed
BPM; loop counts + `all_tagged`. It's a **MIX bus** (peak −1, not mastered) → hand to [[master-track]] for a
standalone master, or [[sample-pack]] for a breakbeat pack.

## Pitfalls

- **Tone, not groove.** Don't expect the funk feel without the source performance.
- **Don't scoop the mids.** The MEQ-5 and API BOOST the midrange — the funk presence is the mids.
- **Keep it band-limited.** The HLF-3C cuts sub + top for the vintage bandwidth; don't restore full air/sub.
- **Keep it narrow.** Don't widen toward stereo (that's [[in-the-air-tonight]]); the breakbeat image is narrow.
- **Dry by default.** Add only a touch of tape (`--tape`) if wanted; no reverb/echo.
- **Honest proxy** — the API/MEQ/dbx/HLF chain chases the tone, not the literal King Studios path.
- **UADx non-determinism** in the tuning workflow (concurrent renders) — trust a sequential re-render for the locked meters.

## Related
[[fool-in-the-rain]] · [[tomorrow-never-knows]] · [[home-at-last]] · [[in-the-air-tonight]] · [[back-in-black]] · [[format-fix]] · [[drum-phase-align]] · [[stem-process]] · [[mix-balance]] · [[api-vision-channel-strip]] · [[pultec-meq-5]] · [[dbx-160]] · [[pultec-hlf-3c]] · [[loops-to-deliverables]] · [[slice-oneshots]] · [[sample-pack]] · [[delivery-qc]] · [[gemini-audio-understanding]] · [[master-track]]
