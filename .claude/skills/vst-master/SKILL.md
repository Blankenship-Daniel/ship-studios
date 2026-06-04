---
name: vst-master
description: "Use when the user wants to master a mix with their own plugins instead of the pure-DSP chain — 'master this with FabFilter/Ozone', 'plugin mastering chain', 'master using my Pro-L limiter', 'EQ+comp+limit this with my plugins'. Builds a measured plugin mastering chain (EQ → comp/MB → limiter) and verifies streaming compliance. The opt-in VST sibling of master-track. Stemmy MCP, the `vst` extra (streaming compliance is pure DSP — no key; GEMINI_API_KEY only for the optional perceptual read)."
argument-hint: <mix.wav> [--platform spotify] [target LUFS]
---

# vst-master — master a mix with your own plugins

Goal: take a near-final stereo mix to a platform-ready master using a **chain of headless-safe
plugins** (EQ → comp / multiband → limiter), measured at every step and checked against streaming
targets. This is the **opt-in VST alternative** to the deterministic pure-DSP `[[master-track]]` —
reach here when the user specifically wants their own mastering plugins.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). `[G] check-streaming-targets`
  is **pure DSP — no key**; only the optional `[G] mastering-feedback` (step 2) needs
  `GEMINI_API_KEY`. Input = a clean **stereo mix bus** (run `[[mix-check]]`/`[[finalize-mix]]`
  first if needed).
- Candidates ([`docs/vst/README.md`](../../../docs/vst/README.md)): EQ `FabFilter Pro-Q 4` /
  `Maag EQ4`; comp `FabFilter Pro-C 2` / `SSL Native Bus Compressor 2`; limiter `FabFilter Pro-L 2`
  / `Brickwall Limiter`. (**All Ozone 11 modules are DAW-only here** — Maximizer / Imager / Match EQ
  are iLok-blocked headless, and even the `Ozone 11 Equalizer` loads but its EQ is **inert offline**
  [only its output gain responds], so prefer FabFilter/SSL for the EQ + comp + limiter → [[izotope]] /
  [[ozone-11-maximizer]].)

## Recipe

1. **Baseline** — `[L] measure-loudness` (LUFS-I/TP/PLR/LRA) + `[L] measure-spectrum` +
   `[L] measure-stereo` + `[L] check-clipping`. Decide `target_lufs`/`ceiling_dbtp` (see
   `projects/<track>/track.md`; e.g. ~-14 LUFS / -1 dBTP, or -2 dBTP for peaky material).
2. **Perceptual read (optional)** — `[G] mastering-feedback` for tonal/loudness guidance.
3. **Build the chain** — confirm each path via `[L] list-vst-plugins`, then ONE
   `[L] apply-vst-chain {path, out_path:"projects/<track>/masters/<track>_vstmaster.wav",
   plugins:[ EQ, comp/MB, limiter ], dump_state:true}` in signal order. The **limiter sets the
   ceiling** — set its output ceiling to `ceiling_dbtp`.
4. **Verify** — `[L] measure-loudness` + `[L] check-clipping` on the master; then
   `[G] check-streaming-targets` (Spotify/Apple/YouTube…). Confirm `changed:true`, no true-peak
   overshoot, and compliance. Re-render (adjust limiter) if a platform will attenuate.
5. Hand off to `[[delivery-qc]]` / `[L] export-deliverables` for the format matrix + tags.

## Outputs

- `projects/<track>/masters/<track>_vstmaster.wav` + per-plugin `.state` blobs (reproducible chain).

## Reporting to the user

- The chain (EQ/comp/limiter + key settings), before→after LUFS-I/TP/PLR/LRA, streaming-compliance
  table, the `.state` paths. State plainly it's a non-deterministic plugin master (vs pure-DSP).

## Pitfalls

- **Verify each stage renders + use `uaudio_*`.** Loads ≠ renders — confirm every stage moves the
  *detail* (a 0.00 change = passthrough → run `[[vst-verify]]`). If a stage needs gain-staging or
  enum/bool params (e.g. a tube/tape master unit), drive it via `[[vst-preset]]` — `apply-vst-chain`
  can't. For any UADx unit use the `uaudio_*.vst3` build (the `UAD ….component` twins passthrough).

- **Non-deterministic & opt-in** — a plugin master won't reproduce across plugin updates; keep the
  `.state` blobs. For a deterministic, dependency-free master use `[[master-track]]`.
- **True-peak overshoot** — verify dBTP after the limiter; inter-sample peaks can exceed sample peaks.
- **Demo-mode** — an unlicensed mastering plugin can pass silent/limited; re-measure (step 4) and flag.
- Don't master a broken mix — fix with `[[mix-check]]` first.

## Fan-out

The **baseline (step 1: `measure-loudness` / `measure-spectrum` / `measure-stereo` /
`check-clipping`) and the post-render verify (step 4) are independent reads** —
issue each cluster as concurrent Agent calls. The chain build (step 3, one
`apply-vst-chain`) is a single serial UADx render — do **not** run concurrent VST
renders (UADx hosts contend → non-deterministic output).

## Related

- `[[master-track]]` (pure-DSP default) · `[[finalize-mix]]` (glue before this) · `[[delivery-qc]]` / `[[batch-master]]`
- `[[vst-chain]]` (backbone) · `[[vst]]` — index/doctrine
