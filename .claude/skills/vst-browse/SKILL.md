---
name: vst-browse
description: "Use when the user wants to see what plugins they can use here — 'what VST plugins do I have', 'list my installed plugins', 'find a compressor/reverb plugin I own', 'which plugins load headless', 'is <plugin> usable in the pipeline', 'show my EQ plugins'. Read-only discovery over installed VST3/AU plugins, filtered to the headless-safe inventory and grouped by task. Stemmy MCP, the `vst` extra."
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
   [`demo/headless-safe-titles.txt`](../../../demo/headless-safe-titles.txt). Flag anything installed
   but *not* in that list as **blocked** (iLok/UAD/unauthorized — won't render unattended) so the
   user isn't tempted to use it.
3. **Group by task** — bucket the safe matches using the category map in
   [`docs/vst/README.md`](../../../docs/vst/README.md) (EQ, comp, reverb, tape, channel-strip, …).
4. Optionally **probe** a specific title's loadability live by handing it to `[[vst-chain]]` on a
   short test WAV (the definitive check if the snapshot is stale).

## Outputs

- A grouped, on-screen list (no files). Each entry: name · format · the `vst-*` skill that uses it.

## Reporting to the user

- Group safe matches by task; show counts. Call out the **blocked** installed plugins separately with
  the one-word reason (iLok / UAD-DSP / unauthorized). Point the user at the matching `vst-*` skill.

## Pitfalls

- **Snapshot drift** — `demo/headless-safe-titles.txt` is a point-in-time load-probe. If the user
  just installed/authorized something, re-probe live (step 4) rather than trusting the snapshot.
- **Format dupes** — the same plugin appears as VST3 + AU; prefer the VST3 path. AU is macOS-only.
- Don't suggest a blocked plugin to any downstream skill.

## Related

- `[[vst]]` — suite index + doctrine · `[[vst-chain]]` — apply what you found
- the `vst-*` task skills this feeds: `[[vst-eq]]`, `[[vst-compress]]`, `[[vst-reverb]]`, etc.
