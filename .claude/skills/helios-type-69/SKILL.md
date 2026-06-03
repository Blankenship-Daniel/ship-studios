---
name: helios-type-69
description: "Use when running the UAD/UADx Helios Type 69 Preamp and EQ for warm, characterful British-console tone or colour on drums, bus, bass, guitar, or vocals — 'Helios Type 69', 'Helios EQ', 'that Olympic Studios / Led Zeppelin console sound', 'warm vintage British EQ', 'drive the preamp for colour', 'use the Helios', or when you want its passive-style 3-band EQ + transformer-preamp saturation dialed for warmth/glue. The measured, plugin-specific deep-dive of [[vst-eq]] / [[vst-channel-strip]] (a preamp+EQ, no compressor) — grounded in the real 14-param surface + isolation/drive/EQ numbers in docs/vst/helios-type-69.md. A WARM, rock-leaning British counterpart to [[kit-bb-n105]] (Neve) and the cleaner [[ssl-4k-e]]. Stemmy MCP, the `vst` extra. UADx native (no iLok)."
argument-hint: <audio.wav> [goal: warm-glue|clean-eq|air|de-box|tighten|colour]
---

# helios-type-69 — drive the UADx Helios Type 69 Preamp & EQ (measured)

The plugin-specific, measured workflow for the **UADx Helios Type 69 Preamp and EQ**
(`/Library/Audio/Plug-Ins/VST3/uaudio_helios_type_69.vst3`) — UA's model of the **passive-EQ + valve/
transformer preamp** channel from the late-'60s **Helios console** (Dick Swettenham / Olympic Studios; Zeppelin,
Hendrix, the Stones). It's a **preamp + 3-band EQ, no compressor** — the warm, characterful, slightly "rock"
British member of [[vst-eq]] / [[vst-channel-strip]], next to the Neve-flavoured [[kit-bb-n105]] and the clean
[[ssl-4k-e]]. Full field guide — real param surface, footguns, recipes, our numbers, sources —
[`docs/vst/helios-type-69.md`](../../../docs/vst/helios-type-69.md). This skill is the workflow.

## The governing facts (read first — all measured on this rig, Pedalboard 0.9.23)

1. **Renders headless — use the `uaudio_` build.** `uaudio_helios_type_69.vst3` loads + processes (UADx native).
   The `UAD Helios Type 69.component` / `… Legacy.component` twins are the **passthrough** offline build — never
   load those ([[vst-verify]]). UADx native = **no iLok** needed for the render.
2. **`gain` is a TONE control, not just level — it's the drive/colour.** Measured on a 1 kHz tone: Line g20 =
   **0.002 % THD** (clean), Mic g20 = 0.049 %, **Mic g40 = 53 %**, Mic g70 = 61 % — **even-harmonic dominant**
   (transformer/tube warmth, 2nd harmonic −8 dB at g40). `gain` saturates in **both** modes; **Mic reaches it
   ~10–20 dB sooner** than Line (Mic g30 ≈ Line g40 ≈ 27–32 % THD). Driving it thickens the low end and softens
   transients (drum crest 14.6 → 7.8 at Mic g40 with no pad).
3. **The −20 dB pad is what makes the drive MUSICAL on line-level signals.** Mic g40 with no pad on a line-level
   drum loop is nuclear (53 % THD, peak +0.65 dBFS). The **input pad** attenuates before the gain stage, so
   **Mic g40 + pad** lands at a gentle ~1.9 % THD, crest 14.6 → 13.1 — moderate, glued warmth. Pad up the gain
   for colour, pad off / gain 50+ to push harder.
4. **The bass BOOST is unreachable headless — only the CUT renders.** The `bass` knob's boost positions
   (60/120/250/400 Hz) produce **exactly 0.00 dB** change via Pedalboard (Line *and* Mic); `bass_gain` is
   hard-locked to its only value `'Off'`. The negative `bass` values (−3…−15) **do** render — a broad low-shelf
   **cut/tighten**. **For low-end WEIGHT, lean on the Mic drive (it fills the lows) or boost with `[L] apply-eq`.**
5. **Peak/Trough is nonlinear (footgun).** Peak (boost) honours `mid_gain` 1:1 (8 → +8.2 dB). **Trough (cut)
   remaps far smaller** — `mid_gain 8` → a true ~−2.1 (only ≈−1.3 dB cut); push toward **12–15** for a real cut
   (12 → −4.1 dB). Always set `mid_type` **first**, then read back `mid_gain` (`getattr`) for the true value.
6. **All 14 params are enums → drive it with the [[vst-preset]] harness, not `apply-vst-chain`'s float dict.**
   The string enums (`input_select`, `mid_type`, `pad`, `eq_in`, `polarity`, `power`) can't be set float-only —
   and those are exactly the colour/character switches. **Meters own it** (Gemini hears mono): read centroid /
   tilt / crest / band-ratios, not vibes.

## Prerequisites

- `[L] apply-vst-chain` / `list-vst-plugins` (`uv sync --extra vst` in `../stemmy-loops-mcp`). `[G]` perceptual
  tools (optional, `GEMINI_API_KEY`) for an A/B read.
- Confirm the build: `[L] list-vst-plugins {name_contains:"Helios"}` → take the **`uaudio_helios_type_69.vst3`**
  path. Screen with `../stemmy-loops-mcp/.venv/bin/python presets/vst/probe_plugin.py "helios"` (expect `RENDERS ✓`).
  Dump the live surface any time: `… presets/vst/dump_params.py uaudio_helios_type_69`.
- **It loads ≠ it rendered** — always re-measure detail after (a 0.00 spectrum/crest delta = the `.component`
  passthrough twin loaded instead).

## The parameter surface (14 enums — authoritative)

| Param | Values | What it does (measured) |
|---|---|---|
| `input_select` | `Line` · `Mic` | clean path vs the **colour** path (Mic saturates ~10–20 dB sooner) |
| `gain` | 20·30·40·50·60·70 dB | preamp **drive/colour** (+ a lot of level) — clean at 20, heavy by 40 |
| `pad` | `Off` · `-20 dB` | input pad **before** the gain stage — tames the drive level (use it with high gain) |
| `hi_shelf_gain` | −16…+12 (steps of 4) | broad **10 kHz high shelf** (asymmetric: boosts to +12, cuts to −16; hinges low ~1–2 kHz) |
| `mid_freq` | 700·1000·1400·2000·2800·3500·4500·6000 Hz | mid bell centre |
| `mid_type` | `Peak` · `Trough` | mid **boost** (Peak) vs **cut** (Trough) — see the nonlinear-gain footgun |
| `mid_gain` | 0 … ~15.3 | mid amount — 1:1 in Peak; remapped (needs 12–15) in Trough |
| `bass` | 400·250·120·60 · 0 · −3…−15 | boost-freq (**inert headless**) / flat / **low-shelf cut** (works) |
| `bass_gain` | `Off` (only) | vestigial / locked — the reason the boost is unreachable |
| `eq_in` | `In` · `Byp` | EQ engage (preamp still passes when `Byp`) |
| `polarity` | `Normal` · `Inverted` | phase flip |
| `level` | −inf … +10 dB | output fader (pull down to offset the drive's level if not normalizing) |
| `power` | `True`/`False` · `master_bypass` `False`/`True` | unit power / plugin bypass |

## Recipe (ordered — measured)

1. **Baseline** — `[L] measure-spectrum` (third-octave + tilt + centroid + 5-band) + `[L] measure-loudness`
   (crest/PLR). The "before" column. Decide the job: **colour/warmth/glue** (→ Mic drive) or **clean EQ** (→ Line).
2. **Pick the path.** *Warmth/glue:* `input_select="Mic"`, `gain` 30–40, `pad="-20 dB"` (start g40+pad ≈ 1.9 %
   THD / crest −1.5). *Clean EQ:* `input_select="Line"`, `gain=20`, `pad="Off"` (0.002 % THD — pure EQ).
3. **Dial the EQ** from the move table. Treble = the broad 10 k shelf; mid = Peak boost or Trough (≥12) cut at a
   selected `mid_freq`; bass = **cut/tighten only** (boost is inert — use Mic drive or `apply-eq` for weight).
4. **Build a preset** (`presets/vst/helios-type-69-*.json`) setting **all** params explicitly, and apply with
   the harness: `../stemmy-loops-mcp/.venv/bin/python presets/vst/apply_vst_preset.py <preset.json> <in>
   projects/<track>/mix/<stem>_helios.wav` (it `setattr`s string enums and peak-normalizes the output, which
   absorbs the drive's level boost). Set `dump_state=true` via `apply-vst-chain` once dialed for a byte-stable re-render.
5. **Prove it** — re-`measure-spectrum`/`measure-loudness`. **Warmth/drive → crest DOWN + harmonics up + low
   fill**; **clean EQ → crest UP** (the tell), centroid/tilt move with the shelves. A 0.00 delta = passthrough twin.
   A/B loudness-matched ([[level-match]] / `[L] render-ab`).
6. **QC** — `[G] detect-mix-issues` / `mastering-feedback` (genre/intent set) for over-drive (harsh/distorted) or
   over-air; cross-check any mono "dark/harsh" flag against the meters ([[gemini-audio-understanding]]).
   It's a per-track/bus colour+EQ insert, not a master — hand the result to [[master-track]] for loudness.

## Move table (measured)

| Goal | Helios move |
|---|---|
| **Warm/glue a drum bus** ★ | `Mic`, `gain 40`, `pad -20`, `hi_shelf +4` → crest 14.6→13.1, +4–5 dB air, slight low fill (the shipped `helios-type-69-warm-drum-glue` preset). |
| **Thick & dark** | `Mic`, `gain 40`, `pad -20`, `hi_shelf 0` (centroid drops to ~168 Hz — pure preamp warmth, no air). |
| **Subtle console colour** | `Mic`, `gain 30`, `pad -20` (~0.24 % THD, crest barely moves) — a hint of character. |
| **Clean air + tighten** ★ | `Line`, `gain 20`, `hi_shelf +4`, `bass -3`, `mid Trough 700/12` → crest 14.6→16.0 (clean), +5 air, de-boxed (the shipped `helios-type-69-clean-air-tighten` preset). |
| **Add air/presence** | `hi_shelf +4…+8` (broad shelf from ~1–2 kHz up); pair with de-ess on bright sources or it can spit. |
| **De-box / de-honk a mid** | `mid_type Trough`, pick `mid_freq` (700 box, 1–2 k honk), `mid_gain 12–15` (Trough needs it high). |
| **Add presence/bite** | `mid_type Peak`, `mid_freq 2.8–4.5 k`, `mid_gain 4–8` (1:1, broad bell). |
| **Tighten low end** | `bass -3…-9` (broad low-shelf cut). |
| **Low-end WEIGHT** | **not via `bass`** (boost inert) — use the `Mic` drive (fills lows) or a separate `[L] apply-eq` low-shelf boost. |

## Outputs

- `projects/<track>/mix/<stem>_helios.wav` + the reusable `presets/vst/helios-type-69-*.json` (and `.state` if dumped).

## Reporting to the user

State the path (Line clean vs Mic-driven + gain/pad), the EQ moves (treble/mid Peak-or-Trough+freq/bass-cut), the
before→after **crest / centroid / tilt / target-band deltas** (crest direction = colour vs clean), that it ran
headless via the `uaudio_` build, and the preset/`.state` path. A/B loudness-matched so warmth isn't a level illusion.

## Pitfalls

- **Wrong build = silent passthrough** — load `uaudio_helios_type_69.vst3`, not the `UAD …`/`Legacy .component` twins.
- **Float dict can't drive it** — string enums (Mic/Trough/pad/eq_in) need the [[vst-preset]] harness.
- **Bass boost does nothing headless** — only the cut renders; get weight from Mic drive or `apply-eq`.
- **Trough cut under-applies** unless `mid_gain` is pushed to ~12–15 (set `mid_type` first, read back).
- **Drive adds (uncompensated) level** — normalize (the harness does) or pull `level`, then A/B level-matched, or
  "warmer" is just "louder".
- **Mic + high gain on a hot signal distorts** — use the −20 pad, lower gain, or feed a quieter level.
- It's a colour+EQ insert, **not** mastering — keep it off the 2-bus loudness stage ([[master-track]]).

## Related

- [`docs/vst/helios-type-69.md`](../../../docs/vst/helios-type-69.md) — the full measured field guide (Part A measured + Part B history/usage, cited)
- [[vst-eq]] / [[vst-channel-strip]] — the generic skills this specializes · [[vst-saturate]] — its drive is preamp saturation ·
  [[vst-preset]] — apply enum/all-explicit chains · [[vst-verify]] — prove the build renders · [[vst-chain]] — the backbone · [[vst]] — index/doctrine
- Warm/colour siblings: [[kit-bb-n105]] (Neve 8078, warm) · [[ssl-4k-e]] (clean British) · [[api-vision-channel-strip]] / [[kit-bb-a5]] (punchy API) · [[studer-a800]] / [[ampex-atr-102]] (tape warmth)
- Pure-DSP twins (no plugin): tube/tape colour → `[L] saturate-loop`; air/presence → [[excite]]; surgical/tilt EQ → `[L] apply-eq`; low-end weight → `[L] apply-eq` / [[sub-design]]
- [[mix-check]] (find the problems first) · [[warm-drum-bus]] / [[drum-stems-warm-loops]] (where a warm console colour fits) · [[vst-verify]] (why the build matters)
