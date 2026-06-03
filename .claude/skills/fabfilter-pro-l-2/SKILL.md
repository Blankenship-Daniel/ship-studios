---
name: fabfilter-pro-l-2
description: "Use when running FabFilter Pro-L 2 to limit / maximize loudness / hit a true-peak ceiling on a master or loud bus — 'Pro-L 2', 'FabFilter limiter', 'limit this', 'maximize loudness', 'get it to -14 LUFS', 'true-peak limit to -1 dBTP', 'make it loud / competitive', 'brickwall the master', 'which Pro-L style'. The measured, plugin-specific deep-dive of [[vst-master]] — a true-peak brickwall limiter with 8 styles (Transparent/Punchy/Dynamic/Allround/Aggressive/Modern/Bus/Safe), LUFS+dBTP metering, oversampling and dither, grounded in the real 37-param Pedalboard surface + render results in docs/vst/fabfilter-pro-l-2.md. Renders headless, no-iLok. The VST alternative to render-mastered's limiter. Stemmy MCP, the `vst` extra."
argument-hint: <audio.wav> [target: -14lufs|-9lufs|loud|clean] [style]
---

# fabfilter-pro-l-2 — drive FabFilter Pro-L 2 (measured)

The plugin-specific, measured workflow for **FabFilter Pro-L 2** (`/Library/Audio/Plug-Ins/VST3/FabFilter
Pro-L 2.vst3`) — a **true-peak brickwall limiter / loudness maximizer**, the **final** stage of a master. The
VST limiter of [[vst-master]] and the boutique alternative to the pure-DSP limiter inside `[L] render-mastered`.
Full field guide — real param surface, the style crest map, the true-peak proof, recipes, our numbers, sources —
[`docs/vst/fabfilter-pro-l-2.md`](../../../docs/vst/fabfilter-pro-l-2.md). This skill is the workflow.

## The governing facts (read first)

1. **It limits headless and it's no-iLok.** Loads + renders via Pedalboard; FabFilter = simple license key (no
   iLok/dongle, offline, 3 machines) → a clean render-farm candidate. Driving **`gain`** in (+0→+12) holds peak
   at the ceiling while **crest falls 14.6 → 8.1**. Use the **VST3** path (an AU twin is also installed).
2. **A LIMITER OWNS THE CEILING — render it faithfully.** The `presets/vst/apply_vst_preset.py` harness
   *peak-normalizes its output*, which re-scales the limiter and pushes true-peak back **over** the ceiling —
   **never use it for Pro-L 2.** Use **`[L] apply-vst-chain`** (writes plugin output unchanged) with a saved
   **`.state`** blob (the enums) + a per-track **`gain`** float override (applied after `state_path`). Verified
   faithful: state + `gain:9` → **−1.018 dBTP** ✓.
3. **True Peak Limiting is the streaming-compliance control (measured).** Ceiling −1.0: **TP on → −1.018 dBTP
   (compliant); TP off → −0.984 dBTP (over)** despite sample-peak −0.99. **Turn TP on for any dBTP delivery** —
   sample-peak limiting alone leaks inter-sample peaks.
4. **Enums need the `.state`/setattr; only numerics take the float dict.** `gain`/`output_level`/`lookahead`/
   `attack`/`release`/`channel_link_*` are settable via `apply-vst-chain` `parameters`; **`style`/`oversampling`/
   `dithering`/`true_peak_limiting`/`noise_shaping` are string/bool enums → a `.state` blob or a Pedalboard
   `setattr` script (the `apply_vst_preset.py` setattr path, but NOT its renormalizing render).** A bare load
   restores the last GUI state — set everything explicitly. **Meters own it** (Gemini mono): `[L] measure-loudness`
   (LUFS-I + dBTP + crest), `[G] check-streaming-targets`.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G] check-streaming-targets`
  / `measure-loudness` to verify compliance.
- **`FabFilter Pro-L 2.vst3`** — confirm with `[L] list-vst-plugins {name_contains:"Pro-L 2"}` (take the **VST3**).
  Screen a new install with `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "Pro-L 2"`. No-iLok,
  but **loads ≠ renders** — always measure dBTP/LUFS after.
- Ready config: `presets/vst/fabfilter-prol2-streaming-master.{state,json}` (Transparent / −1.0 dBTP / TP on / 4×
  OS / dither off). Regenerate the `.state` for another style/ceiling via Pedalboard `setattr` + `p.raw_state`.

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-loudness` on the source (integrated LUFS, crest, dBTP). This sets how much `gain`
   you'll need. Pro-L 2 is the **last** insert — run it after EQ/comp/saturation, not before.
2. **Pick the ceiling + style.** Ceiling = the platform's max true-peak: **−1.0 dBTP** (Spotify/Apple/YouTube/
   EBU R128), **−2.0 dBTP** (broadcast/ATSC). Style by intent (table below). The shipped `.state` is Transparent
   −1.0 / TP on / 4× OS; regenerate it for a different style.
3. **Render faithfully** with `[L] apply-vst-chain {path, out_path:"projects/<track>/masters/<name>_prol2.wav",
   plugins:[{plugin_path:".../FabFilter Pro-L 2.vst3", state_path:"presets/vst/fabfilter-prol2-streaming-master.state",
   parameters:{gain:<dB>}}]}`. Estimate `gain` ≈ (target LUFS − source LUFS); a light streaming master is often
   ~1 dB GR.
4. **Verify + iterate to target.** `[L] measure-loudness`: integrated LUFS within ±1 LU of target, **dBTP ≤ ceiling**;
   `[G] check-streaming-targets` for per-platform compliance. Off target → adjust `gain` and re-render (step 3).
5. **Dither LAST, at the final bit depth** — keep Pro-L 2's dither **Off** and let `export-deliverables` /
   `render-mastered` dither once at the export depth, OR (if Pro-L 2 writes the final file) regenerate the `.state`
   with `dithering` = the output depth (16 Bits for 44.1/16). Never dither twice.
6. **A/B loudness-matched** ([[level-match]] / Pro-L 2 Unity Gain) so "louder" isn't mistaken for "better." Hand
   off to `export-deliverables` for the format matrix + tags.

## Style table (measured density @ +9 gain · manual character)

| Style | crest | Use it for |
|---|---|---|
| **Aggressive** | 9.49 (densest) | maximum loudness — EDM / rock / dance, pushed |
| Transparent | 9.88 | clean masters, no pumping/color |
| Dynamic | 9.93 | preserve punch (enhances transients before limiting) |
| Allround | 9.95 | balanced loudness vs transparency, any material |
| **Bus** | 9.97 | a drum bus / single track — deliberate glue + pump (the screenshot's pick) |
| Punchy | 9.97 | apparent, a little vibey pump |
| Safe | 10.37 | distortion-free at all costs (not aimed at loudness) |
| **Modern** | 10.56 (most dynamic) | the v2 default "best for all" — clean + loud |

Meters rank *density* (Aggressive squashes most, Modern/Safe keep the most transient); the pump/glue *feel* is
perceptual — A/B loudness-matched when style character (not just loudness) matters.

## Outputs

- `projects/<track>/masters/<name>_prol2.wav` + the reusable `.state` (and a per-track gain in the call/log).

## Reporting to the user

State the style + ceiling, the `gain` applied, before→after **integrated LUFS / true-peak dBTP / crest**, that it
ran headless (no-iLok), and per-platform compliance. A/B loudness-matched so taste isn't a level illusion.

## Pitfalls

- **Don't post-normalize the render** (defeats the true-peak ceiling) — use `apply-vst-chain`, not the
  renormalizing `apply_vst_preset.py`.
- **TP off leaks inter-sample peaks** — turn True Peak Limiting on for any dBTP target.
- **Dither once, at the end, at the final depth** — keep Pro-L 2 dither Off if a later stage dithers.
- **`gain` is per-track** — measure the source, set gain to the LUFS target, re-measure; don't bake a fixed gain.
- **Enums (style/OS/dither/TP) can't be set by the float dict** — use the `.state` blob (or regenerate it).
- **Oversampling** 4× is a fine offline default; bump to 16×/32× for a final master bounce (slower).
- **It's the FINAL stage** — never put a limiter mid-chain or on the mix bus before mastering; that's [[finalize-mix]].

## Related

- [`docs/vst/fabfilter-pro-l-2.md`](../../../docs/vst/fabfilter-pro-l-2.md) — the full measured field guide
- [[vst-master]] — the generic plugin mastering-chain skill this is the limiter for · [[vst-chain]] / [[vst-preset]]
  / [[vst-verify]] · [[vst]] — index/doctrine
- Pure-DSP alternative (no plugin, auto-targets LUFS+ceiling): `[L] render-mastered` / [[master-track]] ·
  [[batch-master]] (album) · `[G] check-streaming-targets` for per-platform compliance
- [[fabfilter-pro-q-4]] — its FabFilter EQ sibling (also no-iLok, also flatten/state-first) ·
  [[gemini-audio-understanding]] — why meters (not Gemini) own loudness/peak
