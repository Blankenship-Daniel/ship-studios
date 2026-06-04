# iZotope Neoverb — field guide: the AI-assisted reverb (measured headless)

How to drive **iZotope Neoverb** (`/Library/Audio/Plug-Ins/VST3/Neoverb.vst3`) in this pipeline — iZotope's
**AI-assisted reverb**: three blendable reverb engines (`r1`/`r2`/`r3`) plus a Pre-EQ on the input and a Reverb-EQ on
the tail, 63 params. This doc is **measured on this rig** — the real Pedalboard param surface plus the headline
findings that **it renders & engages headless**, **`dry_wet` defaults to 50 (a bare instance already adds reverb)**,
and the **Reverb Assistant is GUI-only**. The task skill [[neoverb]] is the workflow over this doc.

---

## TL;DR (the headline — read this first)

1. **It RENDERS & engages headless** (NI/iLok-account-authorized on this Mac). It loads + processes through the offline
   Pedalboard host — unlike the iLok-blocked Ozone modules ([[ozone-11-maximizer]]) or the self-bypassing
   [[tape-j-37]], Neoverb runs. Use the **VST3** `Neoverb.vst3` path. **Re-verify on a new machine** with
   [[vst-verify]] — loads ≠ renders; a 0.00 spectrum/stereo delta = passthrough.
2. **`dry_wet` defaults to 50 → a bare instance ALREADY adds reverb.** Unlike most inserts (where a fresh load is
   near-passthrough), a default Neoverb is a 50/50 wet mix. **Set `dry_wet` explicitly** — low for an insert, high for
   a parallel send — or you'll wash the source by accident.
3. **A wide reverb hurts mono-sum — CHECK `[L] measure-stereo`** (correlation / mono-sum loss). Reverb decorrelates
   L/R; favour a **parallel / wet send** and keep `dry_wet` modest on a mono-critical mix.
4. **Params are enums (numeric + string/bool).** `[L] apply-vst-chain`'s float dict sets the **numeric** ones
   (`dry_wet`, `output_gain_db`, `rN_gain_db`, `r3_size_m`, `predelay_time_ms`, the EQ band gains/freqs) — but the
   **string/bool** enums (`preeq_bypass`, `reverbeq_bypass`, `*_tempo_sync`, `r2_synced_time`/`r3_synced_time`,
   `mod_type`) need the **[[vst-preset]] harness** (`apply_vst_preset.py`, `setattr`) or a dumped `.state`.
5. **The "Reverb Assistant" is GUI-only** — it won't run in the offline subprocess; you blend the three engines + EQs
   manually.
6. **Meters own tone & width** (Gemini hears ~16 kbps **mono** — it can't read stereo at all): judge any Neoverb move
   with `[L] measure-stereo` (width / correlation / mono-sum loss), `measure-spectrum` (tilt/centroid),
   `measure-loudness` (crest). A/B loudness-matched with `[L] render-ab` ([[level-match]]).

---

# Part A — measured on this rig

Probe: `Neoverb.vst3` loaded via Pedalboard (stemmy-loops `vst` extra, 0.9.23), processing a **drum bus**. Numbers
below are that source; state it when you reuse them.

## The verdict: loads, engages, renders — and `dry_wet` is hot by default

| test | measured | reading |
|---|---|---|
| `dry_wet=35` (insert) | **stereo width +12.2 dB** | the reverb engines run + decorrelate the tail (big) |
| → 5-band levels | **all −3 dB** | the wet mix dilutes the direct (dry) level |
| → crest | **+1.1 dB** | the tail fills between transients (slightly peakier ratio) |
| default `dry_wet` | **50** | a bare instance is a 50/50 wet mix, NOT a passthrough |

**Conclusion:** Neoverb is a **working headless reverb** — and a strong, wide one (`dry_wet=35` widened the drum bus by
**+12.2 dB**). The trap is the **default-50 `dry_wet`**: a "fresh" insert already adds half-wet reverb, so always set
`dry_wet` and **check the mono-sum** (a +12 dB width gain is a mono-fold liability). Re-measure stereo + spectrum after.

## The parameter surface (Pedalboard-exposed — 63 params)

| Group | Params | Values *(default)* | Notes |
|---|---|---|---|
| **Global** | `global_bypass` | bool *(False)* | bool → harness |
| | `dry_wet` | `0…100` *(**50**)* | **hot by default** — set it |
| | `output_gain_db` | `−60…+10` *(0)* | numeric |
| **Engine 1** (early/plate) | `r1_gain_db` *(−3)* · `r1_size_m` 4–40 *(4.9)* · `r1_time_ms` · `r1_diffusion` · `r1_lowpass_hz` | — | blend with `r1_gain_db` |
| **Engine 2** (mid) | `r2_gain_db` *(−3)* · `r2_size_m` *(7.4)* · `r2_time_s` · `r2_damping` 1–11 · `r2_balance` · `r2_crossover_hz` | `r2_synced_time` (string) · `r2_tempo_sync` (bool) → harness | mid body |
| **Engine 3** (large/hall) | `r3_gain_db` *(−3)* · `r3_size_m` 4–40 *(11)* · `r3_time_s` up to 24 s · `r3_damping` · `r3_balance` · `r3_crossover_hz` | `r3_synced_time`/`r3_tempo_sync` → harness | hall tail |
| **Pre-delay** | `predelay_time_ms` `0…1000` *(20)* | `predelay_synced_time` (string) · `predelay_tempo_sync` (bool) → harness | separates dry from tail |
| **Pre-EQ** (input) | `preeq_bypass` *(False)* + low/high/bell bands (gain ±15 / freq / slope / shape) | `preeq_low_band_shape` (`Low Shelf`/`High Pass`) · `preeq_high_band_shape` (`High Shelf`/`Low Pass`) → harness | shapes what FEEDS the reverb |
| **Reverb-EQ** (tail) | `reverbeq_bypass` *(False)* + low/high/bell bands | shapes → harness | de-mud / de-fizz the TAIL |
| **Mod** | `mod_rate_hz` *(0.48)* · `mod_depth` *(25)* · `mod_type` (`RandomFat`/`Pitch`) | `mod_type` (string) → harness | thickens / detunes the tail |
| **Smoothing** | `smoothing_bypass` *(True)* · `smoothing_amount` | bool → harness | transition smoothing |

> **The AI "Reverb Assistant"** (it auditions and suggests an engine blend from your source) is **GUI-only** — it has
> no headless effect; blend `r1`/`r2`/`r3` + the two EQs by hand.

---

# Part B — how the plugin works (usage synthesis)

## 1. What it is

Neoverb (iZotope, 2020) is a reverb built from **three independent reverb engines you blend together** — typically a
short early/plate (Engine 1), a mid room (Engine 2), and a long hall (Engine 3) — plus a **Pre-EQ** that shapes the
signal before it hits the reverb and a **Reverb-EQ** that shapes the tail after. Its DAW headline is the **Reverb
Assistant** + a "Reverb Score" meter that flags muddy/clashing tails, both GUI-only; in this pipeline you drive the
three engines and the two EQs manually and judge the result on the meters.

## 2. The engines & EQs

- **Engine 1 / 2 / 3** — each has its own size (`rN_size_m` 4–40 m), time, damping, and lowpass; blend their levels
  with `rN_gain_db`. A **plate** = Engine 1 up, small size, short time; a **room** = Engine 2, mid size; a **hall** =
  Engine 3, large size + long `r3_time_s`. Sum them for a layered space.
- **Pre-delay** (`predelay_time_ms`, 20 ms default) — the gap before the tail; raise it (20–80 ms) to keep the dry
  transient clear and the source intelligible.
- **Pre-EQ** — shapes what *feeds* the reverb (e.g. high-pass the input so lows don't muddy the tail).
- **Reverb-EQ** — shapes the *tail itself* (cut a low shelf to de-mud, a high cut to de-fizz). Engage with
  `reverbeq_bypass="False"` (it's not bypassed by default, but set it explicitly when scripting).

## 3. The levers

- **`dry_wet`** — the master balance. **Default 50 is hot.** Insert: 15–35. Parallel wet send: high (sum the wet stem
  back to taste, mono-safer). Because it changes level, **A/B loudness-matched**.
- **Engine blend (`rN_gain_db`) + sizes** — the character (plate / room / hall). Bigger size + longer time = bigger,
  washier space.
- **`predelay_time_ms`** — clarity vs immersion.
- **Reverb-EQ** — the tone of the tail (the difference between a usable reverb and mud).
- **Mod** (`mod_type`/`mod_depth`) — thickens (`RandomFat`) or detunes (`Pitch`) the tail; subtle on drums.

## 4. Recipes (drive via apply-vst-chain for numeric + the harness for the EQ toggles/modes, then measure)

| Goal | Settings |
|---|---|
| **Wide drum space** ★ | `dry_wet=35` → measured **width +12.2 dB**, bands −3 dB, crest +1.1; favour a wet send, **check mono** |
| Plate (vocal / snare) | `r1` up, small `r3_size_m`, short times, `predelay` 20–40, `dry_wet` 15–30 (or wet send) |
| Room | `r2` up, mid `size_m` 6–12 m, short `r2_time_s`, modest tail, subtle `dry_wet` |
| Hall | `r3` up, large `r3_size_m` 20–40 m, long `r3_time_s`, `predelay` 40–80, wet send |
| Tighten / de-wash | lower `dry_wet`, shorten times, cut `reverbeq` low shelf (mud) + high (fizz) |
| Mono-safe | parallel wet send + modest `dry_wet`; verify `[L] measure-stereo` mono-sum loss |

*Default to dial from:* **set `dry_wet` low for an insert (or high for a send), blend one engine first, set predelay,
tame the Reverb-EQ tail, then measure stereo + spectrum.**

## 5. Pipeline integration

1. `[L] measure-stereo` (width / correlation / mono-sum loss) + `measure-spectrum` + `measure-loudness` — the "before".
2. Build a `presets/vst/neoverb-*.json` setting `dry_wet`, the engine gains/sizes/times, predelay, and the EQ
   `*_bypass` + bands (+ any `*_shape`/`*_synced_time`/`mod_type` strings) explicitly. Apply via
   `presets/vst/apply_vst_preset.py` → `projects/<track>/mix/<stem>_neoverb.wav` (or a wet-send stem). Set
   `dump_state=true` (via `apply-vst-chain`) once dialed for a byte-stable re-render.
3. **Measure** — `measure-stereo` (width up / correlation down = working) + the **mono-sum loss** (reject if it
   collapses) + `measure-spectrum`. A 0.00 delta = passthrough.
4. **A/B honestly** with `[L] render-ab` (loudness-matched). For a perceptual read, `[G] analyze-mix-balance` /
   `detect-mix-issues` on the loudness-matched pair (Gemini is mono — trust the meters for width).
5. A reverb is a space insert/send — master the dry bus with [[master-track]].

## 6. Pitfalls & gotchas

- **`dry_wet` defaults to 50** — a bare Neoverb already washes the source; always set it (low insert / high send) or
  you'll ship more reverb than you intended with a false `changed:true`.
- **Wide reverb is a mono-fold landmine** — `dry_wet=35` widened our drum bus **+12.2 dB**; always `[L] measure-stereo`
  for mono-sum loss and prefer a parallel wet send on mono-critical material.
- **Float dict can't toggle the EQs, set band shapes, or synced times** — `preeq_bypass`/`reverbeq_bypass`,
  `*_band_shape`, `*_tempo_sync`, `rN_synced_time`, `mod_type` are string/bool → the [[vst-preset]] harness (or a `.state`).
- **The harness upmixes mono→stereo and peak-normalizes** (`output_peak_dbfs`, def −1.0) — for channel-preserving /
  unrenormalized work use `[L] apply-vst-chain`.
- **The AI Reverb Assistant is GUI-only** — blend the three engines + EQs by hand headless.
- **Don't EQ-mud-fix in the source** — the cleaner lever is the Reverb-EQ tail + a Pre-EQ high-pass on the input.
- **Re-verify on another machine** — headless render here depends on the NI/iLok-account auth; [[vst-verify]] before trusting it elsewhere.

## 7. When to use Neoverb vs the alternatives

| Want | Use |
|---|---|
| A blendable 3-engine reverb (plate+room+hall), headless | **Neoverb** (this) |
| A plate / hall via another reverb plugin | [[vst-reverb]] (ValhallaPlate, Pro-R 2, SSL FlexVerb) |
| Delay / echo instead of reverb | [[vst-delay]] |
| Stereo WIDTH (not reverb) | `[L] adjust-stereo` (M/S width) |
| De-reverb (remove a tail) | [[rx-10-de-reverb]] |

---

## Sources

iZotope Neoverb product/help docs (izotope.com — three reverb engines, Pre-EQ / Reverb-EQ, Reverb Assistant /
Reverb Score) · the iZotope Neutron field guide [`docs/vst/izotope-neutron.md`](izotope-neutron.md) (shared
enum-harness + headless-auth pattern) · the repo VST doctrine [`docs/vst/README.md`](README.md) (loads ≠ renders) ·
**our own Pedalboard load + render measurements** on `Neoverb.vst3` (Part A) — the default-50 `dry_wet` finding + the
measured drum-bus width delta.
