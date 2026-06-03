---
description: Dial the KIT Plugins BB A5 (Blackbird API Legacy console strip) for punchy/forward tone — measured.
argument-hint: <audio.wav> [goal: punchy-bus/clean-eq/smash]
---

Invoke the **kit-bb-a5** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (punchy/forward bus / clean console EQ / aggressive smash). The skill
adds console color via **Mic Mode + `pre_amp_gain`** (the colored/driven path — **Line is the *clean* path**),
tightens with `high_pass_filter`, and shapes with one of three API EQ modules — **55A** (550A 3-band), **55L**
(550L 4-band), **56L** (560L 10-band graphic) — using weight (+@100 bell) + **de-box** (−@300–500) + a small
air shelf, **keeping the top modest** (proportional-Q sharpens big 2–5 kHz boosts into brittle peaks; 5 kHz
sits in 55L hi-mid + the 56L — don't stack). Applies via the [[vst-preset]] harness (`KIT BB A5.vst3`, string
enums honored, `dump_state`) and **measures crest/centroid/tilt before & after** (forward, not just louder).
Decision table + the full 46-param surface: [`docs/vst/kit-bb-a5.md`](../../docs/vst/kit-bb-a5.md). Needs
`uv sync --extra vst`.

Key measured facts: **MSTR BUSS is the *clean* mode here** (defeats the channel grit) — off for grit, on for a
transparent EQ pass. Color ranks **Mic+gain (even+odd) > hot `input_trim`/fader-up (3rd, level-driven) >
Line/output_trim/MSTR-BUSS (clean)**. It's the **forward/punchy American-console** counterpart to
[[studer-a800]] (warm) and a sibling of [[api-vision-channel-strip]] (UAD API). **iLok/PACE** — verified-headless
on this rig; screen with `probe_plugin.py "KIT BB A5"` and never run an unlicensed/trial instance unattended.
Ready preset: `presets/vst/blackbird-a5-drums.json`. Defer to the skill; report Mic/Line + module + moves,
before→after crest/centroid/tilt, and the preset/`.state` path.
