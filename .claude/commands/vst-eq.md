---
description: EQ a stem/bus with your own EQ plugin (Pultec/Maag/Neve/Pro-Q), measured tilt before/after.
argument-hint: <audio.wav> [eq/intent]
---

Invoke the **vst-eq** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the EQ/character. The skill measures spectrum/tilt, optionally pulls targets from `[G] find-resonances`, picks a headless-safe EQ (`FabFilter Pro-Q 4`, `Maag EQ4`, `UAD Pultec/Neve` — see [`docs/vst/README.md`](../../docs/vst/README.md)), applies it via `[L] apply-vst-chain {…, dump_state:true}`, and re-measures. Needs `uv sync --extra vst`. For transparent reference-matching use `[L] match-eq` instead. Defer to the skill; report tilt/band deltas + `.state` path.
