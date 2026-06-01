---
name: vst-master
description: "Use when the user wants to master a mix with their own plugins instead of the pure-DSP chain — 'master this with FabFilter/Ozone', 'plugin mastering chain', 'master using my Pro-L limiter', 'EQ+comp+limit this with my plugins'. Builds a measured plugin mastering chain (EQ → comp/MB → limiter) and verifies streaming compliance. The opt-in VST sibling of master-track. Stemmy MCP, the `vst` extra (+ GEMINI_API_KEY for compliance)."
---

# vst-master — master a mix with your own plugins

Goal: take a near-final stereo mix to a platform-ready master using a **chain of headless-safe
plugins** (EQ → comp / multiband → limiter), measured at every step and checked against streaming
targets. This is the **opt-in VST alternative** to the deterministic pure-DSP `[[master-track]]` —
reach here when the user specifically wants their own mastering plugins.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`); `[G] check-streaming-targets`
  + `[G] mastering-feedback` need `GEMINI_API_KEY`. Input = a clean **stereo mix bus** (run
  `[[mix-check]]`/`[[finalize-mix]]` first if needed).
- Candidates ([`docs/vst/README.md`](../../../docs/vst/README.md)): EQ `FabFilter Pro-Q 4` /
  `Maag EQ4`; comp `FabFilter Pro-C 2` / `SSL Native Bus Compressor 2`; limiter `FabFilter Pro-L 2`
  / `Brickwall Limiter`. (The clean `Ozone 11 …` VST3s are blocked here — prefer FabFilter/SSL.)

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

- **Non-deterministic & opt-in** — a plugin master won't reproduce across plugin updates; keep the
  `.state` blobs. For a deterministic, dependency-free master use `[[master-track]]`.
- **True-peak overshoot** — verify dBTP after the limiter; inter-sample peaks can exceed sample peaks.
- **Demo-mode** — an unlicensed mastering plugin can pass silent/limited; re-measure (step 4) and flag.
- Don't master a broken mix — fix with `[[mix-check]]` first.

## Related

- `[[master-track]]` (pure-DSP default) · `[[finalize-mix]]` (glue before this) · `[[delivery-qc]]` / `[[batch-master]]`
- `[[vst-chain]]` (backbone) · `[[vst]]` — index/doctrine
