# iZotope Ozone 11 — field guide: the mastering suite (DAW-only here)

How the **iZotope Ozone 11** mastering suite behaves in the ship-studios pipeline — and why **none of its
modules are usable headless on this rig**. Ozone ships each processor as its own VST3 (`Ozone 11 <Module>.vst3`)
plus the full-suite plugin; we treat each as a candidate `[L] apply-vst-chain` insert. This doc is the suite's
ground truth: the **iLok-blocked-headless reality**, the measured **"even the Equalizer's EQ doesn't engage"**
finding, the per-module headless substitute, and the **DAW-bounce → measure** workflow. The DAW-only skills below
([[ozone-11-maximizer]], [[ozone-11-equalizer]], [[ozone-11-imager]], [[ozone-11-match-eq]]) are the workflows
over it.

> **Same story for Ozone 10.** Ozone 10 is the older twin — identical NI/iLok licensing, same headless block.
> Everything below applies to both; substitute "10" for "11" throughout.

---

## TL;DR (the headline — read this first)

1. **No Ozone 11 module works in the headless pipeline here.** Maximizer / Dynamics / Imager / Match EQ / Dynamic
   EQ / Vintage Limiter/Comp/EQ/Tape / Stabilizer / Low End Focus / Spectral Shaper / Impact / Master Rebalance /
   Clarity all **hang on iLok authorization** in an unattended no-GUI Pedalboard subprocess (probe: `LOAD-FAIL` /
   timeout). The **Equalizer is the ONLY module that even "loads"** — but **measured, its EQ does not engage
   headless**: enabling any band + setting gain produced **0 dB change** on every band; only the **locked output
   gain** at an extreme (`−144 dB` ≈ mute) responded, which is exactly why a **naive probe falsely reports the
   Equalizer "RENDERS"** (it "changed" by muting, not by EQ'ing). **So all Ozone 11 modules are DAW-only here.**
   Cause: iZotope's Native Instruments / iLok licensing won't satisfy in a headless subprocess.
2. **Never insert an Ozone module in the pipeline.** Do not run any Ozone 11 module through `[L] apply-vst-chain`
   / the [[vst-preset]] harness — the blocked modules hang the render, and the Equalizer ships an unprocessed copy
   (or an all-or-nothing mute via the locked output gain) plus a false `changed:true`. There is deliberately **no
   `presets/vst/ozone-11-*.json`** for any module.
3. **Use it in the DAW; hand the bounce to the pipeline.** Dial the chain on the master bus, **print/bounce to a
   24-bit WAV**, drop it in `projects/<track>/masters/` (or `mix/`), then re-enter ship-studios to measure /
   verify compliance / export. Ozone is the *creative + GUI* mastering stage; ship-studios is *measurement +
   delivery*.
4. **Each module has a verified-headless substitute** (table below) — most map to a FabFilter or pure-DSP tool
   that renders here.
5. **Meters own the deliverable** (Gemini hears ~16 kbps mono, under-reads highs / over-reads lows): judge any
   Ozone bounce with `[L] measure-loudness` (LUFS/TP/PLR), `measure-spectrum` (tilt/centroid), `measure-stereo`
   (correlation/mono-sum), `check-clipping`, and `[G] check-streaming-targets` (pure DSP, **no key**) — never the
   plugin's own readout, and never a mono "dark"/"boomy" vibe ([[gemini-audio-understanding]]).

---

# Part A — measured on this rig

Probe: each `Ozone 11 <Module>.vst3` loaded via Pedalboard (stemmy-loops `vst` extra) in an isolated headless
subprocess, processing a drum/mix bus + a synthetic sine. The whole-suite `Ozone 11.vst3` behaves like its
modules (iLok block).

### The verdict: blocked, except an Equalizer whose EQ is inert

| module | load | engage (audio) | reading |
|---|---|---|---|
| **Maximizer** | `LOAD-FAIL` / timeout | — | iLok hangs at authorization in the no-GUI subprocess |
| **Dynamics** | `LOAD-FAIL` / timeout | — | same |
| **Imager** | `LOAD-FAIL` / timeout | — | same |
| **Match EQ** | `LOAD-FAIL` / timeout | — | same (and the Learn step is GUI-bound anyway) |
| **Dynamic EQ** | `LOAD-FAIL` / timeout | — | same |
| **Vintage Limiter / Comp / EQ / Tape** | `LOAD-FAIL` / timeout | — | same |
| **Stabilizer / Low End Focus / Spectral Shaper / Impact / Master Rebalance / Clarity** | `LOAD-FAIL` / timeout | — | same |
| **Equalizer** | **loads** | **EQ inert — 0 dB per band** | only the **locked output gain** responds (`−144 dB` = mute) |

**The Equalizer false positive.** A naive render-probe sets *some* parameter, renders, and flags `changed:true`
if the output differs. On the Ozone Equalizer the only parameter that moves the output is the **locked output
gain** — push it to `−144 dB` and the file goes to silence, which trips `changed:true` and the probe prints
**"RENDERS"**. But **enable any EQ band and set a real gain (e.g. +12 dB @ 1 kHz) and the spectrum does not move —
0 dB on every band.** The EQ DSP never engages; only the master output trim does. So the Equalizer is **DAW-only**
exactly like the iLok-blocked modules — the "RENDERS" is a mute-via-output-gain artifact, not working EQ. This is
the **"loads ≠ renders"** trap (`docs/vst/README.md`) in its subtlest form: it loads, it *appears* to render, and
it still does nothing useful.

> **Verify it yourself** with [[vst-verify]]: the decisive test for the Equalizer is **enable a band + set a
> large gain → `[L] measure-spectrum`** (0 dB band change = inert). For the rest, a `LOAD-FAIL`/timeout is the
> block. A bare `changed:true` is **never** sufficient proof for an Ozone module.

---

# Part B — per-module headless substitute

For each Ozone job, the verified-headless tool/skill that renders here and does the same thing:

| Ozone 11 module | What it does | Headless substitute (renders here) |
|---|---|---|
| **Maximizer** | IRC true-peak brickwall limiter / loudness | [[fabfilter-pro-l-2]] (true-peak, no-iLok) · pure-DSP `[L] render-mastered` limiter ([[master-track]]) |
| **Equalizer** | 8-band post / dynamic / M-S EQ | [[fabfilter-pro-q-4]] (surgical/dynamic/spectral/M-S) · pure-DSP `[L] apply-eq` |
| **Imager** | 4-band multiband stereo width + mono-maker | `[L] adjust-stereo` (graduated bass mono-maker + M/S width) |
| **Match EQ** | learn a reference curve, match to it | [[reference-match]] / [[house-curve]] (pure-DSP `[L] match-eq`) |
| **Dynamics / Vintage Comp** | multiband / bus compression | [[vst-compress]] (FabFilter Pro-C, SSL Bus Comp, etc.) · pure-DSP `[L] multiband-compress` |
| **Vintage Tape** | tape warmth/glue | [[studer-a800]] / [[ampex-atr-102]] · pure-DSP `[L] saturate-loop` |
| **Dynamic EQ** | level-dependent band EQ | [[dynamic-eq]] (pure DSP) · [[fabfilter-pro-q-4]] dynamic bands |
| **Spectral Shaper / Stabilizer** | dynamic harshness / resonance taming | [[de-harsh]] (pure DSP) · [[fabfilter-pro-q-4]] spectral mode |
| **Low End Focus / Impact / Master Rebalance / Clarity / Vintage Limiter** | low-end clarity / transient / rebalance / loudness | **DAW-only** — no exact headless twin; approximate with `[L] shape-bands` (transient), `[L] multiband-compress` (low-end), or a FabFilter chain, then measure |

The headline four — Maximizer, Equalizer, Imager, Match EQ — each carry a dedicated DAW-only skill
([[ozone-11-maximizer]], [[ozone-11-equalizer]], [[ozone-11-imager]], [[ozone-11-match-eq]]); the rest route
through the substitute above.

---

# Part C — the DAW-bounce → measure workflow (the part that matters here)

Because every Ozone module is DAW-only in this environment, the workflow is **hand-off, not insert**:

1. In the DAW, build the Ozone chain on the master bus (or use the assistant), dial it to taste.
2. **Print/bounce to a 24-bit WAV** → `projects/<track>/masters/<track>_ozone.wav`.
3. **Measure** the bounce with pure-DSP meters:
   - `[L] measure-loudness` — LUFS-I to target, true-peak ≤ ceiling, PLR not crushed.
   - `[L] measure-spectrum` — tilt / centroid / 5-band moved as intended (no surprise 2–5 kHz rise).
   - `[L] measure-stereo` — correlation / mono-sum loss (Imager moves are mono-fold risks).
   - `[L] check-clipping` — no inter-sample clip / DC.
4. **Streaming compliance** — `[G] check-streaming-targets` (Spotify/Apple/YouTube/Tidal; pure DSP, **no key**).
   Re-bounce if a platform will attenuate.
5. **A/B honestly** — `[L] render-ab` (loudness-matched) dry vs the Ozone bounce so the verdict isn't just
   "louder"; optionally `[G] compare-to-reference` on the matched pair.
6. **Deliver** — `[L] export-deliverables` (presets + tags) / [[delivery-qc]].

If you don't want the DAW round-trip at all, build the master entirely from the substitutes (Part B) — e.g.
[[fabfilter-pro-q-4]] → [[vst-compress]] → [[fabfilter-pro-l-2]], all of which render here — via [[vst-master]] /
[[master-track]].

---

## Pitfalls & gotchas

- **#1: the Equalizer's "RENDERS" is a false positive.** It changed because the locked output gain muted it, not
  because the EQ engaged. Always verify the Equalizer per-band, never on `changed:true`.
- **The other modules hang the render** — an iLok-blocked module in `apply-vst-chain` times out the call; don't
  put any Ozone module in a chain.
- **No `presets/vst/ozone-11-*.json`** exists by design — there's nothing safe to save.
- **Imager widening collapses in mono** — when you do bounce an Imager move from the DAW, `[L] measure-stereo` and
  mono-sum the bounce; keep the lows mono.
- **Match EQ at 100% sounds wrong** — and its Learn step is GUI-only; the pure-DSP [[reference-match]] is usually
  the better answer regardless.
- **Don't loudness-paper a broken mix** — diagnose with [[mix-check]] first; Ozone is the last stage, not a fix.
- **Mono codec lies about tone** — don't EQ off a Gemini "dark"/"boomy" call; confirm tilt/centroid against
  `[L] measure-spectrum` ([[gemini-audio-understanding]]).

---

## When to use Ozone vs the headless substitutes

| Want | Use |
|---|---|
| The Ozone assistant / a specific Ozone module, hands-on | **Ozone in the DAW** → bounce → pipeline (this doc) |
| Limiting *inside* the pipeline | [[fabfilter-pro-l-2]] · pure-DSP [[master-track]] |
| EQ *inside* the pipeline | [[fabfilter-pro-q-4]] · `[L] apply-eq` |
| Reference match *inside* the pipeline | [[reference-match]] / [[house-curve]] |
| Stereo width / mono-maker *inside* the pipeline | `[L] adjust-stereo` |
| A whole plugin master *inside* the pipeline | [[vst-master]] (FabFilter chain) · pure-DSP [[master-track]] |

---

## Sources

iZotope Ozone 11 product/module documentation (izotope.com) for the module roster (Maximizer, Equalizer, Imager,
Match EQ, Dynamics, Dynamic EQ, the Vintage modules, Stabilizer, Low End Focus, Spectral Shaper, Impact, Master
Rebalance, Clarity) and the NI/iLok licensing model · the headless-safe doctrine + "loads ≠ renders" trap
cross-referenced from [`README.md`](README.md), [`tape-j-37.md`](tape-j-37.md) (the passthrough archetype) and
[`izotope-rx.md`](izotope-rx.md) (the De-hum passthrough) · plus **our own Pedalboard load + render measurements**
on each `Ozone 11 *.vst3` (Part A) — the iLok block on every module and the Equalizer's inert-EQ /
mute-via-output-gain false-RENDERS finding.
