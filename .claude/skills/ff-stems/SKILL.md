---
name: ff-stems
description: "Use when the user wants to run the FabFilter chain (Pro-Q 4 -> Pro-MB -> Pro-C 2 -> Pro-L 2) on each individual drum stem of a multi-mic kit — 'run the FabFilter chain on my drum stems', 'Pro-Q/Pro-MB/Pro-C/Pro-L on each stem', 'channel-finalize my drum mics', 're-run the ff-stems pass'. KIT-AWARE: phase-aligns the kit FIRST, runs phase-safe (Linear Phase, latency-matched) floor-safe per-stem chains, optionally unmasks across stems, and VERIFIES the mics still sum coherently. Local DSP (drum-prep) + the stemmy-loops `vst` extra."
argument-hint: <stems-dir> [duration_s]
---

# ff-stems — kit-aware FabFilter channel-finalize on each drum stem

Goal: run the **FabFilter chain Pro-Q 4 → Pro-MB → Pro-C 2 → Pro-L 2** on *each* mic of a multi-mic drum
kit — corrective EQ → multiband dynamics → compression → true-peak safety ceiling — in a way that **still
sums coherently** when the kit is mixed. A blind per-stem pass tonally improves each mic but silently breaks
the inter-mic **phase/time** relationships (different per-stem latency + phase rotation → comb filtering on
the sum); this skill does it the right way: **align first, phase-safe chains, floor-safe, then verify
coherence.** The per-stem channel stage between [[drum-prep]] (align) and [[mix-balance]] / [[drum-mix]] /
[[warm-drum-bus]] (the bus) → [[master-track]].

**Local DSP + VST.** Phase-align is `drum-prep` (local). The chain runs through the stemmy-loops **`vst` venv**
via [`presets/vst/apply_vst_preset.py`](../../../presets/vst/apply_vst_preset.py) (it sets FabFilter's enum
params, which `apply-vst-chain`'s float-only dict can't). Translator:
[`scripts/mix/build_ff_chain_presets.py`](../../../scripts/mix/build_ff_chain_presets.py); coherence verify:
[`scripts/mix/check_phase_coherence.py`](../../../scripts/mix/check_phase_coherence.py). All FabFilter
plugins here are headless & **no-iLok** (see [[fabfilter-pro-q-4]] / [[fabfilter-pro-mb]] / [[fabfilter-pro-l-2]];
Pro-C 2 is the [[vst-compress]] FabFilter compressor). **Worktree caveat:** the loops `vst` venv lives next to
the **main** checkout, not under `.claude/worktrees/<name>/` — resolve it there and pass the **absolute** venv
path (e.g. `/abs/.../stemmy-loops-mcp/.venv/bin/python`).

## The governing facts (obey)

- **Phase-align FIRST, on full-band raw stems, before any EQ.** Mic delays are physical distances estimated
  from the unprocessed low end; an HPF strips the low end the kick needs to lock onto the overheads, so
  EQ-then-align gives a bogus delay. (Repo doctrine — see [[drum-prep]] / [[drum-phase-align]].)
- **Kit mode = Linear Phase at a FIXED resolution + lookahead off = UNIFORM latency, no phase rotation.**
  A blind per-stem pass (Pro-Q Natural/min-phase, per-stem spectral bands that self-engage linear phase, Pro-MB
  lookahead) gives *different* per-stem latencies AND per-stem phase rotation → the aligned mics drift apart and
  pairs that were in-phase partially CANCEL on the sum (observed: snare-top × overheads went from r=+0.55 to
  **−0.47**). `--mode kit` forces Pro-Q **Linear Phase** at a fixed `processing_resolution` + Pro-MB **Linear
  Phase** + lookahead off + spectral demoted to plain dynamic. A linear-phase EQ's latency at a fixed resolution
  is FFT-fixed and **curve-INDEPENDENT**, so every stem comes out delayed by the **same** amount (impulse-verified:
  all six chains = 2112 samp @ Medium) and linear phase adds **no** rotation → the prior alignment **survives the
  EQ with no per-stem compensation.** (Verify with `latency_check.py`; only a per-stem resolution change would
  break uniformity.)
- **Floor-safe: NO makeup gain anywhere.** Multi-mic drum stems carry continuous bleed/room in the gaps
  between hits; any makeup (Pro-C auto-gain, output trim, or Pro-L drive) lifts that floor. The translator
  forces Pro-C `auto_gain` OFF + unity output and Pro-L `gain` 0. The chain only *ducks/controls* → outputs
  sit **lower** than the inputs; that is correct. Set levels later by measured LUFS at [[mix-balance]].
- **Pro-L is a true-peak SAFETY ceiling, not a maximizer.** `output_peak_dbfs:null` (faithful) lets Pro-L 2
  own the −1.0 dBTP ceiling (True Peak on); never renormalize after a limiter (it pushes true-peak back over).
- **Don't carve same-source mics apart.** Cross-stem unmask on a kit means the **ambient mics (overheads,
  room) yield low/low-mid to the close mics** — NOT carving kick vs sub/crotch (same source; they reinforce).
- **FabFilter mechanics:** a bare Pro-Q load restores the last GUI curve, so the preset **flattens all 24
  bands** and sets every used band explicitly; enum/string params (shapes, slopes, phase mode, ratios) need
  the **harness** (`apply_vst_preset.py`), the float dict can't set them.
- **Verify coherence with the IMPULSE check, not just program-material cross-correlation.** `latency_check.py`
  (impulse-probes each chain's exact latency) is the un-confounded proof the kit stays coherent. A broadband
  cross-correlation (`check_phase_coherence.py`) is confounded by aggressive per-stem EQ — a stem whose shared
  band you gutted reads a changed correlation that is the EQ, NOT a phase defect — so judge it on STRONG
  shared-content pairs only. The `check-clipping` `polarity_inverted` flag is a per-stem mono heuristic; ignore it
  for inter-mic phase. Also measure before/after per stem: not-passthrough, floor-not-lifted, TP ≤ −1, move landed.

## Recipe (ordered)

1. **Roles** — `drum-prep detect <stems-dir>`; confirm/scaffold `<stems-dir>/kit.json`. Pin non-standard mics
   (a between-the-knees weight mic → role `kick_sub` so it low-pass-correlates to the OH); the overheads are
   the stereo reference.
2. **Phase-align FIRST** — `drum-prep phase-align <stems-dir>` → `<stems-dir>/phase-aligned/` (full-band,
   before EQ). This is the kit-aware foundation; do not skip it.
3. **Design per stem (role-aware), on the ALIGNED stems** — `[L] measure-spectrum` (+ `measure-microdynamics`,
   `measure-stereo` for OH/room) per stem and author a plan: kick (tight sub via gentle HPF, de-box, beater
   click), snare-top (HPF kick spill, de-box, crack, dynamic de-harsh), snare-bottom (steep HPF, wire detail,
   tame spit dynamically), overheads (HPF so close mics own lows, de-box, air shelf, dynamic de-harsh, keep
   width), room (HPF, de-mud, gentle glue — don't lift the bleed). Emit `plans.json` (array; schema in
   `build_ff_chain_presets.py`). Fan this out one-agent-per-stem for breadth (optional; direct measurement
   works too).
4. **Cross-stem unmask (recommended)** — `[L] detect-masking <aligned stems>` (pure DSP, no key) to score the
   collisions. Add COMPLEMENTARY cuts to the LOSER — in practice the ambient mics (OH/room) ceding low/low-mid
   to the close mics — into an `unmask.json` `{stem:[bands]}`. (Perceptual cross-check: `[G] analyze-stem-masking`,
   needs `GEMINI_API_KEY`.) Do NOT carve same-source close mics.
5. **Build presets (KIT mode)** — `python scripts/mix/build_ff_chain_presets.py plans.json <chains_dir> --mode
   kit --unmask unmask.json`. Kit mode = phase-safe (above). `--mode single` only for one stereo source.
6. **Render serially on the ALIGNED stems** — per stem:
   `<abs-loops-vst-venv>/bin/python presets/vst/apply_vst_preset.py <chains_dir>/<stem>.json
   <stems-dir>/phase-aligned/<stem>.wav <out>/<stem>_ffchain.wav`. ONE at a time — VST renders are
   lock-serialized; parallel only adds overhead. Validate at a short `duration_s` first if iterating.
7. **Verify** — (a) `python scripts/mix/latency_check.py <chains_dir>` → every chain reports the SAME latency
   (impulse-probed; ~2112 samp @ Medium) ⇒ the kit stays coherent, no compensation needed. (b) `python
   scripts/mix/check_phase_coherence.py <stems-dir>/phase-aligned <out> --suffix _ffchain` → STRONG
   shared-content pairs preserved (read the caveat above — gutted-overlap pairs and weak pairs are noise/EQ, not
   phase). (c) `[L] measure-loudness` + `[L] measure-spectrum` per stem: not passthrough, **out LUFS ≤ in**
   (floor not lifted), true-peak ≤ −1 dBTP, the planned moves landed.
8. **Hand off** — these are channel-finalized stems, NOT a mix. Balance by measured LUFS ([[mix-balance]] /
   [[drum-mix]]), optional bus glue ([[warm-drum-bus]]), then [[master-track]]. QC with [[delivery-qc]].

## Outputs

- Phase-aligned source stems in `<stems-dir>/phase-aligned/`.
- Per-stem preset JSONs in `<chains_dir>` (reproducible — re-render any time) + `unmask.json`.
- Channel-finalized stems `<out>/<stem>_ffchain.wav` (e.g. `projects/<track>/mix/`).

## Reporting to the user

Per-stem before→after table (LUFS / true-peak / crest / tilt / centroid) + what each stem got and why; the
`check_phase_coherence.py` verdict (inter-mic pairs preserved); and a plain statement that outputs sit lower
by design (no makeup) and get re-leveled at [[mix-balance]]. Flag any pair that degraded.

## Pitfalls

- **Skipping the align (step 2) = an incoherent sum.** This is the #1 failure; per-stem chains alter phase,
  so without a prior alignment (and kit mode to preserve it) the mics comb-filter when summed.
- **Min/Natural phase or per-stem spectral/lookahead** = different per-stem latencies + phase rotation → comb
  filtering on the sum. Kit mode prevents it (Linear Phase at a fixed resolution = uniform, curve-independent
  latency); `latency_check.py` proves the chains are latency-matched. Only a NON-uniform latency (e.g. you set a
  different resolution per stem) needs fixing — `latency_check.py --processed <dir> --write` advances each stem by
  its exact excess latency (a pure time-shift commutes with linear-phase EQ). Do NOT "compensate" by estimating
  latency from program material — it is too noisy (±tens of samples) and will ADD drift.
- **The broadband cross-correlation is confounded by aggressive per-stem EQ.** A stem whose shared band you gutted
  (e.g. a snare-bottom HPF'd to wires) reads a changed/flipped correlation vs another mic even though both are
  sample-locked + linear-phase — that's the EQ, not a phase bug. The impulse `latency_check.py` is the clean proof.
- **Linear-phase pre-ring** softens transient attacks (the cost of phase-safety on drums) — Medium resolution
  keeps it modest; use `--mode single` for a lone stereo source where min-phase is better.
- **Bleed floor** — never add makeup or drive Pro-L; outputs are meant to be quiet (balance comes later).
- **AIFF-as-`.wav`** — drum-prep can emit 24-bit AIFF under a `.wav` name; read real format with `soundfile`
  (the harness does) and don't feed such files to ffmpeg blind (see [[format-fix]]).
- **Hiss is not hum — Pro-Q can't denoise broadband HF.** For hiss, measure each stem's HF energy
  **rolloff** and place a **steep High Cut there** (slopes to 96 dB/oct / Brickwall): ambient/room mics
  often have **no useful content above ~6 kHz**, so a ~7 kHz high-cut deletes their hiss at zero cost (the
  single biggest hiss win). Gate residual hiss **between hits** with a **Pro-MB HF band in Expansion** mode
  **on CLOSE mics only** — never on overheads/room (it chops cymbal/reverb decay). De-harsh ringing/sizzle
  with **dynamic bells** (auto-threshold, cut-only-when-it-rings); Pro-Q's **Spectral Dynamics is demoted to
  a plain dynamic bell in kit mode**, so use [[de-harsh]] for broadband harshness on a kit. Watch
  **HF-boost stacking** — a per-stem air shelf + a console/tube HF boost + a bus air shelf all *multiply* the
  noise floor; the cure is to remove a boost, not add a cut.

## Fan-out

The **per-stem design (step 3) is the parallel win** — each stem's measure → role-aware plan is independent,
so fan it out one agent per stem (parallel reads). The **render (step 6) is serial** — VST renders hold a
process-global lock and load only on the main thread, so concurrent renders are non-deterministic; run one at
a time. Coherence verify (step 7) is one pass over the kit.

## Related

- [[drum-prep]] / [[drum-phase-align]] — align the kit first (the foundation) · [[stem-process]] — the
  pure-DSP/console per-stem cousin (this one is the FabFilter chain + phase-coherence guarantee)
- [[drum-stems-character]] — the **align-AFTER** variant: when per-stem chains have *varying* latency (different
  UADx character per stem) you can't preserve a prior alignment, so re-align the processed stems instead (ff-stems
  aligns FIRST because its linear-phase chains are uniform-latency) · [[stem-master]] / [[unmask-stems]] — sibling
  per-stem stages that now carry the same align-first + zero-phase coherence rule
- [[fabfilter-pro-q-4]] / [[fabfilter-pro-mb]] / [[fabfilter-pro-l-2]] / [[vst-compress]] — the four plugins,
  measured · [[vst-chain]] — the generic headless chain · [[vst-preset]] — the harness for enum/gain params
- [[unmask-stems]] — cross-stem complementary carving · [[mix-balance]] / [[drum-mix]] / [[warm-drum-bus]] —
  balance + bus from the finalized stems · [[master-track]] — master the bus · [[delivery-qc]] — pre-ship QC
- Scripts: `scripts/mix/build_ff_chain_presets.py` (plan→preset), `presets/vst/apply_vst_preset.py` (apply),
  `scripts/mix/latency_check.py` (impulse latency-match proof), `scripts/mix/check_phase_coherence.py` (inter-mic verify)
