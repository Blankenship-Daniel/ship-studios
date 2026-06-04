---
name: drum-stems-warm-loops
description: "Use when the user has a FOLDER of drum stems (kick, snare, overheads, room, +optional FX returns) and wants the whole job done end-to-end: process the stems, volume-balance them, EQ them, sum them into the user's WARM/tight drum bus, and cut drum loops — 'turn these drum stems into a warm bus and loops', 'process+mix my drum stems and make loops', 'warm drum bus + loop pack from this folder', 'do the whole drum-stems-to-loops workflow'. The composite pipeline that chains [[stem-process]] → [[mix-balance]] → [[warm-drum-bus]] → [[loops-to-deliverables]], parameterized by a stems folder + slug, with two confirm-points (BPM, FX-return A/B). Local DSP + the stemmy MCP servers; needs the `vst` extra (Studer/API) + GEMINI_API_KEY (perceptual A/B)."
argument-hint: <stems-folder> [slug]
---

# drum-stems-warm-loops — drum stems → warm/tight bus → loops (end to end)

One ordered pipeline that takes a **folder of drum stems** and produces (a) the user's approved
**warm + tight/controlled drum bus** and (b) **drum loops** (raw warm-bus loops + a mastered
multi-format pack). It composes existing skills/scripts; **defer to those for the per-stage detail**
and reuse their proven numerics. First validated on `projects/watercolors` (5-piece kit, 104 BPM).

**The five user-facing steps map to the stages below:** process the stems (Stage 2) · volume-adjust
(Stage 3) · EQ the stems (Stage 2, per-stem corrective + Stage 4 warm tilt) · sum with the warm-bus
preference (Stages 3–4) · create loops (Stage 5). Per repo doctrine: per-stem **corrective** EQ in
Stage 2, **level** balance in Stage 3, **warm tonal tilt** at the bus in Stage 4 — never EQ to fix a
balance problem ([[mix-balance]]).

## Inputs & setup

- **`$1` = stems folder** (e.g. `~/Desktop/<Name> - Drum Stems` or `projects/<slug>/stems`). **`$2` = slug** (optional; else slugify the folder name).
- Prereqs: `uv sync --extra drum-prep` (this repo); in `../stemmy-loops-mcp`: `uv sync --extra vst --extra mixing`. `GEMINI_API_KEY` for the Stage-4b A/B. UADx `uaudio_studer_a800.vst3` + `uaudio_api_vision_channel_strip.vst3` installed/authorized.
- **Run scripts with the stemmy-loops venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python`. `drum-prep` via `uv run --no-sync drum-prep`.
- **MCP/Gemini tools resolve relative paths to the SERVER's cwd → always pass ABSOLUTE paths** to `find-loops` / the `stemmy-gemini` tools.

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` (`afconvert -d LEI24 -f WAVE in.aif out.wav`; `[[format-fix]]`). True WAV matters: `find-loops` is WAV-only, and genuine AIFF confuses ffmpeg.
- Baseline-measure each stem (`measure-loudness` + `measure-spectrum` + `check-clipping`). Keep the third-octave spectra — they drive the Stage-2 EQ plan. Watch for the **overheads being the loudest stem / inter-sample clipping + low-frequency kick bleed** (the usual case — the warm balance pulls OH down, which also fixes the clip).

## Stage 1 — phase-align close mics → overheads (gated)

- `uv run --no-sync drum-prep detect <stems-dir>` → confirm roles. **FX/reverb returns auto-detect as `fx` and are excluded** from align; overheads = stereo anchor; room = polarity-only.
- `uv run --no-sync drum-prep phase-align <stems-dir>` → `phase-aligned/`. Expect close mics to go from *negatively* correlated with the OH to positive (tighter lows).
- **Stereo-image gate** (these are usually stereo *bounces*, not mono mics): `measure-stereo` each source. drum-prep **mono-collapses close mics** — that's **lossless if they're dual-mono** (`is_mono=True`, `max|L−R|=0`), which kick/snare bounces usually are; OH/room stay stereo and must be preserved. If a close mic has real width, fall back to a stereo-preserving integer-sample shift, or skip align. Note: `phase-aligned/` files are 24-bit AIFF with `.wav` names — soundfile reads them; don't feed them to ffmpeg.

## Stage 2 — process the stems (+ per-stem corrective EQ)

Diagnose from the Stage-0 spectra, then author `presets/mix/<slug>-stem-process.plans.json` (schema = `scripts/mix/process_stems.py`). **Measure-driven & conservative** (finished bounces). Warm-philosophy rules: **cuts, never bright boosts**; no exciter; top-taming happens at the bus.

- **HPF every stem** to clear rumble/bleed (kick ~30; snare ~70; **overheads ~110 to kill kick bleed**; room ~120). De-box **only where there's a real peak** (e.g. an OH/room ~400 Hz honk) — don't cut a region that's already 10 dB down (that just brightens it; see the Watercolors snare).
- `suppress_resonances` (de_harsh) only catches **narrow** resonances — it's a no-op on broadband presence; don't add it as a top-tamer.
- Run: `$VENV scripts/mix/process_stems.py presets/mix/<slug>-stem-process.plans.json <phase-aligned-dir> <processed-dir>`. **GOTCHA:** `process_stems.py` **always** runs the API Vision strip (near-passthrough at `line_gain 0`) **and peak-normalizes each stem to −1 dBFS** — harmless because Stage 3 re-levels by LUFS. declick stays OFF (percussive). See `[[stem-process]]` — for a big kit, the `stem-process` workflow fans the per-stem diagnosis out one-agent-per-stem (the executor still runs as one serial UADx-safe pass).

## Stage 3 — warm balance (volume-adjust) + sum

Measured-LUFS warm spread (bright stem **down**, body/room **up**), one global −6 dBFS headroom trim, `pan 0` for all (stereo stems keep their image; `pan` only affects mono inputs). Reuse the approved targets (`presets/mix/warm-tight-drum-bus.json`): **kick −16 · snare −18 · overhead −22 · room −26 · FX return −30**.

- Build **two** specs → `$VENV scripts/mix/balance_stems.py <spec.json>`: one **with** the FX return, one **dry**. The FX return enters here (not Stage 2): light-HPF it and **pad to full kit length** first (balance truncates to the shortest input). See `[[mix-balance]]`.

## Stage 4 — warm drum-bus tone chain

`$VENV scripts/mix/warm_bus.py <pre-bus> <out>` on **both** pre-buses: HPF 35 + warm tilt (LS +1.5@180, bell −1.5@2.5k, HS −4@6k, zero-phase) → multiband on the **<110 Hz** band (3:1, tight bottom) → **Studer A800 30 IPS** tape → −1 dBFS mix bus. **Defaults reproduce the approved signature** (tilt ~−2.65, corr ~0.97, crest ~21).

- **Dark/bright source tuning (now parameterized):** if the result over-darkens (centroid/tilt too low — common when the kit has few cymbals / the OH was pulled down), ease `--hs-gain -2 --repro-hf 3`; if over-glued (crest < ~20) lower `--tape-in-gain 4`. Watercolors used `--hs-gain -2 --repro-hf 3`. See `[[warm-drum-bus]]` / `[[studer-a800]]`.

### Stage 4b — FX-return decide-by-ear (Gemini), then promote

Loudness-match the two warm buses (peak-safe gain to a common LUFS) and A/B by ear: `compare-audio-files` (which is better for a warm/tight bus?) **plus** `detect-mix-issues` on the with-FX bus (does the reverb add wash/mud?). Promote the winner → `projects/<slug>/mix/bus_warm.wav`. For a rigorous, meter-grounded pick, run the **`warm-bus-shootout` workflow** instead (one Gemini lens agent per bus × {warmth, tightness, life}, ranked with dissent) — pass both level-matched buses as `variants:[{name,path(ABSOLUTE),meters}]`.
- **Gemini hears ~16 kbps MONO → cross-check every claim against the meters** (`[[gemini-audio-understanding]]`): a "serious boominess / cut the lows" flag is often the mono downmix exaggerating centered kick/bass — trust the *stereo* tilt vs the approved signature. Gemini may also **hallucinate content over near-silence** (it once reported a "spoken-word voiceover" on a −65 dBFS tail) — verify structure with a meter/energy scan, not Gemini's ears.

## Stage 5 — create loops (raw + mastered)

1. **Structure scan** (per-second RMS) to find where the drums actually play and **trim trailing silence** before slicing (Watercolors: drums 0–58 s, then silence). Save the trimmed performance as `projects/<slug>/mix/bus_warm.wav` (keep the untrimmed as `bus_warm_dry.wav`).
2. **BPM — detect, then CONFIRM with the user** (the one mandatory checkpoint). Beat-track the steady groove; auto-detect is octave/phase-ambiguous, so present the estimate + ask (the user usually knows the session tempo). Never guess.
3. `find-loops` (absolute path, confirmed `bpm`, `bars=[1,2,4,8]`, `separate=false`, `out_dir=artifacts/<slug>-loops`).
4. `$VENV scripts/loops/build_loops.py artifacts/<slug>-loops projects/<slug>/loops projects/<slug>/deliverables --name-prefix <slug>_drums --target-lufs -15` — per loop: seam → **raw** (tagged, no re-master, keeps warm character) and **mastered** (gentle −15, ×3 formats, tagged). It encodes the tagging gotchas (below).
5. `uv run --no-sync drum-prep verify-tags projects/<slug>/loops` and `…/deliverables` → expect `all_tagged=True` ([[delivery-qc]]).

**Tagging gotchas (handled in `build_loops.py` — don't undo):** `export-deliverables tag=true` drops the RIFF INFO → export `tag=False` then tag after; and `tag-deliverable` force-writes **PCM_24**, so tagging a 16-bit file upgrades it — 24-bit exports get the full in-WAV tag, **16-bit (distribution) keeps PCM_16 and has the RIFF LIST chunk spliced in from a tagged 24-bit twin** (true 16-bit *with* the in-WAV tag — beats sidecar-only; see [[delivery-qc]]). **Master gently**: drums are high-crest, so a low LUFS target over-limits (−12 collapsed crest 14→9); −15 preserves it.

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/phase-aligned/ · stems/processed/
  mix/   bus_warm_pre_{withfx,dry}.wav · bus_warm_{withfx,dry}.wav · bus_warm.wav (FINAL, trimmed) · ab_*_m.wav
  loops/        raw warm-bus loops (tagged)
  deliverables/ mastered ×3 formats (tagged; 16-bit distribution stays 16-bit)
  track.md      BPM, warm settings, structure, FX decision
presets/mix/<slug>-stem-process.plans.json
artifacts/<slug>-loops/  (find-loops scratch + manifest + seam/ + master/)
```

## Report to the user

Per-stage before→after metrics; the final warm signature vs the approved (tilt/corr/crest); the FX-return verdict + why; the confirmed BPM; loop counts + formats + `all_tagged`. The warm bus is a **mix bus** (peak −1, not loud) → hand to `[[master-track]]` if a standalone master is wanted.

## Unattended / batch

For no-checkpoint runs (CI/batch), pass the BPM up front and pre-decide the FX return (skip the Gemini A/B), or fold these into a `ship-studios` CLI subcommand over `ship_studios/pipelines.py`. Interactive runs should keep both confirm-points.

## Related
[[format-fix]] · [[drum-phase-align]] · [[stem-process]] · [[mix-balance]] · [[warm-drum-bus]] · [[studer-a800]] · [[api-vision-channel-strip]] · [[loops-to-deliverables]] · [[delivery-qc]] · [[gemini-audio-understanding]] · [[master-track]]
