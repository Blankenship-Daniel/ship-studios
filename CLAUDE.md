# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What ship-studios is

ship-studios is the **central MCP host** for a music *create → mix → master → deliver* workflow. It owns no DSP of its own: it composes two sibling MCP servers into one coherent pipeline surface.

- **stemmy-loops** (`../stemmy-loops-mcp`) — loop extraction + **in-process pure-DSP** mix/master tools. Slices drum stems/mixes into loops; deterministic measurement and rendering (loudness, EQ, compression, mastering, export). No network, no listening — just signal processing.
- **stemmy-gemini** (`../stemmy-gemini-mcp`) — **Gemini perceptual critique** (the model actually *listens*) plus a **parallel pure-DSP measurement suite**. Use it to hear what a meter can't (sibilance feel, pumping, "too harsh") and for platform-compliance / reference-match numbers.

Both servers are registered in `.mcp.json` and launched as stdio subprocesses via `uv --directory <rel> run <console-script>`. This file is the contract: **only use the tool names listed below, exactly as spelled (mind hyphen vs underscore).**

> **Worktree note:** the hub (`ship_studios/config.py`) and the `.mcp.json` servers (via `scripts/mcp_launch.py`) auto-resolve the `../stemmy-*-mcp` siblings from the **main checkout** even when run from a worktree under `.claude/worktrees/` — no env vars needed. `SHIP_STUDIOS_LOOPS_DIR` / `SHIP_STUDIOS_GEMINI_DIR` override for a non-standard layout (CI, vendored checkout). A running session must reload to pick up an `.mcp.json` change.

> **Surface & caveats:** `[L]` is **48 tools** (43 pure-DSP + the 2-tool VST pair + 3 batch tools), `[G]` **23**. The six `[G]` critique tools are meter-grounded + typed (see §4); `check-streaming-targets` projects asymmetric playback gain. Roadmap: [`docs/mix-master-capability-roadmap.md`](docs/mix-master-capability-roadmap.md). **Caveat:** `suppress-resonances` / `apply-dynamic-eq` (time-varying DSP) are unit-tested only — ear-tune on real material before trusting them on a release.

> **Gemini audio:** what *every* Gemini model can do with audio (understanding — the part wired here — plus TTS, Live API, Lyria), with models/pricing/SDK/limits, lives in [`docs/gemini-audio/`](docs/gemini-audio/README.md) (the `[[gemini-audio]]` suite). Governing fact: Gemini downmixes to ~16 kbps **mono**, so **meters own loudness/peak/stereo**.

> **VST hosting:** `apply-vst-chain` + `list-vst-plugins` (`[L]`, the `vst` extra → Pedalboard) run third-party VST3/AU **effect** plugins offline/headless — the one part of the surface that loads external, non-deterministic binaries (opt-in, effects-only; VST3 cross-platform, AU macOS-only; `list-vst-plugins` needs no extra). Two traps: **loads ≠ renders** (verify with `[[vst-verify]]`, measuring *detail* not just `changed:true`), and for **UAD** load the `uaudio_*.vst3` build, never the passthrough `UAD ….component` twin. Full doctrine + ~32 per-plugin deep-dives + headless-safe inventory: the `[[vst]]` suite ([`docs/vst/README.md`](docs/vst/README.md)).

### Philosophy

A track moves left-to-right: **understand** → **create loops** (optional) → **measure** → **perceptual critique** → **corrective + render** → **deliver**. Measure before you move; let Gemini's ears and the DSP meters cross-check each other; never master inside the mix stage. Pipelines below encode the canonical orderings.

### By goal — request → skill

Most work starts from a **skill**, not a raw tool — match the request here, then let the skill drive the tools.

- **Master a track / "-14 LUFS for Spotify"** → `[[master-track]]`; whole EP/folder → `[[batch-master]]`; assemble already-mastered tracks → `[[release-package]]`.
- **Diagnose a mix / "too harsh / muddy / boomy"** → `[[mix-check]]` (hands to `[[master-track]]`); glue before mastering → `[[finalize-mix]]`.
- **Sound like a reference** → `[[reference-match]]`; one shared tone across an EP → `[[house-curve]]`.
- **Balance levels / "hi-hat too loud / X is buried"** → `[[mix-balance]]` FIRST (a balance problem is not an EQ problem); de-spill a close mic → `[[bleed-gate]]`.
- **Work from stems** → `[[stem-master]]` (correct→sum→master); carve clashes only → `[[unmask-stems]]`; per-stem correct+color → `[[stem-process]]`; split a mixdown → `[[stem-split]]`.
- **A multi-mic drum kit** → `[[drum-prep]]`; a raw Logic/interface dump → `[[logic-extract]]` → `[[multitrack-triage]]`.
- **Bounce a prepped kit / song to stereo** → `[[drum-mix]]` (drums) · `[[song-mix]]` (full song); set levels first with `[[mix-balance]]`.
- **A drum-bus character / famous drum tone** → `[[warm-drum-bus]]` · `[[drum-stems-character]]` · `[[fool-in-the-rain]]` (Bonham) · `[[home-at-last]]` (Aja) · `[[tomorrow-never-knows]]` (Beatles) · `[[in-the-air-tonight]]` (Collins gated) · `[[when-the-levee-breaks]]` (Bonham stairwell) · `[[back-in-black]]` (AC/DC) · `[[funky-drummer]]` (James Brown). Not sure which? `/famous-drum-shootout` renders your kit through all of them and recommends one.
- **A targeted corrective move** → `[[de-ess]]` · `[[de-harsh]]` · `[[dynamic-eq]]` · `[[excite]]` · `[[multiband-compress]]` · `[[drum-punch]]` · `[[sub-design]]` · `[[groove-tighten]]`.
- **Your own VST3/AU plugins** → `[[vst]]` (index + doctrine), then a `vst-*` task skill or per-plugin deep-dive.
- **Loops / one-shots / a pack** → `[[loops-to-deliverables]]` · `[[slice-oneshots]]` · `[[sample-pack]]` · `[[sampler-kit]]`.
- **Understand a reference** → `[[understand-audio]]`. **New project** → `[[new-track]]`. **QC before shipping** → `[[delivery-qc]]`.

For batch / parallel runs (an album, a folder of stems, a plugin sweep, a variant shootout) reach for the matching **workflow** — `/batch-master`, `/house-curve`, `/stem-process`, `/audio-shootout`, … — see [Workflows](#workflows-multi-agent-fan-out).

---

## Combined tool surface

Two servers, six lifecycle stages. `[L]` = stemmy-loops, `[G]` = stemmy-gemini. Tools marked `(Gemini)` need `GEMINI_API_KEY`; `(LLM)` need `ANTHROPIC_API_KEY`; everything else is pure DSP with no env/network requirement.

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

> What Gemini can/can't do here (tasks, formats, 32 tok/s cost, 9.5 h limit, mono-downmix caveat) → `[[gemini-audio-understanding]]` / [`docs/gemini-audio/audio-understanding.md`](docs/gemini-audio/audio-understanding.md).

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
| Loudness over a LIST of files, ONE call, concurrent | `measure-loudness-batch` | — |
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
| Per-platform LUFS/TP compliance + asymmetric playback-gain projection | — | `check-streaming-targets` |
| Kick fundamental note + cents off | `tune-kick` | — |
| Per-band microdynamics: crest/PLR/punch, read-only | `measure-microdynamics` | — |
| Reusable house-curve target: build from refs / match a mix → `[[house-curve]]` | `build-target-profile` · `match-to-profile` | — |
| Album shared-gain (TD1008 + album-integrated offsets) → `[[batch-master]]` / `[[release-package]]` | `analyze-album-normalization` | — |

**Overlap rule:** both servers expose `measure-loudness` / `measure-spectrum` (independent implementations). Prefer **`[L]`** inside a loops/mastering chain (same code path that renders), **`[G]`** when the gemini session is already open. For stereo, `[L] measure-stereo` and `[G] analyze-phase-mono` are interchangeable — pick by which server is in play.

### 4. Perceptual critique (Gemini listens — all `[G]`, all need `GEMINI_API_KEY`)

| Capability | Tool |
|---|---|
| Tonal/stereo/depth balance critique + suggestions | `analyze-mix-balance` (Gemini) |
| Audible problems (clip/sibilance/mask/pump/phase) + severity/timestamps | `detect-mix-issues` (Gemini) |
| A/B against a reference, perceptual deltas + moves | `compare-to-reference` (Gemini) |
| Master-bus critique + platform guidance + release-ready bool | `mastering-feedback` (Gemini) |
| Hybrid: measure + propose chain + Gemini critique → `[[mastering-plan]]` | `recommend-mastering-chain` (Gemini) |
| Region-focused critique on a DSP-trimmed, onset-snapped clip → `[[mix-check]]` | `critique-region` (Gemini) |
| Intent/intensity/style → meter-grounded complete typed mastering chain (plan only) → `[[mastering-plan]]` | `master-assistant` (Gemini) |

**Grounded + typed:** all six run meter-grounded — the matching pure-DSP meters (LUFS / true-peak / crest / LRA / 5-band tilt / L-R correlation / mono-sum loss) are injected as ground truth the model reasons **from**, not re-estimates by ear. Gemini hears only ~16 kbps mono, so meters own loudness/peak/stereo — **and the codec degrades the tonal read too (chronically under-reads highs / over-reads lows): verify any "dark"/"boomy" note against `[L] measure-spectrum` (tilt + centroid), make ONE correction, then trust the meter — don't iterate the read.** All accept optional `genre`+`intent`, split `technical_defects` (auto-applyable) vs `creative_observations` (taste), and emit tool-ready typed moves (`eq_moves [{freq_hz,gain_db,q,type}]`, de-ess `{center_hz,q,threshold_db,gr_db}`) clamped server-side for `apply-eq`/`de-ess`, plus a `meters` passthrough. Why → `[[gemini-audio]]` / [`docs/gemini-audio/caveats-and-limits.md`](docs/gemini-audio/caveats-and-limits.md).

### 5. Corrective + render (write new WAVs — all `[L]`; pure DSP except `apply-vst-chain`)

| Capability | Tool |
|---|---|
| RBJ biquad EQ (shelves/bells/pass) + tilt; `phase` = min/zero/linear | `apply-eq` |
| `apply-eq` over a LIST of files, ONE call, concurrent | `apply-eq-batch` |
| Threshold-gated per-band dynamic EQ (difference-signal) → `[[dynamic-eq]]` | `apply-dynamic-eq` |
| Render a reference delta curve as a min/linear-phase FIR EQ → `[[reference-match]]` / `[[house-curve]]` | `match-eq` |
| Soothe-style dynamic resonance/harshness suppressor → `[[de-harsh]]` | `suppress-resonances` |
| Split-band de-esser (consumes `find-sibilance` settings) → `[[de-ess]]` | `de-ess` |
| Downward + parallel compressor, GR stats | `compress-loop` |
| Proper LR4 multiband compressor, per-band GR → `[[multiband-compress]]` | `multiband-compress` |
| Bass mono-maker (graduated 12/24/48 slope) + M/S width | `adjust-stereo` |
| Oversampled tanh/tape/soft-clip saturation | `saturate-loop` |
| Band-limited parallel harmonic exciter (air/presence) → `[[excite]]` | `excite-loop` |
| Multiband transient design + per-band gain (LR4) → `[[drum-punch]]` | `shape-bands` |
| DC/HPF/declick/denoise/gate cleanup | `clean-loop` |
| Best loop wrap point + equal-power crossfade | `optimize-seam` |
| HPF → transient → optional zero-phase EQ → normalize → limiter → resample/dither | `render-mastered` |
| Normalize to target/reference LUFS, peak-safe (no limiting) → `[[level-match]]` | `match-loudness` |
| Loudness-matched [ref \| gap \| processed] audition | `render-ab` |
| Full per-stem corrective + optional console-color chain over a LIST of stems, ONE call → `[[stem-process]]` | `process-stems` |
| Run a chain of 3rd-party VST3/AU **effect** plugins, offline/headless (needs `vst` extra; non-deterministic) | `apply-vst-chain` |
| Discover installed VST3/AU plugins (read-only; no `vst` extra) | `list-vst-plugins` |

> **`apply-vst-chain`** is the one non-pure-DSP render tool — loads external plugin binaries via Pedalboard (`uv sync --extra vst`; not deterministic across versions; effects only; VST3 cross-platform, AU macOS-only). Pass `plugins=[{plugin_path, parameters?, state_path?, bypass?}]`; `dump_state=true` captures each plugin's opaque state next to the output for a reproducible re-render. Find paths with `list-vst-plugins`.

> **Batch, don't fan out.** For a folder of files use the batch tools over N per-file calls: `measure-loudness-batch` / `apply-eq-batch` run a LIST in one **genuinely concurrent** call (pure-DSP handlers thread-offload — numpy releases the GIL — bounded by `STEMMY_LOOPS_DSP_CONCURRENCY`). `process-stems` runs the whole per-stem corrective chain (clean → zero-phase EQ → de-harsh → dynamic-EQ → transient → excite) + an optional API-console color stage over a LIST in one call (server-side `scripts/mix/process_stems.py`) — **serial by design**: the color VST loads only on the main thread + renders non-deterministically; a process-global lock serializes every VST render. **Never fan out `apply-vst-chain` / `process-stems` color** — parallel calls only add overhead. Pass `color_plugin_path` for the API-Vision stage, or omit for a pure-DSP pass.

### 6. Deliver (tag + export — all `[L]`, pure DSP)

| Capability | Tool |
|---|---|
| Embed BPM/key/root/bars/comment + `tags.json` sidecar | `tag-deliverable` |
| Batch format matrix + dither — presets `distribution_44k_16` (44.1/16) · `production_48k_24` (48/24) · `master_96k_24` (96/24) | `export-deliverables` |

---

## Canonical pipelines

Each is an ordered tool-call recipe; `[L]`/`[G]` precedes the tool. Outputs go to `projects/<track>/` (loop scratch to `artifacts/<run>/`). Skills under `.claude/skills/` wrap these — prefer the skill over hand-typing.

### master-track — near-final mix → platform-ready master + deliverables

1. `[L] measure-loudness` — baseline LUFS / true-peak / crest / PLR / LRA / DR.
2. `[L] measure-spectrum` — baseline tilt + 5-band balance.
3. `[L] measure-stereo` — baseline correlation + mono-sum loss.
4. `[L] check-clipping` — confirm no inter-sample clip / DC / polarity issue.
5. `[L] measure-distortion` — baseline THD / aliasing before the limiter stage.
6. `[G] mastering-feedback` — perceptual critique + `target_platform` + release-ready bool. *(Alt: `[G] master-assistant` with `intent`/`intensity`/`style` → a complete typed chain to drive step 7; both wrapped as [[mastering-plan]].)*
7. `[L] render-mastered` — to chosen `target_lufs` + `ceiling_dbtp` (optional `eq_bands` for a zero-phase corrective move) → `projects/<track>/masters/`.
8. `[G] check-streaming-targets` — re-verify the render vs Spotify/Apple/YouTube/Tidal…; also projects the **asymmetric** playback gain per platform (attenuate-only vs boost-and-attenuate, headroom-capped).
9. If non-compliant, adjust target and re-render (back to 7).
10. `[L] export-deliverables` — presets `["distribution_44k_16", "production_48k_24", "master_96k_24"]` (exact allow-list — the server rejects free-form `<sr>/<bits>`), `tag=true` → `projects/<track>/deliverables/`.

### batch-master — folder of near-final mixes → consistent masters + cross-track table

Per track (loop the folder), then a cross-track pass. One **shared** target for the whole set.

1. `[L] measure-loudness` + `[L] measure-spectrum` + `[L] check-clipping` — per-track baseline.
2. `[G] mastering-feedback` — per-track release-ready bool + harshness flags to steer that track's render.
3. `[L] render-mastered` — to the **shared** `target_lufs`/`ceiling_dbtp` → `projects/<album>/masters/`.
4. `[G] check-streaming-targets` — per-track compliance; re-render that track if it'll be attenuated.
5. `[L] export-deliverables` — presets, `tag=true` → `projects/<album>/deliverables/`.
6. Cross-track: loop `[L] measure-loudness` over every master → LUFS-I / true-peak / LRA + **Δ-from-album-median** table; flag outliers (>0.5 LU off median). For the shared album-gain a platform applies, run `[L] analyze-album-normalization`.
7. `drum-prep verify-tags` (or delivery-qc) — confirm the RIFF INFO chunk survived export.

The consistency table is the headline. Hand any not-release-ready track to mix-check first; don't loudness-paper a broken mix.

### stem-master — per-stem corrective mixdown → sum → hand to master-track

You **mix** the stems (correct + sum), then **master** the bus. This stage does NOT limit.

1. Per stem: `[L] measure-loudness` + `[L] measure-spectrum` — baseline.
2. `[G] analyze-stem-masking` (stem map) — per-collision dominant stem, stem-to-cut, center Hz, cut dB, Q. Optional `[L] detect-masking` cross-check.
3. `[G] find-resonances` / `[G] find-sibilance` — surgical notch / de-ess settings on the offending stems.
4. `[L] apply-eq` — one call **per losing stem**; complementary cuts (carve bass under kick, tame vocal mud). Cut the loser, don't boost the winner. `[L] de-ess` ([[de-ess]], from the `[G] find-sibilance` settings) and `[L] suppress-resonances` ([[de-harsh]]) clean harsh/ringing stems; `[L] apply-dynamic-eq` ([[dynamic-eq]]) for level-dependent collisions.
5. `[L] compress-loop` / `[L] multiband-compress` ([[multiband-compress]]) / `[L] shape-bands` ([[drum-punch]]) — per stem where dynamics / transients / per-band density call for it.
6. `drum-prep stem-mix` — sum the corrected stems to one stereo bus (local DSP; no MCP tool sums a stem set).
7. Re-run `[G] analyze-stem-masking` + `[L] measure-spectrum` — confirm the overlaps shrank.
8. Hand the summed bus to **master-track** for loudness / limiting / compliance / export.

### unmask-stems — masking-only subset of stem-master (no sum, no master)

1. `[G] analyze-stem-masking` — the collision map (dominant stem, stem-to-cut, center Hz, cut dB, Q). Optional `[L] detect-masking` cross-check.
2. `[L] apply-eq` (or `[L] apply-dynamic-eq`, [[dynamic-eq]]) — one complementary cut **per losing stem**; cut the loser, don't boost the winner.
3. `[G] analyze-stem-masking` — re-score to prove the overlap shrank.

stem-master adds the per-stem baseline, tone/dynamics shaping, the `drum-prep stem-mix` sum, and the master-track hand-off on top of these three steps. ([[unmask-stems]])

### mix-check — diagnose a mix (perceptual + measurement) → concrete moves

1. `[G] detect-mix-issues` — audible problems w/ severity + timestamps. *(To zoom into a flagged window, `[G] critique-region` re-critiques a DSP-trimmed, onset-snapped clip.)*
2. `[G] analyze-mix-balance` — band-by-band tonal/stereo/depth critique.
3. `[L] measure-loudness` — ground the read with objective numbers.
4. `[L] measure-spectrum` — third-octave / tilt / 5-band to confirm or refute the tonal call.
5. `[L] measure-stereo` — correlation / width / mono-sum loss.
6. `[G] find-resonances` — narrow-Q peaks + notch dB → feed `apply-eq` bells.
7. `[G] find-sibilance` — de-esser settings (center Hz, Q, threshold, GR).
8. `[G] analyze-phase-mono` — per-band correlation + polarity flag before EQ.
9. Reconcile perceptual vs measured into a prioritized issue list.
10. `[L] apply-eq` — notches + shelves/tilt from the findings (use `phase=zero` on drum material).
11. `[L] de-ess` ([[de-ess]]) / `[L] suppress-resonances` ([[de-harsh]]) when sibilance/ringing flagged; `[L] apply-dynamic-eq` ([[dynamic-eq]]) when level-dependent; `[L] excite-loop` ([[excite]]) when dull not harsh.
12. `[L] compress-loop` / `[L] multiband-compress` ([[multiband-compress]]) — where dynamics analysis called for it. Write to `projects/<track>/mix/`.

**Do not master here** — hand off to master-track.

### reference-match — make a mix sound like a reference

1. `[G] match-reference-numeric` — per-third-octave delta-dB curve + LUFS/TP/RMS/crest/tilt deltas.
2. `[G] compare-to-reference` — perceptual A/B deltas + actionable moves (`goal`).
3. `[L] compare-tonality` — second numeric per-band delta + confidence (cross-check).
4. `[L] match-eq` — **always runs** (the primary corrective): render the reconciled source-minus-reference delta as a min/linear-phase corrective FIR toward the reference (pass `source_path`+`reference_path`, or the `delta_db_curve`; `match_strength` ~0.5, `phase` min/linear) → the matched mix.
5. `[L] apply-eq` — **optional residual** (only when reconciled `eq_bands` are supplied): a few surgical shelves/bells (+ `tilt_db_per_octave`) on the matched output.
6. `[L] render-ab` — `processed`=corrected mix, `reference`=ref → single A/B WAV in `projects/<track>/mix/`. Report the residual from `match-eq`'s returned `residual_delta_db` (no second `compare-tonality` pass).

For a whole EP/album, capture **one shared house curve** with `[L] build-target-profile` over the references, then match each mix with `[L] match-to-profile` → `[L] match-eq` ([[house-curve]]).

### house-curve — one shared tonal target across an EP/album

1. `[L] build-target-profile` — power-average the reference paths into a reusable profile JSON.
2. `[L] match-to-profile` — the mix's per-band delta vs the profile.
3. `[L] match-eq` — render the delta as a min/linear-phase FIR correction (only when a per-band delta is recoverable; `match_strength` ~0.5) → `projects/<track>/mix/`. Follow with `[L] apply-eq` for surgical residuals.

### loops-to-deliverables — stem/mix → tagged, mastered loop deliverables

1. `[L] find-loops` (fast; full mix → `separate=true`) **or** `[L] analyze-loops` (when role labels / `analysis.json` wanted) → manifest in `artifacts/<run>/`.
2. Per selected loop: `[L] clean-loop` → `[L] optimize-seam` → `[L] render-mastered`.
3. `[L] tag-deliverable` (bpm/key/root/bars/`originator`) → `[L] export-deliverables` (presets, `tag=true`) → `projects/<track>/deliverables/`.
4. Optional: `[L] describe-loops` for audible groove/feel notes.

### understand-audio — perceptual analysis of a reference/stem (no rendering)

Pick the tool(s) matching the ask; never modify the audio: `[G] transcribe-audio` (optional `diarize`) · `[G] describe-audio-region` (`start_s`/`end_s`/`prompt`) · `[G] extract-audio-events` (`event_description`) · `[G] classify-audio` (`labels`, `multi_label`) · `[G] compare-audio-files` (2–10 `paths`, optional `schema`) · `[G] audio-to-json` for deep structured pulls.

### new-track — scaffold a project (filesystem only, no MCP tools)

Slugify the name; create `projects/<slug>/` with the layout below; tell the user where to drop the source and which skill to run next.

### raw-intake — Logic project → clean, song-split, role-labeled kits (local-DSP skills, no MCP tools)

The create-loops / mix pipelines assume clean, named stems. For raw multitrack (a Logic session, an interface dump) two **local-DSP skills** cover the front end:

1. **[[logic-extract]]** — copy the raw, pre-processing recordings out of a `.logicx` package (`Media/Audio Files/`) into `artifacts/<slug>-raw/`, by take, **never mutating the package**. (Raw captures ≠ a Logic "All Tracks as Audio Files" export — that bakes in edits/plugins.)
2. **[[multitrack-triage]]** — scan levels/clipping, quarantine DAW merge-fragments, split dual-mono pairs, group takes into *songs* (Gemini), drop dead channels, declip, infer roles → a `kit.json` per song → hand to the drum-prep family ([[drum-prep]] / [[drum-phase-align]] / [[drum-reference-match]] / [[drum-audition]]). Helper scripts: `.claude/skills/multitrack-triage/scripts/`.

### Field notes (hard-won gotchas)

- **Logic is non-destructive** — copy the originals out for true raw stems, don't export.
- **Interface names ≠ instruments.** ID roles by signal: spectrum for close mics (kick = LF-dominant…); inter-channel correlation (`measure-stereo` on a candidate pair) to find the overhead pair. **Gemini `classify-audio` is confounded by drum bleed** — don't use it for close-mic roles.
- **Different takes can be different songs** — compare the melodic/DI channel via `[G] compare-audio-files` before collapsing; differing durations are a tell. **"Dead" is per-song** — cross-check across takes before deleting.
- **Format/CLI traps:** drum-prep writes 24-bit AIFF with `.wav` names (ffmpeg misreads → use sox / `aiff2wav.sh`); `kit.json` file fields must name the real on-disk file *with its actual extension*; `adeclip` overshoots 0 dBFS (renormalize); multi-input ffmpeg trims need `atrim` in the filtergraph.
- **Phase-align BEFORE corrective EQ**, and never HPF the overheads before aligning — it strips the low end the kick correlates against (bogus 971-sample / 20 ms slip). Already-EQ'd? Align off the full-band originals; delays commute with zero-phase EQ + gating (see Guardrails).
- **Pin a non-standard mic role in `kit.json`** — a "crotch mic" or sub-kick won't auto-detect; set role `kick_sub` so it low-pass-correlates to the overheads like a kick mic.

---

## Workflows (multi-agent fan-out)

Reusable Claude Code **dynamic workflows** live in `.claude/workflows/*.js` — JS scripts orchestrating parallel subagents (invoked via `ultracode` / "use a workflow", or as `/<name>`). Use them for **parallel fan-out / judge-panels / batch / cross-checked verification**, NOT sequential file-mutating DSP (that stays a skill). A workflow has **no filesystem/bash access** — render variants / gather lists **inline first**, pass via `args`; the script returns a structured object the session writes out.

| Workflow | Fans out / purpose |
|---|---|
| `audio-shootout` | one Gemini lens agent per (variant × criterion) → ranked pick + dissent (render + level-match variants inline; pack `meters`) |
| `warm-bus-shootout` | a warm-drum-bus preset over `audio-shootout` (warmth/tightness/life) |
| `vst-probe-inventory` | chunked parallel `presets/vst/probe_plugin.py` → render-verified inventory |
| `batch-master` | one agent per track runs the master chain → cross-track consistency table (pass the folder + ONE shared `target_lufs`/`ceiling_dbtp`) |
| `house-curve` | one agent per mix → match-to-profile → match-eq → re-measure; cross-track spread reduce (tonal companion to `batch-master`) |
| `stem-process` | one agent per stem diagnoses + authors a corrective plan; the executor then runs as ONE serial UADx-safe pass |
| `drum-stems-character` | two-mode per-stem fan-out: `mode:'correct'` → plan + ONE serial `process_stems.py`; `mode:'character'` → plan a role+character-aware UADx chain + ONE serial `character_stems.py`. The skill drives it twice with an AskUserQuestion (chosen character) between |
| `fool-in-the-rain` / `home-at-last` / `tomorrow-never-knows` / `in-the-air-tonight` / `when-the-levee-breaks` / `back-in-black` / `funky-drummer` | famous-drum bus-tuning twins: render N drum-bus variants → parallel multi-lens Gemini judge panel against the brief → pick the winner (whose meters become the preset's `approved_signature`) |
| `famous-drum-shootout` | render ONE prepared drum bus through ALL 7 famous-drum character bus scripts (defaults) → parallel Gemini fit-to-brief panel → RECOMMEND the best iconic character for the material (cross-character recommender, not a per-recipe tuner) |
| `audit-skill-consistency` | one agent per skill → wikilink / tool-name / doc / key-label / mono-caveat / argument-hint / frontmatter drift |
| `audit-pipeline-lockstep` | one agent per coded pipeline → CLAUDE.md prose ↔ `pipelines.py` ↔ tests drift |
| `fold-learnings` | one agent per session learning → dedupe-grep + route to its durable home + draft the patch; a skeptic challenges each → a ranked fold plan |
| `measure-performance` | a SERIAL measure agent (import/startup · test-suite · DSP bench+scaling+memory · CLI cold-start) → one analysis agent per surface → adversarial skeptic per finding → prioritized report |
| `fix-perf-issues` | one edit agent per DISJOINT file group (parallel, conflict-free) → one central CI gate → automatic repair pass on red (pass `args.fixes=[{id,title,files,instr}]`) |

Reference a workflow in prose as `name` / `/name` — **not** as a `[[name]]` wikilink (those resolve to skills/docs only). **Workflows are NOT in the auto-injected skill list** — only this table (and the `/name` surface) advertises them. Three more are **dev/meta** workflows for working *on* this repo (`create-skill`, `repo-review`, `repo-review-fix`) — see [Developing this repo](#developing-this-repo-tests--lint--types).

---

## Conventions

### Output locations

- **`artifacts/<run>/`** — scratch / intermediates (loop sessions, manifests, candidate WAVs, debug plots). Disposable; gitignored.
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

- **Never hardcode API keys.** Use `${ANTHROPIC_API_KEY}` / `${GEMINI_API_KEY}` env expansion (wired in `.mcp.json`); `.env.example` holds placeholders only. *Accepted risk:* the `settings.json` `Read(./.env*)` deny only constrains the **Read tool** — `Bash(uv:*)` can read any file, so keep secrets in the **shell env**, never on disk.
- **Only use verified tool names** from the surface above, spelled exactly (hyphen vs underscore matters).
- **Measure before and after** any corrective/render step so changes are quantified.
- **Concurrency: batch, don't fan out.** Per-file DSP and every VST render are serialized server-side (pure-DSP handlers thread-offload so they parallelize internally; VST renders sit behind a process-global lock and load only on the main thread). For a folder of files, reach for the **batch tools** (`process-stems`, `apply-eq-batch`, `measure-loudness-batch`) or scripts (`scripts/mix/process_stems.py`) — ONE call that loops internally — not N separate MCP calls. **Never parallelize `apply-vst-chain` / `process-stems` color.**
- **Balance volumes before EQ.** When summing stems/mics set levels by **measured integrated LUFS** (`[[mix-balance]]` / `[[drum-mix]]` / `[[song-mix]]`), never eyeballed dB, never RMS (overheads read hot in LUFS and carry the hi-hat/cymbals → put them *under* the close mics), never by peak-normalizing the sum. A balance problem ("too much hi-hat") is **not** an EQ problem; de-spill forward close mics with `[[bleed-gate]]` first.
- BPM is required for `find-loops` / `analyze-loops` / `quantize-loop` / `extract-drums` — never guess; ask or read `track.md`.
- **Capability docs are discoverable via skills.** The `[[gemini-audio]]` suite links to `docs/gemini-audio/*.md` — a deliberate extension of the skill→skill wikilink convention so an agent can pull a Gemini audio capability doc on demand.

---

## Setup prerequisites

Both servers are sibling repos using `uv`; sync each in its own directory before first use. **Full extras list + the complete `STEMMY_*` / `SHIP_STUDIOS_*` env-var reference → [`docs/setup.md`](docs/setup.md) (the `[[setup]]` skill).**

```bash
# stemmy-loops — minimal (DSP measure/render) | + VST hosting | full superset:
uv sync --extra loops-mcp --extra mixing
uv sync --extra loops-mcp --extra mixing --extra vst
uv sync --extra loops-mcp --extra mixing --extra ml

# stemmy-gemini — no extras, all deps bundled:
uv sync
```

**Keys:** `[G]` tools + `[L] describe-loops` need `GEMINI_API_KEY`; `[L]` LLM tools (`diagnose/ask/suggest/caption-loops`, `analyze-loops` w/ llm flags) need `ANTHROPIC_API_KEY`; pure-DSP tools need neither. The optional tuning knobs (model overrides, `*_CONCURRENCY` caps, hub timeouts, `STEMMY_MCP_ALLOWED_ROOTS` allow-list, cache controls) live in [`docs/setup.md`](docs/setup.md).

---

## Developing this repo (tests · lint · types)

The repo's *own* Python is two `uv` packages — **`ship_studios/`** (the DSP-free MCP-client hub: `cli.py` · `pipelines.py` · `mcp_client.py`) and **`drum_prep/`** (the only DSP). The whole suite runs **offline** (`tests/conftest.py` monkeypatches `Hub._open_session` with a `FakeSession` — no siblings, keys, audio, or network).

```bash
uv sync --extra drum-prep      # adds the DSP test deps (dev tools install by default)
uv run pytest                  # full offline suite; -k drum_prep for the DSP subset (needs the extra)
uv run ruff check              # lint (line-length 100; scripts/ + presets/ excluded)
uv run mypy                    # types — ship_studios + drum_prep only
uv run python scripts/lint_skills.py   # skill-contract lint (CI-gated)
```

- **Editing a pipeline = editing `ship_studios/pipelines.py`**; `tests/test_pipelines.py` asserts the *ordered tool-call log*, so a reorder/rename fails loudly — keep it in lockstep with **Canonical pipelines** above.
- Full developer reference — the VST harness workflow, the skill/doc contract guards (`/audit-skill-consistency`, `/audit-pipeline-lockstep`, `/create-skill`, `/repo-review`, `/fold-learnings`), the opt-in pre-release live-contract check, **and the headless `ship-studios` CLI** (nine pipeline subcommands + `doctor`, for batch/CI runs) → [`docs/developing.md`](docs/developing.md) (the `[[developing]]` skill).

---

## drum-prep — local multi-mic drum DSP (outside the MCP servers)

ship-studios owns no DSP — **except** the `drum_prep/` package, a deliberate local-DSP addition for a job neither stemmy server covers: phase-aligning and per-stem tonally reference-matching a *whole multi-mic drum kit*. No MCP tools (numpy/scipy/soundfile/pyloudnorm, opt-in via `uv sync --extra drum-prep`); ships its own `drum-prep` console script. The stemmy `apply-eq` / `render-ab` are single-stereo-file tools, not kit-aware.

### Mic roles & `kit.json`

Roles auto-detect from filenames: `overhead` (or `overhead_l`+`overhead_r`), `room`, `kick_in`/`kick_beater`/`kick_out`/`kick_sub`, `snare_top`/`snare_bottom`, `hihat`, `ride`, `crash`, `tom`, and `fx` (effect returns like a snare plate auto-detect as `fx` and are excluded from phase-align). Commit a `kit.json` (see `drum_prep/examples/kit.json`) to pin/override roles, partner links, per-mic low-pass, ambience, or polarity. JSON is committable; audio is gitignored. Keep the reference outside the stems folder (or pass `--reference`, which excludes it).

### Flows (each a `drum-prep` subcommand; many also have a `/drum-*` skill)

1. `detect <dir>` — show/confirm roles (overlaying `kit.json` if present); `--write-manifest` scaffolds one.
2. `stereo-merge <dir>` — merge every `<name> - left`/`right` pair into format-preserving stereo + image review.
3. `overheads <dir>` — merge an L/R overhead pair into one stereo reference (`--align` to phase-lock a coincident pair).
4. `phase-align <dir>` — align close mics to the overheads (broadband → OH; kick low-passed → OH; snare-bottom→top & kick-beater→in as partner pairs; room polarity-only) → `<dir>/phase-aligned/`.
5. `normalize <dir>` — balance-preserving GLOBAL gain by default (per-file changes the kit balance).
6. `analyze <dir> --reference <ref>` — read-only tonal report (per-band ownership); writes nothing.
7. `reference-match <dir> --reference <ref>` — match the coherent kit sum toward the reference, distributed per stem → `<dir>/ref-matched/`.
8. `mix <dir> --feel <roomy|punchy|natural|dry> --perspective <audience|drummer> [--plate FILE] [--flat]` — mix the prepped kit to a stereo bus.
9. `audition <dir> --reference <ref>` — loudness-matched stereo A/B WAVs → `<dir>/auditions/`; also emits `cmp_reference.wav`/`cmp_after.wav` for `compare-to-reference`.
10. `chain <dir> --reference <ref>` — phase-align → reference-match → audition end to end (`--out-root` to redirect).
11. `stem-mix <dir>` — mix arbitrary named stems to a stereo bus by loudness offsets + per-stem spec ([[song-mix]]).
12. `sub-design <kick> --out <f>` — synthesize an envelope-followed sine sub under a kick ([[sub-design]]).
13. `tune <sample> [--out <f>]` — measure a drum's fundamental; retune a SAMPLE by resampling ([[drum-tune]]).
14. `verify-tags <dir>` — verify deliverables carry their RIFF INFO LIST chunk + sidecar ([[delivery-qc]]).

### Guardrails (do not change the proven numerics in `drum_prep/dsp.py`)

- **Coherent time-domain sum, not power-sum** when measuring the kit (a power-sum undercounts the correlated kick lows → low-end over-boost).
- **Zero-phase EQ** (real, symmetric gain) so the phase alignment survives the tonal match.
- **Envelope-coarse → waveform refine** alignment to avoid half-period slips on resonant snares.
- **Cuts → all stems, boosts → band owners**; one **global** headroom trim preserves inter-stem balance.
- **Phase-align on FULL-BAND signals, before corrective EQ.** Delays are physical mic distances; estimate from the unprocessed stems. HPF'ing the overheads first strips the low end the kick (LP180) needs → a bogus delay (971 samples / 20 ms, post_corr 0.05). Already-EQ'd? Derive delays from the full-band originals and apply to the processed stems — a pure time-shift commutes with zero-phase EQ + gating (all LTI).
- Regression tests: `uv run pytest -k drum_prep` (needs `--extra drum-prep`).
