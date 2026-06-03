---
name: drum-prep
description: Use when the user has a folder of individual multi-mic drum stems (overheads, snare top/bottom, kick in/beater, hi-hat, toms, room) and wants them prepped — "phase-align my drum kit", "prep these drum stems", "align the drums to the overheads and match them to this reference", "tighten up my multi-mic drums". Runs the local drum-prep CLI: detect roles → phase-align to the overheads → per-stem reference-match EQ → loudness-matched A/B auditions. Local DSP, NOT the stemmy MCP servers.
argument-hint: <stems dir> <reference.wav>
---

# Prep a multi-mic drum kit (phase-align → reference-match → audition)

Goal: take a folder of individual drum-mic stems and make them phase-coherent
and tonally matched to a reference, non-destructively, with auditions to check
the result. This is the umbrella over [[drum-phase-align]], [[drum-reference-match]],
and [[drum-audition]] — run the whole chain, or the steps individually for control.

This is **local DSP**, not the MCP servers. It lives in the `drum_prep` package
(numpy/scipy/soundfile/pyloudnorm) and is driven by the `drum-prep` console
script — there are no `stemmy-*` tools involved. It exists because multi-mic
*whole-kit* alignment + per-stem reference EQ is a job neither stemmy server
covers (their `apply-eq` / `render-ab` operate on a single stereo file).

## Prerequisites

- Install the extra once: `uv sync --extra drum-prep` (pulls numpy/scipy/
  soundfile/pyloudnorm). No API keys, no network — pure local DSP.
- A directory of drum-mic stems, all same sample rate. Roles are auto-detected
  from filenames (overhead/room/kick/snare/hi-hat/tom…). Effect returns
  (plate/reverb/send/fx/aux keywords, incl. "snare plate") auto-detect as role
  `fx` and are **excluded from the phase-align topology** — they're not mics, so
  they never become a stray second `snare_top`. If a name is
  ambiguous, commit a `kit.json` to pin it (see `drum_prep/examples/kit.json`).
  **Interface-named dumps** (`A ADAT 1`, `B MIC_LINE_HIZ 1_2`) won't auto-detect —
  run [[multitrack-triage]] first to clean, split songs, and emit a `kit.json`.
- A reference audio file (loop or track) to match the kit's tone to. Keep it
  **outside** the stems folder, or it gets auto-excluded by basename when passed
  as `--reference`.
- Overheads are the fixed timing/tonal anchor. A pre-merged stereo OH is ideal;
  a separate L/R pair is merged automatically (image preserved).

## Recipe (ordered)

1. **Confirm the kit** — `drum-prep detect "<stems dir>"`. Check every stem got
   the right role and the partner wiring (snare-bottom → snare-top, kick-beater
   → kick-in), and that any effect returns landed as role `fx` (excluded from
   alignment), not a phantom second `snare_top`. If anything is off, `drum-prep
   detect "<dir>" --write-manifest "<dir>/kit.json"`, edit it, and re-run.
2. **(Pre-align, optional) Stage the inputs.** If overheads/room arrived as L/R
   pairs, merge them to stereo first with `drum-prep stereo-merge` ([[drum-stereo-merge]]).
   If mic levels are wildly uneven, balance them with `drum-prep normalize`
   ([[drum-normalize]]) — a balance-preserving gain-stage, not a per-stem level
   reset.
3. **Run the chain** — `drum-prep chain "<stems dir>" --reference "<ref>"`.
   This runs phase-align → reference-match → audition, writing into
   `<dir>/phase-aligned/`, `<dir>/ref-matched/`, `<dir>/auditions/`. Pass
   `--out-root <dir>` to send all three elsewhere; `--strength 0..1` to dial the
   tonal match (default 0.75); `--no-strict` to warn instead of fail on
   unknown mics.
4. **Or run the steps** for control: [[drum-phase-align]] → [[drum-reference-match]]
   → [[drum-audition]] (each reads the previous step's output dir).
5. **(Post-match, optional) Bounce to a stereo bus** — `drum-prep mix` ([[drum-mix]])
   sums the prepped kit to a single stereo file, ready to hand to [[master-track]].

## Outputs

- `<dir>/phase-aligned/` — every stem time/polarity aligned to the overheads (24-bit AIFF).
- `<dir>/ref-matched/` — the aligned stems, per-stem EQ'd toward the reference.
- `<dir>/auditions/` — `AB_before-vs-after.wav` and `AB_reference-vs-after.wav`.
- All audio is gitignored; only a committed `kit.json` persists in the repo.

## Reporting to the user

Summarize each stage from the JSON: the per-stem delays + any polarity flips and
the partner-pair validation correlations; the per-stem EQ moves + the 6-band
residual before→after and the tilt move toward the reference; and the audition
file paths with their matched LUFS. Note the global headroom trim. Point the user
at `AB_before-vs-after.wav` to hear the change.

## Pitfalls

- **Keep the reference out of the stems folder** (or pass it via `--reference` so
  it's excluded) — otherwise it's detected as an unknown mic.
- **Overheads are required** — the whole topology is OH-referenced; no OH → it
  fails loud. Provide `overhead` (stereo) or `overhead_l` + `overhead_r`.
- **This does not master or balance.** It's tonal + timing prep on stems; mix
  levels/panning and mastering are downstream ([[master-track]]).
- **Re-running overwrites the output subdirs.** Use `--out-root` to compare runs.
- **Output is 24-bit AIFF with a `.wav` extension.** ffmpeg's container sniffing
  misreads these ("Invalid PCM packet"). Read aligned stems with sox/afconvert, or
  convert first with `.claude/skills/multitrack-triage/scripts/aiff2wav.sh`, before
  any ffmpeg step.
- **`kit.json` file fields need the `.wav` extension** or detect/align fails with
  "manifest references a file that is not in '<dir>'".

## Related

- [[multitrack-triage]] — upstream: cleans a raw/interface-named dump and emits the `kit.json` this consumes
- [[logic-extract]] — further upstream: pulls the raw recordings out of a Logic project
- [[drum-stereo-merge]] · [[drum-normalize]] — pre-align staging: merge L/R pairs to stereo, balance-preserving gain-stage
- [[drum-phase-align]] · [[drum-reference-match]] · [[drum-audition]] — the individual stages
- [[drum-mix]] — post-match: sum the prepped kit to a stereo bus
- [[reference-match]] — the MCP analogue for a finished stereo *mix* (this is per-stem, whole-kit, local DSP)
- [[master-track]] — once the kit is prepped and bounced to a stereo bus
- [[loops-to-deliverables]] — if the goal is loops cut from the prepped kit
