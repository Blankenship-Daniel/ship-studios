---
name: hitsville-eq-mastering
description: "Use when running the UADx Hitsville EQ Mastering (UA's model of the custom Motown / Hitsville U.S.A. disk-mastering EQ) for broad, musical 'Motown' tone or Mid/Side mastering on a 2-bus, master, drum bus, or stem — 'Hitsville EQ', 'Motown EQ', 'Motown mastering EQ', 'that Motown low end / Motown sound', 'mid-side master EQ', 'tighten the lows and widen the top', 'broad passive vintage mastering EQ', 'half-speed mastering EQ', or when you want a passive, proportional-Q graphic EQ + the 70 Hz/15 kHz Motown Filters. The measured, plugin-specific deep-dive of [[vst-eq]] / [[vst-master]] — a 7-fixed-band passive graphic EQ with Dip/Peak per band, a half-speed frequency set, fixed Motown Filters, and TRUE Mid/Side; grounded in the real 53-enum-param surface + isolation/curve/M-S render numbers in docs/vst/hitsville-eq-mastering.md. A BROAD/MUSICAL mastering EQ (not surgical — pair with [[fabfilter-pro-q-4]] for surgery). Stemmy MCP, the `vst` extra. UADx native (iLok account, verified-headless on this rig)."
---

# hitsville-eq-mastering — drive the UADx Hitsville EQ Mastering (measured)

The plugin-specific, measured version of [[vst-eq]] / [[vst-master]] for the **Hitsville EQ Mastering**
(`/Library/Audio/Plug-Ins/VST3/uaudio_hitsville_eq_mastering.vst3`) — UA's model of the **custom Motown /
Hitsville U.S.A. disk-mastering equalizer**: a **passive, inductor-based, proportional-Q graphic EQ** with **7
fixed bands per channel** (Dip/Peak each), a half-speed frequency set, the fixed **"Motown Filters,"** and — UA's
own addition — **true Mid/Side**. It's **broad and musical** (a "colour" mastering EQ), the opposite of a
surgical parametric. Full field guide — param surface, curve/band table, M-S numbers, recipes, decision table,
history — lives in [`docs/vst/hitsville-eq-mastering.md`](../../../docs/vst/hitsville-eq-mastering.md). This skill
is the workflow.

## The governing facts (read first — measured)

1. **The 0–8 knob is NOT dB, and boost ≠ cut.** A single band at amount **8** measured ≈ **+5 dB (Peak)** /
   **−3 dB (Dip)** — gentle, **asymmetric**, ~0.6 dB/step, and **bands interact** (passive). Dial broad and
   **stack bands**; don't expect "+8 = +8 dB." Fixed centers: **50 / 130 / 320 / 800 / 2k / 5k / 12.5k** (bands
   1–6 broad bells; band 7 = an **air shelf**). Half-speed halves them (25/65/160/400/1k/2.5k/6.25k).
2. **M/S is the standout, and it's a SPECTRAL width tool.** Our M-S preset tightened **low width −30→−33 dB**
   (mono-er bass) while **widening the top** (high −19.8→−15.3 dB), correlation still safe (0.981→0.986). The
   master move = **warm mono bass in the Mid, lush wide air in the Side. M/S REQUIRES `ctrl_link='Unlink'`.**
3. **FILTER = the fixed "Motown Filters"** (4-position, no sweepable corner): HP ≈ **70 Hz**, LP ≈ **15 kHz**,
   Band-Pass = both; applies to **both channels** regardless of LINK.
4. **It's an EQ, not dynamics — and a MASTERING/tonal stage.** Adding lows lowers crest (denser); it adds no
   punch/glue (use [[drum-punch]] / a comp for that). **Master/limit AFTER in [[master-track]] — never here.**
5. **Meters own this** (Gemini hears mono): `[L] measure-spectrum` (tilt / band ratios / centroid),
   **`[L] measure-stereo`** (correlation / per-band width / mono-sum loss — the one that matters for M/S),
   `[L] measure-loudness`. A **0.00 change = passthrough** (wrong build) — re-measure detail, not `changed:true`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- **`uaudio_hitsville_eq_mastering.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"hitsville"}`.
  Load the **UADx `uaudio_*.vst3`** build (renders headless — verified here); **NOT** the
  `UAD Hitsville EQ Mastering.component` twin (passthrough offline), and **NOT** `uaudio_hitsville_eq.vst3` (the
  channel version) or `uaudio_hitsville_chambers.vst3` (the reverb). iLok account (no dongle); **re-verify on a
  new machine** — but note `probe_plugin.py` false-flags it "PASSTHROUGH" (it nulls `l1_gain` to 0 = a no-op);
  confirm with a real **boost** instead.
- **⚠ Headless gotchas (measured):**
  - `apply-vst-chain`'s float dict sets `lN_gain` / `lN_freq` / `*_gain` (floats) but **silently drops** the
    string enums (`lN_dip_pk`, `ctrl_link`, `filter`, `mid_side`, `*_byp`, `*_speed`) — a "Dip" never engages.
    **Use the [[vst-preset]] harness** (`presets/vst/apply_vst_preset.py`) for any real patch.
  - **`*_speed` is inert headless** — set the per-band **`lN_freq`** (e.g. `l1_freq=25.0`) to pick half-speed,
    not the global `left_speed`/`right_speed`.
  - **LINK mirrors the top channel onto both**; use **`Unlink` + set both sections** for a reproducible render
    (and Unlink is required for M-S). Auto-Solo is GUI-only — dial M/S by the meter.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (tilt / band ratios / centroid) + **`[L] measure-stereo`** (correlation
   / per-band width) + `[L] measure-loudness` (crest). The "before" column.
2. **Pick the mode** — **L-R** for tonal shaping (Motown low end, drum sweetening), **M-S** for width control
   (mono lows + wide top). M-S ⇒ `ctrl_link='Unlink'`, `mid_side='M-S'` (top = Mid, bottom = Side).
3. **Choose bands + direction** — Peak to boost / Dip to cut at a fixed center; set the per-band **`lN_freq`**
   (Normal vs half-speed). Keep amounts modest (2–4 ≈ +1–2.5 dB); stack bands rather than maxing one.
4. **Filter (optional)** — `filter='High Pass'` (70 Hz) to tighten sub, `'Low Pass'` (15 kHz) for tape-smooth
   top, `'Band Pass'` for both. Both channels.
5. **Apply via [[vst-preset]]** — `apply_vst_preset.py <preset.json> <in> <out>` (the `vst` venv). Ready-made:
   `presets/vst/hitsville-motown-master.json` (L-R Motown curve) · `hitsville-ms-master-width.json` (M-S tight
   lows / wide top) · `hitsville-drum-bus-weight.json` (L-R drum sweetening). Output → `projects/<track>/mix/`
   (tonal) or `masters/` only if this is the final tonal pre-limiter stage.
6. **Verify** — re-measure. Tonal move = band ratios / centroid shifted as intended, centroid stays musical;
   **M/S = per-band width redistributed (low tighter, top wider) with correlation still safe** (keep > ~0.5 on a
   master) + small mono-sum loss; `check-clipping`. A/B loudness-matched with `[L] render-ab`.

## Recipes (measured / from the manual)

| Goal | Mode | Moves (band · Dip/Peak · amount) | Filter |
|---|---|---|---|
| **Motown master tone** ★ | L-R | 50 Pk3 + 130 Pk2 + 320 Dip2 + 5k Pk2 + 12.5k Pk2 | Off |
| **Mono-tight lows + wide air** ★ | **M-S** | Mid: 50 Pk2 / 320 Dip2 / 2k Pk1 · Side: 130 Dip2 / 5k Pk3 / 12.5k Pk3 | Off |
| **Drum-bus sweetening** | L-R | 130 Pk3 + 800 Dip2 + 5k Pk2 + 12.5k Pk1 | HP 70 |
| Tape-smooth top | L-R | 12.5k Pk2–3 | **LP 15k** |
| Deep sub control | L-R | band 1 `freq=25` (½-speed) Pk/Dip 2–3 | HP 70 |
| Forward (guitar/lead) | L-R | 5k Dip2 + 2k Pk2 + Channel Gain +2 | — |

★ validated: **motown-master** low 0.589→0.722, air 0.0130→0.0167, centroid 2223→2388 (fuller + airier, musical).
**ms-master** low width −30→−33, high −19.8→−15.3, corr 0.981→0.986 (tight lows / wide top, mono-safe).

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset (and `.state` if `dump_state`).
- Report: mode (L-R / M-S), bands + Dip/Peak + amounts + any filter, before→after **band ratios / centroid**
  (tonal) and **per-band width / correlation / mono-sum loss** (M/S), that it ran headless (real Δ, not 0.00),
  and that mastering/limiting is deferred to [[master-track]]. A/B loudness-matched.

## Pitfalls

- **String enums don't set via the float dict** — `*_dip_pk`/`mid_side`/`ctrl_link`/`filter`/`*_byp`/`*_speed`
  need the harness; `parameters_set` ≠ "it took" (a dropped "Dip" silently becomes a boost).
- **`*_speed` is inert headless** — use `lN_freq` for half-speed.
- **"8" is not 8 dB** — ≈ +5/−3 dB at max, asymmetric; bands interact. Dial broad, stack.
- **M/S needs Unlink**; Auto-Solo is GUI-only — judge by `measure-stereo`. Don't over-widen (watch correlation).
- **It's an EQ, not a comp** — no punch/glue; adding lows lowers crest. Master/limit later in [[master-track]].
- **Load the right build** — UADx `uaudio_hitsville_eq_mastering.vst3` (not the `.component`, not the channel EQ).
- **iLok/PACE** — re-verify load+render on any new machine (with a real boost, not the auto-probe).

## Related

- [`docs/vst/hitsville-eq-mastering.md`](../../../docs/vst/hitsville-eq-mastering.md) — the full measured field guide
- [[vst-eq]] — the generic EQ skill this specializes · [[vst-master]] — the master-bus EQ context · [[vst-preset]] — apply enum/string chains (required here)
- [[hitsville-eq]] — the single-channel **Studio EQ** sibling (same Motown bands + proportional-Q, but L/R-only, real-dB stepped gains, no M/S) — use it per-track, this one on the 2-bus / for M/S
- [[fabfilter-pro-q-4]] — the SURGICAL/clean EQ to pair with this BROAD one (notch with Pro-Q, shape with Hitsville)
- [[master-track]] — do the loudness/limiting/compliance AFTER this tonal stage · [[finalize-mix]] — bus-glue stage that can precede it
- [[ampex-atr-102]] / [[studer-a800]] — vintage tape colour alternatives · [[ssl-4k-e]] / [[api-vision-channel-strip]] — console-strip tone alternatives
- [[vst-verify]] — prove the build renders (with a real boost) · [[vst-shootout]] — judge band/mode variants · [[vst-chain]] — the backbone recipe
- [[gemini-audio-understanding]] — why meters (not Gemini) own width/centroid/peak
