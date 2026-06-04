---
name: drum-stems-character
description: "Use when the user has a FOLDER of drum stems and wants the whole kit corrected then shaped to a CHOSEN tonal character end-to-end — 'process my drum stems and give them a character', 'EQ+normalize+soothe each stem then make the kit warm/punchy/crushed/aggressive/clean', 'apply a tonal character to my drum bus', 'Bonham or Tomorrow-Never-Knows character on these stems', 'reusable drum-stems character pipeline'. Fans out a PURE-DSP per-stem corrective, ASKS the user a character (Clean/Warm/Punchy/Crushed/Aggressive/Bonham/TNK), fans out per-stem PLANNING of a character-aware UADx chain then applies it one stem at a time (serial — concurrent UADx is non-deterministic), phase-aligns the processed stems, balances + colors the bus to that character, finalizes the bus, and hands to [[master-track]]. Local DSP + the stemmy MCP servers; needs the `vst` extra (Studer/API + the bus scripts' Fairchild/Helios/SSL/Vibe) + optional GEMINI_API_KEY (perceptual A/B)."
argument-hint: <stems-folder> [character] [slug]
---

# drum-stems-character — drum stems → character → mastered

One reusable pipeline that takes a **folder of drum stems**, corrects each stem, applies a **user-chosen tonal character** (per-stem + on the bus), sums to a stereo drum bus, finalizes it, and masters it. It composes existing skills/scripts and the **`drum-stems-character` fan-out workflow** — **defer to those for per-stage detail** and reuse their proven numerics. The sibling of [[drum-stems-warm-loops]] (which is warm-only and ends at loops); this is **character-parameterized** and ends at a master.

**The user-facing steps map to the stages below:** (2) EQ+normalize+soothe each stem → Stage 1 · (3) ask the character → Stage 2 · (4) apply the character per stem → Stage 3 · (5) phase-align → Stage 4 · (6) mix to a bus targeting the character → Stage 5 · (7) EQ+normalize+soothe the bus → Stage 6 · then master → Stage 7. Per repo doctrine: per-stem **corrective** EQ in Stage 1, **level** balance by measured LUFS in Stage 5, **tonal character** per-stem (Stage 3) + at the bus (Stage 5) — never EQ to fix a balance problem ([[mix-balance]]).

## Inputs & setup

- **`$1` = stems folder** (e.g. `~/Desktop/<Name> - Drum Stems` or `projects/<slug>/stems`). **`$2` = character** (optional; else ask in Stage 2). **`$3` = slug** (optional; else slugify the folder name).
- Prereqs: `uv sync --extra drum-prep` (this repo); in `../stemmy-loops-mcp`: `uv sync --extra vst --extra mixing`. The `vst` extra + UADx plugins authorized: `uaudio_studer_a800.vst3`, `uaudio_api_vision_channel_strip.vst3` (per-stem), plus the bus scripts' `uaudio_fairchild_660` / `uaudio_helios_type_69` / SSL / Vibe for the famous characters. `GEMINI_API_KEY` only for the optional Stage-6 A/B.
- **Run scripts with the stemmy-loops venv:** `VENV=../stemmy-loops-mcp/.venv/bin/python`. `drum-prep` via `uv run --no-sync drum-prep`.
- **MCP tools resolve relative paths to the SERVER's cwd → always pass ABSOLUTE paths.**

## Stage 0 — convert + baseline measure

- Convert every stem to **48k/24 true WAV** into `projects/<slug>/stems/` (`afconvert -d LEI24 -f WAVE in.aif out.wav`; [[format-fix]]). True WAV matters.
- Baseline-measure each stem (`measure-loudness` + `measure-spectrum` + `check-clipping`). Watch for the **overheads being the loudest stem + low-frequency kick bleed** (the usual case — the Stage-5 balance pulls OH down).

## Stage 1 — corrective fan-out (EQ + normalize + soothe each stem)

Run the **`drum-stems-character` workflow** in `mode:'correct'` — it fans out one agent per stem (parallel, read-only measure → a pure-DSP corrective plan: clean/HPF + corrective `eq_bands` + `de_harsh` soothe + level-dependent `dynamic_eq`), then runs `scripts/mix/process_stems.py` ONCE serially.

```
Workflow drum-stems-character { mode:'correct',
  stems:[<ls the kit dir>], srcDir:"<ABS projects/<slug>/stems>", outDir:"<ABS …/stems/corrected>" }
```

- `process_stems.py` **always** runs the API strip at `line_gain 0` (near-passthrough) **and peak-normalizes each stem to −1 dBFS** (= the "normalize" step) — harmless; Stage 5 re-levels by LUFS. declick stays OFF (percussive). `suppress_resonances` (the "soothe") only catches **narrow** ringing.
- **Confirm-point A:** show the returned per-stem before→after table (LUFS / crest / centroid / tilt); proceed on user OK.

## Stage 2 — ask the tonal character

If `$2` wasn't given, the **session** (not the workflow — workflows can't prompt) calls **AskUserQuestion** with these options (each maps to a proven bus chain):

| Option | Character | Per-stem | Bus signature |
|---|---|---|---|
| **Clean** | corrective only, no color | empty chain | balance only |
| **Warm** | tape warmth, tight bottom | Studer 30 IPS light | `warm_bus.py` (Studer 30 IPS) |
| **Punchy** | tight American console punch | API comp light | `punchy_bus.py` (API Vision) |
| **Aggressive** | dense/forward, hard comp | API comp driven | `punchy_bus.py` harder comp |
| **Crushed** | dark, fat, pumped | Studer 15 IPS dark | `tomorrow_never_knows_bus.py` |
| **Bonham** (Fool In The Rain) | room-forward 70s warm | Studer 30 IPS light | `fool_in_the_rain_bus.py` |
| **TNK** (Tomorrow Never Knows) | lo-fi, mono, crushed | Studer 15 IPS dark | `tomorrow_never_knows_bus.py` (+ mono/Vibe) |

## Stage 3 — character fan-out (apply the character per stem)

Run the **`drum-stems-character` workflow** in `mode:'character'` with the chosen `character`. It fans out one agent per stem to **PLAN** a role-aware UADx recipe (parallel, read-only measure), then runs `scripts/mix/character_stems.py` ONCE serially (one stem at a time — concurrent UADx is non-deterministic).

```
Workflow drum-stems-character { mode:'character', character:"<chosen>",
  stems:[…], srcDir:"<ABS …/stems/corrected>", outDir:"<ABS …/stems/character>" }
```

- **Per-stem character is intentionally LIGHTER than the bus** and uses ONLY the two UADx plugins with exact, proven param templates — **Studer A800** ([[studer-a800]]) and **API Vision** ([[api-vision-channel-strip]]). The *signature* color (Fairchild/Helios/SSL/Vibe) is added at the BUS in Stage 5 (avoids double-coloring). Close mics (kick/snare/tom) get the template's `close` recipe; ambient mics (overhead/room/cymbals) get the lighter `ambient` recipe or an empty chain.
- **Confirm-point B:** show the per-stem before→after table; a `FAIL:` note = a param that didn't set or a passthrough render → for that stem, fall back to a pure-DSP approximation (e.g. Warm → low-shelf + HF-cut via `apply-eq`).

## Stage 4 — phase-align the processed stems

`uv run --no-sync drum-prep phase-align <ABS …/stems/character> [--kick-lowpass 180]` → `…/stems/character/phase-aligned/`. Aligning the **processed** stems means drum-prep cross-correlates exactly the audio that will be summed. **HPF'd-overheads gate:** if Stage 2/3 high-passed the overheads, the kick (LP180) has nothing in the OH to lock to → a bogus delay. In that case derive the delays from the **full-band originals** and apply them to the processed stems (a pure time-shift commutes with the zero-phase EQ/gating already applied — all LTI), or keep an un-HPF'd OH for the correlation ([[drum-phase-align]] Pitfalls). **Stereo-image gate** (these are usually stereo bounces): drum-prep mono-collapses close mics — lossless only if they're dual-mono (`measure-stereo`: `is_mono`, `max|L−R|=0`); OH/room stay stereo. **AIFF-as-.wav trap:** `phase-aligned/` files are 24-bit AIFF with `.wav` names — soundfile reads them; never feed that dir to ffmpeg ([[drum-phase-align]]).

## Stage 5 — balance + character bus color (mix to a bus targeting the character)

Set levels by **measured LUFS** (`$VENV scripts/mix/balance_stems.py <spec.json>` — bright stems down, body/room per character; one global −6 dBFS headroom; `pan 0`, stereo stems keep their image), then run the character's bus script on the pre-bus. **Never peak-normalize the sum; never balance by eyeballed dB/RMS** ([[mix-balance]]).

| Character | balance targets | Bus script + flags |
|---|---|---|
| **Clean** | neutral (close mics fwd, ambience moderate) | none — the balanced bus IS the output |
| **Warm** | reuse `presets/mix/warm-tight-drum-bus.json` (kick −16 · snare −18 · OH −22 · room −26) | `warm_bus.py <pre> <out>` (`--hs-gain -2 --repro-hf 3` if over-dark) — [[warm-drum-bus]] |
| **Punchy** | dry/tight (close mics fwd, OH under, ambience out) | `punchy_bus.py <pre> <out>` |
| **Aggressive** | same dry/tight | `punchy_bus.py <pre> <out> --comp-thresh -14 --comp-ratio 6` (never boost the top) |
| **Crushed** | tom-forward (reuse `presets/mix/tomorrow-never-knows.json`) | `tomorrow_never_knows_bus.py <pre> <out> --width 1.0 --dark -2` ([[fairchild-660]]) |
| **Bonham** | room-forward (reuse `presets/mix/fool-in-the-rain.json`: room −16 · OH −18 · kick −20 · snare −21) | `fool_in_the_rain_bus.py <pre> <out>` ([[fool-in-the-rain]], [[helios-type-69]]) |
| **TNK** | tom-forward | `tomorrow_never_knows_bus.py <pre> <out>` (+ `--la3a` / `--vibe`) ([[tomorrow-never-knows]]) |

## Stage 6 — finalize the bus (EQ + normalize + soothe on the bus)

The character is already on — this is gentle corrective only ([[finalize-mix]], **no limiting**): `apply-eq` (corrective shelves/cuts), `suppress-resonances` (soothe any bus ring), and the −1 dBFS the bus scripts already emit. **Verify against the character's approved signature** (`measure-spectrum`/`measure-loudness`) — if centroid/tilt overshoots, back off the **per-stem** drive first (Stage 3), not the bus (double-coloring guard). Optional: a Gemini A/B for the famous characters (cross-check every claim against the meters — Gemini hears ~16 kbps mono).

## Stage 7 — master the bus

The finalized bus is a **mix bus** (peak −1, not loud) → hand to [[master-track]] (or `ship-studios master <bus> --platform <p>`) for loudness target / limiter / streaming-compliance / deliverable export.

## Fan-out

- **Stage 1 (corrective) is PURE DSP** → the `drum-stems-character` workflow fans out the per-stem *planning* one agent per stem; the apply is one serial `process_stems.py` (the executor loads one strip per stem at `line_gain 0`, so the render stays serial — the documented UADx render non-determinism).
- **Stage 3 (character) is UADx VST** → fan out the per-stem *PLANNING* (the expensive part — measure + author a chain), then ONE serial `character_stems.py` pass applies each chain one stem at a time. This reconciles "fan out the character" with UADx-serial: the *thinking* is parallel, only the *rendering* is serialized.
- Stages 4–7 are serial single-commands (phase-align / balance+bus / finalize / master) — no fan-out benefit, so they stay in this skill, not the workflow. The workflow is reusable on its own as `/drum-stems-character`.

## Outputs

```
projects/<slug>/
  stems/ (48k/24 WAV) · stems/corrected/ · stems/character/ · stems/character/phase-aligned/
  mix/   bus_<character>_pre.wav · bus_<character>.wav (finalized mix bus)
  masters/  <character> master (from master-track)
  track.md  character, per-stage signatures, BPM, target platform/LUFS
  stems/corrected/drum-stems-character.correct.plans.json   (per-stem corrective plans)
  stems/character/drum-stems-character.character.plans.json (per-stem UADx recipes)
```
(the workflow defaults `plansOut` next to each stage's `outDir`; pass `plansOut` to redirect.)

## Report to the user

Per-stage before→after metrics; the chosen character; the final bus signature vs the character's approved signature (tilt/centroid/crest); any per-stem `FAIL:` notes + the fallback taken; the master's LUFS/true-peak vs the platform target.

## Unattended / batch

For no-checkpoint runs, pass `$2` (character) up front and skip the Gemini A/B. Interactive runs should keep both confirm-points (the per-stem tables).

## Related
[[drum-stems-warm-loops]] · [[stem-process]] · [[format-fix]] · [[mix-balance]] · [[drum-phase-align]] · [[warm-drum-bus]] · [[fool-in-the-rain]] · [[tomorrow-never-knows]] · [[finalize-mix]] · [[master-track]] · [[studer-a800]] · [[api-vision-channel-strip]] · [[fairchild-660]] · [[helios-type-69]] · [[vst-preset]]
