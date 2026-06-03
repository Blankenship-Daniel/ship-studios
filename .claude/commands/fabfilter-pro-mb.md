---
description: Drive FabFilter Pro-MB (measured) — 6-band multiband dynamics (comp/expand, up/down), dynamic-EQ/de-ess/glue, M-S, headless, no-iLok.
argument-hint: <audio.wav> [goal: de-harsh|de-ess|multiband-glue|tame-mud|tame-boom|add-presence|tighten|m-s|parallel]
---

Invoke the **fabfilter-pro-mb** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the goal (dynamic de-harsh / de-ess / multiband bus glue / tame mud /
tame boom / add presence-air / tighten tails / mid-side dynamics / parallel multiband). The skill applies
**FabFilter Pro-MB** (`/Library/Audio/Plug-Ins/VST3/FabFilter Pro-MB.vst3`) — a **6-band multiband dynamics**
processor doing **compression AND expansion, downward AND upward**, on dynamic crossover bands, each with its own
side-chain (Band/Free, internal/external) and Mid/Side, in Dynamic/Minimum/Linear phase. It **measures
spectrum/tilt/centroid/crest before & after** (confirming the targeted band moved while the others stayed flat —
band-split) and A/Bs loudness-matched.

**Governing facts (measured):** **renders headless AND no-iLok** (clean render candidate) — use the **VST3** path
(an AU twin is also installed). **A bare load is a TRUE passthrough** (all 6 bands default `Unused`; 0.00 dB vs
input) — so **do NOT flatten** (the opposite of Pro-Q 4). **RANGE is the master "amount" knob — set it NONZERO or
the band is inert**: measured, a band Enabled with threshold −35 / ratio 4:1 but `range=0` rendered bit-for-bit
identical to dry. The **four quadrants** = `dynamics_mode` (Compression/Expansion) × sign of `range`: Comp−range =
duck loud (de-harsh/glue), Comp+range = upward comp (density), Expansion+range = **upward expansion** (add
presence/air — measured +5.6 dB, crest up), Expansion−range = downward expansion/gate (acts *below* threshold — set
it ABOVE the quiet parts). **All 156 params are enums → `apply-vst-chain`'s float dict can't drive it** (it
returned `changed:false` — can't enable a band or set `band_N_state`/`dynamics_mode`/`ratio`/slopes/`processing_mode`
string enums). Use the **[[vst-preset]]** harness (`apply_vst_preset.py`, `setattr`). attack/release are exposed
**normalized 0–100** (not ms); global `mix` 0–200 % = parallel. **Linear Phase pre-rings transients** → Dynamic
Phase (default) / Minimum for drums. Needs `uv sync --extra vst`.

Ready examples: `presets/vst/fabfilter-promb-drum-deharsh.json` (1 band 3–9 kHz Comp range −9 → measured 5 kHz
−4.7 dB, 4 kHz −4.0 while 1 kHz −0.05 & lows untouched — surgical band-split) · `presets/vst/fabfilter-promb-drum-multiband-glue.json`
(3 bands: lows + low-mid + presence). Full param surface + numbers:
[`docs/vst/fabfilter-pro-mb.md`](../../docs/vst/fabfilter-pro-mb.md).
Pure-DSP alternatives (no plugin): [[multiband-compress]] · [[dynamic-eq]] · [[de-harsh]] · [[de-ess]] · [[excite]].
Sibling FabFilter EQ (no band-split): [[fabfilter-pro-q-4]]. Defer to the skill; report the bands/quadrant/phase,
before→after tilt/centroid/target-band deltas + crest (and that the other bands stayed flat), and the preset/`.state` path.
