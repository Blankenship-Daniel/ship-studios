---
description: Drive the UADx Pultec HLF-3C passive filter (measured) — clean high-pass / low-pass band-limiting, headless. Pure filter, no tone/color.
argument-hint: <audio.wav> [goal: low-cut|high-cut|band-limit|lofi|tame-top|rumble]
---

Invoke the **pultec-hlf-3c** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the goal (clean rumble low-cut · tame harsh top high-cut · musical band-limit ·
lo-fi/telephone · vintage air trim). The skill drives the **UADx Pultec HLF-3C EQ** (`/Library/Audio/Plug-Ins/VST3/
uaudio_pultec_hlf-3c.vst3`) — UA's model of the Pultec/Pulse Techniques **HLF-3C passive FILTER set**: a stepped
**LOW CUT-OFF** (high-pass, 50–2000 CPS) + **HIGH CUT-OFF** (low-pass, 1.5–15 KCS). It **measures spectrum/tilt/
centroid/crest before & after** and proves the move.

**Governing facts (measured, Pedalboard 0.9.23):** **renders headless via the `uaudio_` build** (UADx native, iLok
account / no dongle) — NOT the `UAD …`/`/Universal Audio/` passthrough twins. **⚠️ The standard `probe_plugin.py`
FALSE-flags it as passthrough** — it has no gain param, so the probe pushes `low_cut` to its first enum `'Off'` (=
default) → Off-vs-Off → Δ0; it DOES render (verify with a *real* value, e.g. `low_cut='500 CPS'` → −59 dB @50 Hz).
**It is a PURE PASSIVE FILTER** — only **4 params** (`low_cut`, `high_cut`, `enable`, `master_bypass`), **no boost/Q/
gain**, **0.000 % THD**: it *subtracts* frequencies and cannot warm/thicken/brighten/excite (color elsewhere —
`saturate-loop`/[[excite]]/[[helios-type-69]]/tape). **Slopes (measured):** low-cut ~**18 dB/oct**, label ≈ the −4 dB
point (true −3 dB ~6–12 % above); high-cut **gentlest at 15 KCS** (~12 dB/oct, only −5 @15k) → ~18 dB/oct lower — *to
cut more, step the frequency, not the slope*. `low_cut`/`high_cut`/`enable` are **string enums** → use the
**[[vst-preset]]** harness (`apply_vst_preset.py`), not `apply-vst-chain`'s float dict; `enable='Out'` & `master_bypass`
are both true bypass. **Meters own it** (Gemini hears mono); crest UP = band-limited. Needs `uv sync --extra vst`.

Ready examples (rendered + measured on the Watercolors drum loop): `presets/vst/pultec-hlf-3c-drum-bus-shape.json`
(50 CPS / 15 KCS → gentle musical band-limit, crest 14.6→15.9), `pultec-hlf-3c-tame-harsh-top.json` (high_cut 10 KCS
→ smooth top rolloff, centroid 1593→1324, body untouched), `pultec-hlf-3c-lofi-bandpass.json` (250 CPS / 3 KCS →
telephone band, lows gutted 0.80→0.01, crest 14.6→24.1). Full param surface + slope numbers + history:
[`docs/vst/pultec-hlf-3c.md`](../../docs/vst/pultec-hlf-3c.md). It's a filter, NOT the tonal EQP-1A. Pure-DSP twin
(no plugin): `[L] apply-eq` high/low-pass; for **dynamic** harshness use [[de-harsh]]/[[de-ess]] (a static high-cut
just dulls). Defer to the skill; report the corners set, before→after centroid/tilt/target-band/crest deltas, that
it's a pure filter (no color), and the preset/`.state` path.
