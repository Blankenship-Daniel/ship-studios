# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What ship-studios is

ship-studios is the **central MCP host** for a music *create → mix → master → deliver* workflow. It owns no DSP of its own: it composes two sibling MCP servers into one coherent pipeline surface.

- **stemmy-loops** (`../stemmy-loops-mcp`) — loop extraction + **in-process pure-DSP** mix/master tools. Slices drum stems/mixes into loops, and does deterministic measurement and rendering (loudness, EQ, compression, mastering, export). No network, no listening — just signal processing.
- **stemmy-gemini** (`../stemmy-gemini-mcp`) — **Gemini perceptual critique** (the model actually *listens* to the audio) plus a **parallel pure-DSP measurement suite**. Use it to hear what a meter can't (sibilance feel, pumping, "too harsh"), and for platform-compliance / reference-match numbers. For the **full Gemini audio surface** (understanding + TTS + Live API + Lyria) and its limits — chiefly that **Gemini hears mono**, so it can't judge stereo/true-peak/loudness — see [`docs/gemini-audio/`](docs/gemini-audio/README.md) (the `[[gemini-audio]]` skill suite).

Both servers are registered in `.mcp.json` and launched as stdio subprocesses via `uv --directory <rel> run <console-script>`. This file is the contract: **only use the tool names listed below, exactly as spelled (mind hyphen vs underscore).**

> **Worktree note:** the hub (`ship_studios/config.py`) and the `.mcp.json` servers (via `scripts/mcp_launch.py`) auto-resolve the `../stemmy-*-mcp` siblings from the **main checkout** even when run from a git worktree under `.claude/worktrees/` — no env vars needed (a linked worktree's `.git` pointer + `commondir` is read to find the canonical root). `SHIP_STUDIOS_LOOPS_DIR` / `SHIP_STUDIOS_GEMINI_DIR` still override for a non-standard layout (CI, a vendored checkout). *(An already-running Claude Code session must reload/restart to pick up an `.mcp.json` change.)*

> **Mix/master/EQ surface:** the roadmap in [`docs/mix-master-capability-roadmap.md`](docs/mix-master-capability-roadmap.md) is implemented in both sibling repos and folded into the tool surface + pipelines below — `[L]` is **48 tools** (43 pure-DSP + the 2-tool VST-hosting pair + the 3 batch tools below), `[G]` 23. The six `[G]` critique tools are meter-grounded + typed (see the note under §4), and `check-streaming-targets` projects asymmetric playback gain. Per-tool Gemini thinking tiers + a Files-API upload cache are internal (no surface change). **Caveat:** `suppress-resonances` / `apply-dynamic-eq` (time-varying DSP) are unit-tested only and want an ear-tuning pass on real material before you trust them on a release.

> **Gemini audio reference:** what *every* Gemini model can do with audio — understanding (the part this repo wires up) plus speech/TTS, the Live API, and Lyria music generation, with models, pricing, SDK patterns, and limits — is documented in [`docs/gemini-audio/`](docs/gemini-audio/README.md) and surfaced as the **`[[gemini-audio]]`** skill suite (`gemini-audio` index + `gemini-audio-understanding` / `gemini-speech-generation` / `gemini-live-audio` / `gemini-music-generation`). Reach for it whenever you need to know what Gemini can/can't hear or which model/format/limit/price applies. The governing fact: Gemini downmixes to ~16 kbps mono, so **meters own loudness/peak/stereo**.

> **VST plugin hosting:** `apply-vst-chain` + `list-vst-plugins` (`[L]`, the `vst` extra → Pedalboard) run third-party **VST3 / AU *effect*** plugins offline & headless (no DAW/GUI/device) — e.g. a stage-5 insert before `render-mastered`. The **one** part of the surface that loads external, non-deterministic binaries: opt-in, effects-only, VST3 cross-platform / AU macOS-only (`list-vst-plugins` is read-only and needs no extra). Two traps an agent must respect: **loads ≠ renders** (a plugin can load yet pass audio through unchanged — verify with `[[vst-verify]]`, measuring *detail* not just `changed:true`), and for **UAD** load the `uaudio_*.vst3` build, never the passthrough `UAD ….component` twin. The **full doctrine, the ~32 per-plugin measured deep-dives, and the headless-safe inventory live in the `[[vst]]` skill suite** ([`docs/vst/README.md`](docs/vst/README.md)) — reach for a specific `[[<plugin>]]` skill when you know the box, the generic `[[vst-eq]]` / `[[vst-compress]]` / `[[vst-saturate]]` / … otherwise.

### Philosophy

A track moves left-to-right through the lifecycle: **understand** the source → **create loops** (optional) → **measure** → **perceptual critique** → **corrective + render** → **deliver**. Measure before you move; let Gemini's ears and the DSP meters cross-check each other; never master inside the mix stage. Pipelines below encode the canonical orderings.

### By goal — request → skill

Most work starts from a **skill**, not a raw tool — match the request here, then let the skill drive the tools. (The lifecycle-ordered tool tables follow; the [Canonical pipelines](#canonical-pipelines) are the hand-typed recipes the skills wrap.)

- **Master a track / "streaming-ready / -14 LUFS for Spotify"** → `[[master-track]]`; a whole EP/folder → `[[batch-master]]`; assemble already-mastered tracks → `[[release-package]]`.
- **Diagnose a mix / "what's wrong / too harsh / muddy / boomy"** → `[[mix-check]]` (hands off to `[[master-track]]`); glue before mastering → `[[finalize-mix]]`.
- **Sound like a reference** → `[[reference-match]]`; one shared tone across an EP → `[[house-curve]]`.
- **Balance levels / "the hi-hat's too loud / X is buried"** → `[[mix-balance]]` FIRST (a balance problem is not an EQ problem); de-spill a close mic → `[[bleed-gate]]`.
- **Work from stems** → `[[stem-master]]` (correct→sum→master); carve clashes only → `[[unmask-stems]]`; per-stem correct+color → `[[stem-process]]`; split a mixdown → `[[stem-split]]`.
- **A multi-mic drum kit** (overheads/room/close mics) → `[[drum-prep]]`; a raw Logic/interface dump → `[[logic-extract]]` → `[[multitrack-triage]]`.
- **Bounce a prepped kit / song to a stereo bus** → `[[drum-mix]]` (drums) · `[[song-mix]]` (full song); set levels first with `[[mix-balance]]`.
- **A drum-bus character / a famous drum tone** → `[[warm-drum-bus]]` · `[[drum-stems-character]]` · `[[fool-in-the-rain]]` (Bonham) · `[[home-at-last]]` (Aja) · `[[tomorrow-never-knows]]` (Beatles).
- **A targeted corrective move** → `[[de-ess]]` · `[[de-harsh]]` · `[[dynamic-eq]]` · `[[excite]]` · `[[multiband-compress]]` · `[[drum-punch]]` · `[[sub-design]]` · `[[groove-tighten]]`.
- **Use your own VST3/AU plugins** → `[[vst]]` (index + doctrine), then a `vst-*` task skill or a per-plugin deep-dive.
- **Loops / one-shots / a pack** → `[[loops-to-deliverables]]` · `[[slice-oneshots]]` · `[[sample-pack]]` · `[[sampler-kit]]`.
- **Understand a reference** (transcribe / events / compare) → `[[understand-audio]]`. **New project** → `[[new-track]]`. **QC before shipping** → `[[delivery-qc]]`.

For batch / parallel runs (a whole album, a folder of stems, a plugin sweep, a variant shootout) reach for the matching **workflow** — `/batch-master`, `/house-curve`, `/stem-process`, `/audio-shootout`, … — see [Workflows](#workflows-multi-agent-fan-out) below.

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

> What Gemini can/can't do here (tasks, formats, 32 tok/s cost, 9.5 h limit, the mono-downmix caveat) → `[[gemini-audio-understanding]]` / [`docs/gemini-audio/audio-understanding.md`](docs/gemini-audio/audio-understanding.md).

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

**Overlap rule:** both servers expose `measure-loudness` / `measure-spectrum`. They are independent implementations. Prefer **`[L]`** when you're inside a loops/mastering chain (same code path that renders), and **`[G]`** when you've already opened the gemini session for perceptual work — don't spin up a server just to duplicate a meter. For stereo, `[L] measure-stereo` and `[G] analyze-phase-mono` are interchangeable; pick by which server is already in play.

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

**Grounded + typed (the critique tools above):** `analyze-mix-balance`, `detect-mix-issues`, `mastering-feedback`, `compare-to-reference`, `critique-region`, and `master-assistant` now run meter-grounded — the matching pure-DSP meters (LUFS / true-peak / crest / LRA / 5-band tilt / L-R correlation / mono-sum loss) are measured and injected as ground truth the model must reason **from**, not re-estimate by ear (Gemini hears only ~16 kbps mono, so meters own loudness/peak/stereo — **and the codec degrades the tonal read too: Gemini chronically under-reads highs / over-reads lows, so verify any "dark"/"boomy" note against `[L] measure-spectrum` (tilt + centroid) before a brighten/darken move, make ONE correction toward the goal, then trust the meter — don't iterate the read**). All accept optional `genre` + `intent`, split findings into `technical_defects` (meter-groundable, safe to auto-apply) vs `creative_observations` (taste), and emit **tool-ready typed** moves — e.g. `eq_moves` `[{freq_hz, gain_db, q, type}]`, de-ess `{center_hz, q, threshold_db, gr_db}` — clamped server-side so they drop straight into `apply-eq` / `de-ess`, plus a `meters` passthrough.

> Why these are meter-grounded (Gemini hears only ~16 kbps mono) and the broader Gemini audio surface → `[[gemini-audio]]` / [`docs/gemini-audio/caveats-and-limits.md`](docs/gemini-audio/caveats-and-limits.md).

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

> **`apply-vst-chain` is the one non-pure-DSP render tool** — it loads external plugin binaries via Pedalboard, so it needs `uv sync --extra vst` and is not deterministic across plugin versions. Effects only; VST3 cross-platform, AU macOS-only. Pass `plugins=[{plugin_path, parameters?, state_path?, bypass?}]`; set `dump_state=true` to capture each plugin's opaque state next to the output for a reproducible re-render. Use `list-vst-plugins` to find plugin paths. See the **VST plugin hosting** note near the top of this file.

> **Batch tools — one call, not N (the efficiency contract).** For a *folder of stems/files*, prefer the batch tools over fanning out per-file MCP calls. `measure-loudness-batch` / `apply-eq-batch` measure/EQ a LIST in one call, **genuinely concurrent** (the loops server thread-offloads its pure-DSP handlers — numpy releases the GIL — and bounds the fan-out with `STEMMY_LOOPS_DSP_CONCURRENCY`). `process-stems` runs the whole per-stem corrective chain (clean → zero-phase EQ → de-harsh → dynamic-EQ → transient → excite) + an optional API-console color stage over a LIST in one call, the server-side equivalent of `scripts/mix/process_stems.py`. It is **serial by design**: the color stage loads a VST per stem and Pedalboard plugins load only on the main thread + render non-deterministically under concurrency, so `process-stems` (and every `apply-vst-chain` render) is serialized server-side. **Never fan out `apply-vst-chain` / `process-stems` color across parallel calls** — it's structurally serialized (a process-global render lock), so parallel calls only add overhead. The color stage is API-Vision-specific: pass `color_plugin_path` to an API-Vision-compatible plugin, or omit it for a pure-DSP pass.

### 6. Deliver (tag + export — all `[L]`, pure DSP)

| Capability | Tool |
|---|---|
| Embed BPM/key/root/bars/comment + `tags.json` sidecar | `tag-deliverable` |
| Batch format matrix + dither — presets `distribution_44k_16` (44.1/16) · `production_48k_24` (48/24) · `master_96k_24` (96/24) | `export-deliverables` |

---

## Canonical pipelines

Each is an ordered tool-call recipe. Server prefix `[L]`/`[G]` precedes the tool. Outputs go to `projects/<track>/` (loop scratch to `artifacts/<run>/`). Skills under `.claude/skills/` and slash commands under `.claude/commands/` wrap these — prefer the skill over hand-typing.

### master-track — near-final mix → platform-ready master + deliverables

1. `[L] measure-loudness` — baseline LUFS / true-peak / crest / PLR / LRA / DR.
2. `[L] measure-spectrum` — baseline tilt + 5-band balance.
3. `[L] measure-stereo` — baseline correlation + mono-sum loss.
4. `[L] check-clipping` — confirm no inter-sample clip / DC / polarity issue.
5. `[L] measure-distortion` — baseline THD / aliasing before the limiter stage.
6. `[G] mastering-feedback` — perceptual critique + `target_platform` + release-ready bool. *(Alt: `[G] master-assistant` with `intent`/`intensity`/`style` → a complete typed chain — EQ/comp/sat/limiter targets — to drive step 7; both wrapped as [[mastering-plan]].)*
7. `[L] render-mastered` — to chosen `target_lufs` + `ceiling_dbtp` (optional `eq_bands` for a zero-phase corrective move) → `projects/<track>/masters/`.
8. `[G] check-streaming-targets` — re-verify the render vs Spotify/Apple/YouTube/Tidal… It also projects the **asymmetric** playback gain per platform (attenuate-only vs boost-and-attenuate, headroom-capped) so you can see what each platform will actually do to the level.
9. If non-compliant, adjust target and re-render (back to 7).
10. `[L] export-deliverables` — presets `["distribution_44k_16", "production_48k_24", "master_96k_24"]` (44.1/16, 48/24, 96/24; exact allow-list — the server rejects free-form `<sr>/<bits>`), `tag=true` → `projects/<track>/deliverables/`.

### batch-master — folder of near-final mixes → consistent masters + cross-track table

Per track (loop the folder), then a cross-track pass. One **shared** target for the whole set.

1. `[L] measure-loudness` + `[L] measure-spectrum` + `[L] check-clipping` — per-track baseline.
2. `[G] mastering-feedback` — per-track release-ready bool + harshness flags to steer that track's render.
3. `[L] render-mastered` — to the **shared** `target_lufs`/`ceiling_dbtp` → `projects/<album>/masters/`.
4. `[G] check-streaming-targets` — per-track compliance; re-render that track if it'll be attenuated.
5. `[L] export-deliverables` — presets, `tag=true` → `projects/<album>/deliverables/`.
6. Cross-track: loop `[L] measure-loudness` over every master → LUFS-I / true-peak / LRA + **Δ-from-album-median** table; flag outliers (e.g. >0.5 LU off median). For the shared album-gain a platform will actually apply, run `[L] analyze-album-normalization` (TD1008 loudest-track + album-integrated offsets).
7. `drum-prep verify-tags` (or delivery-qc) — confirm the RIFF INFO chunk survived export.

The consistency table is the headline. Hand any not-release-ready track to mix-check first; don't loudness-paper a broken mix.

### stem-master — per-stem corrective mixdown → sum → hand to master-track

You **mix** the stems (correct + sum), then **master** the bus. This stage does NOT limit.

1. Per stem: `[L] measure-loudness` + `[L] measure-spectrum` — baseline.
2. `[G] analyze-stem-masking` (stem map) — per-collision dominant stem, stem-to-cut, center Hz, cut dB, Q. Optional `[L] detect-masking` cross-check.
3. `[G] find-resonances` / `[G] find-sibilance` — surgical notch / de-ess settings on the offending stems.
4. `[L] apply-eq` — one call **per losing stem**; complementary cuts (carve bass under kick, tame vocal mud). Cut the loser, don't boost the winner. `[L] de-ess` ([[de-ess]], from the `[G] find-sibilance` settings) and `[L] suppress-resonances` ([[de-harsh]]) clean harsh/ringing stems; `[L] apply-dynamic-eq` ([[dynamic-eq]]) for level-dependent collisions (carve only when the kick hits).
5. `[L] compress-loop` / `[L] multiband-compress` ([[multiband-compress]]) / `[L] shape-bands` ([[drum-punch]]) — per stem where dynamics / transients / per-band density call for it.
6. `drum-prep stem-mix` — sum the corrected stems to one stereo bus (local DSP; no MCP tool sums a stem set).
7. Re-run `[G] analyze-stem-masking` + `[L] measure-spectrum` — confirm the overlaps shrank.
8. Hand the summed bus to **master-track** for loudness / limiting / compliance / export.

### unmask-stems — masking-only subset of stem-master (no sum, no master)

The corrective core of stem-master when you only need to carve cross-stem collisions — no per-stem baseline, no tone/dynamics shaping, no summing, no mastering.

1. `[G] analyze-stem-masking` — the collision map (dominant stem, stem-to-cut, center Hz, cut dB, Q). Optional `[L] detect-masking` cross-check.
2. `[L] apply-eq` (or `[L] apply-dynamic-eq`, [[dynamic-eq]]) — one complementary cut **per losing stem**; cut the loser, don't boost the winner.
3. `[G] analyze-stem-masking` — re-score to prove the overlap shrank.

stem-master adds the per-stem baseline, tone/dynamics shaping, the `drum-prep stem-mix` sum, and the master-track hand-off on top of these three steps. ([[unmask-stems]])

### mix-check — diagnose a mix (perceptual + measurement) → concrete moves

1. `[G] detect-mix-issues` — audible problems w/ severity + timestamps. *(To zoom in on a flagged window, `[G] critique-region` re-critiques a DSP-trimmed, onset-snapped clip.)*
2. `[G] analyze-mix-balance` — band-by-band tonal/stereo/depth critique.
3. `[L] measure-loudness` — ground the read with objective numbers.
4. `[L] measure-spectrum` — third-octave / tilt / 5-band to confirm or refute the tonal call.
5. `[L] measure-stereo` — correlation / width / mono-sum loss.
6. `[G] find-resonances` — narrow-Q peaks + notch dB → feed `apply-eq` bells.
7. `[G] find-sibilance` — de-esser settings (center Hz, Q, threshold, GR).
8. `[G] analyze-phase-mono` — per-band correlation + polarity flag before EQ.
9. Reconcile perceptual vs measured into a prioritized issue list.
10. `[L] apply-eq` — notches + shelves/tilt from the findings (use `phase=zero` to keep transients/phase intact on drum material).
11. `[L] de-ess` ([[de-ess]], consumes the `find-sibilance` settings) / `[L] suppress-resonances` ([[de-harsh]]) — when sibilance or narrow ringing was flagged; `[L] apply-dynamic-eq` ([[dynamic-eq]]) when a problem is level-dependent (mud only on kicks, harsh only on loud phrases) rather than static; `[L] excite-loop` ([[excite]]) when it's dull, not harsh.
12. `[L] compress-loop` / `[L] multiband-compress` ([[multiband-compress]]) — where dynamics analysis called for it. Write to `projects/<track>/mix/`.

**Do not master here** — hand off to master-track.

### reference-match — make a mix sound like a reference

1. `[G] match-reference-numeric` — per-third-octave delta-dB curve + LUFS/TP/RMS/crest/tilt deltas.
2. `[G] compare-to-reference` — perceptual A/B deltas + actionable moves (`goal`).
3. `[L] compare-tonality` — second numeric per-band delta + confidence (cross-check).
4. `[L] match-eq` — **always runs** (the primary corrective): render the reconciled source-minus-reference delta as a min/linear-phase corrective FIR toward the reference (pass `source_path`+`reference_path`, or the `delta_db_curve` from step 1/3; `match_strength` ~0.5, `phase` min/linear) → the matched mix.
5. `[L] apply-eq` — **optional residual** (runs only when reconciled `eq_bands` are supplied): layer a few surgical shelves/bells (+ `tilt_db_per_octave`) on the matched output from step 4.
6. `[L] render-ab` — `processed`=corrected mix (the match-eq output, or the apply-eq output if step 5 ran), `reference`=ref → single A/B WAV in `projects/<track>/mix/`. Report the residual from `match-eq`'s returned `residual_delta_db` (no second `compare-tonality` pass).

For a whole EP/album, capture **one shared house curve** with `[L] build-target-profile` over the references, then match each mix to it with `[L] match-to-profile` → `[L] match-eq` — a single consistent target across the set ([[house-curve]]).

### house-curve — one shared tonal target across an EP/album

The reusable-profile path branching off reference-match: build a single house curve from a set of references, then match each mix to it (reuse the one profile JSON across the set for a consistent sound).

1. `[L] build-target-profile` — power-average the reference paths into a reusable profile JSON.
2. `[L] match-to-profile` — the mix's per-band delta vs the profile.
3. `[L] match-eq` — render the delta as a min/linear-phase FIR correction (runs only when a per-band delta is recoverable; `match_strength` ~0.5, `phase` min/linear) → `projects/<track>/mix/`. Follow with `[L] apply-eq` for surgical residuals.

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

### raw-intake — Logic project → clean, song-split, role-labeled kits (local-DSP skills, no MCP tools)

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
  misreads → use sox / `aiff2wav.sh`); `kit.json` file fields must name the real
  on-disk file *with its actual extension* (`.wav`/`.aif`/`.aiff`/`.flac` — the
  example uses `.aif`; validated against the files on disk, not forced to `.wav`);
  `adeclip` overshoots 0 dBFS (renormalize); multi-input ffmpeg trims need
  `atrim` in the filtergraph (input `-ss/-t` only affects the first input).
- **Phase-align BEFORE corrective EQ**, and never HPF the overheads before
  aligning — it removes the low end the kick correlates against and the lock goes
  bogus (a 971-sample / 20 ms slip). Already-EQ'd? Align off the full-band
  originals; delays commute with zero-phase EQ + gating (see Guardrails).
- **Pin a non-standard mic role in `kit.json`** — a "crotch mic" (between the
  knees, low-end weight off kick + snare) or a sub-kick won't auto-detect; set
  role `kick_sub` so it low-pass-correlates to the overheads like a kick mic.

---

## Workflows (multi-agent fan-out)

Reusable Claude Code **dynamic workflows** live in `.claude/workflows/*.js` — JS
scripts that orchestrate parallel subagents (invoked via `ultracode` / "use a
workflow", or as `/<name>`). Use them for **parallel fan-out / judge-panels /
batch / cross-checked verification**, NOT sequential file-mutating DSP (that
stays a skill). A workflow script has **no filesystem/bash access** — render the
variants / gather the lists **inline first**, pass them via `args`, and the
script returns a structured object the session writes out.

| Workflow | Fans out | Render / gather inline first |
|---|---|---|
| `audio-shootout` | one Gemini lens agent per (variant × criterion) → ranked pick + dissent | render + **level-match** the variant WAVs; pack `meters` |
| `warm-bus-shootout` | a warm-drum-bus preset over `audio-shootout` (warmth/tightness/life) | the warm-bus variants (e.g. via `scripts/mix/warm_bus.py`) |
| `vst-probe-inventory` | chunked parallel `presets/vst/probe_plugin.py` → render-verified inventory | the plugin list (`list-vst-plugins` / `demo/headless-safe-titles.txt`) |
| `batch-master` | one agent per track runs the master chain → cross-track consistency table | the folder + the ONE shared `target_lufs` / `ceiling_dbtp` |
| `house-curve` | one agent per mix → match-to-profile → match-eq → re-measure; cross-track spread reduce (tonal companion to `batch-master`) | the references (or a prebuilt profile JSON) + the mix list |
| `stem-process` | one agent per stem diagnoses + authors a corrective plan (parallel reads); the executor then runs as ONE serial UADx-safe pass | the kit's stem dir (`srcDir`/`outDir`); a prebuilt plans list is optional |
| `drum-stems-character` | two-mode per-stem fan-out: `mode:'correct'` → one agent per stem authors a pure-DSP corrective plan, then ONE serial `process_stems.py`; `mode:'character'` → one agent per stem plans a role+character-aware UADx chain, then ONE serial `character_stems.py` (one stem at a time, UADx-safe). The `drum-stems-character` skill drives it twice with an AskUserQuestion (the chosen character) in between | the kit's stem dir (`srcDir`/`outDir`), the chosen `character` (Clean/Warm/Punchy/Crushed/Aggressive/Bonham/TNK) |
| `fool-in-the-rain` / `home-at-last` / `tomorrow-never-knows` | the famous-drum **bus-tuning** twins: render N drum-bus variants → a parallel multi-lens Gemini judge panel against that recipe's brief → pick the winner (whose meters become the preset's `approved_signature`). The same-named skill calls this to lock its chain | the balanced pre-bus + `out_dir` (+ the variant flags) |
| `audit-skill-consistency` | one agent per skill → wikilink / tool-name / doc / key-label / **mono-caveat** / **argument-hint** / frontmatter drift | the skill-dir list + valid-target sets |
| `audit-pipeline-lockstep` | one agent per coded pipeline → CLAUDE.md prose ↔ `pipelines.py` ↔ tests drift | (agents read the files themselves) |

Reference a workflow in prose as `name` / `/name` (a slash command) — **not** as
a `[[name]]` wikilink (those resolve to skills/docs only). **Workflows are NOT in
the auto-injected skill list** an agent sees each turn — only this table (and the
`/name` slash surface) advertises them, so consult it whenever a task wants
parallel fan-out. Three more are **dev/meta** workflows for working *on* this repo
(`create-skill`, `repo-review`, `repo-review-fix`) — see [Developing this repo](#developing-this-repo-tests--lint--types).

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
  - *Accepted risk:* the `settings.json` `Read(./.env*)` deny only constrains the **Read tool** — `Bash(uv:*)` (a general Python runner) can read any file, so it can bypass that deny. Keep secrets in the **shell env**, never on disk (`.env.example` holds placeholders only).
- **Only use verified tool names** from the surface above, spelled exactly (hyphen vs underscore matters).
- **Measure before and after** any corrective/render step so changes are quantified.
- **Concurrency: batch, don't fan out.** Per-file DSP and every VST render are **serialized server-side** (pure-DSP handlers are thread-offloaded so they parallelize internally; VST renders are behind a process-global lock and load only on the main thread). For a **folder of stems/files**, reach for the **batch tools** (`process-stems`, `apply-eq-batch`, `measure-loudness-batch`) or the batch **scripts** (`scripts/mix/process_stems.py`) — ONE call that loops internally and bounds its own concurrency — instead of firing N separate MCP calls. **Never parallelize `apply-vst-chain` / `process-stems` color**: concurrent plugin renders are non-deterministic, so parallel calls only add overhead, not speed.
- **Balance volumes before EQ.** When summing stems/mics, set levels by **measured integrated LUFS** (`[[mix-balance]]` / `[[drum-mix]]` / `[[song-mix]]`), never eyeballed dB, never RMS (overheads read hot in LUFS and carry the hi-hat/cymbals → put them *under* the close mics), and never by peak-normalizing the sum. A balance problem (e.g. "too much hi-hat" = overhead too loud) is **not** an EQ problem; de-spill forward close mics with `[[bleed-gate]]` first.
- BPM is required for `find-loops` / `analyze-loops` / `quantize-loop` / `extract-drums` — never guess; ask or read `track.md`.
- **Capability docs are discoverable via skills.** The `[[gemini-audio]]` suite links to `docs/gemini-audio/*.md`; these reference skills link directly to their doc file — a deliberate extension of the usual skill→skill wikilink convention — so an agent can pull a Gemini audio capability doc on demand.

---

## Setup prerequisites

Both servers are sibling repos using `uv`. Sync each in its own directory before first use.

### `../stemmy-loops-mcp`

```bash
# Minimal — MCP server + DSP mix/master measurement & render tools:
uv sync --extra loops-mcp --extra mixing

# VST hosting — add the `vst` extra to run third-party VST3/AU effect plugins (apply-vst-chain):
uv sync --extra loops-mcp --extra mixing --extra vst

# Full — every optional capability (LLM, Gemini listen, Demucs, classify, quantize, beats, viz, embed, vst):
uv sync --extra loops-mcp --extra mixing --extra llm --extra listen \
        --extra separate --extra classify --extra quantize --extra beats --extra viz --extra embed --extra vst

# Or the convenience superset (separate + embed + classify + quantize + viz + llm + listen + beats):
uv sync --extra loops-mcp --extra mixing --extra ml
```

- `loops-mcp` → MCP server itself · `mixing` → loudness/render/AB tools · `llm` → `diagnose/ask/suggest/caption-loops/analyze-loops` LLM flags · `listen` → `describe-loops` (Gemini) · `separate` → `extract-drums` + `find-loops separate=true` · `classify` → hit tagging · `quantize` → `quantize-loop` · `beats` → deep beat tracker · `viz` → debug plots · `embed` → CLAP loop/bar embeddings (semantic similarity / structure clustering) · `vst` → `apply-vst-chain` (host external VST3/AU effect plugins via Pedalboard; `list-vst-plugins` needs no extra) · `ml` → convenience superset of all of the above.

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
| `STEMMY_LISTEN_MODEL` | optional `[L] describe-loops` Gemini model override (default `gemini-3.1-pro-preview`). **Separate from `STEMMY_MCP_MODEL`** — the loops server's listen tool reads its own var, so to move *every* Gemini read off the default you must set this **alongside** `STEMMY_MCP_MODEL` (changing only `STEMMY_MCP_MODEL` leaves `describe-loops` on the old model — the footgun) |
| `STEMMY_MCP_THINKING_LEVEL` / `STEMMY_MCP_THINKING_BUDGET` | optional `[G]` per-call thinking-tier override (else a per-tool default tier is used: high for verdict/critique tools, low for cheap tags) |
| `STEMMY_MCP_MODEL_CONCURRENCY` | optional `[G]` cap on concurrent Gemini **model** calls (default `3`; separate from the File-API upload cap). Throttles a perceptual-tool fan-out at the source so it doesn't trip the 429 per-minute quota |
| `STEMMY_LOOPS_DSP_CONCURRENCY` | optional `[L]` cap on concurrent pure-DSP offloads inside the batch tools (`measure-loudness-batch` / `apply-eq-batch`); default `min(cpu, 4)` |
| `STEMMY_MCP_ALLOWED_ROOTS` | optional `[G]` filesystem allow-list — an OS-path-separator-delimited (`:` on POSIX, `;` on Windows) list of **absolute** directory roots. The **Gemini server enforces** it (each input path is `Path.resolve()`d and must be a child of an allowed root, else the read is refused); the **hub passes paths through unmodified** (no validation/rewrite on this side). Add your `projects/` / `artifacts/` roots, or leave it unset for unrestricted local use. |
| `SHIP_STUDIOS_LOOPS_DIR` / `SHIP_STUDIOS_GEMINI_DIR` | optional override for the sibling-repo locations (the hub/CLI auto-resolve `../stemmy-*-mcp` from the **main** checkout, git worktrees included); set these only for a non-standard layout (CI, a vendored checkout) |
| `SHIP_STUDIOS_STARTUP_TIMEOUT` / `SHIP_STUDIOS_CALL_TIMEOUT` | optional **hub** timeouts in seconds (`ship_studios/config.py`): MCP-handshake budget (default `120`) and per tool-call budget (default `600`); `0` disables either. **A `SHIP_STUDIOS_CALL_TIMEOUT` fire abandons the client's *wait* but does NOT abort server-side work** — no cancellation is sent, so the sibling subprocess keeps running the in-flight tool until it is reaped at Hub/stack teardown; set it generously for heavy tools (Demucs separation, Gemini renders) |
| `SHIP_STUDIOS_ARTIFACTS_DIR` / `SHIP_STUDIOS_PROJECTS_DIR` | optional **hub** path overrides (`ship_studios/config.py`): run-artifacts root (default `<repo>/artifacts`) and per-track workspace root (default `<repo>/projects`) |
| `STEMMY_CACHE_DIR` / `STEMMY_NO_CACHE` | optional `[L]` disk-cache controls read by the loops server's `separate`/`embed`/`classify` tools (`stemmy/_diskcache.py`): cache root, and `STEMMY_NO_CACHE=1` to disable |

Pure-DSP measurement/render tools on **either** server need **no env vars and no network** — they read and write WAVs directly. Set keys only when reaching for a Gemini/LLM tool.

---

## Developing this repo (tests · lint · types)

This repo's *own* Python is just two `uv`-managed packages — **`ship_studios/`** (the DSP-free MCP-client hub: `cli.py` · `pipelines.py` · `mcp_client.py`) and **`drum_prep/`** (the only DSP). The sibling `uv sync` commands above provision the *servers*; the commands below develop *this* hub. The whole test suite runs **offline** — `tests/conftest.py` provides a `FakeSession` + `fake_hub` that monkeypatches `Hub._open_session`, so **no sibling servers, no API keys, no audio, and no network are needed** to run it.

```bash
# One-time: dev tools (pytest/ruff/mypy — the `dev` group) install by default;
# add --extra drum-prep so the DSP test deps (numpy/scipy/soundfile/pyloudnorm) are present.
uv sync --extra drum-prep

uv run pytest                                   # the full offline suite (asyncio_mode=auto; under tests/)
uv run pytest tests/test_pipelines.py           # one file
uv run pytest tests/test_pipelines.py::test_severity_choices_are_server_valid   # one test
uv run pytest -k drum_prep                       # the drum_prep DSP subset (needs --extra drum-prep)

uv run ruff check        # lint (line-length 100; scripts/ + presets/ are EXCLUDED by design — terse one-off probe/sweep helpers)
uv run ruff format       # format
uv run mypy              # types — checks ship_studios + drum_prep only
uv run python scripts/lint_skills.py   # skill-contract lint: [G]-keyless labels, wikilinks, frontmatter (CI-gated)
```

- **The DSP test subset (drum_prep + scripts/mix + the vst harness) SKIPS without `--extra drum-prep`** — those modules `pytest.importorskip` numpy/scipy/soundfile/pyloudnorm and skip cleanly, so the hub stays DSP-free and the DSP deps are opt-in. Add the extra to actually run them; hub tests (pipelines/cli/config/mcp_client) run on base deps alone.
- **Editing a pipeline = editing `ship_studios/pipelines.py`**; the matching `tests/test_pipelines.py` asserts the *ordered tool-call log* (server, tool, args) against a `RecordingHub`/`FakeSession`, not live output — so a pipeline change that reorders/renames a tool call will fail loudly. Keep the call order in lockstep with the **Canonical pipelines** section above.
- **VST plugin work** (the `[[vst]]` deep-dives): iterate with the harness/probe scripts under `presets/vst/` (`probe_plugin.py` · `dump_params.py` · `apply_vst_preset.py`) and `scripts/mix/*_sweep.py`, run with the **sibling** loops `vst` venv — `../stemmy-loops-mcp/.venv/bin/python presets/vst/dump_params.py <plugin.vst3>`. These live outside ruff/mypy coverage on purpose.
- **Skill/doc contract guards** keep the ~102 `SKILL.md` files + CLAUDE.md in lockstep in two layers. (1) `scripts/lint_skills.py` — a deterministic, dependency-light, **CI-gated** check (the recurring `[G]`-keyless label bug — `find-sibilance`/`find-resonances`/`check-streaming-targets` are pure DSP, no key — plus wikilink resolution + frontmatter presence). (2) The deeper **agent workflows**, run on demand: `/audit-skill-consistency` (per skill: wikilinks · tool-name drift · doc paths · key-labels · the Gemini **mono-caveat** on `[G]`-critique skills · **argument-hint** drift · frontmatter) and `/audit-pipeline-lockstep` (CLAUDE.md ↔ `pipelines.py` ↔ tests). Author a new skill with `/create-skill`; review the whole repo with `/repo-review` → `/repo-review-fix`.
- **Pre-release / live-contract check.** The offline suite proves only that the hub is *internally* consistent (pipelines ↔ tests ↔ this file's prose) — it asserts tool names/enums against a `RecordingHub` that accepts anything, never against the **real** sibling servers. The one guard that does is `tests/test_pipelines.py::test_live_tool_names_exist_on_servers`, which opens both real servers and asserts every tool name + enum-subset a pipeline emits actually exists on them; it is **opt-in** (skips unless `SHIP_STUDIOS_LIVE_CONTRACT=1` **and** both siblings are synced). Run it against synced siblings before a release — `SHIP_STUDIOS_LIVE_CONTRACT=1 uv run pytest tests/test_pipelines.py -k live` — so a sibling-side tool rename or removed enum value can't slip through green. CI runs this for you off the PR path in the separate, additive `live-contract` job in `.github/workflows/ci.yml` (manual `workflow_dispatch` + nightly `schedule`; it best-effort checks out the siblings and **skips cleanly** when they're absent, so it never blocks the normal PR gate).

## Headless alternative — the `ship-studios` CLI

The same pipelines run without an interactive Claude session via the `ship-studios` console script (`ship_studios.cli:main`). It opens both servers over stdio and drives `call_tool` in the verified order:

```bash
ship-studios doctor          # check env vars + sibling repos before first run
ship-studios master          projects/<track>/mix/final.wav --platform spotify
ship-studios batch-master    projects/<album>/mix/*.wav --platform spotify
ship-studios mix-check       projects/<track>/mix/draft.wav
ship-studios reference-match projects/<track>/mix/draft.wav --reference projects/<track>/refs/ref.wav
ship-studios house-curve     projects/<track>/mix/draft.wav --reference refs/a.wav --reference refs/b.wav
ship-studios stem-master     projects/<track>/stems/kick.wav projects/<track>/stems/bass.wav  # then drum-prep stem-mix + master
ship-studios unmask-stems    projects/<track>/stems/kick.wav projects/<track>/stems/bass.wav  # masking-only subset
ship-studios loops           projects/<track>/stems/drums.wav --bpm 120
ship-studios understand      projects/<track>/refs/ref.wav
```

The nine pipeline subcommands (`master`, `batch-master`, `mix-check`, `reference-match`, `house-curve`, `stem-master`, `unmask-stems`, `loops`, `understand`) each map to the matching function in `ship_studios/pipelines.py`, talking to both servers through the hub in `ship_studios/mcp_client.py`. `doctor` is a self-contained setup check in `ship_studios/cli.py` (it only reads env vars + sibling-repo presence — no pipeline, no server launch). `stem-master` drives only the MCP-side per-stem corrective + masking-verify steps — summing the corrected stems (`drum-prep stem-mix`) and mastering the bus (`ship-studios master`) are separate local-DSP / pipeline stages, by design. Use the CLI for batch/CI runs; use the skills/slash commands for interactive work.

---

## drum-prep — local multi-mic drum DSP (outside the MCP servers)

ship-studios owns no DSP — **except** the `drum_prep/` package, a deliberate local-DSP addition for a job neither stemmy server covers: phase-aligning and per-stem tonally reference-matching a *whole multi-mic drum kit*. It uses **no MCP tools** (numpy/scipy/soundfile/pyloudnorm, opt-in via `uv sync --extra drum-prep`) and ships its own `drum-prep` console script. Prefer the `drum-prep` skills/commands for a multi-mic kit; the stemmy `apply-eq` / `render-ab` are single-stereo-file tools, not kit-aware.

### Mic roles & `kit.json`

Roles auto-detect from filenames: `overhead` (or `overhead_l`+`overhead_r`), `room`, `kick_in`/`kick_beater`/`kick_out`/`kick_sub`, `snare_top`/`snare_bottom`, `hihat`, `ride`, `crash`, `tom`, and `fx` (effect returns like a snare plate auto-detect as `fx` and are excluded from phase-align). Commit a `kit.json` (see `drum_prep/examples/kit.json`) to pin/override roles, partner links, per-mic low-pass, ambience, or polarity. The manifest (JSON) is committable; audio is gitignored. Keep the reference file outside the stems folder (or pass it via `--reference`, which excludes it from detection).

### Flows (each a `drum-prep` subcommand; many also have a `/drum-*` skill)

1. `drum-prep detect <dir>` — show/confirm roles (overlaying `<dir>/kit.json`, or `--manifest`, if present); `--write-manifest` scaffolds a `kit.json`.
2. `drum-prep stereo-merge <dir>` — merge every `<name> - left`/`right` pair into format-preserving stereo + image review; generalizes `overheads`.
3. `drum-prep overheads <dir>` — merge an L/R overhead pair into one stereo reference (no-op if already stereo; `--align` to phase-lock a coincident pair).
4. `drum-prep phase-align <dir>` — align close mics to the overheads (fixed reference): broadband → OH; kick low-passed → OH; snare-bottom→top & kick-beater→in as partner pairs composed onto OH; room polarity-only → `<dir>/phase-aligned/`.
5. `drum-prep normalize <dir>` — balance-preserving GLOBAL gain by default (per-file changes the kit balance).
6. `drum-prep analyze <dir> --reference <ref>` — read-only tonal report (reference vs kit, per-band ownership); writes nothing.
7. `drum-prep reference-match <dir> --reference <ref>` — match the coherent kit sum toward the reference, distributed per stem → `<dir>/ref-matched/`.
8. `drum-prep mix <dir> --feel <roomy|punchy|natural|dry> --perspective <audience|drummer> [--plate FILE] [--flat]` — mix the prepped kit to a stereo bus by per-role loudness offsets + panning + FX return; the stage between prep and master.
9. `drum-prep audition <dir> --reference <ref>` — loudness-matched stereo A/B WAVs → `<dir>/auditions/`; also emits loudness-matched halves (`cmp_reference.wav`/`cmp_after.wav`) for stemmy-gemini `compare-to-reference`.
10. `drum-prep chain <dir> --reference <ref>` — resolve the kit, then the three reported stages phase-align → reference-match → audition end to end (`--out-root` to redirect).
11. `drum-prep stem-mix <dir>` — mix arbitrary named stems to a stereo bus by loudness offsets + per-stem spec; the role-agnostic song-mix ([[song-mix]]).
12. `drum-prep sub-design <kick> --out <f>` — synthesize an envelope-followed sine sub under a kick; low-end EXTENSION EQ can't add ([[sub-design]]).
13. `drum-prep tune <sample> [--out <f>]` — measure a drum's fundamental; retune a SAMPLE by resampling (samples/oneshots only) ([[drum-tune]]).
14. `drum-prep verify-tags <dir>` — verify deliverables carry their RIFF INFO LIST chunk + sidecar; catches `export-deliverables` silently dropping tags ([[delivery-qc]]).

### Guardrails (do not change the proven numerics in `drum_prep/dsp.py`)

- **Coherent time-domain sum, not power-sum** when measuring the kit (a power-sum undercounts the correlated kick lows → low-end over-boost).
- **Zero-phase EQ** (real, symmetric gain) so the phase alignment survives the tonal match.
- **Envelope-coarse → waveform refine** alignment to avoid half-period slips on resonant snares.
- **Cuts → all stems, boosts → band owners**; one **global** headroom trim preserves inter-stem balance.
- **Phase-align on FULL-BAND signals, before corrective EQ.** Delays are physical mic distances; estimate them from the unprocessed stems. HPF'ing the overheads first strips the low end the kick (LP180) needs to lock onto → a bogus delay (seen: 971 samples / 20 ms, post_corr 0.05). If stems are already EQ'd, derive delays from the full-band originals and apply them to the processed stems — a pure time-shift **commutes** with zero-phase EQ + gating (all LTI), so the result is identical in the interior.
- Regression tests: `uv run pytest -k drum_prep` (needs `--extra drum-prep`).
