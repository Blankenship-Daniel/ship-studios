# vst-mcp/ — Ship Studios MCP plugin

A [JUCE](https://juce.com) + CMake plugin project, sibling to [`../vst/`](../vst/README.md).
One C++ source tree builds **AU**, **VST3**, and a **standalone app**.

**Status: walking skeleton.** Today this is a transparent gain trim with a
bypass. That is the point of the stage: a plugin's identity — `PLUGIN_CODE`,
`BUNDLE_ID`, parameter IDs — is what a host writes into a saved session, so
those get frozen and render-verified *before* real DSP or any MCP wiring lands
on top. `../vst/` went through the same "Ship Studios Gain" phase before it
became Distance; the difference is that Distance's rename happened before any
session referenced the old codes, which is the only safe window for it.

## Why a separate directory

`../vst/` and `vst-mcp/` are independent CMake projects with independent build
trees and independent plugin identities. They deliberately share nothing but
the pinned JUCE version — one plugin's build should never be able to break the
other's. Keep `JUCE_VERSION` in the two `CMakeLists.txt` files in lockstep;
debugging two plugins against two framework versions is a trap.

## Build

```bash
cd vst-mcp
cmake -B build                 # universal (arm64 + x86_64), the default
cmake --build build -j8
```

For faster local iteration, build native-only:

```bash
cmake -B build -D SHIPSTUDIOS_UNIVERSAL=OFF
cmake --build build -j8
```

The first configure clones JUCE into `build/_deps/` (~1 min) and compiles
`juceaide`. Both are cached; later builds skip them. Note that this is a
*separate* build tree from `../vst/build/`, so it fetches its own JUCE copy.

`COPY_PLUGIN_AFTER_BUILD` is on, so a successful build installs to:

- `~/Library/Audio/Plug-Ins/Components/Ship Studios MCP.component` (AU)
- `~/Library/Audio/Plug-Ins/VST3/Ship Studios MCP.vst3` (VST3)

Logic rescans on launch. Live rescans from Preferences → Plug-Ins. To build
without installing, set `COPY_PLUGIN_AFTER_BUILD FALSE` in `CMakeLists.txt`.

### Requirements

Command Line Tools are enough — full Xcode is **not** required, including for
the AU target.

## Verifying

The same three gates `../vst/` uses, in the order they catch problems:

```bash
# 1. Logic's own gate. Anything that fails here, Logic silently refuses to load.
auval -v aufx Smc1 Shst

# 2. Does it actually process, or just load? ("loads != renders")
../../stemmy-loops-mcp/.venv/bin/python ../presets/vst/probe_plugin.py \
    ~/Library/Audio/Plug-Ins/VST3/"Ship Studios MCP.vst3"
```

Gate 2 pushes a parameter and confirms the output responds — the `[[vst-verify]]`
doctrine, because a plugin that loads headless may still render passthrough.
For the skeleton, pushing `gain_db` off 0 dB is the meaningful probe.

Gate 3 — a DSP acceptance suite like `../vst/verify_distance.py` — does not
exist yet; there is no DSP to assert beyond "gain is gain". Add it with the
first real processing stage.

Do not run bare `auval -a` on this machine — it opens every installed AU and
takes many minutes given the plugin collection here. Always target the codes.

## Identity

Frozen from the first session that references them. Distinct from Distance's
(`Sdt1` / `com.shipstudios.distance`).

| | |
|---|---|
| Manufacturer code | `Shst` |
| Plugin code | `Smc1` |
| Bundle ID | `com.shipstudios.mcp` |

Parameters (IDs are what pedalboard and the host see; hyphens are illegal in
VST3 parameter IDs, so everything is snake_case):

| ID | Range / type | What it is |
|---|---|---|
| `gain_db` | −24 … +24 dB | Output trim; smoothed over 20 ms |
| `bypass` | bool | Host-visible bypass; rides the smoother to unity |

## Adding DSP

1. Add the parameter in `createParameterLayout()` (`PluginProcessor.cpp`), with
   a `ParameterID` version hint that never goes backwards.
2. Add processing in `processBlock()`.
3. Add a control + attachment in `PluginEditor.cpp`, binding via the
   `ShipStudiosMcpProcessor::param*` constants rather than a string literal.

State save/restore is handled by the APVTS and needs no changes. Re-run the
gates above.

## Distribution

Local builds are ad-hoc signed and load fine on this machine. Shipping to
another Mac needs a Developer ID certificate and notarization — otherwise
Gatekeeper blocks it. Not set up here.

## Files

```
vst-mcp/
  CMakeLists.txt            JUCE version pin, formats, plugin identity (codes!)
  Source/
    PluginProcessor.{h,cpp}   parameters, the signal chain, state
    PluginEditor.{h,cpp}      UI, APVTS attachments
  build/                    gitignored (also holds the fetched JUCE)
```
