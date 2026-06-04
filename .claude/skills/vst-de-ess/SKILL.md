---
name: vst-de-ess
description: "Use when the user wants to tame sibilance / harsh 'ess' on a vocal or bright track via their own plugin — 'de-ess this vocal', 'the s's are harsh', 'tame the sibilance', 'too much ess on the lead', 'de-ess the cymbals'. Pairs the pure-DSP find-sibilance measure to set the band/threshold, then applies a headless-safe de-esser (FabFilter Pro-DS, SSL DeEss, Lindell 902). Stemmy MCP, the `vst` extra (find-sibilance needs no key)."
argument-hint: <vocal.wav>
---

# vst-de-ess — tame sibilance with your own de-esser

Goal: reduce harsh sibilance ("ess"/"sh") on vocals or bright sources via a real de-esser, with the
band and threshold **grounded by `[G] find-sibilance`** rather than guessed. A task preset of
`[[vst-chain]]`. (Pure-DSP alternative: `[L] de-ess`.)

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst`). `[G] find-sibilance` is **pure
  DSP — no `GEMINI_API_KEY`** (gemini server, no model call). Candidates
  ([`docs/vst/README.md`](../../../docs/vst/README.md)):
  `FabFilter Pro-DS`, `SSL DeEss`, `Lindell 902 De-esser`, `De Esser`,
  `RX 10 De-ess` (iZotope — spectral de-ess, renders & engages headless → [[rx-10-de-ess]]).

## Recipe

1. **Baseline** — `[L] measure-spectrum` (see the 5–9 kHz region) + `[L] measure-loudness`.
2. **Locate the sibilance** — `[G] find-sibilance` → center Hz, Q, threshold, target GR. This sets the
   de-esser's band + threshold so you're cutting the actual offending frequency.
3. **Pick the de-esser** — split-band (Pro-DS) is the most transparent; confirm path via `[L] list-vst-plugins`.
4. **Apply** — `[L] apply-vst-chain {path, out_path:"projects/<track>/mix/<stem>_deess.wav",
   plugins:[{plugin_path, parameters?}], dump_state:true}` with the band/threshold from step 2.
5. **Verify** — re-`measure-spectrum`; confirm the sibilant band came down without dulling the whole
   top, and `changed:true`.

## Outputs

- `projects/<track>/mix/<stem>_deess.wav` (+ `.state`).

## Reporting to the user

- The de-esser + band/threshold/GR (from find-sibilance), before→after high-band level, `.state` path.

## Pitfalls

- **Verify it renders + use `uaudio_*`.** Loads ≠ renders — confirm the sibilant band actually came down
  (a 0.00 high-band change = passthrough → run `[[vst-verify]]`). For any UADx de-esser use the
  `uaudio_*.vst3` build, not the `UAD ….component` twin. Enum/bool params need `[[vst-preset]]`, not
  `apply-vst-chain`'s float dict.

- **Over-de-essing lisps the vocal** — aim for a few dB of GR on the peaks only; verify by ear/spectrum.
- **Wrong band dulls everything** — use `[G] find-sibilance`, don't guess a generic 6 kHz.
- Thin plugin category — if none of the safe de-essers fit, `[L] de-ess` (pure DSP) is always available.

## Related

- `[[vst-chain]]` · `[L] de-ess` (pure-DSP) · `[[mix-check]]` (flags sibilance) · `[[vst]]` — index/doctrine
