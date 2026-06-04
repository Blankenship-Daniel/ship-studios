---
name: neoverb
description: "Use when running the iZotope Neoverb AI-assisted reverb to add space/plate/room/hall on a stem, bus, or send — 'Neoverb', 'iZotope reverb', 'add a plate/room/hall', 'put this in a space', 'reverb send', 'wide reverb on the drums'. The measured, plugin-specific deep-dive of [[vst-reverb]]. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [space: plate|room|hall|wide] [dry_wet]
---

# neoverb — drive the iZotope Neoverb reverb (measured)

The plugin-specific, measured workflow for **iZotope Neoverb** (`/Library/Audio/Plug-Ins/VST3/Neoverb.vst3`) —
iZotope's **AI-assisted reverb**: three blendable reverb engines (`r1`/`r2`/`r3`) plus a Pre-EQ (on the input) and a
Reverb-EQ (on the tail), 63 params. The plugin-specific member of [[vst-reverb]] (vs Valhalla / Pro-R). Full field
guide — the engine surface, footguns, recipes, our numbers, sources —
[`docs/vst/izotope-neoverb.md`](../../../docs/vst/izotope-neoverb.md). This skill is the workflow.

## The governing facts (read first — measured on this rig, Pedalboard 0.9.23)

1. **It RENDERS headless** (NI/iLok-account-authorized on this Mac). Use the **VST3** `Neoverb.vst3` path. **Loads ≠
   renders elsewhere** — re-verify on a new machine with [[vst-verify]] (a 0.00 spectrum/stereo delta = passthrough).
2. **`dry_wet` defaults to 50 → a bare instance ALREADY adds reverb.** Unlike most inserts, a default Neoverb is not a
   passthrough; it's a 50/50 wet mix. **Set `dry_wet` explicitly** (low for an insert, high for a send) or you'll wash
   the source by accident.
3. **A wide reverb hurts mono-sum — CHECK `[L] measure-stereo`** (correlation / mono-sum loss). Reverb decorrelates
   L/R; favour a **parallel / wet send** and keep `dry_wet` modest on a mono-critical mix.
4. **Params are enums (numeric + string/bool).** `[L] apply-vst-chain`'s float dict can set the **numeric** ones
   (`dry_wet`, `output_gain_db`, `r1`/`r2`/`r3_gain_db`, `r3_size_m`, `predelay_time_ms`, the EQ band gains/freqs) — but
   the **string/bool** enums (`preeq_bypass`, `reverbeq_bypass`, `*_tempo_sync`, `r2_synced_time`, `mod_type`) need the
   **[[vst-preset]] harness** (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
5. **The "Reverb Assistant" is GUI-only** — it won't run headless; you blend the three engines + EQs manually.
6. **Meters own tone & width** (Gemini hears ~16 kbps mono — it can't read stereo at all): read `[L] measure-stereo`
   (width / correlation / mono-sum loss), `measure-spectrum` (tilt/centroid), `measure-loudness` (crest). A/B
   loudness-matched ([[level-match]] / `[L] render-ab`).

## The parameter surface (see the doc for the full table)

Global: `dry_wet` (0..100, def **50**), `output_gain_db`, `global_bypass`. **Three engines**, each blendable via its
`rN_gain_db` (−70..0, def −3): `r1` (early/plate, `r1_size_m` 4..40, `r1_time_ms`, `r1_lowpass_hz`), `r2` (mid,
`r2_size_m`, `r2_time_s`, `r2_damping`, `r2_synced_time` string → harness), `r3` (large/hall, `r3_size_m`,
`r3_time_s`, `r3_damping`). **Pre-delay**: `predelay_time_ms` (0..1000, def 20). **Pre-EQ** (input): `preeq_bypass`
(harness) + low/high/bell bands. **Reverb-EQ** (tail): `reverbeq_bypass` (harness) + low/high/bell bands. **Mod**:
`mod_rate_hz`/`mod_depth`/`mod_type` (`RandomFat`/`Pitch`, string → harness).

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-stereo` (width / correlation / mono-sum loss) + `[L] measure-spectrum` (tilt/centroid)
   + `[L] measure-loudness`. The "before" column.
2. **Decide insert vs send.** Insert on the stem (low `dry_wet`, ~15–35) or a parallel **wet send** (`dry_wet` high,
   sum back to taste) — the send is mono-safer. **Always set `dry_wet`** (default 50 is hot).
3. **Blend the engines.** Bring up `r1_gain_db` for early/plate, `r2`/`r3` for body/hall; set sizes (`r3_size_m`
   4..40 m). A plate = small `r3_size_m` + short times; a hall = large size + long `r3_time_s`.
4. **Pre-delay** — `predelay_time_ms` (20–60) to keep the dry transient clear of the tail.
5. **Tame the tail** — `reverbeq_bypass="False"` (harness) + a low-shelf cut (de-mud) and/or high cut (de-fizz) on
   `reverbeq_*`; `preeq_*` shapes what feeds the reverb.
6. **Build a preset** (`presets/vst/neoverb-*.json`) setting `dry_wet`, the engine gains/sizes/times, predelay, and the
   EQ `*_bypass` + bands explicitly, and apply: `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py
   <preset.json> <in> projects/<track>/mix/<stem>_neoverb.wav`. Set `dump_state=true` via `apply-vst-chain` once dialed.
7. **Prove it** — re-`measure-stereo` (**width UP, correlation DOWN** = it's working) + `measure-spectrum`. **Check the
   mono-sum loss** — reject if it collapses in mono. A 0.00 delta = passthrough. A/B loudness-matched.
8. **QC** — `[G] detect-mix-issues` / `analyze-mix-balance` (genre/intent set) for over-wet / smeared transients;
   cross-check against the meters ([[gemini-audio-understanding]]). It's a space insert/send, not a master — hand the
   dry-bus result to [[master-track]].

## Move table (measured on a drum bus)

| Goal | Neoverb move |
|---|---|
| **Wide drum space** ★ | `dry_wet=35` → see ★ below. Favour a wet send; check mono. |
| **Plate (vocal/snare)** | `r1` up (early/plate), small `r3_size_m`, short times, `predelay` 20–40; `dry_wet` 15–30 insert or wet send. |
| **Room** | `r2` up, mid `size_m` (6–12 m), short `r2_time_s`, modest tail; subtle `dry_wet`. |
| **Hall** | `r3` up, large `r3_size_m` (20–40 m), long `r3_time_s`, `predelay` 40–80; wet send. |
| **Tighten / de-wash** | lower `dry_wet`, shorten times, cut `reverbeq` low-shelf (mud) + high (fizz). |
| **Keep it mono-safe** | parallel wet send + modest `dry_wet`; verify `[L] measure-stereo` mono-sum loss. |

★ the shipped example (`presets/vst/neoverb-drum-wide.json`, `dry_wet=35`) measured on a drum bus: **stereo width
+12.2 dB** (big — Neoverb decorrelates the tail), all 5 bands **−3 dB** (the wet mix dilutes the direct level), crest
**+1.1**. A wide, real reverb — **check the mono-sum loss** before committing on a mono-critical mix.

## Outputs

- `projects/<track>/mix/<stem>_neoverb.wav` (or a wet-send stem) + the reusable `presets/vst/neoverb-*.json` (and
  `.state` if dumped).

## Reporting to the user

State the space (engine blend + sizes/times + predelay), the `dry_wet` (and insert vs send), the before→after
**width / correlation / mono-sum loss** + any tonal tilt move, that it ran headless, and the preset/`.state` path.
A/B loudness-matched so "more space" isn't just "louder", and report the mono-sum read.

## Pitfalls

- **`dry_wet` defaults to 50** — a bare Neoverb already washes the source; set it explicitly (low insert / high send).
- **A wide reverb is a mono-fold landmine** — always `[L] measure-stereo` for mono-sum loss; prefer a parallel wet
  send + modest `dry_wet` on mono-critical material.
- **Float dict can't toggle the EQs or set synced times** — `preeq_bypass`/`reverbeq_bypass`/`*_tempo_sync`/
  `r2_synced_time`/`mod_type` are string/bool enums → the [[vst-preset]] harness (or a `.state`).
- **The harness upmixes mono→stereo and peak-normalizes** (`output_peak_dbfs`, def −1.0) — for channel-preserving /
  unrenormalized work use `[L] apply-vst-chain`.
- **The AI Reverb Assistant is GUI-only** — blend the three engines + EQs by hand headless.
- Reverb is a space insert/send, **not** mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/izotope-neoverb.md`](../../../docs/vst/izotope-neoverb.md) — the full measured field guide ·
  [[izotope]] — the iZotope index
- [[vst-reverb]] — the generic reverb skill this specializes · [[vst-delay]] — its echo cousin · [[vst-preset]] —
  apply enum/all-explicit chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone ·
  [[vst]] — index/doctrine
- Pure-DSP twin (width, not reverb): `[L] adjust-stereo` (M/S width) — Neoverb generates the space; stereo width is a
  separate move
- [[mix-check]] (find the problems first) · [[finalize-mix]] · [[gemini-audio-understanding]] — why meters own the stereo read
