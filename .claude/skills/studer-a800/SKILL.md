---
name: studer-a800
description: "Use when running the UAD/UADx Studer A800 tape plugin for warmth/glue/tape-compression on a stem, drum bus, or mix bus — 'add tape', 'Studer A800', 'tape warmth on the drums', 'tape glue on the 2-bus', 'tame the harshness with tape', or when a tape chain sounds harsh/bright and you need to know which knob. The measured, plugin-specific deep-dive of [[vst-saturate]] — grounded in the real A800 param surface + isolation numbers in docs/vst/studer-a800.md. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [goal: warm/glue/tame-harshness/punch]
---

# studer-a800 — drive the UAD Studer A800 tape machine (measured)

The plugin-specific, measured version of [[vst-saturate]] for the **UAD/UADx Studer A800**
(`uaudio_studer_a800.vst3`). Full field guide — real param surface, the 5 sonic levers, harmonic theory,
recipes, decision table, and our own isolation/sweep numbers — lives in
[`docs/vst/studer-a800.md`](../../../docs/vst/studer-a800.md). This skill is the workflow; pull the doc for
the *why* and the settings tables.

## The governing facts (read first)

1. **Lightly-driven tape DARKENS — *usually* a harshness cure, not the cause.** Measured on a drum bus, the
   A800 pulled spectral centroid **−341 Hz**; every lever only darkened further. So **suspect upstream first** —
   isolate each plugin and measure before blaming the tape (on our 70s bus it was a Neve +2 dB @ 3.2 kHz mid,
   centroid **+808**, not the tape). **But tape can be the harsh one itself** when **over-driven or under-biased**
   (its own 3rd-harmonic + IMD lands in **2–6 kHz**; fact #2 + doc §5) — cure a *tape-stage* harshness with
   **less Input / over-bias / higher-headroom tape**.
2. **Tape's harmonics are odd/3rd-order (harsh), not even/2nd (sweet).** The real warmth is the **LF head
   bump + gentle compression**, not "even-order glow." Over-driving adds 2–5 kHz edge + IMD that no EQ fixes
   — the cure is **less Input**.
3. **It's a −12 dBFS plugin.** A −18-referenced feed under-drives ~6 dB (no saturation); a near-0 dBFS mix
   slams it. Gain-stage so peaks land near 0 VU. **Input both saturates AND raises level** → always
   A/B loudness-matched.
4. **Meters own this** (Gemini hears mono): verify with `[L] measure-spectrum` / `measure-loudness` /
   `measure-microdynamics` / `check-clipping`. Centroid + tilt are the harshness proxies.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`).
- The **`uaudio_studer_a800.vst3`** build (UADx native — renders headless). The `UAD ….component`/twin
  passes through offline — never use it. Confirm with `[L] list-vst-plugins {name_contains:"studer"}`.
  **UADx = UA's native (CPU) build** (VST3/AU, no UAD DSP hardware; one purchase = both licenses). **iLok account +
  PACE must be present** on a render farm even with no UAD hardware — but a *perpetual* UADx license uses local
  auth (**no USB dongle**). [[vst-verify]].
- Enum/float/bool params (`ips='15 IPS'`, `tape_type='456'`, `cal_level=6.0`, `emphasis_eq='NAB'`,
  `auto_cal=True`) → set via the **[[vst-preset]]** harness (`presets/vst/apply_vst_preset.py`), since
  `apply-vst-chain`'s `parameters` is float-only and can't gain-stage.
- **The simple panel = *primary* controls only** (Path · IPS · Tape · Cal · Input · Output · VU). **Bias,
  NAB/CCIR, the Repro/Sync EQ cards, Noise, Auto Cal, Gang** live on the **expanded view** (click the Studer badge /
  "Open") → set them via the preset harness, never the headless float dict. Top-bar **IN / A·B / COPY·PASTE /
  preset** are UAD-Toolbar shell features (not A800 params, not reachable headless) → use **`dump_state`** for
  reproducibility. Full **panel→param control-map: doc §8**.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (centroid/tilt) + `[L] measure-loudness` (crest/PLR) +
   `[L] measure-microdynamics`. The "before" column.
2. **Gain-stage** — get peaks near 0 VU (≈ −12 dBFS). In the preset harness that's `input_gain_db`; on the
   plugin it's `input_level`. Too quiet = no tape; too hot = slammed.
3. **Pick the starting point** by goal (see the doc's §3 + decision table):
   - **Default / warm:** `path_select=Repro · tape_type=456 · ips=15 IPS · emphasis_eq=NAB · cal_level=6.0 ·
     auto_cal=True · noise=False`.
   - **Tame harshness:** as above, then darken via the *direct* levers (measured order): **`repro_hf_eq` down**
     (strongest), **less Input**, **30 IPS**, **over-`bias`** (raise the bias voltage). `emphasis_eq` and
     `auto_cal` moved the spectrum negligibly on a drum bus — don't rely on them for tone.
   - **Tight modern punch:** `ips=30 IPS · tape_type=GP9/900 · cal_level=9.0` and push Input (high headroom).
4. **Drive to taste** — raise Input until you see only **~1–3 dB of transient reduction** (crest drop) on the
   loudest hits; **stop the moment the top starts to spit** (that's rising 3rd harmonic = new harshness).
   Trim `output_level` (or `output_peak_dbfs`) to gain-match.
5. **Apply** — via `[[vst-preset]]` (`apply_vst_preset.py <preset.json> <in.wav> <out.wav>`) so enum params +
   gain-stage are honored, `dump_state` for reproducibility. Output → `projects/<track>/mix/`.
6. **Verify** — re-measure. Confirm the move is **LF lift + HF softening (centroid/tilt DOWN)**, not a
   2–5 kHz rise; confirm crest didn't collapse (tape glue ≠ squash); `check-clipping` (Input pushes true-peak).
   If too dull, **don't** add `hf_record_eq`/HF Driver (re-adds brightness + changes saturation) — lighten
   drive or move toward 30 IPS / CCIR.

## Outputs

- Processed WAV in `projects/<track>/mix/` + the reusable preset JSON (and `.state` if dumped).
- Ready-made presets: **`presets/vst/studer-a800-warm-glue.json`** (standalone single-plugin default — the
  warm/glue starting point, ready for `apply_vst_preset.py`) · `presets/vst/tight-70s-{dry,warm,warmer}.json`
  (Neve→dbx→Studer drum-bus chains; see the doc for what each measured).

## Reporting to the user

State the chain + key A800 settings (path/IPS/tape/cal/EQ/Input), the before→after **centroid / tilt / crest**,
that it ran **headless**, and — if relevant — whether the darkening came from the tape vs an upstream EQ.
A/B with `[L] render-ab` (loudness-matched) so taste isn't a level illusion.

## Pitfalls

- **Don't blame the tape for harshness** — isolate & measure; it's almost always upstream EQ/drive.
- **30 IPS isn't simply "brighter."** By centroid it measured *darker* on drums (head bump → ~100 Hz). It also
  loses real sub below ~70–85 Hz and **removes the NAB/CCIR choice** (AES-locked).
- **Head bump is level-independent** — boomy 15-IPS lows are the bump, not saturation; HPF post-tape or use 30 IPS.
- **Auto Cal ON** after any Tape/Speed/Cal change (aligns bias + EQ). Our early presets used `False` with no
  measured difference, but ON is the correct default.
- **No Wow/Flutter knob**; **Noise OFF by default** and stacks across instances; **extra latency** (upsampling).
- **Gang Controls is destructive** — when linked, any edit overwrites *every* open A800 instance (no undo). Leave
  it off unless you're deliberately driving a multi-instance kit in lockstep.
- **Tape can't do surgery** — a true sibilance hotspot or harsh imbalance wants `[L] de-ess` /
  `[L] apply-dynamic-eq` / `[[mix-balance]]`, not tape. Tape is glue + tilt only.

## Related

- [`docs/vst/studer-a800.md`](../../../docs/vst/studer-a800.md) — the full measured field guide (levers, theory, decision table, **§8 panel→param control-map + UADx/UAD-2 build notes**)
- [[vst-saturate]] — the generic tape/harmonic-color skill this specializes · [[vst-preset]] — apply enum/gain-staged chains
- [[vst-verify]] — prove the build renders (responds to params) before trusting it · [[vst-chain]] — the backbone recipe
- [[vst-shootout]] — render A800 setting variants & judge to a winner · [[ampex-atr-102]] — the smoother Ampex ATR-102 *master* tape sibling for the 2-bus / mastering (UADx native, no iLok) · [[vst-master]] — the mastering-tape stage it lives in
- [[finalize-mix]] — the pure-DSP glue stage a tape insert lives in · [[drum-mix]] — balance the kit (by measured loudness) before tape
- [[gemini-audio-understanding]] — why meters (not Gemini) own loudness/peak/stereo for tape moves
