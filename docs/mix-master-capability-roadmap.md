# Mix / Master / EQ capability roadmap — stemmy MCP servers

**Status:** research-backed proposal (no code changes yet) · **Date:** 2026-05-31 · **Scope:** both `stemmy-gemini` and `stemmy-loops`

This document answers one question: *how do we make our Gemini-backed MCP servers more capable at mixing, mastering, and EQ?* It is the output of a verified research pass — 8 web-research angles, consolidation, adversarial feasibility verification, and synthesis — with every finding grounded against the actual code of both servers. Five proposals were **killed** as infeasible (see [Explicitly rejected](#explicitly-rejected)); the survivors are organized into four shippable phases.

> **Legend:** `[G]` = stemmy-gemini · `[L]` = stemmy-loops · effort/impact ∈ {low, med, high}.

---

## The one finding that shapes everything

Gemini **downsamples audio to ~16 kbps and mixes multichannel down to MONO** before the model ever "hears" it ([ai.google.dev/gemini-api/docs/audio](https://ai.google.dev/gemini-api/docs/audio)). Therefore **Gemini cannot actually hear true stereo width, true-peak, or absolute loudness** — yet several of our critique tools currently ask it to estimate exactly those quantities. This independently confirms our standing policy ("trust the dBTP meter over Gemini").

The governing principle for all Gemini work below:

> **Meters are ground truth. Gemini is reserved for what meters can't see** — harshness, pumping, sibilance *feel*, masking, depth, "too brittle." Never let Gemini drive a loudness/peak/stereo *amount*.

---

## Where the two servers stand today

### `stemmy-gemini` (perceptual + measurement, no rendering)
- FastMCP on the `google-genai` SDK; default model `gemini-3.1-pro-preview`.
- Already uses structured output (`response_mime_type="application/json"` + `response_schema`) and multi-file upload (up to 3 parts).
- **No corrective/render DSP** — it critiques and measures only.
- **New-tool recipe:** add a module under `stemmy_gemini_mcp/tools/`, reuse `_call.call_gemini` / `_upload.audio_part` / `_dsp.load_audio`, register in `tools/__init__.py`.
- **Not yet using:** thinking config, Files-API content caching, numerically-bounded schemas, genre/intent context, the Live API.

### `stemmy-loops` (all the corrective/render DSP)
- FastMCP on numpy / scipy / soundfile / librosa / pyloudnorm.
- Has: RBJ biquad `apply-eq`, single-band `compress-loop`, M/S `adjust-stereo`, tanh/tape `saturate-loop`, LR4 transient `shape-bands`, `clean-loop`, 4×-oversampled iterative `render-mastered`, plus the full measurement suite.
- **New-tool recipe:** add `_dsp/<x>.py` (pure DSP returning a pydantic result) + `tools/<x>.py` (`@app.tool`) + register in `tools/__init__.py`.
- **Reusable substrates already in-repo:** `recommend_mastering_chain._measure` (meter bundle), `_dsp/eq.py` RBJ biquads, `_dsp/multiband.py::_lr4_lowpass_sos`, `_dsp/env.py::onepole_envelope`, `_dsp/dynamics.py::_soft_knee_reduction`, `_dsp/cleanup.py` STFT/overlap-add denoiser, `_dsp/saturation.py::_apply_waveshaper`, `drum_prep/dsp.py` zero-phase FFT EQ, `pyloudnorm` (already a dependency).

### Confirmed capability gaps (vs. named pro tools)
Dynamic EQ · dynamic resonance suppression (soothe-style) · matched/FIR EQ from a reference delta · mid-side EQ · automated de-esser · multiband compression/limiting · linear-/zero-phase EQ · band-limited exciter · per-band microdynamics · reusable house-curve targets.

---

## Cross-cutting Gemini API facts (verified)

These are the levers the Gemini-leverage phase pulls on:

| Fact | Implication | Source |
|---|---|---|
| Audio = **32 tokens/sec**, up to **9.5 h** combined, **unlimited files** per request | Batch many A/B/reference files into a single call cheaply | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| **20 MB inline cap** | Above it, use the Files API; reuse one handle across tools | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| Audio is **16 kbps, mono-downmixed** before the model hears it | Gemini cannot judge true stereo/peak/loudness — meters must | [docs/audio](https://ai.google.dev/gemini-api/docs/audio) |
| **Context caching:** 90% input-token discount on 2.5+, **32,768-token (~17 min) minimum** | Cache a long file once across a multi-tool run | [docs/caching](https://ai.google.dev/gemini-api/docs/caching) |
| Structured output supports **min/max, enum, nullable, minItems/maxItems**, and (Nov 2025) `additionalProperties` — **bounds are advisory, not enforced** | Emit tool-ready typed JSON, but **clamp server-side** | [docs/structured-output](https://ai.google.dev/gemini-api/docs/structured-output) |
| **Thinking is tunable** — `thinkingLevel` (3.x) or `thinkingBudget` (2.5), never both; on `gemini-3.1-pro` level is already `high` and `minimal` is rejected | Per-tool tier helps cost only if cheap tools also route to a Flash model | [docs/thinking](https://ai.google.dev/gemini-api/docs/thinking) |
| The `audioTimestamp` flag is **effectively broken** on the public endpoint and model timestamps drift | Get timestamps via a schema `segments` array; cross-check the DSP onset detector; trim regions in DSP | [python-aiplatform#5056](https://github.com/googleapis/python-aiplatform/issues/5056) |
| **Live API** (16 kHz PCM in / 24 kHz voice out, VAD, async tool calls) exists | Future "live monitoring" / spoken-review UX — not a critique-quality win | [docs/live-api](https://ai.google.dev/gemini-api/docs/live-api/capabilities) |

---

## Phase 0 — Quick wins / wire-ups
*Low effort, immediate value. These are thin reuses of code that already exists, each unblocking a broken or hand-translated step. Ship before any large DSP build so downstream automation has clean inputs.*

**1. De-esser that consumes `find-sibilance`** — `[L]` dsp · low/high
`find-sibilance` already *emits* `{center_hz, q, threshold_dbfs, reduction_db}`, but no tool *applies* them — the find→apply chain is broken (the salt-shaker-hat "reads brittle" case). New `_dsp/deess.py`: bandpass the mono sum to `[center_hz, Q]` (sos) → rectify → `onepole_envelope` (attack ~1–3 ms, release ~50–120 ms) → `_soft_knee_reduction` at the given threshold, **clamping gain reduction to `reduction_db` (a max GR, not makeup)**; split-band duck (default) + wide mode; **stereo-linked detector** for a stable image. Measure the 4–9 kHz band delta + offer a `render-ab` audition. Ref: [oeksound soothe2 manual](https://oeksound.com/manuals/soothe2/).

**2. Standalone loudness-match / normalize-to-LUFS** — `[L]` dsp · low/high
Removes the "is it just louder?" confound that `variant-shootout`, `drum-audition`, and `compare-to-reference` all need; standardizes gain math currently copied in three places (`ab.py`, `mastering._normalize_to_lufs`, drum-prep audition). `pyloudnorm` is already a dep. New `_dsp/loudness_match.py`: **preserve channel count** (do *not* mono-collapse like `render_ab`), measure integrated LUFS, apply one linear gain; a `peak_safe` mode clamps the gain so 4×-oversampled true-peak stays under a ceiling (a clamp, **not** a limiter — limiting stays `render-mastered`'s job). Return `applied_gain_db`, in/out LUFS + true-peak, overshoot bool.

**3. Renderer-side pydantic `Field` validation** — `[L]` dsp · low/med
The salvageable core of a rejected "guardrail" idea: add bounds to `apply-eq` / `shape-bands` / `compress-loop` params (`freq > 0`, `q ∈ 0–50`, `gain ∈ −24..24`, crossovers strictly ascending) so malformed params can't reach the DSP. Deliberately **not** a tilt-target guardrail — that would suppress correct de-harsh cuts.

**4. Per-tool thinking-level policy** — `[G]` gemini · low/med
Centralize at the `call_gemini` chokepoint: a tool-name→tier map; set `thinking_level` (3.x) or `thinking_budget` (2.5), **never both** (400 error); clamp `minimal`→`low` (Pro rejects `minimal`); keep temperature at the model default (Google warns low temp causes looping). The cheap-tool cost win only materializes if low-stakes tools (classify/tag) also point `STEMMY_MCP_MODEL` at a Flash variant. Ref: [docs/thinking](https://ai.google.dev/gemini-api/docs/thinking).

**5. Genre/intent context + technical-vs-creative split** — `[G]` gemini · low/med
Optional `genre` (enum) + `intent` (free-text) injected into the critique prompts so the model never "corrects" a deliberately dark/crushed aesthetic toward a pop curve. Split every critique's findings into `technical_defects` (meter-groundable, safe to auto-correct) vs `creative_observations` (taste, never auto-applied). Ref: [izotope — using mastering references](https://www.izotope.com/community/blog/how-to-use-mastering-references).

**6. Band-limited parallel exciter** — `[L]` dsp · low/med
Adds perceived "air"/detail that EQ alone can't, *without* a static high-shelf that raises the noise floor (a recurring pain on the hissy kit). New `excite-loop` reusing `eq.py` HPF/LPF + `saturation._apply_waveshaper`: bandpass (air 6–16k / presence 1–3k) → oversample (allow 8×) → waveshaper (tanh default) → downsample → **required DC-block** → `dry + mix*wet`. Report added-harmonic dB **plus a 5–7 kHz delta** to auto-surface the harsh-band trap; gate steeply so it doesn't excite preamp hiss. Ref: [The Scientist & Engineer's Guide to DSP, ch.19](https://www.dspguide.com/ch19/4.htm).

**7. Elliptical / adaptive bass-mono on `adjust-stereo`** — `[L]` dsp · low/med
Replace the single fixed 2nd-order hard Side high-pass with a slope-selectable (12/24/48 dB/oct) **graduated** Side low-shelf collapse (reuse `_rbj_low_shelf`), for tighter lows and better phone/club mono compatibility. Report headroom reclaimed (true-peak before/after) and mono-sum delta (reuse `measure_stereo.worst_mono_sum_loss_db`). Concept: HoRNet ElliptiQ-style frequency-progressive width.

**8. Per-platform playback-gain + loss projection** — `[G]`/dsp · med/high *(can land here or in Phase 1)*
`check-streaming-targets` reports only pass/fail + one `recommended_attenuation_db`; it does not model **attenuate-only** (YouTube/Tidal/Amazon/Deezer) vs **boost-and-attenuate** (Spotify/Apple) with headroom-capped boost — exactly the `-15 LUFS / -2 dBTP` strategy we rely on (master quiet, let Spotify gain it up, keep a ceiling so the gain-up can't overshoot). Add `normalization_mode` + dated, editable `sources[]` per spec (the taxonomy is web-disputed); project `projected_playback_lufs` / `projected_true_peak`; gate the overshoot flag to naive / Spotify-Loud mode. Unit-test the documented Spotify example. Refs: [Spotify loudness normalization](https://support.spotify.com/us/artists/article/loudness-normalization/), [ITU-R BS.1770-5](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!TOC-HTM-E.htm), [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128).

---

## Phase 1 — Core SOTA DSP (the differentiators)
*These add the corrective capability the servers fundamentally lack today — rendering a measured curve, multiband density, per-band dynamics, reusable targets. They share substrates (LR4 split, FIR builder, spectral smoothing), so building them together amortizes the primitives. Depends on Phase 0's loudness-match + validation.*

**9. Matched-EQ render** — `[L]` dsp · med/high
Renders the per-third-octave delta that `match-reference-numeric` / `compare-tonality` only *measure* today — the missing end of `reference-match`, which currently stops at numbers a human hand-translates into a few bells. Pipeline: log-interp the delta to a dense grid → fractional-octave/ERB smooth → zero-mean → clip ±12 dB → ×`match_strength` (~0.5) → honor the sign (`eq_curve` is mix−ref, so filter gain = −delta×strength) → build FIR via `scipy.signal.firwin2` (1024–4096 taps). Phase modes: `linear`, `minimum` (`scipy.signal.minimum_phase`, no pre-ring, default), and a `tilt-only` safe mode reusing `apply-eq` shelves. Convolve per channel (`oaconvolve`), re-measure third-octave, return `residual_delta_db`. Refs: [AutoEq — how it works](https://github.com/jaakkopasanen/AutoEq/wiki/How-Does-AutoEq-Work%3F), [scipy.signal.firwin2](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.firwin2.html), [scipy.signal.minimum_phase](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.minimum_phase.html).

**10. Linear-/zero-phase EQ mode** — `[L]` dsp · med/med
`apply-eq` is `sosfilt` (minimum-phase) only; `render-mastered` has no EQ stage at all. Add a `phase ∈ {min, zero, linear}` option (`zero` = `sosfiltfilt` with halved per-biquad gains; `linear` = `firwin2` symmetric FIR + reported latency), and an optional zero-phase FFT EQ stage to `render-mastered` (a working implementation already exists in `drum_prep/dsp.py` to model on). Shares the FIR builder with #9; protects drum-prep's phase alignment through tonal moves. Ref: [Minimum-phase filters (Smith, dsprelated)](https://www.dsprelated.com/freebooks/filters/Minimum_Phase_Filters.html).

**11. Multiband compressor** — `[L]` dsp · med/high
The missing density/glue control — `shape-bands` is transient-only and `compress-loop` is single-band, so nothing tames low-end vs presence independently. Build a **proper LR4 HP/LP split** (do *not* reuse `multiband.py`'s residual-subtraction split — measured poor band isolation, ~+1 dB net per −6 dB move); optional 2nd-order allpass on the low band to correct the 3-band summation dip. Factor `compress-loop` internals into a reusable `compress_signal()` (reuse `onepole_envelope` + `_soft_knee_reduction` verbatim); stereo-linked per-band detector; API mirrors `shape-bands` (`crossovers_hz` + per-band param lists). Drop any "zero-phase via filtfilt" option (dynamics are inherently causal). Test identity reconstruction ±0.05 dB. Ref: [Cadenza — multiband compression tutorial](https://cadenzachallenge.org/cadenza_tutorials/signal_processing/mbc.html).

**12. Per-band microdynamics measurement** — `[L]` dsp · med/med
Read-only per-band crest/PLR/punch report telling you *which* band is flat/over-compressed, and giving Gemini a per-band punch read it can't hear from low-bitrate mono. Drives `shape-bands` / the new multiband comp. **Zero-phase LR bandpass** (`filtfilt`) for clean isolation (not the residual-subtraction splitter); per band emit block-crest (reuse `_compute_dr`), an LRA-like short-term spread, true-peak vs RMS, and a transient/sustain punch proxy via `onepole_envelope`. **Document every number as relative** (crest is bandwidth-dependent) and emit per-band RMS so level is disambiguated from dynamics.

**13. Build / save-recall target profile (house curve)** — `[L]` dsp · med/med
Persist a reusable `target.json` (smoothed third-octave curve + LUFS/crest/PLR/LRA/width) so a whole EP matches one captured average. The measurement primitives already exist; compose them over N refs — **aggregate third-octave in linear power, then back to dB** (not a dB mean); average LUFS/crest/LRA as per-file scalars (never concatenate audio). Add a `snapshot_path` arg to `compare-tonality` / a `match-to-profile` that reads the curve and runs the existing delta+suggested-move logic. Feeds #9. Concept: Ozone Target Library / FabFilter saved spectrum.

**14. Album / loudest-track normalization analyzer** — `[L]` dsp · med/med
Extends `batch-master` with the shared album-gain that platforms actually apply. Emit **both** the TD1008 loudest-track offset (`target − max(track_lufs)`) and the album-integrated offset (concatenate per-track buffers, run gated BS.1770 — do *not* average per-track LUFS, the gates make averaging diverge). Per track report source LUFS, shared offset, resulting playback LUFS, and which tracks play quieter under album vs track mode; bound a positive offset so the hottest track stays under ceiling. Wire into `batch-master` step 6. Ref: [productionadvice — TD1008](https://productionadvice.co.uk/td1008/).

---

## Phase 2 — Larger time-varying DSP
*High effort, high reward — artifact mitigation dominates the work. These reuse the STFT/overlap-add scaffolding from `cleanup.py` and the dynamics math from Phase 1, and directly serve the recurring "too harsh/brittle" notes. Sequenced last among DSP because they're the riskiest to get artifact-free.*

**15. Dynamic resonance / harshness suppressor (soothe-STYLE)** — `[L]` dsp · high/high
Content-following STFT suppressor that tames resonances **only when they ring** — the biggest concrete gap vs named tools (we can *find* resonances and apply *static* notches, but not only-when-it-rings suppression). Serves the hi-hat 5–7 kHz de-harsh and air-boosts-raise-noise cases a static notch over-gouges. Model on `cleanup.py::_denoise_channel`'s STFT/ISTFT overlap-add: per frame estimate a smooth spectral envelope (running-median over log-mag via `scipy.ndimage.median_filter`), `excess = log_mag − envelope`, map positive excess to per-bin attenuation gated by selectivity × depth. **The bulk of the effort is artifact control:** per-bin attack/release across frames, gain-curve smoothing across bins, a soft gain law, short windows for percussion transients, and a **stereo-linked** gain mask. Add a sensitivity tilt biasing 2–10 kHz, a `focus_band`, and a delta-listen render. Label soothe-STYLE, not parity. Refs: [oeksound soothe2 manual](https://oeksound.com/manuals/soothe2/).

**16. Dynamic EQ (threshold-gated per-band)** — `[L]` dsp · high/high
The time-varying sibling of static `apply-eq` (de-mud only when the kick hits; tame 3 kHz only on loud vocal phrases) — the most common "smart" modern move, and the consumer of Gemini's time-localized issue map. Use the **difference-signal method** (not coefficient modulation, which zipper-distorts): per band, fixed bandpass extract → detect via `onepole_envelope` (+ optional external sidechain) → per-sample gain from the existing soft-knee curve (cut/boost over a static fallback) → `out = dry + (gain−1)·band`. Extend `EqBand` with dynamics fields; v1 gain-only under ~6 dB GR (where Q drift is benign). Ref: [FabFilter Pro-Q — dynamic EQ](https://www.fabfilter.com/help/pro-q/using/dynamic-eq).

**Stretch (not committed):** dynamic sidechain unmasking EQ (Bark spreading function, à la Neutron Unmask); CDPAM before/after perceptual distance (opt-in `torch` extra — band-limited to ~11 kHz so blind to air/sibilance, unmaintained since 2021); a *static* perception-weighted spectral balancer (LTAS, Gullfoss-inspired — the static, not per-frame, version). Refs: [Neutron Unmask](https://s3.amazonaws.com/izotopedownloads/docs/neutron4/en/unmask/index.html), [PerceptualAudio / CDPAM](https://github.com/pranaymanocha/PerceptualAudio).

---

## Phase 3 — Gemini-leverage layer
*Once the typed DSP renderers exist, this layer makes the find→emit→validate→render handoff fully automatic and meter-grounded — curing the "trust the meter over Gemini" failure mode and removing redundant uploads.*

**17. DSP-grounded critique prompts** — `[G]` hybrid · med/high
Refactor the FOUR genuinely-Gemini critique tools (`analyze-mix-balance`, `detect-mix-issues`, `mastering-feedback`, `compare-to-reference`) to first run the matching meters and inject them as **ground truth the model reasons FROM, not re-estimates** — generalizing the pattern already in `recommend-mastering-chain`. Extract a shared `_grounding.py` (LUFS-I/S/M, true-peak dBTP per channel, crest/PLR, LRA, 5-band + spectral tilt, L/R correlation, mono-sum loss; both files + deltas for `compare-to-reference`) by lifting `recommend_mastering_chain._measure`; run off-loop via `asyncio.to_thread`; inject under a system line stating the meter facts are exact DSP and must not be re-estimated by ear; reserve perceptual fields strictly for harshness/pumping/sibilance/masking/depth; reorder each `response_schema` so evidence precedes verdict; add a `meters` passthrough. Additive and backward-compatible. (Exclude `find-resonances`/`find-sibilance` — already pure DSP with no prompt to ground.)

**18. Typed, numerically-bounded tool-ready schemas** — `[G]` gemini · med/high
Enrich the four critique schemas to emit tool-ready params — EQ moves as `[{freq_hz, gain_db (min/max), q, type:enum}]`, de-ess as `{center_hz, q, threshold_db, gr_db}`, severities as enums, findings with evidence timestamp + affected band — so output drops straight into `apply-eq` / the new de-esser / `shape-bands` without regex scraping. Keep the OpenAPI-subset `response_schema` path (it already supports min/max/enum). **Critical: bounds are advisory, not API-enforced — pair with a mandatory server-side clamp** on the parsed values before handoff.

**19. Shared audio cache (Files-API reuse)** — `[G]` gemini · med/med
`_upload.py` re-uploads the same audio on every call and deletes it in a `finally` block (verified ~2× redundancy across a multi-tool run). **Tier 1 (lead with this):** a process-level cache keyed on file **content-hash** (not path — renders reuse filenames); in `audio_part`, return the existing `Part.from_uri` on a hit; stop per-tool deletion (one session-scoped cleanup or rely on the 48 h TTL); put the audio Part first in `contents` so free implicit caching fires; catch not-found `APIError` for expired URIs and re-upload; add a small persistent hash→uri sidecar with TTL so CLI subprocesses reuse within 48 h. **Tier 2 (gate it):** explicit `CachedContent` only when audio tokens exceed the model minimum AND ≥3 tools hit the same file (storage cost can erase savings on short runs). Verify via `usage_metadata.cached_content_token_count`. Ref: [docs/caching](https://ai.google.dev/gemini-api/docs/caching).

**20. Region-focused critique** — `[G]` gemini · med/med
To make Gemini focus on a problem region (e.g., the chorus where it pumps), have `stemmy-loops` **trim the region** (~2 s padding for musical context) and send the clip — don't trust prompt-only MM:SS windowing. Snap timestamps using the **DSP onset detector**, not Gemini's hallucination-prone ones, and keep the snap advisory within a tight tolerance (spectral-flux onsets also fire on bass/pad/vocal). Pairs with #17.

**21. Master-assistant orchestration** — `[G]` med · med/high
An intent + intensity + style "listen → recommend chain → render → re-check" flow over the now-complete typed DSP. **Sequenced last — it gates on #9, #11, #16, and #18 all landing.** Concept: [Ozone 11 Master Assistant](https://docs.izotope.com/ozone11/en/master-assistant/index.html), [LANDR — what is AI mastering](https://www.landr.com/what-is-ai-mastering-and-how-does-it-work).

---

## Stale defaults to fix

- **`check-streaming-targets`** lacks the asymmetric attenuate-only vs boost-and-attenuate playback model (→ #8).
- **No thinking config anywhere in `[G]`** (→ #4); and the default model is a **preview** SKU applied to *all* tools including cheap classify/tag — route low-stakes tools to a Flash variant and track when the stable Gemini-3 SKU ships.
- **Critique schemas** use the bare OpenAPI subset with no numeric bounds/enums (→ #18).
- **`_upload.py`** has no client-side cache (→ #19).
- **`apply-eq`** has no phase mode and **`render-mastered`** has no EQ stage (→ #10).
- **`adjust-stereo`** bass-mono is a single fixed hard high-pass of the Side (→ #7).
- **`measure-distortion`** returns one global number validated only on sine tones; for program material the actionable version is a **loudness-matched pre/post-limiter residual** (`render-mastered` already holds both buffers in memory), not a per-band single-file THD.
- **Loudness-match gain math** is duplicated in ≥3 places (→ #2).

---

## Explicitly rejected
*Recorded so they're not re-proposed. Each was killed by adversarial verification.*

- **Aesthetic scorer (Audiobox PQ/CE)** — the front end is 16 kHz mono and independently shown fidelity-insensitive; it's a learned model, not a meter, conflicting with the trust-the-meter policy. At most expose the PC sub-score experimentally on `[G]`. Refs: [audiobox-aesthetics](https://github.com/facebookresearch/audiobox-aesthetics), [arXiv 2502.05139](https://arxiv.org/html/2502.05139v1).
- **Per-band single-file THD** — THD needs a *known stimulus*; on program material it measures musical richness, not distortion. Build the loudness-matched pre/post-limiter residual instead.
- **DSP-validated EQ guardrail (as specced)** — no Gemini tool emits clampable numeric EQ today; only renderer-side `Field` validation (#3) survives. A tilt-target version would suppress correct de-harsh cuts.
- **ViSQOL leg of a perceptual-distance A/B** — wrong algorithm for a *foreign* reference; valid only for self-referential export-fidelity QC. Ref: [google/visqol](https://github.com/google/visqol).

---

## Risks & unknowns

- **Gemini non-determinism + parroting** — even with injected meters, by-ear judgments vary run-to-run and the model may repeat injected numbers as if "heard." Label meter facts as ground-truth-do-not-re-estimate; reserve perceptual fields for what meters can't see; never let Gemini drive loudness/peak/stereo amounts.
- **Advisory schema bounds** — Gemini does not enforce min/max; typed schemas (#18) **must** be paired with a server-side clamp before any value reaches a renderer.
- **Time-varying DSP artifacts** (#15/#16) — musical noise/birdies, pre-echo, drum-attack smear, stereo-image wander. These are the hard part and need listening-based tuning beyond unit tests; results are soothe-/Gullfoss-STYLE, not knob-for-knob parity.
- **Platform-normalization taxonomy** is web-disputed and policy-drifts — encode it as a dated, source-cited, editable table, not hard facts. The boost-overshoot sub-claim is conditional (Spotify Loud mode / naive normalizers) and should be gated, not headlined.
- **ML-dependent stretch items** pull `torch` + first-run weight downloads, breaking `stemmy-loops`' no-network/numpy-scipy charter — host on `[G]` or behind an explicit opt-in extra.
- **Cache ROI is ~2×**, not 4–7× — gate explicit caching to long multi-tool runs; key on content-hash (renders reuse filenames). The headless CLI may spawn fresh subprocesses, so the cache needs a persistent TTL-bounded sidecar to span runs.
- **Sequencing** — don't wire to capabilities that don't exist yet. `render-mastered` only consumes `target_lufs` + `ceiling_dbtp`; tilt/width need separate `apply-eq` / `adjust-stereo` calls. #21 (master-assistant) gates on the typed DSP from earlier phases.

---

## Suggested sequencing

1. **Phase 0** unblocks everything (de-esser closes the find→apply chain; loudness-match + validation are prerequisites for clean automation downstream).
2. **Phase 1** builds the shared DSP substrates (LR4 split, FIR builder, spectral smoothing) once and reuses them.
3. **Phase 2** layers the time-varying processors on those substrates (highest artifact risk → last among DSP).
4. **Phase 3** wires Gemini to the now-complete, typed, validated DSP so the whole chain is machine-validated and meter-grounded end to end.

---

*Generated from a verified web-research pass (8 angles → consolidate → adversarial feasibility verify → synthesize). Citations were checked live; dead vendor URLs surfaced during research (a FabFilter EQ-match page, several iZotope doc pages, a SoundOnSound AI-mastering article) were replaced with the live equivalents linked above.*
