# vst/ — Ship Studios' own plugins

A [JUCE](https://juce.com) + CMake plugin project. One C++ source tree builds
**AU**, **VST3**, and a **standalone app** from the same code.

This is the one part of ship-studios that isn't Python. It's here rather than in
its own repo so the build product can be render-verified by the pipeline that
will use it (`list-vst-plugins`, `apply-vst-chain`, `[[vst-verify]]`) without a
cross-repo hop.

## Why JUCE

The format matrix is the whole reason:

| DAW | Format it requires |
|---|---|
| Logic Pro, GarageBand | **AU** — Logic has never loaded VST3 |
| Ableton Live | VST3 (also AU on macOS) |
| LUNA | AU; VST3 on current versions |
| Studio One, Cubase, Reaper, Bitwig, FL, Ardour | VST3 |
| Pro Tools | AAX — **not covered**, see below |

Logic's AU-only requirement is the binding constraint. It disqualifies
Rust's nih-plug (VST3 + CLAP, no AU) regardless of that framework's other
merits. JUCE emits AU + VST3 from one codebase and cross-compiles to Windows
VST3 later without a rewrite.

**Pro Tools is not covered.** AAX needs an Avid developer agreement and PACE
signing. JUCE has an AAX target if you obtain the SDK; add `AAX` to `FORMATS`.

## Build

```bash
cd vst
cmake -B build                 # universal (arm64 + x86_64), the default
cmake --build build -j8
```

For faster local iteration, build native-only:

```bash
cmake -B build -D SHIPSTUDIOS_UNIVERSAL=OFF
cmake --build build -j8
```

The first configure clones JUCE into `build/_deps/` (~1 min) and compiles
`juceaide`. Both are cached; later builds skip them.

`COPY_PLUGIN_AFTER_BUILD` is on, so a successful build installs to:

- `~/Library/Audio/Plug-Ins/Components/Ship Studios Distance.component` (AU)
- `~/Library/Audio/Plug-Ins/VST3/Ship Studios Distance.vst3` (VST3)

Logic rescans on launch. Live rescans from Preferences → Plug-Ins.

JUCE's version is pinned in `CMakeLists.txt` (`JUCE_VERSION`, currently 8.0.15).
Bump it there — 9.0.0 exists but has API changes this code hasn't been checked
against.

### Requirements

Command Line Tools are enough — full Xcode is **not** required, including for
the AU target. Verified against AppleClang 17 / CMake 4.2.

## Verifying

Three automated gates, in the order they catch problems:

```bash
# 1. Logic's own gate. Anything that fails here, Logic silently refuses to load.
auval -v aufx Sdt1 Shst

# 2. Does it actually process, or just load? ("loads != renders")
../../stemmy-loops-mcp/.venv/bin/python ../presets/vst/probe_plugin.py \
    ~/Library/Audio/Plug-Ins/VST3/"Ship Studios Distance.vst3"

# 3. Is the DSP right? The acceptance suite: transparency at centre, latency
#    lockstep, tone/level laws, ballistics, clip aliasing, ceiling, the
#    adaptive-EQ behaviours, state round-trip.
../../stemmy-loops-mcp/.venv/bin/python verify_distance.py
```

Do not run bare `auval -a` on this machine — it opens every installed AU and
takes many minutes given the plugin collection here. Always target the codes.

**What the suite does NOT cover** (needs a live host, verify by hand in a DAW):
auto gain staging's transport-stop ending, LINKed multi-instance mirroring and
group triggers, A/B slots, host preset menus, and the editor UI itself. The
pedalboard harness runs one headless instance with no transport and no message
loop, so these are manual-only by construction.

## Current plugin: Ship Studios Distance

A distance/proximity effect: **one fader** morphs the source closer (up) or
further away (down); centre is bit-exact flat. Under the fader, in order:
input gain → a four-band distance EQ (proximity / room / presence / air) →
a compressor and transient shaper whose ballistics reverse across the fader →
loudness compensation + a 6 dB-per-doubling level law + output trim → an
ADAA-anti-aliased soft/hard clipper (close side only) → a lookahead brick-wall
limiter (~2 ms, latency reported to the host).

| | |
|---|---|
| Manufacturer code | `Shst` |
| Plugin code | `Sdt1` |
| Bundle ID | `com.shipstudios.distance` |

Parameters (IDs are what pedalboard sees; hyphens never appear in VST3 IDs):

| ID | Range / type | What it is |
|---|---|---|
| `distance` | −100 (far) … +100 (close) | The one control the plugin is about |
| `extreme` | bool | 2× the EQ / compression / transient / level amounts |
| `input_db` | −24 … +24 dB | Drive into the fixed-threshold dynamics |
| `output_db` | −12 … +12 dB | Trim after the level law |
| `ceiling_db` | −12 … 0 dB (−0.3 default) | Clip knee + limiter target (sample-peak, not dBTP) |
| `hard_clip` | bool | SOFT (tanh) vs HARD (flat-top) clip shape |
| `analyse` | bool, momentary, non-automatable | Rising edge arms the adaptive-EQ capture (the harness's trigger) |
| `gemini` | bool, non-automatable, **off by default** | Opt-in: ANALYSE may upload the capture to Google for classification |
| `bypass` | bool | Host-visible bypass; rides the smoothers, keeps latency |

### Adaptive EQ (ANALYSE)

Pressing ANALYSE captures the raw input, measures it (third-octave spectrum,
detrended peaks, rolloff knee), and moves the four band frequencies onto that
source's own features — clamped to per-band ranges so a pathological source
cannot produce a nonsense curve. Everything is measured DSP; the optional
Gemini leg (right-click menu, off by default, requires an API key) only
classifies **what** the source is and **where** the representative stretch is —
it never supplies a frequency, gain or Q, because the ~16 kbps mono codec the
API hears through makes its tonal reads untrustworthy (measured; see
`GeminiClient.h`). The measured profile is published *before* the network is
consulted, so a network failure has nothing to break. The model is
`gemini-pro-latest` (a stable alias); override with `GEMINI_MODEL` in the
environment. The API key comes from `GEMINI_API_KEY` or — because a DAW
launched from Finder has no shell environment — a plaintext per-user
properties file the UI warns about.

### UI

Simple view: the distance fader (CLOSE / FLAT / FAR scale), the live EQ-curve
display with the 5–7 kHz harshness guard marked, the ANALYSE control, 2X, and
IN/OUT drag-number trims with meters behind them. ADVANCED adds the dynamics
display (compressor transfer + stacked CMP/CLIP/LIM gain-reduction meter),
CEILING, and the SOFT/HARD clip switch. Header: presets, A/B, LINK (mirror
parameters across instances), bypass. AUTO under the input trim arms an
open-ended gain-staging scan (see the doctrine comments in
`PluginProcessor.h`).

**Gotcha if you touch the fader drawing.** Do not position anything from the
`minSliderPos` / `maxSliderPos` arguments to `drawLinearSlider`. On a
single-value slider JUCE sets both equal to `sliderPos`, so they describe a
point, not a range — using them collapses the whole scale onto one line. JUCE
insets thumb travel by `getSliderThumbRadius`, which this LookAndFeel pins to
a constant so the groove, the cap and the dB scale all derive from the same
arithmetic. The scale is drawn *inside* `drawLinearSlider` (not in the editor's
`paint()`) for the same reason: one source of truth for the mapping.

Because the slider's bounds cover the tick column as well as the groove,
`resized()` centres the *visible ink* rather than the bounds.

### Adding DSP

1. Add the parameter in `createParameterLayout()` (`PluginProcessor.cpp`).
2. Add processing in `processBlock()`.
3. Add a control + attachment in `PluginEditor.cpp`.

State save/restore is handled by the APVTS and needs no changes (the adapted
EQ profile rides along as XML attributes — see `getStateInformation`). Re-run
the three gates above.

## Distribution

Local builds are ad-hoc signed and load fine on this machine. Shipping to
another Mac needs a Developer ID certificate (~$99/yr Apple Developer Program)
and notarization — otherwise Gatekeeper blocks it. Not set up here.

## Files

```
vst/
  CMakeLists.txt          JUCE version pin, formats, plugin identity (codes!)
  Source/
    PluginProcessor.{h,cpp}   parameters, the signal chain, analysis worker, state
    PluginEditor.{h,cpp}      UI, LookAndFeel, APVTS attachments
    DistanceCurve.h           the distance model: bands, laws, ranges — shared
                              by the audio thread AND the editor's displays
    SourceAnalysis.{h,cpp}    measured adaptive-EQ analysis (pure DSP)
    GeminiClient.{h,cpp}      optional classification leg (opt-in upload)
  verify_distance.py      acceptance suite (gate 3) — run with the stemmy vst venv
  build/                  gitignored (also holds the fetched JUCE)
```
