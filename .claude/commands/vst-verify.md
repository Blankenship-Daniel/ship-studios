---
description: Probe whether a plugin actually RENDERS headless (responds to params) vs just loads/passthrough.
argument-hint: <plugin.vst3 | basename | "/abs/path"> [more…]
---

Invoke the **vst-verify** skill on `$ARGUMENTS`.

`$ARGUMENTS` are plugin paths/basenames to test. The skill runs `presets/vst/probe_plugin.py` (via the stemmy-loops `vst` venv): renders a loud burst at default and with one param pushed, and reports `RENDERS ✓` (responds) vs `PASSTHROUGH ✗ (ignores params)`. Catches the UADx trap — `uaudio_*.vst3` renders, `UAD ….component` twins passthrough — and the load≠render gap in [`demo/headless-safe-titles.txt`](../../demo/headless-safe-titles.txt). Defer to the skill; report the verdict + the working alternative when one is passthrough.
