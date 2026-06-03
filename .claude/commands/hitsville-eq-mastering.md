---
description: Dial the UADx Hitsville EQ Mastering (Motown disk-mastering / M-S EQ) — broad musical tone + width, measured.
argument-hint: <audio.wav> [goal: motown/ms-width/drum-bus/tape-top/sub]
---

Invoke the **hitsville-eq-mastering** skill on `$ARGUMENTS`.

`$1` is the WAV; the rest hints the goal (motown master tone / M-S tight-lows-wide-top / drum-bus sweetening /
tape-smooth top / deep sub). The **Hitsville EQ Mastering** is UA's model of the **custom Motown / Hitsville
U.S.A. disk-mastering EQ** — a **passive, proportional-Q graphic EQ** with **7 fixed bands** (50/130/320/800/2k/
5k/12.5k, Dip=cut / Peak=boost each), a half-speed set, the fixed **70 Hz/15 kHz Motown Filters**, and **true
Mid/Side**. **Broad/musical**, not surgical (pair with [[fabfilter-pro-q-4]] for surgery); a tonal/master stage
— do loudness/limiting AFTER in [[master-track]].

Key facts (measured): **the 0–8 knob is NOT dB** — a band at amount 8 ≈ **+5 dB (Peak) / −3 dB (Dip)**, gentle +
asymmetric, ~0.6 dB/step, bands interact → dial broad, stack. **M/S is the standout** (warm mono bass in the Mid,
wide air in the Side; our preset took low width −30→−33 dB while widening the top −19.8→−15.3, corr 0.981→0.986
mono-safe) — **M/S requires `ctrl_link='Unlink'`.** Bands 1–6 are broad bells, band 7 is an air shelf.

**Headless gotchas:** load the UADx **`uaudio_hitsville_eq_mastering.vst3`** (renders headless here — NOT the
`.component` twin = passthrough, NOT the `_eq` channel version or `_chambers` reverb). `apply-vst-chain`'s float
dict sets `lN_gain`/`lN_freq` but **silently drops the string enums** (`lN_dip_pk`, `ctrl_link`, `filter`,
`mid_side`, `*_byp`, `*_speed`) — use the [[vst-preset]] harness (`presets/vst/apply_vst_preset.py`). **`*_speed`
is inert headless** — set per-band `lN_freq` (e.g. `l1_freq=25.0`) for half-speed. The generic `probe_plugin.py`
false-flags it PASSTHROUGH (it nulls `l1_gain`) — verify with a real boost. Ready presets:
`presets/vst/hitsville-motown-master.json` · `hitsville-ms-master-width.json` · `hitsville-drum-bus-weight.json`.
Needs `uv sync --extra vst`; iLok account (verified-headless here — re-verify elsewhere).

**Measure before & after** with `[L] measure-spectrum` (band ratios/centroid) and especially **`[L] measure-stereo`**
(per-band width / correlation / mono-sum loss) — a 0.00 change = wrong build. A/B loudness-matched with
`[L] render-ab`. Full param surface + curve/M-S tables + decision table:
[`docs/vst/hitsville-eq-mastering.md`](../../docs/vst/hitsville-eq-mastering.md). Defer to the skill; report
mode + bands/Dip-Peak/amounts + filter, before→after band-ratios/centroid (tonal) or per-band width/correlation
(M/S), the preset/`.state` path, and that mastering/limiting is deferred to [[master-track]].
