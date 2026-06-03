---
description: Drive the Arturia Tape J-37 (Studer J37 valve tape) — DAW-only here; dial + bounce + measure.
argument-hint: <audio.wav | goal> [goal: warm/glue/vintage/dirty/transparent]
---

Invoke the **tape-j-37** skill on `$ARGUMENTS`.

`$1` is the WAV (a bounce to measure) or the goal; the rest hints the goal (warm drum bus / bus glue / vintage /
dirty-FX / transparent). The skill teaches how to dial the Arturia **Tape J-37** — a neural-modeled **Studer J37**
valve tape machine (Abbey Road / *Sgt. Pepper*) — from the recipes + decision table in
[`docs/vst/tape-j-37.md`](../../docs/vst/tape-j-37.md) (default **Color2 · 15 IPS · Vintage · Drive ~12–15 ·
ST Offset off until mono-verified**), then measures the **DAW bounce** (centroid/tilt DOWN = warming; crest a
touch lower = glue; mono correlation for ST Offset) and A/Bs loudness-matched with `[L] render-ab`.

**CRITICAL:** the Tape J-37 **does NOT render in the headless pipeline** on this rig — measured passthrough
(1 kHz sine @ drive 50 / Color4 → 0.00 % THD; `output_level_db=−24` → no change; drive 0 ≡ drive 40 ≡ Bypassed,
bit-for-bit; Arturia ASC licensing self-bypasses headless). So **never** run it through `apply-vst-chain` / the
`[[vst-preset]]` harness as a tape stage (there is deliberately no `presets/vst/tape-j-37-*.json`). Workflow is:
dial it **in the DAW** → print/bounce to WAV → drop into `projects/<track>/` → measure / loop / master. For a tape
stage **inside** the pipeline use the headless substitutes: [[studer-a800]] (punchy), [[ampex-atr-102]] (glossy
2-bus), IK `Tape Machine 80/440`, or pure-DSP `[L] saturate-loop`. It's a **Studer**, not an Ampex.

Defer to the skill; report the constraint up front, the DAW settings, and the bounce's before→after
centroid/tilt/crest/mono with an honest loudness-matched A/B.
