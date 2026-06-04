---
name: fool-in-the-rain
description: "Use when the user wants the Led Zeppelin 'Fool In The Rain' / John Bonham drum sound from a FOLDER of multi-mic drum stems (which must include ROOM + overhead mics) — 'Bonham drums', 'Fool In The Rain drum sound', 'room-forward 70s rock drums', 'make the room the star', 'big warm dark Bonham kit', 'that Zeppelin drum tone'. Room-dominant, warm/dark, fat low-mids, breathing glue; the room mic IS the reverb. The TONE, not the shuffle groove, and it NEEDS room mics. Local DSP + the stemmy MCP servers; needs the `vst` extra + optional GEMINI_API_KEY (perceptual A/B)."
argument-hint: <stems-folder> [slug] [bpm]
---

# fool-in-the-rain — Bonham "Fool In The Rain" drum sound (end to end)

One ordered pipeline that takes a **folder of multi-mic drum stems** and produces the **room-dominant,
warm/dark, breathing John Bonham drum sound** as (a) a finished drum **bus** and (b) drum **loops**. It
composes existing skills/scripts plus a new Bonham bus chain — **defer to those for per-stage detail** and
reuse their proven numerics. Dev-validated 2026-06-03 on a 45 s `artifacts/drums` clip.

**The user-facing steps map to the stages below:** process the stems (Stage 2) · volume-adjust, ROOM-FORWARD
(Stage 3) · EQ the stems (Stage 2 corrective + Stage 4 warm tilt) · use the VST plugins + sum to a bus
(Stage 4: Helios → Studer 15 IPS → SSL) · create loops (Stage 5). Per repo doctrine: per-stem **corrective**
EQ in Stage 2, **level** balance in Stage 3, **warm tonal colour** at the bus in Stage 4 — never EQ to fix a
balance problem ([[mix-balance]]).

## What this is — and is NOT

- It chases the **TONE/feel** (room-dominant balance, warm/dark top, fat low-mids, breathing glue), **not**
  the half-time shuffle **groove** or the ghost-note performance — those live in the source recording.
- It **requires ROOM mics** (and overheads) in the source. No room channel → the defining "the room is the
  reverb" trait cannot be made. The room mic is the **loudest layer** in the balance.
- **Honest nuance:** the real track was cut on an **SSL at Polar Studios, Stockholm** (eng. Leif Mases,
  prod. Jimmy Page) — not a Helios desk. We use the repo's **SSL Bus Compressor 2** for the glue (the SSL
  lineage) and **Helios Type 69** as era-appropriate *warmth colour* ([[helios-type-69]] models the
  Olympic/Basing-Street desk Zeppelin used elsewhere). This is the tone, not a literal signal path —
  the tuning workflow can A/B Helios-on/off.

## Inputs & setup

- Inputs (prose — **`$ARGUMENTS`** is the whole string): the **stems folder** the user provided (it may contain SPACES, e.g. "Ship Studios - Drum Stems" — treat the WHOLE path as ONE argument and QUOTE it in every command); an optional **slug** (else slugify the folder name); an optional **BPM** (for Stage 5 loops). Do NOT rely on positional `$1`/`$2`/`$3` — a spaced path space-splits and they expand to garbage tokens.
- Prereqs: `uv sync --extra drum-prep` (this repo); in `../stemmy-loops-mcp`: `uv sync --extra vst --extra mixing`. UADx `uaudio_helios_type_69.vst3` + `uaudio_studer_a800.vst3` + `SSL Native Bus Compressor 2.vst3` installed/authorized (the `uaudio_*` builds render headless; never the `UAD ….component` twins). `GEMINI_API_KEY` only for the optional Stage-4b A/B.
- **Run scripts with the stemmy-loops vst venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python` (normal main-checkout default). **In a git worktree the `../` is WRONG** — unlike the `.mcp.json` servers, these scripts take the path literally and fail (`MISSING ../stemmy-loops-mcp/.venv/bin/python`); the sibling lives next to the MAIN checkout, so resolve it and pass the ABSOLUTE venv path. `drum-prep` via `uv run --extra drum-prep drum-prep`.
- **Always pass ABSOLUTE paths** to `find-loops` / `stemmy-gemini` tools (they resolve relative to the server cwd). In a git worktree, `artifacts/`/`projects/` live in the canonical checkout.

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` (`[[format-fix]]`).
- Baseline-measure each stem (`measure-loudness` + `measure-spectrum` + `check-clipping`); keep the third-octave spectra — they drive the Stage-2 plan. **Confirm a ROOM mic and overheads are present** (this recipe is built around them).

## Stage 1 — phase-align close mics → overheads (gated)

- `uv run --extra drum-prep drum-prep detect <stems-dir>` → confirm roles (FX/reverb returns auto-detect as `fx`, excluded; overheads = stereo anchor; room = polarity-only; an UNKNOWN role from a non-standard mic NAME, e.g. "Crotch Mic", must be identified by SIGNAL not name — a ~70 Hz LF-dominant channel is a `kick_sub` — and pinned in a `kit.json`, passed with `--manifest`). → `uv run --extra drum-prep drum-prep phase-align <stems-dir>` → `phase-aligned/`.
- **Stereo-image gate** (same as [[drum-phase-align]]): drum-prep mono-collapses close mics — lossless only if dual-mono; **OH/room MUST stay stereo** (the room/OH width is the Bonham image). See [[drum-stems-warm-loops]] Stage 1 for the full gate.

## Stage 2 — process the stems (GENTLE, warmth-preserving)

Author `presets/mix/<slug>-stem-process.plans.json` from the Stage-0 spectra — **use
`presets/mix/fool-in-the-rain-stem-process.plans.json` as the template** (it's built for `artifacts/drums`;
adapt freqs/gains to the supplied kit). Bonham rules differ from the warm-tight recipe:

- **Keep the low-mid warmth.** De-box **gently and only where there's a real peak**, and on the LOUD room
  + overhead stems do NOT also cut lows/low-mids in the `color_api.eq` (set `lf_gain`/`lmf_gain` = 0). Stacking
  a corrective bell + an API low-mid cut SCOOPS the warmth and brightens the whole bus (learned in the dev
  pass: it pulled the final tilt from −2.0 to −1.6). **NO air boosts** anywhere (Bonham is dark).
- **Don't gate the snare** and don't add transient snap — we want the natural body + ghost notes, not a
  modern crack. Keep the room **light** (HPF ~45 to keep its low weight; one tiny box trim at most).
- declick OFF (percussive). Run: `$VENV scripts/mix/process_stems.py presets/mix/<slug>-stem-process.plans.json <phase-aligned-dir> <kit>/processed-fitr`. **GOTCHA:** process_stems always runs the API strip + peak-normalizes each stem to −1 dBFS — harmless, Stage 3 re-levels by LUFS ([[stem-process]]).

## Stage 3 — ROOM-FORWARD balance (the Bonham inversion) + sum

Measured-LUFS balance where the **ambience is the loudest layer** — the inverse of a modern close-mic
balance. Reuse the targets in `presets/mix/fool-in-the-rain.json` → build the spec → `$VENV
scripts/mix/balance_stems.py <spec.json>` → `bus_fitr_pre.wav`:

| Role | target LUFS | pan | |
|---|---|---|---|
| **drum room** | **−16** | 0.0 | THE STAR (stereo) |
| overhead | −18 | 0.0 | kit image, just under |
| kick in | −20 | 0.0 | weight/support |
| snare top | −21 | −0.05 | deep, fat, ghost-notes intact |
| kick beater | −30 | 0.0 | a little click |
| snare bottom | −34 | −0.05 | a touch of wires |
| hi hat | −32 | −0.25 | barely (OH/room own the cymbals) |

One global **−6 dBFS** headroom trim (never per-stem). The balance table should show **room/OH with the
smallest attenuation** (loudest). If the supplied room is weak, raise the room/OH floor (e.g. −14/−16) — the
tuning workflow sweeps this. A balance problem is **not** an EQ problem ([[mix-balance]]).

## Stage 4 — Bonham bus chain (Helios → Studer 15 IPS → SSL → polish)

`$VENV scripts/mix/fool_in_the_rain_bus.py <pre-bus> bus_fitr.wav` — **defaults reproduce the approved
signature** (params in `presets/mix/fool-in-the-rain.json`):

- **A. HPF 35** (subsonic, zero-phase) → **B. Helios Type 69** (Mic gain 40 + pad −20, 700 Hz Peak +3, NO
  air, output level −14) → **C. Studer A800 @ 15 IPS NAB** (fat ~50–70 Hz head-bump BLOOM, repro_hf 2 darkens)
  → **D. SSL Bus Comp 2** (4:1, attack 10 ms, AUTO release, SC-HPF 60, ~3 dB makeup — clean STEREO breathing
  glue) → **E. zero-phase polish** (low_shelf +1.5@120, bell +1.5@300 thump, bell −2@3k, high_shelf +0.5@10k)
  → −1 dBFS mix bus.
- **Why these, and the do-NOT-fix list:** 15 IPS (not 30) BLOOMS the lows = the fat Bonham bottom; NO
  low-band multiband (warm-tight tightens, Bonham blooms); SSL attack 10 ms — a 30 ms attack on a peaky drum
  bus RAISES crest (compresses sustain, not peaks); Helios hi-shelf only CUTS and its bass boost is INERT
  headless (weight comes from the tape, not Helios). See [[studer-a800]] / [[ssl-bus-compressor-2]] /
  [[helios-type-69]].
- **Tuning knobs:** `--no-helios` (drop the colour), `--ips "30 IPS"` (tighter), `--ssl-thresh/--ssl-makeup`
  (more/less glue), `--repro-hf` (top darkness), `--helios-gain`/`--helios-level` (colour amount). Expect:
  centroid DOWN ~1000 Hz, tilt more negative (warm, ~−2.0), correlation MODERATE ~0.65–0.85 (room stereo
  preserved — far below the warm-tight bus's 0.97). **Crest is content-dependent** (a hyper-dynamic room
  stays high); "breathing glue" = a few dB of crest reduction vs the pre-bus, not an absolute 16–18.

### Stage 4b — lock the settings (the tuning workflow)

Run `.claude/workflows/fool-in-the-rain.js` (`/workflows`) — it renders chain variants (15 vs 30 IPS ·
Helios on/off · SSL attack/threshold · room floor) and runs a **parallel Gemini judge panel** scoring each
against the Bonham brief (roominess, warmth, glue-not-crush, low-mid weight, breathing). Write the winner's
meters into the preset's `approved_signature_full_kit`. **Gemini hears ~16 kbps MONO → trust the meters for
tilt/low-end/correlation, ears for feel** ([[gemini-audio-understanding]]).

## Stage 5 — create loops (raw + mastered)

Same as [[loops-to-deliverables]] / [[drum-stems-warm-loops]] Stage 5, on `bus_fitr.wav`: structure-trim →
**confirm BPM** (the mandatory checkpoint; `$3` or ask — never guess) → `find-loops` (absolute path, `bpm`,
`bars=[1,2,4,8]`, `separate=false`) → seam → raw (tagged) + mastered (gentle **−15** to preserve the high
crest; ×3 formats, tagged) → `drum-prep verify-tags` ([[delivery-qc]]). The tagging gotchas are handled in
`scripts/loops/build_loops.py` — don't undo them.

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/phase-aligned/ · stems/processed-fitr/
  mix/   bus_fitr_pre.wav · bus_fitr.wav (FINAL Bonham bus, peak −1) · ab_*_m.wav
  loops/        raw Bonham-bus loops (tagged)
  deliverables/ mastered ×3 formats (tagged)
  track.md      BPM, Bonham settings, room-forward balance, structure
presets/mix/<slug>-stem-process.plans.json
artifacts/<slug>-loops/  (find-loops scratch)
```

## Report to the user

Per-stage before→after metrics; the final Bonham signature vs the approved (centroid down, tilt warm,
correlation moderate = room preserved); the room-forward balance table (room/OH loudest); the confirmed BPM;
loop counts + `all_tagged`. It's a **MIX bus** (peak −1, not mastered) → hand to [[master-track]] for a
standalone master.

## Related
[[format-fix]] · [[drum-phase-align]] · [[stem-process]] · [[mix-balance]] · [[warm-drum-bus]] · [[drum-stems-warm-loops]] · [[helios-type-69]] · [[studer-a800]] · [[ssl-bus-compressor-2]] · [[loops-to-deliverables]] · [[delivery-qc]] · [[gemini-audio-understanding]] · [[master-track]]
