# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What ship-studios is

ship-studios is the **central MCP host** for a music *create → mix → master → deliver* workflow. It owns no DSP of its own: it composes two sibling MCP servers into one coherent pipeline surface.

- **stemmy-loops** (`../stemmy-loops-mcp`) — loop extraction + **in-process pure-DSP** mix/master tools. Slices drum stems/mixes into loops, and does deterministic measurement and rendering (loudness, EQ, compression, mastering, export). No network, no listening — just signal processing.
- **stemmy-gemini** (`../stemmy-gemini-mcp`) — **Gemini perceptual critique** (the model actually *listens* to the audio) plus a **parallel pure-DSP measurement suite**. Use it to hear what a meter can't (sibilance feel, pumping, "too harsh"), and for platform-compliance / reference-match numbers.

Both servers are registered in `.mcp.json` and launched as stdio subprocesses via `uv --directory <rel> run <console-script>`. This file is the contract: **only use the tool names listed below, exactly as spelled (mind hyphen vs underscore).**

### Philosophy

A track moves left-to-right through the lifecycle: **understand** the source → **create loops** (optional) → **measure** → **perceptual critique** → **corrective + render** → **deliver**. Measure before you move; let Gemini's ears and the DSP meters cross-check each other; never master inside the mix stage. Pipelines below encode the canonical orderings.

---

## Combined tool surface

Two servers, six lifecycle stages. `[L]` = stemmy-loops, `[G]` = stemmy-gemini. Tools marked `(Gemini)` send audio to the model and need `GEMINI_API_KEY`; `(LLM)` need `ANTHROPIC_API_KEY`; everything else is pure DSP with no env/network requirement.

### 1. Understand (analyze a source perceptually / structurally)

| Capability | Tool | Server |
|---|---|---|
| Transcribe speech, MM:SS timestamps, optional diarize | `transcribe-audio` (Gemini) | `[G]` |
| Q&A over a `start_s..end_s` window | `describe-audio-region` (Gemini) | `[G]` |
| Compare 2–10 files, discriminating features | `compare-audio-files` (Gemini) | `[G]` |
| Zero-shot tag against a label list | `classify-audio` (Gemini) | `[G]` |
| Detect timestamped event instances (kicks, drops) | `extract-audio-events` (Gemini) | `[G]` |
| Summarize long-form audio (>1h / >100MB) | `summarize-long-audio` (Gemini) | `[G]` |
| Extract structured JSON per supplied schema | `audio-to-json` (Gemini) | `[G]` |

### 2. Create loops (extract / shape loops from a stem or mix)

| Capability | Tool | Server |
|---|---|---|
| Fast slice chain → loop WAVs + `manifest.json` | `find-loops` | `[L]` |
| Full analysis chain (roles/structure/`analysis.json`, optional LLM) | `analyze-loops` (LLM when llm flags set) | `[L]` |
| Run Demucs, return drum stem path | `extract-drums` | `[L]` |
| Isolate individual hits (one WAV per onset) | `extract-oneshots` | `[L]` |
| Quantize one loop (groove / length / midi) | `quantize-loop` | `[L]` |
| Show dependency registry / missing primitives | `plan-chain` | `[L]` |
| Diff top loops across runs | `compare-runs` | `[L]` |
| Audible descriptions of a finished loop set | `describe-loops` (Gemini) | `[L]` |
| Feature-derived Haiku captions for loops | `caption-loops` (LLM) | `[L]` |
| LLM critique of an output dir | `diagnose-output` (LLM) | `[L]` |
| NL Q&A over an output dir | `ask-about-output` (LLM) | `[L]` |
| Pre-flight flag recommendation | `suggest-approach` (LLM) | `[L]` |

### 3. Measure (objective DSP reports — read-only)

| Capability | `[L]` tool | `[G]` tool |
|---|---|---|
| Loudness (LUFS-I/ST/M, true-peak, crest, LRA …) | `measure-loudness` | `measure-loudness` |
| Spectrum (third-octave, tilt, bands, centroid) | `measure-spectrum` | `measure-spectrum` |
| Stereo / phase / mono-sum loss | `measure-stereo` | `analyze-phase-mono` |
| Clipping / DC / polarity | `check-clipping` | *(in `check-delivery-spec`)* |
| Distortion (THD/THD+N/aliasing) | `measure-distortion` | — |
| One-shot deliverability report | `inspect-loop` | — |
| Per-band overlap across N loops/stems | `detect-masking` | `analyze-stem-masking` |
| Numeric per-band delta vs reference | `compare-tonality` | `match-reference-numeric` |
| Narrow-Q resonance peaks + notch dB | — | `find-resonances` |
| Sibilance transients + de-esser settings | — | `find-sibilance` |
| Pre-flight delivery checks | — | `check-delivery-spec` |
| Per-platform LUFS/TP compliance | — | `check-streaming-targets` |
| Kick fundamental note + cents off | `tune-kick` | — |

**Overlap rule:** both servers expose `measure-loudness` / `measure-spectrum`. They are independent implementations. Prefer **`[L]`** when you're inside a loops/mastering chain (same code path that renders), and **`[G]`** when you've already opened the gemini session for perceptual work — don't spin up a server just to duplicate a meter. For stereo, `[L] measure-stereo` and `[G] analyze-phase-mono` are interchangeable; pick by which server is already in play.

### 4. Perceptual critique (Gemini listens — all `[G]`, all need `GEMINI_API_KEY`)

| Capability | Tool |
|---|---|
| Tonal/stereo/depth balance critique + suggestions | `analyze-mix-balance` (Gemini) |
| Audible problems (clip/sibilance/mask/pump/phase) + severity/timestamps | `detect-mix-issues` (Gemini) |
| A/B against a reference, perceptual deltas + moves | `compare-to-reference` (Gemini) |
| Master-bus critique + platform guidance + release-ready bool | `mastering-feedback` (Gemini) |
| Hybrid: measure + propose chain + Gemini critique | `recommend-mastering-chain` (Gemini) |

### 5. Corrective + render (write new WAVs — all `[L]`, pure DSP)

| Capability | Tool |
|---|---|
| RBJ biquad EQ (shelves/bells/pass) + tilt | `apply-eq` |
| Downward + parallel compressor, GR stats | `compress-loop` |
| Bass mono-maker + M/S width | `adjust-stereo` |
| Oversampled tanh/tape/soft-clip saturation | `saturate-loop` |
| Multiband transient design + per-band gain (LR4) | `shape-bands` |
| DC/HPF/declick/denoise/gate cleanup | `clean-loop` |
| Best loop wrap point + equal-power crossfade | `optimize-seam` |
| HPF → transient → normalize → limiter → resample/dither | `render-mastered` |
| Loudness-matched [ref \| gap \| processed] audition | `render-ab` |

### 6. Deliver (tag + export — all `[L]`, pure DSP)

| Capability | Tool |
|---|---|
| Embed BPM/key/root/bars/comment + `tags.json` sidecar | `tag-deliverable` |
| Batch format matrix (44.1/16, 48/24, 96/24) + dither | `export-deliverables` |

---

## Canonical pipelines

Each is an ordered tool-call recipe. Server prefix `[L]`/`[G]` precedes the tool. Outputs go to `projects/<track>/` (loop scratch to `artifacts/<run>/`). Skills under `.claude/skills/` and slash commands under `.claude/commands/` wrap these — prefer the skill over hand-typing.

### master-track — near-final mix → platform-ready master + deliverables

1. `[L] measure-loudness` — baseline LUFS / true-peak / crest / PLR / LRA / DR.
2. `[L] measure-spectrum` — baseline tilt + 5-band balance.
3. `[L] measure-stereo` — baseline correlation + mono-sum loss.
4. `[L] check-clipping` — confirm no inter-sample clip / DC / polarity issue.
5. `[L] measure-distortion` — baseline THD / aliasing before the limiter stage.
6. `[G] mastering-feedback` — perceptual critique + `target_platform` + release-ready bool.
7. `[L] render-mastered` — to chosen `target_lufs` + `ceiling_dbtp` → `projects/<track>/masters/`.
8. `[G] check-streaming-targets` — re-verify the render vs Spotify/Apple/YouTube/Tidal…
9. If non-compliant, adjust target and re-render (back to 7).
10. `[L] export-deliverables` — presets 44.1/16, 48/24, 96/24, `tag=true` → `projects/<track>/deliverables/`.

### batch-master — folder of near-final mixes → consistent masters + cross-track table

Per track (loop the folder), then a cross-track pass. One **shared** target for the whole set.

1. `[L] measure-loudness` + `[L] measure-spectrum` + `[L] check-clipping` — per-track baseline.
2. `[G] mastering-feedback` — per-track release-ready bool + harshness flags to steer that track's render.
3. `[L] render-mastered` — to the **shared** `target_lufs`/`ceiling_dbtp` → `projects/<album>/masters/`.
4. `[G] check-streaming-targets` — per-track compliance; re-render that track if it'll be attenuated.
5. `[L] export-deliverables` — presets, `tag=true` → `projects/<album>/deliverables/`.
6. Cross-track: loop `[L] measure-loudness` over every master → LUFS-I / true-peak / LRA + **Δ-from-album-median** table; flag outliers (e.g. >0.5 LU off median).
7. `drum-prep verify-tags` (or delivery-qc) — confirm the RIFF INFO chunk survived export.

The consistency table is the headline. Hand any not-release-ready track to mix-check first; don't loudness-paper a broken mix.

### stem-master — per-stem corrective mixdown → sum → hand to master-track

You **mix** the stems (correct + sum), then **master** the bus. This stage does NOT limit.

1. Per stem: `[L] measure-loudness` + `[L] measure-spectrum` — baseline.
2. `[G] analyze-stem-masking` (stem map) — per-collision dominant stem, stem-to-cut, center Hz, cut dB, Q. Optional `[L] detect-masking` cross-check.
3. `[G] find-resonances` / `[G] find-sibilance` — surgical notch / de-ess settings on the offending stems.
4. `[L] apply-eq` — one call **per losing stem**; complementary cuts (carve bass under kick, tame vocal mud). Cut the loser, don't boost the winner.
5. `[L] compress-loop` / `[L] shape-bands` — per stem where dynamics / transients call for it.
6. `drum-prep stem-mix` — sum the corrected stems to one stereo bus (local DSP; no MCP tool sums a stem set).
7. Re-run `[G] analyze-stem-masking` + `[L] measure-spectrum` — confirm the overlaps shrank.
8. Hand the summed bus to **master-track** for loudness / limiting / compliance / export.

unmask-stems is the masking-only subset (steps 2 + 4 + re-score), when you don't need the sum or master.

### mix-check — diagnose a mix (perceptual + measurement) → concrete moves

1. `[G] detect-mix-issues` — audible problems w/ severity + timestamps.
2. `[G] analyze-mix-balance` — band-by-band tonal/stereo/depth critique.
3. `[L] measure-loudness` — ground the read with objective numbers.
4. `[L] measure-spectrum` — third-octave / tilt / 5-band to confirm or refute the tonal call.
5. `[L] measure-stereo` — correlation / width / mono-sum loss.
6. `[G] find-resonances` — narrow-Q peaks + notch dB → feed `apply-eq` bells.
7. `[G] find-sibilance` — de-esser settings (center Hz, Q, threshold, GR).
8. `[G] analyze-phase-mono` — per-band correlation + polarity flag before EQ.
9. Reconcile perceptual vs measured into a prioritized issue list.
10. `[L] apply-eq` — notches + shelves/tilt from the findings.
11. `[L] compress-loop` — where dynamics analysis called for it. Write to `projects/<track>/mix/`.

**Do not master here** — hand off to master-track.

### reference-match — make a mix sound like a reference

1. `[G] match-reference-numeric` — per-third-octave delta-dB curve + LUFS/TP/RMS/crest/tilt deltas.
2. `[G] compare-to-reference` — perceptual A/B deltas + actionable moves (`goal`).
3. `[L] compare-tonality` — second numeric per-band delta + confidence (cross-check).
4. `[L] apply-eq` — reconciled delta curve + tilt.
5. `[L] render-ab` — `processed`=corrected mix, `reference`=ref → single A/B WAV in `projects/<track>/mix/`. Report residual deltas.

### loops-to-deliverables — stem/mix → tagged, mastered loop deliverables

1. `[L] find-loops` (fast; full mix → `separate=true`) **or** `[L] analyze-loops` (when role labels / `analysis.json` wanted) → manifest in `artifacts/<run>/`.
2. Per selected loop: `[L] clean-loop` → `[L] optimize-seam` → `[L] render-mastered`.
3. `[L] tag-deliverable` (bpm/key/root/bars/`originator`) → `[L] export-deliverables` (presets, `tag=true`) → `projects/<track>/deliverables/`.
4. Optional: `[L] describe-loops` for audible groove/feel notes on the set.

### understand-audio — perceptual analysis of a reference/stem (no rendering)

Pick the tool(s) matching the ask; never modify the audio:

- `[G] transcribe-audio` (speech, optional `diarize`)
- `[G] describe-audio-region` (`start_s`/`end_s`/`prompt` window)
- `[G] extract-audio-events` (`event_description` for timestamped hits)
- `[G] classify-audio` (`labels`, `multi_label`)
- `[G] compare-audio-files` (2–10 `paths`, optional `schema`)
- `[G] audio-to-json` for deep structured pulls.

### new-track — scaffold a project (filesystem only, no MCP tools)

Slugify the name; create `projects/<slug>/` with the layout below; tell the user where to drop the source and which skill to run next.

### raw-intake — Logic project → clean, song-split, role-labeled kits

The create-loops / mix pipelines assume you already have clean, named stems. For
raw multitrack (a Logic session, an interface dump) two **local-DSP skills**
(under `.claude/skills/`, not in the tool surface above) cover the front end:

1. **[[logic-extract]]** — copy the raw, pre-processing recordings out of a
   `.logicx` package (`Media/Audio Files/`) into `artifacts/<slug>-raw/`, by take,
   **never mutating the package**. (Raw captures ≠ a Logic "All Tracks as Audio
   Files" export — that bakes in edits/plugins and is a UI action.)
2. **[[multitrack-triage]]** — scan levels/clipping, quarantine DAW
   merge-fragments, split dual-mono pairs, group takes into *songs* (Gemini), drop
   dead channels, declip, infer roles → a `kit.json` per song → hand to the
   drum-prep family ([[drum-prep]] / [[drum-phase-align]] / [[drum-reference-match]]
   / [[drum-audition]]). Helper scripts: `.claude/skills/multitrack-triage/scripts/`.

### Field notes (hard-won gotchas)

- **Logic is non-destructive** — original recordings sit intact in the package;
  copy them out for true raw stems, don't export.
- **Interface names ≠ instruments.** ID roles by signal: spectrum for close mics
  (kick = LF-dominant…); inter-channel correlation (`measure-stereo` on a merged
  candidate pair) to find the overhead pair. **Gemini `classify-audio` is
  confounded by drum bleed** (every mic reads "snare/hat") — don't use it for
  close-mic roles.
- **Different takes can be different songs** — compare the melodic/DI channel via
  `[G] compare-audio-files` before collapsing; differing durations are a tell.
- **"Dead" is per-song** — a channel silent in one song may be a real mic in
  another; cross-check across takes before deleting.
- **Format/CLI traps:** drum-prep writes 24-bit AIFF with `.wav` names (ffmpeg
  misreads → use sox / `aiff2wav.sh`); `kit.json` file fields need the `.wav`
  extension; `adeclip` overshoots 0 dBFS (renormalize); multi-input ffmpeg trims
  need `atrim` in the filtergraph (input `-ss/-t` only affects the first input).

---

## Conventions

### Output locations

- **`artifacts/<run>/`** — scratch / intermediates. Loop extraction sessions, manifests, candidate WAVs, debug plots. Disposable; gitignored.
- **`projects/<track>/`** — durable per-track workspace. Stable, human-owned.

### `projects/<track>/` layout

```
projects/<slug>/
  stems/          # source stems / drum stems / extracted Demucs output
  mix/            # corrected mixes, A/B auditions (mix-check, reference-match output)
  masters/        # render-mastered output
  refs/           # reference tracks for reference-match / compare-to-reference
  loops/          # extracted + processed loop deliverables
  track.md        # track name, BPM, key, target platform/LUFS/ceiling, notes
```

Always master into `masters/`, never overwrite `mix/`. Deliverable exports land in `projects/<track>/deliverables/` (created on export).

### Rules

- **Never hardcode API keys.** Use `${ANTHROPIC_API_KEY}` / `${GEMINI_API_KEY}` env expansion (already wired in `.mcp.json`); `.env.example` holds placeholders only.
- **Only use verified tool names** from the surface above, spelled exactly (hyphen vs underscore matters).
- **Measure before and after** any corrective/render step so changes are quantified.
- BPM is required for `find-loops` / `analyze-loops` / `quantize-loop` / `extract-drums` — never guess; ask or read `track.md`.

---

## Setup prerequisites

Both servers are sibling repos using `uv`. Sync each in its own directory before first use.

### `../stemmy-loops-mcp`

```bash
# Minimal — MCP server + DSP mix/master measurement & render tools:
uv sync --extra loops-mcp --extra mixing

# Full — every optional capability (LLM, Gemini listen, Demucs, classify, quantize, beats, viz):
uv sync --extra loops-mcp --extra mixing --extra llm --extra listen \
        --extra separate --extra classify --extra quantize --extra beats --extra viz
```

- `loops-mcp` → MCP server itself · `mixing` → loudness/render/AB tools · `llm` → `diagnose/ask/suggest/caption-loops/analyze-loops` LLM flags · `listen` → `describe-loops` (Gemini) · `separate` → `extract-drums` + `find-loops separate=true` · `classify` → hit tagging · `quantize` → `quantize-loop` · `beats` → deep beat tracker · `viz` → debug plots.

### `../stemmy-gemini-mcp`

```bash
uv sync   # no extras — all deps bundled
```

### Environment variables

| Var | Needed by |
|---|---|
| `ANTHROPIC_API_KEY` | `[L]` LLM tools (`diagnose-output`, `ask-about-output`, `suggest-approach`, `caption-loops`, `analyze-loops` w/ llm flags) |
| `GEMINI_API_KEY` | `[G]` Gemini perceptual tools + `[L] describe-loops` |
| `STEMMY_LLM_MODEL` / `STEMMY_LLM_CAPTION_MODEL` | optional `[L]` model overrides |
| `STEMMY_MCP_MODEL` | optional `[G]` Gemini model override (default `gemini-3.1-pro-preview`) |
| `STEMMY_MCP_ALLOWED_ROOTS` | optional `[G]` filesystem allow-list |

Pure-DSP measurement/render tools on **either** server need **no env vars and no network** — they read and write WAVs directly. Set keys only when reaching for a Gemini/LLM tool.

---

## Headless alternative — the `ship-studios` CLI

The same pipelines run without an interactive Claude session via the `ship-studios` console script (`ship_studios.cli:main`). It opens both servers over stdio and drives `call_tool` in the verified order:

```bash
ship-studios master          projects/<track>/mix/final.wav --platform spotify
ship-studios mix-check       projects/<track>/mix/draft.wav
ship-studios reference-match projects/<track>/mix/draft.wav --reference projects/<track>/refs/ref.wav
ship-studios loops           projects/<track>/stems/drums.wav --bpm 120
ship-studios understand      projects/<track>/refs/ref.wav
```

Each subcommand maps to the matching pipeline function in `ship_studios/pipelines.py`, talking to both servers through the hub in `ship_studios/mcp_client.py`. Use it for batch/CI runs; use the skills/slash commands for interactive work.

---

## drum-prep — local multi-mic drum DSP (outside the MCP servers)

ship-studios owns no DSP — **except** the `drum_prep/` package, a deliberate local-DSP addition for a job neither stemmy server covers: phase-aligning and per-stem tonally reference-matching a *whole multi-mic drum kit*. It uses **no MCP tools** (numpy/scipy/soundfile/pyloudnorm, opt-in via `uv sync --extra drum-prep`) and ships its own `drum-prep` console script. Prefer the `drum-prep` skills/commands for a multi-mic kit; the stemmy `apply-eq` / `render-ab` are single-stereo-file tools, not kit-aware.

### Mic roles & `kit.json`

Roles auto-detect from filenames: `overhead` (or `overhead_l`+`overhead_r`), `room`, `kick_in`/`kick_beater`/`kick_out`/`kick_sub`, `snare_top`/`snare_bottom`, `hihat`, `ride`, `crash`, `tom`, and `fx` (effect returns like a snare plate auto-detect as `fx` and are excluded from phase-align). Commit a `kit.json` (see `drum_prep/examples/kit.json`) to pin/override roles, partner links, per-mic low-pass, ambience, or polarity. The manifest (JSON) is committable; audio is gitignored. Keep the reference file outside the stems folder (or pass it via `--reference`, which excludes it from detection).

### Flows (each a `/drum-*` skill + `drum-prep` subcommand)

1. `drum-prep detect <dir>` — show/confirm roles; `--write-manifest` scaffolds a `kit.json`.
2. `drum-prep stereo-merge <dir>` — merge every `<name> - left`/`right` pair into format-preserving stereo + image review; generalizes `overheads`.
3. `drum-prep overheads <dir>` — merge an L/R overhead pair into one stereo reference (no-op if already stereo; `--align` to phase-lock a coincident pair).
4. `drum-prep phase-align <dir>` — align close mics to the overheads (fixed reference): broadband → OH; kick low-passed → OH; snare-bottom→top & kick-beater→in as partner pairs composed onto OH; room polarity-only → `<dir>/phase-aligned/`.
5. `drum-prep normalize <dir>` — balance-preserving GLOBAL gain by default (per-file changes the kit balance).
6. `drum-prep analyze <dir> --reference <ref>` — read-only tonal report (reference vs kit, per-band ownership); writes nothing.
7. `drum-prep reference-match <dir> --reference <ref>` — match the coherent kit sum toward the reference, distributed per stem → `<dir>/ref-matched/`.
8. `drum-prep mix <dir> --feel <roomy|punchy|natural> --perspective <audience|drummer> [--plate FILE] [--flat]` — mix the prepped kit to a stereo bus by per-role loudness offsets + panning + FX return; the stage between prep and master.
9. `drum-prep audition <dir> --reference <ref>` — loudness-matched stereo A/B WAVs → `<dir>/auditions/`; also emits loudness-matched halves (`cmp_reference.wav`/`cmp_after.wav`) for stemmy-gemini `compare-to-reference`.
10. `drum-prep chain <dir> --reference <ref>` — detect → phase-align → reference-match → audition end to end (`--out-root` to redirect).
11. `drum-prep stem-mix <dir>` — mix arbitrary named stems to a stereo bus by loudness offsets + per-stem spec; the role-agnostic song-mix ([[song-mix]]).
12. `drum-prep sub-design <kick> --out <f>` — synthesize an envelope-followed sine sub under a kick; low-end EXTENSION EQ can't add ([[sub-design]]).
13. `drum-prep tune <sample> [--out <f>]` — measure a drum's fundamental; retune a SAMPLE by resampling (samples/oneshots only) ([[drum-tune]]).
14. `drum-prep verify-tags <dir>` — verify deliverables carry their RIFF INFO LIST chunk + sidecar; catches `export-deliverables` silently dropping tags ([[delivery-qc]]).

### Guardrails (do not change the proven numerics in `drum_prep/dsp.py`)

- **Coherent time-domain sum, not power-sum** when measuring the kit (a power-sum undercounts the correlated kick lows → low-end over-boost).
- **Zero-phase EQ** (real, symmetric gain) so the phase alignment survives the tonal match.
- **Envelope-coarse → waveform refine** alignment to avoid half-period slips on resonant snares.
- **Cuts → all stems, boosts → band owners**; one **global** headroom trim preserves inter-stem balance.
- Regression tests: `uv run pytest -k drum_prep` (needs `--extra drum-prep`).
