---
name: vst-browse
description: "Use when the user wants to see what plugins they can use here — 'what VST plugins do I have', 'list my installed plugins', 'find a compressor/reverb plugin I own', 'which plugins load headless', 'is <plugin> usable in the pipeline', 'show my EQ plugins'. Read-only discovery over installed VST3/AU plugins, filtered to the headless-safe inventory and grouped by task. Stemmy MCP, the `vst` extra."
argument-hint: [search term, e.g. "comp" or a vendor]
---

# vst-browse — discover installed, headless-safe plugins

Goal: answer "what can I actually use?" — search the installed VST3/AU plugins, cross-reference the
**headless-safe** inventory, and present matches grouped by task so the user can pick one to feed a
`[[vst-chain]]` (or any `vst-*`) workflow. Read-only; renders nothing.

## Prerequisites

- `[L] list-vst-plugins` (live scan of the standard plugin dirs; needs no extra). For the
  headless-safe filter, read [`docs/vst/README.md`](../../../docs/vst/README.md) +
  [`demo/headless-safe-titles.txt`](../../../demo/headless-safe-titles.txt) (the 779 that load).

## Recipe

1. **Live scan** — `[L] list-vst-plugins` (optionally `{name_contains}` to narrow, e.g. a vendor or
   "comp"/"verb"/"eq"). Returns name · path · format for everything installed.
2. **Filter to headless-safe** — keep only titles present in
   [`demo/headless-safe-titles.txt`](../../../demo/headless-safe-titles.txt). **That list is a *load*
   probe — loads ≠ renders**; for UADx prefer the `uaudio_*.vst3` build (the `UAD ….component` twins
   passthrough), and re-verify anything recently installed with `[[vst-verify]]`. Flag installed-but-not-listed
   plugins as **blocked** (iLok/UAD/unauthorized) so the user isn't tempted to use them.
3. **Group by task** — bucket the safe matches using the category map in
   [`docs/vst/README.md`](../../../docs/vst/README.md) (EQ, comp, reverb, tape, channel-strip, …).
4. **Confirm it renders** — for any pick (or a recently installed/updated plugin), run `[[vst-verify]]`:
   it pushes a param and proves the plugin processes vs passes through — the definitive check the load
   list can't give.

## Outputs

- A grouped, on-screen list (no files). Each entry: name · format · the `vst-*` skill that uses it.

## Reporting to the user

- Group safe matches by task; show counts. Call out the **blocked** installed plugins separately with
  the one-word reason (iLok / UAD-DSP / unauthorized). Point the user at the matching `vst-*` skill.

## Pitfalls

- **Loads ≠ renders.** The list is a load-probe; a listed title can still passthrough (UAD `.component`,
  unauthorized). Confirm a pick with `[[vst-verify]]`.
- **UAD two builds** — `uaudio_*.vst3` renders; `UAD ….component`/`.vst3` passthrough → always steer to `uaudio_*`.
- **Format dupes** — the same plugin appears as VST3 + AU; prefer the VST3 path. AU is macOS-only.
- Don't suggest a blocked/passthrough plugin to any downstream skill.

## Related

- `[[vst]]` — suite index + doctrine · `[[vst-chain]]` — apply what you found
- the `vst-*` task skills this feeds: `[[vst-eq]]`, `[[vst-compress]]`, `[[vst-reverb]]`, etc.
