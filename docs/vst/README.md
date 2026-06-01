# VST plugins in ship-studios — the headless-safe reference

The `[[vst]]` skill suite runs your installed **third-party VST3 / Audio Unit effect** plugins
inside the pipeline via the `[L] apply-vst-chain` tool (Pedalboard, the `vst` extra) — fully
**offline & headless** (no DAW, no GUI, no audio device). This doc is the suite's ground truth:
what's safe to use, why, and the strong candidates per task.

## What "headless-safe" means

A plugin is **headless-safe** when it *instantiates in an unattended, no-GUI process* on this Mac —
so `apply-vst-chain` can load and render through it without a window, a dialog, or a hang. This was
established empirically: every installed VST3/AU was load-tested via Pedalboard in an isolated,
timeout-guarded subprocess. **779 of 944 loadable titles passed.**

⚠️ **This is a *load* probe — loads ≠ renders.** A title can load yet pass audio through unprocessed
(notably the UAD `.component` build) or ignore its parameters. Before trusting a plugin, confirm it
actually *processes* with `[[vst-verify]]` (a parameter-response probe). The list below over-counts.

- Full raw list: [`../../demo/headless-safe-titles.txt`](../../demo/headless-safe-titles.txt) (779 titles)
- Full table + the blocked set with reasons: [`../../demo/installed-plugins-headless-safe.md`](../../demo/installed-plugins-headless-safe.md)

**Skills must only ever suggest a plugin that appears in that list.** Confirm the on-disk path at
run time with `[L] list-vst-plugins {name_contains}` before calling `apply-vst-chain` — and for UADx
prefer the `uaudio_*.vst3` build. When in doubt a plugin renders (vs just loads), screen it with `[[vst-verify]]`.

## Caveats (carry these into every skill)

- **Non-deterministic & opt-in.** Unlike the pure-DSP tools, this loads an external binary whose
  output isn't reproducible across plugin versions. Pin versions; persist `dump_state` blobs.
- **A clean load ≠ a valid render.** A plugin can instantiate yet pass audio through or ignore its
  params (demo/unlicensed, or the UAD `.component` build). Always **re-measure detail** after applying —
  spectrum / crest / tilt, not just `changed:true`/LUFS; a **0.00 change = passthrough**. Screen with `[[vst-verify]]`.
- **UAD has two builds (critical).** `/Library/Audio/Plug-Ins/VST3/uaudio_*.vst3` (UADx native) **renders
  headless**; the `/Components/UAD ….component` and `/VST3/Universal Audio/UAD ….vst3` twins **pass audio
  through unprocessed** offline — they ignore params even when authorized. **Always load the `uaudio_*.vst3`
  path.** Candidate names below written `UAD …` mean the `uaudio_*` build.
- **Gain-stage analog units.** Tube comps / tape / consoles need ~+18 dB into the chain to engage;
  `apply-vst-chain` has no gain-stage → use `[[vst-preset]]` for chains that need drive.
- **Format/OS.** VST3 is cross-platform; **AU (`.component`) is macOS-only**. Prefer VST3 paths.
- **Blocked classes** (will *not* render unattended here): iLok-gated vendors not machine-authorized
  (**Slate Digital**, **Eiosis**, part of **iZotope**), **UAD-2 DSP** (needs Apollo hardware), and
  **UAD Spark** subscriptions (cloud/dongle). UA *perpetual native UADx* are fine — via `uaudio_*.vst3`.

## Strong candidates by task (all confirmed headless-safe on this Mac)

Pick from these first; fall back to the raw list. Names are exact (feed to `list-vst-plugins`).

| Task | Confirmed-safe candidates | Skill |
|---|---|---|
| **Channel strip / console** | `British Channel`, `bx_console SSL 4000 E`, `bx_console AMEK 200`, `SSL Native Channel Strip 2`, `UAD API Vision Channel Strip`, `UAD Neve 1073` | `[[vst-channel-strip]]` |
| **EQ (vintage / surgical)** | `FabFilter Pro-Q 4`, `Maag EQ4`, `UAD Pultec EQP-1A`, `UAD Pultec MEQ-5`, `UAD Neve 1073`, `EQP-1A` | `[[vst-eq]]` |
| **Compressor / dynamics** | `Black 76`, `Comp FET-76`, `FabFilter Pro-C 2`, `SSL Native Bus Compressor 2`, `UAD Tube-Tech CL 1B`, `UAD API 2500` | `[[vst-compress]]` |
| **Tape / saturation / color** | `Tape Machine 80`, `Tape Machine 440`, `FabFilter Saturn 2`, `Airwindows Consolidated` | `[[vst-saturate]]` |
| **Reverb** | `ValhallaPlate`, `FabFilter Pro-R 2`, `SSL Native FlexVerb` | `[[vst-reverb]]` |
| **Delay / echo** | `Delay BRIGADE`, `UAD EP-34 Tape Echo`, `FabFilter Timeless 3` | `[[vst-delay]]` |
| **De-esser** | `FabFilter Pro-DS`, `SSL DeEss`, `Lindell 902 De-esser`, `De Esser` | `[[vst-de-ess]]` |
| **Limiter (master)** | `FabFilter Pro-L 2`, `Brickwall Limiter`, `TR5 Brickwall Limiter` | `[[vst-master]]` |
| **Amp / pedal (guitar/bass)** | `TONEX`, `NeuralAmpModeler`, `UAD Softube Bass Amp Room`, `UAD Softube Metal Amp Room` | `[[vst-amp]]` |

> Avoid (blocked here): `AIR Studios Reverb`, anything `Slate …`, `Eiosis …`, the clean `Ozone 11 …`
> VST3 entries (use FabFilter/SSL for mastering instead), and the `UAD ….component` build — load the
> `uaudio_*.vst3` twin instead. When unsure it renders, screen with `[[vst-verify]]`; grep the raw list.

## Presets

Saved, reusable chains live in [`presets/vst/`](../../presets/vst/README.md) — a portable recipe
(gain-stage → chain → narrow → trim) + byte-exact `.state` blobs, re-applicable to any file via
`presets/vst/apply_vst_preset.py`. Available: **`vintage-1960s`** (UADx Pultec → Fairchild 670 →
Ampex tape → period-mono; warm/dark/glued 1960s drums) and **`tight-70s`** (UADx Neve 1073 → dbx 160
→ Studer A800 @15 IPS; punchy/dry/present 1970s drums). Presets use the `uaudio_*.vst3` UADx build.

## Refresh

The inventory is a snapshot. To regenerate after installing/authorizing plugins, run `[[vst-browse]]`
(which calls `[L] list-vst-plugins` live) and re-run the load-probe that produced the two `demo/`
files. Counts as of the last scan: **779 headless-safe** of 944 loadable (4,883 bundles on disk).
