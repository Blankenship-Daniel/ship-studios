---
description: Drive FabFilter Pro-Q 4 (measured) — surgical / dynamic / spectral / M-S EQ, headless, no-iLok.
argument-hint: <audio.wav> [goal: notch|de-harsh|de-ess|dynamic|mid-side|tilt|character]
---

Invoke the **fabfilter-pro-q-4** skill on `$ARGUMENTS`.

`$1` is the WAV/stem/bus; the rest hints the goal (surgical notch / spectral de-harsh / de-ess / dynamic mud /
mid-side master / tilt / Warm character). The skill applies **FabFilter Pro-Q 4** (`/Library/Audio/Plug-Ins/VST3/
FabFilter Pro-Q 4.vst3`) — a 24-band parametric EQ with per-band **dynamic EQ**, the new **Spectral Dynamics**
(Soothe-style de-harsh/de-ess/resonance), **Character** saturation (Clean/Subtle/Warm), and Zero-Latency/Natural/
Linear phase. It **measures spectrum/tilt/centroid before & after** and A/Bs loudness-matched.

**Governing facts (measured):** **renders headless AND no-iLok** (clean render candidate, unlike the iLok/UAD
landmines) — use the **VST3** path (not the AU twin or Pro-Q 3). **A bare load is NOT flat — it restores
FabFilter's last-saved GUI curve**, so **flatten first** (disable all 24 bands = bit-exact bypass) then configure.
**All 581 params are enums**: numeric `*_frequency`/`gain`/`q`/`dynamic_range`/`spectral_density` accept a float
(snap to grid), but **`*_shape`/`*_slope`/`*_used`, `processing_mode`, `character` are string enums and you can't
enable a band → `apply-vst-chain`'s float dict can't really drive it** (our `band_8_gain` move was a no-op). Use
the **[[vst-preset]]** harness (`apply_vst_preset.py`, `setattr`). **Spectral forces linear phase on that band**;
**Linear Phase pre-rings transients** → Natural Phase/Zero Latency for drums. `character≠Clean` colors even with
no bands (+0.5 dB measured); Auto Gain isn't metered. `spectral_tilt` (4.02) isn't in the Pedalboard surface here.
Needs `uv sync --extra vst`.

Ready example: `presets/vst/fabfilter-proq4-drum-deharsh.json` (HPF 35 + −3 @250 + a **Spectral Dynamics** band
@5k → measured 5 kHz −3.0 dB while 4 kHz & 8 kHz are spared — surgical). Full param surface + numbers:
[`docs/vst/fabfilter-pro-q-4.md`](../../docs/vst/fabfilter-pro-q-4.md).
Pure-DSP alternatives (no plugin): [[de-harsh]] · [[dynamic-eq]] · [[de-ess]] · [[reference-match]] · `[L] apply-eq`.
Defer to the skill; report the bands/phase/character, before→after tilt/centroid/target-band deltas, and the
preset/`.state` path.
