---
name: manley-drums
description: "Use when the user has a FOLDER of multi-mic drum stems and wants the user's preferred WARM, dynamic, hi-fi TUBE drum sound through an all-Manley chain — 'the Manley drum sound', 'warm tube drums with my Manley plugins', 'all-Manley drum chain', 'Manley drum bus', 'VOXBOX the kit then glue with Variable Mu', 'my warm Manley preference on these drum stems', 'process this folder of drum stems through Manley'. VOXBOX channel strip per stem → balance + sum → Massive Passive EQ + Variable Mu glue on the bus → [[master-track]]. For ONE Manley plugin on a single drum bus reach for [[manley-voxbox]] / [[manley-massive-passive]] / [[manley-variable-mu]] directly; this is the WHOLE all-Manley chain across a multi-mic kit. The all-tube engine alternative to [[drum-stems-character]]'s tape/console characters, and a tube-chain alternative to [[warm-drum-bus]]'s Studer recipe for the same WARM goal. Local DSP + the `vst` extra (Manley UADx plugins)."
argument-hint: <stems-dir> [--platform spotify|apple|youtube]
---

# manley-drums — an all-Manley tube chain for a warm, dynamic, hi-fi drum kit

Mix a prepped **folder of multi-mic drum stems** through an **all-tube Manley chain**: the **VOXBOX channel strip per stem** (tube pre + opto comp + Pultec EQ + de-ess), balance and sum, then **Massive Passive EQ → Variable Mu glue on the bus**, then hand the bus to [[master-track]]. This is the user's stated **warm + dynamic + hi-fi tube** drum preference — the WARM-tube pick chosen over the brighter API (VCME + BB A5) chain in this session's Gemini A/B. It composes the three Manley deep-dives — it does **not** re-teach their params; defer to [[manley-voxbox]] · [[manley-massive-passive]] · [[manley-variable-mu]]. For just ONE of these on a single stereo drum bus, reach for that plugin's deep-dive directly; this skill is the whole per-stem-then-bus pipeline for a multi-mic kit.

**The two governing principles (don't violate):**
- **Warmth + color come from the tube path (VOXBOX Mic mode + Variable Mu drive), NEVER a bright EQ boost.** The Massive Passive air shelf is the *only* lift, and it's small.
- **Shape tone BEFORE glue.** On the bus, **Massive Passive (EQ) first, Variable Mu (comp) second** — the same doctrine as `home_at_last_bus.py` (tone-EQ → vari-mu → tape). Don't reorder.

This is a **mix bus, not a master** — no limiting happens here.

## Prerequisites

- **The `vst` extra** on the sibling loops repo: `uv sync --extra loops-mcp --extra mixing --extra vst` in `../stemmy-loops-mcp`.
- **UADx authorized** (these are UAD plugins; the `uaudio_*.vst3` builds need their license). All four installed and confirmed: `uaudio_manley_voxbox.vst3` · `uaudio_manley_massive_passive.vst3` · `uaudio_manley_variable_mu.vst3` (+ the unused `_m` MST build).
- **build-verify:** **loads ≠ rendered.** Use the **`uaudio_*.vst3`** builds — the `UAD Manley ….component`/`.vst3` twins **pass audio through unprocessed offline**. Confirm `changed:true` with measured *detail* per [[vst-verify]] before trusting a stage.
- **No API key needed** for the chain (pure VST/DSP). `GEMINI_API_KEY` only if you run an optional perceptual A/B (`[G] compare-to-reference`).
- The harness venv (absolute; `../` won't resolve from a worktree): **`/Users/ship/Documents/code/stemmy-loops-mcp/.venv/bin/python`**.
- **All Manley params are enums** (VOXBOX 25 · Variable Mu 23 · Massive Passive 51) — `[L] apply-vst-chain`'s float-only dict **can't set the string/bool switches** (it leaves bands disengaged → silent passthrough). Drive everything through the **`apply_vst_preset.py` harness** ([[vst-preset]]): `setattr` + nearest-valid snap. Invocation:
  ```
  /Users/ship/Documents/code/stemmy-loops-mcp/.venv/bin/python \
    presets/vst/apply_vst_preset.py <preset.json> <in.wav> <out.wav>
  ```
  The harness peak-normalizes the output to the recipe's `output_peak_dbfs` (default −1.0).

## Recipe (ordered)

### Stage 0 — prep the kit (local drum-prep, before any Manley)

Manley work assumes clean, balanced, phase-aligned stems. Do these first:
1. **De-spill the close mics with [[bleed-gate]] BEFORE balancing** — turning a mic up turns its bleed up too. (`voxbox_stems.py` defaults to the desktop-drums `raw-debled/` dir but takes the de-bled stems dir as its first arg — Stage 1 passes it explicitly.)
2. **Phase-align** ([[drum-prep]] / [[drum-phase-align]]) — full-band, before any corrective EQ.
3. **Baseline:** `[L] measure-spectrum` + `[L] measure-loudness` + `[L] measure-microdynamics` on the rough kit sum — capture tilt, centroid, LUFS, and **crest per band** so the after-pass can prove the tube path *held* dynamics.

### Stage 1 — VOXBOX per stem (the tube channel)

Run the shipped per-stem driver — it writes one VOXBOX preset per stem and applies it:
```
/Users/ship/Documents/code/stemmy-loops-mcp/.venv/bin/python \
  scripts/mix/voxbox_stems.py <de-bled-stems-dir> <voxbox-out-dir>
```
`voxbox_stems.py` processes its **hardcoded STEMS keys** (`kick_in`, `kick_beater`, `snare_top`, `snare_bottom`, `overheads`, `room`, `crotch_mic`), each applied to `<key>.wav` in the source dir — it does **not** auto-detect roles. STEMS is the **union over mic-set variants**: a key with no matching `<key>.wav` is **skipped with a note (not an error)**, so a kit with `kick_in`+`kick_beater` and no crotch mic — or the reverse — both just work; only a *zero-match* run (all filenames wrong) raises. Rename keys / add entries (and match your filenames to `<key>.wav`) to cover any other stem.

VOXBOX audio path is **fixed: INPUT → opto COMP (first) → tube PREAMP → Pultec EQ → de-ess** — not GUI order. `source_select Mic` for tube drive; `gain 50`; Pultec is **PEAK-DIP-PEAK only** (LOW boost / MID **negative** dip / HIGH boost), dials 0–10 nonlinear; **no make-up gain** (the harness peak-normalizes). The committed `STEMS` settings:
- **kick_in** — `comp_attack "Med Fast"`, lo **+5@100**, mid **−3@500**, hi **+3@4000**.
- **kick_beater (2nd kick mic)** — `low_cut "80 Hz"`, `comp_attack "Med Fast"`, lo **+1@90**, mid **−2@500**, hi **+4@4000**. The **click/attack** layer: low-cut so it doesn't stack sub under kick_in (kick_in owns the weight, the beater owns the attack). Sits well *under* kick_in in the balance (~−10 to −15 dB).
- **snare_top** — `low_cut "80 Hz"`, `thr7`, lo **+3@150**, mid **−3@700**, hi **+5@5000**, de-ess `In 9K thr4`.
- **snare_bottom** — `low_cut "120 Hz"`, `in3`, mid **−2@500**, hi **+4@8000**, de-ess `In 9K thr5`.
- **overheads (stereo)** — `low_cut "80 Hz"`, `thr5`, `comp_attack "Med Slow"`, mid **−2@500**, hi **+4@12000**, de-ess `In 12K thr4`.
- **room (stereo)** — `low_cut "80 Hz"`, `thr7`, `comp_attack "Med Slow"`, lo **+3@100**, mid **−3@500**, hi **+3@10000**.
- **aux/low/sub mic** — the script's `crotch_mic` role (`in4 thr6`, lo **+4@100**, mid **−3@500**); rename the dict key to your low-weight mic's stem name, or pin its role per [[drum-prep]].

**de-ess bands are 3K/6K/9K/12K + a 5th "Limit" (opto-limiter) position.** `comp_thresh` is relative to input: **higher = more GR**.

★ **VERIFY this stage on a couple of stems:** `[L] measure-microdynamics` before/after — **expect crest UP** (VOXBOX's opto comp *raises* crest, the measured mechanism: a drum loop went 14.6→19.5 in the deep-dive). Re-measure rather than promise fixed numbers. If a stem went *down* in crest, the wrong build loaded — passthrough → re-check [[vst-verify]].

> Optional extra per-stem drive: the installed `uaudio_manley_preamp.vst3` (Manley Reference preamp). ⚠️ **UNVERIFIED here** — no skill/doc, not render-verified this pass. VOXBOX Mic mode already supplies tube drive, so skip it unless you've run `probe_plugin.py "manley_preamp"` (RENDERS-check) + a measured pass first.

### Stage 2 — balance + sum (local DSP)

1. **Balance by measured LUFS, not eyeballed dB** ([[mix-balance]] / [[drum-mix]]) — overheads read hot in LUFS and carry the cymbals → set them *under* the close mics. **A balance problem is not an EQ problem.** This rebalance is **mandatory, not cosmetic:** the harness peak-normalizes every VOXBOX render to −1 dBFS, which **destroys the inter-stem balance** — the kit MUST be re-levelled by measured loudness before summing.
2. **Sum** the corrected stems to one stereo bus. For a multi-mic kit *with roles* (OH + room + close mics), the one-call path is **`drum-prep mix <voxbox-out-dir> --feel natural --perspective audience --dur 0`** — this IS the role-aware [[drum-mix]] tool: it LUFS-balances by role offset (OH = anchor), pans, and blends the room in a single bounce (writes `drums-mix-<feel>-<persp>.wav`). Use `--feel natural` for the warm/dynamic goal (`roomy` over-washes; `dry` kills the room glue). Only fall back to **`drum-prep stem-mix`** for *role-less* stems (it needs a `--spec` JSON of per-file gains). No MCP tool sums a stem set.

### Stage 3 — the all-Manley bus (EQ → glue)

There is **no `manley_drums_bus.py` script** — chain the two shipped presets through the harness, **Massive Passive first, then Variable Mu** (or compose both into one preset `chain`):
```
PY=/Users/ship/Documents/code/stemmy-loops-mcp/.venv/bin/python
$PY presets/vst/apply_vst_preset.py presets/vst/massive-passive-drum-bus.json  bus.wav  bus_mp.wav
$PY presets/vst/apply_vst_preset.py presets/vst/manley-vari-mu-drum-glue.json  bus_mp.wav bus_manley.wav
```
- **`massive-passive-drum-bus.json`** — low shelf **@68** for weight + low-mid bell **CUT @270** for tight + high shelf **@12k** for air. Measured on a drum loop: low 0.798→0.856, low-mid 0.176→0.128, centroid 1593→1849, **crest 14.63→14.55 (HELD — it's EQ)**. Both **ch1+ch2** are set (engage both); bands default OUT — `enable` must be BOOST/CUT or it's silent. GAIN dial is **not dB**, nonlinear + bandwidth-coupled — dial to the meter.
- **`manley-vari-mu-drum-glue.json` ★** — `dual_input 6`, `l/r_thresh 5`, **attack 3 (slow = keep punch)**, `recovery Med`, Comp mode, **HP sidechain In** (kick stops pumping the bus), `mix 100`, `headroom 16`, L-R linked. Measured: **crest 17.17→17.39 (UP), LRA 2.44→2.07 (tighter), low punch held, true-peak −0.98.** **Threshold is DIRECT (lower = more GR); HEADROOM is INVERTED (lower = hotter / more color / less GR).** Aim **~2–4 dB GR** for glue, not squash.

### Stage 4 — prove it + hand off

1. **Re-measure** the bus: `[L] measure-spectrum` (tilt + centroid up a touch, weight up) + `[L] measure-microdynamics` (**crest preserved/up** = the chain glued without squashing). Quantify the deltas vs the Stage 0 baseline.
2. **Loudness-matched A/B:** `[L] render-ab` (processed = `bus_manley.wav`, reference = the pre-Manley bus) so you judge tone, not level. Optional ears: `[G] compare-to-reference` (needs `GEMINI_API_KEY`).
3. **Hand the bus to [[master-track]]** for loudness / limiting / streaming compliance / export. **Don't master here.**

## Outputs

```
projects/<track>/stems/voxbox/      # per-stem VOXBOX renders (Stage 1)
projects/<track>/mix/bus.wav        # balanced + summed pre-Manley bus (Stage 2)
projects/<track>/mix/bus_manley.wav # Massive Passive + Variable Mu bus (Stage 3) — the deliverable of THIS skill
projects/<track>/mix/ab_manley.wav  # loudness-matched A/B (Stage 4)
```
`bus_manley.wav` is a **mix bus, not a master** — it goes into [[master-track]], never overwrites the pre-Manley bus.

## Reporting to the user

Surface before→after for the whole chain:
- **Per-stem (Stage 1):** crest delta on kick + snare_top (expect **UP** — tube opto leveling raises crest).
- **Bus (Stages 3–4):** centroid (Hz) · band-ratio low / low-mid / air · **crest + LRA** (prove glue ≠ squash: crest held/up, LRA tighter) · true-peak.
- State the **GR on the Variable Mu (~2–4 dB)** and confirm the warmth came from the tube path, not an EQ boost.

## Pitfalls

- **Float-dict trap.** Never drive these via `[L] apply-vst-chain`'s param dict — it can't set the string/bool enums, so Massive Passive bands stay OUT and Variable Mu mode/sidechain/matrices don't take → **silent passthrough**. Always the `apply_vst_preset.py` harness ([[vst-preset]]).
- **Passthrough twin.** Use the **`uaudio_*.vst3`** build; the `UAD Manley ….component` twin renders unchanged offline. **Verify `changed:true` with detail** ([[vst-verify]]) — `probe_plugin.py` *false-flags* Massive Passive as passthrough, so check a real corner, not just `changed`.
- **Over-dark / double-color.** VOXBOX Pultec mid-dips + Massive Passive's tube make-up both pull warmth/centroid down; if the bus reads too dark, **add at most ONE small Massive Passive air move and only if the meter confirms it** — don't pile on. Gemini hears ~16 kbps MONO and **chronically under-reads highs / over-reads lows**, so cross-check any "dark"/"boomy" note against `[L] measure-spectrum` (tilt + centroid), make ONE correction toward the goal, then trust the meter — don't loop the read ([[gemini-audio-understanding]]).
- **Variable Mu enum direction.** Threshold is **direct** (lower = more GR) but headroom is **inverted** (lower = hotter/more color) — dial both *to the GR meter*, not by intuition.
- **No MP M/S.** Massive Passive has **no built-in Mid/Side** (L/R + Link only) — for an M/S bus, Variable Mu does M/S (its `in/out_matrix "M-S"` + unlinked links → L=MID/R=SIDE, the `manley-vari-mu-master-ms-glue.json` preset), but you'd handle MP's M/S externally. **Don't promise Massive Passive M/S.**
- **Bus order is load-bearing.** Massive Passive (EQ) BEFORE Variable Mu (glue). Glue-then-EQ undoes the tone the compressor was reacting to.
- **This chain prints a HIGH-crest bus — warn before mastering loud.** All the leveling here is gentle (opto + slow-attack vari-mu *raise* crest), so `bus_manley.wav` lands very dynamic — commonly **crest ~22–25 dB** on raw multi-mic drums. Telling [[master-track]] to hit a loud target means the limiter does *all* the work: at a streaming −14/−16 LUFS it can cost **~5 dB of overall crest**. For a **mix-stem / gain-stage print, master gentle (~−21 LUFS)** — only ~+2–3 dB over the bus, so the limiter barely engages and crest stays within ~2 dB. Useful nuance: even when *overall* crest drops, **per-band block-crest + punch survive** (the true-peak limiter shaves inter-band peak *stacking*, not the drums' attack) — so check `[L] measure-microdynamics` per band, not just the one crest number, before deciding the master "killed the punch." **The "−21 ≈ +2–3 dB over the bus" estimate holds for a ~−23/−24 bus; a SPARSE, very-dynamic kit prints much quieter (seen: −29 LUFS / crest ~31), where −21 then costs ~8 dB of limiting (real crest loss). When the bus prints that quiet, deliver BOTH a peak-safe full-dynamics stem AND an explicit limited version rather than forcing −21.**
- **VOXBOX re-amplifies a floor-safe upstream's noise floor.** The harness peak-normalizes each VOXBOX render to −1 dBFS, so a deliberately-quiet, floor-safe upstream (e.g. an [[ff-stems]] pass whose outputs sit low by design) gets **+9–12 dB of makeup that lifts its hiss right back up** — so **clean hiss at the upstream chain BEFORE VOXBOX, not after**. Then mind that the Massive Passive **+12k air shelf lifts the summed floor again** (dial the air down if the bus hisses).

## Related

[[manley-voxbox]] · [[manley-massive-passive]] · [[manley-variable-mu]] · [[warm-drum-bus]] · [[drum-stems-character]] · [[mix-balance]] · [[drum-mix]] · [[drum-prep]] · [[drum-phase-align]] · [[bleed-gate]] · [[stem-process]] · [[vst-preset]] · [[vst-verify]] · [[vst-channel-strip]] · [[vst-chain]] · [[drum-punch]] · [[finalize-mix]] · [[studer-a800]] · [[fairchild-660]] · [[master-track]]