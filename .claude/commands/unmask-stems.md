---
description: Resolve frequency collisions between stems — score masking, cut the losing stem, re-score to prove it.
argument-hint: <stems-dir-or-map>
---

Invoke the **unmask-stems** skill on `$ARGUMENTS`.

`$1` is the folder/map of named stems. The skill runs `analyze-stem-masking` to rank collisions, applies complementary `apply-eq` cuts to the losing stem of each (one call per stem), then re-scores with `analyze-stem-masking` + `measure-spectrum` to prove the overlap shrank. Pure DSP, no key. Corrective only — no summing/mastering. Defer to the skill; report the before→after overlap table.
