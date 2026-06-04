# ship-studios

A centralized music creation, mixing, and mastering hub built on top of
[`stemmy-loops-mcp`](../stemmy-loops-mcp) and
[`stemmy-gemini-mcp`](../stemmy-gemini-mcp).

The two stemmy servers are narrow capability providers: one does drum-loop
extraction plus pure-DSP mix/master measurement and correction, the other
wraps Gemini's perceptual audio understanding. ship-studios is their primary
consumer — it doesn't re-implement any DSP or LLM logic. It is the place where
those primitives get composed into end-to-end pipelines (master a track,
diagnose a mix, match a reference, turn a stem into deliverables) and where
your actual project files live.

If stemmy is the toolbox, ship-studios is the studio.

## Architecture

ship-studios is an **MCP host**. It registers the two stemmy servers as
**stdio MCP subprocesses** and orchestrates calls across both:

```
                          ship-studios  (MCP host)
                                  │
              ┌───────────────────┴───────────────────┐
              │                                         │
   stemmy-loops  (stemmy-loops-mcp)        stemmy-gemini  (stemmy-gemini-mcp)
   loop extraction + DSP measurement       Gemini perceptual audio
   + EQ/comp/saturate/master/export        understanding + critique
              │                                         │
        ../stemmy-loops-mcp                    ../stemmy-gemini-mcp
        uv run stemmy-loops-mcp                uv run stemmy-gemini-mcp
```

Both servers are **sibling repos** alongside this one. ship-studios launches
each via `uv --directory <rel-path> run <console-script>` over stdio — no
network ports, no global install.

There are **two ways to consume the hub**:

1. **Interactive — Claude Code.** Open this project in Claude Code. The
   `.mcp.json` registers both servers; the `.claude/skills/` and
   `.claude/commands/` drive each pipeline conversationally (`/master`,
   `/mix-check`, …). Claude calls the MCP tools directly.
2. **Headless — the `ship-studios` CLI.** A Python package (`ship_studios/`)
   opens its own `ClientSession` to both servers and runs the same pipelines
   from the command line, with no Claude in the loop. Same tools, same order,
   scriptable.

Both paths call the *same verified tool surface* in the *same verified order*.

## Setup

Do these in order.

### 1. Clone the siblings adjacent to this repo

The hub resolves the servers by relative path (`../stemmy-loops-mcp`,
`../stemmy-gemini-mcp`), so the three repos must share a parent directory:

```
code/
├── ship-studios/        ← you are here
├── stemmy-loops-mcp/
└── stemmy-gemini-mcp/
```

### 2. Sync both server venvs

The loops server is gated behind extras — **its tools will not appear unless
you sync the extras it needs.** From `../stemmy-loops-mcp`:

```bash
# Minimal: MCP server + the mix/master measurement & render tools
uv sync --extra loops-mcp --extra mixing

# Full: every optional capability (LLM, Gemini listen, Demucs, classify, quantize, beats, viz, embed, vst)
uv sync --extra loops-mcp --extra mixing --extra llm --extra listen \
        --extra separate --extra classify --extra quantize --extra beats --extra viz --extra embed --extra vst

# Or the convenience superset for everything EXCEPT vst (separate+embed+classify+quantize+viz+llm+listen+beats):
uv sync --extra loops-mcp --extra mixing --extra ml   # add --extra vst on top if you want VST hosting
```

The `vst` extra adds `apply-vst-chain` + `list-vst-plugins` (host your own VST3/AU
*effect* plugins offline/headless via Pedalboard; VST3 cross-platform, AU
macOS-only). `--extra ml` does **not** include it — add `--extra vst` explicitly.

The Gemini server bundles all its deps — no extras. From
`../stemmy-gemini-mcp`:

```bash
uv sync
```

### 3. Set API keys

Copy the template and fill it in (never commit real keys):

```bash
cp .env.example .env
# edit .env: ANTHROPIC_API_KEY=..., GEMINI_API_KEY=...
```

Or export them in your shell:

```bash
export ANTHROPIC_API_KEY=...   # LLM-backed loops tools (diagnose/ask/suggest/caption/…)
export GEMINI_API_KEY=...      # every Gemini perceptual tool + loops describe-loops
```

Pure-DSP tools (`measure-*`, `check-clipping`, `apply-eq`, `render-mastered`,
…) need no keys.

#### Environment overrides

The hub honours a few optional `SHIP_STUDIOS_*` knobs (defined in
`ship_studios/config.py`); leave them unset for the defaults:

| Var | Default | Purpose |
|---|---|---|
| `SHIP_STUDIOS_LOOPS_DIR` | `../stemmy-loops-mcp` | Loops-server location — the escape hatch when the repos don't share a parent (see the sibling-layout note above). Auto-resolved from the main checkout even in a git worktree; set this only for a non-standard layout. |
| `SHIP_STUDIOS_GEMINI_DIR` | `../stemmy-gemini-mcp` | Gemini-server location. |
| `SHIP_STUDIOS_STARTUP_TIMEOUT` | `120` | MCP handshake budget, seconds; `0` disables the timeout. |
| `SHIP_STUDIOS_CALL_TIMEOUT` | `600` | Per tool-call budget, seconds; `0` disables the timeout. |
| `SHIP_STUDIOS_ARTIFACTS_DIR` | `<repo>/artifacts` | Override the run-artifacts root (config override). |
| `SHIP_STUDIOS_PROJECTS_DIR` | `<repo>/projects` | Override the per-track workspace root (config override). |

Server-level overrides the hub *forwards* to the spawned servers
(`STEMMY_LLM_MODEL`, `STEMMY_MCP_MODEL`, `STEMMY_MCP_THINKING_LEVEL/BUDGET`,
`STEMMY_MCP_ALLOWED_ROOTS`, …) are documented in `.env.example` and CLAUDE.md.

### 4. Use it interactively (Claude Code)

Open this directory in Claude Code and approve the two servers from
`.mcp.json` when prompted. The hub keys are `stemmy-loops` and `stemmy-gemini`;
the harness expands `${ANTHROPIC_API_KEY}` / `${GEMINI_API_KEY}` from your
environment at launch. Then run a slash command or just describe what you want.

### 5. Use it headless (the CLI)

From this repo:

```bash
uv sync
ship-studios doctor   # verify the sibling repos + API keys are in place
ship-studios --help
```

## Pipelines

Nine pipelines, each available as a Claude Code skill/command and (where it
processes audio) as a CLI subcommand.

### `master-track` — mix → platform-ready master

Measure the source, get a perceptual mastering read, render to a target
LUFS / true-peak ceiling, re-verify streaming compliance, export the format
matrix.

- **Interactive:** `/master` or *"master this track to -14 LUFS for Spotify"*
- **Headless:** `ship-studios master projects/<track>/mix/mix.wav --target-lufs -14 --ceiling-dbtp -1`
- **Chain:** loops `measure-loudness` / `measure-spectrum` / `measure-stereo` /
  `check-clipping` / `measure-distortion` → gemini `mastering-feedback` →
  loops `render-mastered` → gemini `check-streaming-targets` →
  loops `export-deliverables`

### `batch-master` — folder of mixes → consistent masters

Master every mix in a folder to one shared platform target, then emit a
cross-track loudness/true-peak consistency table (Δ-from-album-median, outliers
flagged) — the album-level read a single-file master can't give.

- **Interactive:** `/batch-master` or *"master this whole EP for Spotify"*
- **Headless:** `ship-studios batch-master projects/<album>/mix/*.wav --platform spotify`
- **Chain (per track):** loops `measure-loudness` / `measure-spectrum` /
  `check-clipping` → gemini `mastering-feedback` → loops `render-mastered` →
  gemini `check-streaming-targets` → loops `export-deliverables`, then a
  cross-track `measure-loudness` consistency pass (+ `analyze-album-normalization`)

### `mix-check` — diagnose a mix before mastering

Fuse Gemini's perceptual listen with DSP measurement into one prioritized
issue list and concrete corrective moves.

- **Interactive:** `/mix-check` or *"what's wrong with this mix?"*
- **Headless:** `ship-studios mix-check projects/<track>/mix/mix.wav`
- **Chain:** gemini `detect-mix-issues` / `analyze-mix-balance` →
  loops `measure-loudness` / `measure-spectrum` / `measure-stereo` →
  gemini `find-resonances` / `find-sibilance` / `analyze-phase-mono` →
  loops `apply-eq` / `compress-loop`

### `reference-match` — match a mix to a reference

Derive numeric and perceptual deltas, apply EQ to close the gap, render a
loudness-matched A/B audition.

- **Interactive:** `/reference-match` or *"make it sound like this track"*
- **Headless:** `ship-studios reference-match projects/<track>/mix/mix.wav --reference path/to/ref.wav`
- **Chain:** gemini `match-reference-numeric` / `compare-to-reference` →
  loops `compare-tonality` → loops `apply-eq` → loops `render-ab`

### `house-curve` — one shared tonal target across an EP/album

Build a single house curve from a set of references, then match each mix to it —
reuse the one profile across the set for a consistent sound.

- **Interactive:** `/house-curve` or *"give the EP one consistent tonal balance"*
- **Headless:** `ship-studios house-curve projects/<track>/mix/mix.wav --reference refs/a.wav --reference refs/b.wav`
- **Chain:** loops `build-target-profile` → loops `match-to-profile` →
  loops `match-eq`

### `stem-master` — per-stem corrective access before the limiter

Treat each stem correctively (resolve cross-stem masking, de-harsh,
transient-shape), then sum (`drum-prep stem-mix`) and hand the bus to
`master-track` — corrective access a stereo-bus master physically can't do.

- **Interactive:** `/stem-master` or *"master from stems"*
- **Headless:** `ship-studios stem-master projects/<track>/stems/kick.wav projects/<track>/stems/bass.wav`
  (then `drum-prep stem-mix`, then `ship-studios master`)
- **Chain:** loops `measure-loudness` / `measure-spectrum` (per stem) → gemini
  `analyze-stem-masking` / `find-resonances` / `find-sibilance` → loops `apply-eq`
  / `de-ess` / `compress-loop` → re-score with gemini `analyze-stem-masking`

### `unmask-stems` — carve cross-stem frequency clashes (corrective only)

The masking-only subset of stem-master: score cross-stem masking, cut the losing
stem of each collision, re-score. No summing, no mastering.

- **Interactive:** `/unmask-stems` or *"the kick and bass are masking"*
- **Headless:** `ship-studios unmask-stems projects/<track>/stems/kick.wav projects/<track>/stems/bass.wav`
- **Chain:** gemini `analyze-stem-masking` → loops `apply-eq` / `apply-dynamic-eq`
  (losing stem) → gemini `analyze-stem-masking` (re-score)

### `loops-to-deliverables` — stem/mix → tagged mastered loops

Extract loops, clean and seam them, master, tag, export the format matrix.

- **Interactive:** `/loops` or *"slice this drum stem into mastered loops"*
- **Headless:** `ship-studios loops projects/<track>/stems/drums.wav --bpm 120`
- **Chain:** loops `find-loops` (or `analyze-loops`) → loops `clean-loop` →
  loops `optimize-seam` → loops `render-mastered` → loops `tag-deliverable` →
  loops `export-deliverables` (optional loops `describe-loops`)

### `understand-audio` — perceptual analysis of a track/stem

Transcribe, region Q&A, event detection, zero-shot tagging, multi-file
comparison. Read-only; never modifies audio.

- **Interactive:** `/understand` or *"what happens at 1:30?"* / *"find every kick"*
- **Headless:** `ship-studios understand path/to/audio.wav`
- **Chain:** gemini `transcribe-audio` / `describe-audio-region` /
  `extract-audio-events` / `classify-audio` / `compare-audio-files` /
  `audio-to-json`

### `new-track` — scaffold a project working dir

Pure filesystem. Creates `projects/<slug>/` with `stems/`, `mix/`, `masters/`,
`refs/`, `loops/`, `deliverables/`, and a `track.md`.

- **Interactive:** `/new-track` or *"start a new song called …"*
- **Headless:** create the dirs yourself, or run the skill from Claude Code.

### Workflows (parallel fan-out)

The pipelines above are sequential. For **parallel fan-out** — a whole album, a
folder of stems, a plugin sweep, a variant shootout, a judge panel — reach for a
Claude Code **workflow** instead. These live in `.claude/workflows/*.js` (15 of
them: `batch-master`, `house-curve`, `stem-process`, `audio-shootout`,
`vst-probe-inventory`, the famous-drum bus-tuning twins, the repo audits, …) and
are invoked interactively as `/<name>` slash commands. See the **Workflows**
section of [`CLAUDE.md`](CLAUDE.md) for the full table (what each fans out and
what to render/gather inline first).

## drum-prep — multi-mic drum stem prep (local DSP)

Unlike the nine pipelines above, **`drum-prep` is local DSP, not the MCP servers.**
It lives in a separate `drum_prep/` package (numpy/scipy/soundfile/pyloudnorm)
behind an optional extra, and covers a job neither stemmy server does: taking a
folder of *individual drum mics* (overheads, snare top/bottom, kick in/beater,
hi-hat, toms, room) and making the whole kit phase-coherent and tonally matched
to a reference — stem by stem. (The stemmy `apply-eq` / `render-ab` operate on a
single stereo file, not a multi-mic kit.)

Install the extra (the core hub doesn't need it), then:

```bash
uv sync --extra drum-prep
drum-prep --help
```

Mic roles auto-detect from filenames; commit a `kit.json` to pin/override (it's
JSON, so it's safe to commit — audio stays gitignored). See
`drum_prep/examples/kit.json`.

The core close-mic flows + an end-to-end chain. Each is a `drum-prep`
subcommand; `phase-align` / `reference-match` / `audition` / `chain` also have
Claude Code skills/commands (`overheads` is CLI-only). The full CLI exposes more
subcommands — several with their own `/drum-*` skills (e.g. `mix`, `normalize`,
`stereo-merge`, `tune`, `sub-design`) — run `drum-prep --help` for the complete list:

- **overheads** — merge an L/R overhead pair into one stereo reference (no-op if
  already stereo). `drum-prep overheads <dir>` *(CLI only — no slash command)*
- **phase-align** (`/drum-phase-align`) — align every close mic to the overheads
  (broadband; kick low-passed; snare-bottom→top & kick-beater→in partner pairs;
  room polarity-only). `drum-prep phase-align <dir>`
- **reference-match** (`/drum-reference-match`) — match the coherent kit sum to a
  reference, distributed per stem (cuts to all, boosts to band owners), zero-phase
  so the alignment survives. `drum-prep reference-match <dir> --reference <ref>`
- **audition** (`/drum-audition`) — loudness-matched (BS.1770) stereo A/B WAVs:
  before-vs-after and reference-vs-after. `drum-prep audition <dir> --reference <ref>`
- **chain** (`/drum-prep`) — all of the above end to end:
  `drum-prep chain <dir> --reference <ref>`

Outputs land alongside the stems in `phase-aligned/`, `ref-matched/`, and
`auditions/` (`--out-root` redirects all three on `chain`; individual flows take
`--out-dir`). There's also `drum-prep analyze <dir> --reference <ref>` for a
read-only tonal report. The synthetic-audio test suite runs
with `uv run pytest -k drum_prep` (after `uv sync --extra drum-prep`).

## Project layout

```
ship-studios/
├── .mcp.json                  registers stemmy-loops + stemmy-gemini (stdio)
├── .env.example               ANTHROPIC_API_KEY / GEMINI_API_KEY template
├── .claude/
│   ├── settings.json          enables both servers, pre-allows their tools (+ uv/stemmy/drum-prep Bash)
│   ├── skills/                one SKILL.md per pipeline
│   └── commands/              thin slash-command entry points
├── ship_studios/              headless CLI package
│   ├── config.py              sibling paths, server keys, stdio params
│   ├── mcp_client.py          async hub over both ClientSessions
│   ├── pipelines.py           the nine pipeline async functions
│   └── cli.py                 `ship-studios` console script
├── drum_prep/                 local drum-stem DSP (opt-in `drum-prep` extra)
│   ├── dsp.py io.py roles.py kit.py qc.py     shared DSP + role/kit model + QC
│   ├── overheads.py stereo_merge.py phase_align.py reference_match.py   prep flows
│   ├── mix.py stem_mix.py normalize.py sub_design.py tune.py audition.py chain.py   mix/finish flows
│   └── cli.py                 `drum-prep` console script (run `drum-prep --help`)
├── tests/                     pipeline/CLI tests (MCP mocked) + drum_prep synth tests
├── projects/                  your tracks live here (gitignored contents)
└── artifacts/                 stemmy run outputs (gitignored contents)
```

Convention: project work goes under `projects/<slug>/`; raw stemmy run outputs
(manifests, candidate loops) land in `artifacts/<run>/`.

## Tool surface

The hub composes two servers. Pick a server by key, then a tool by exact name
(hyphens, not underscores).

| Server (`key`) | What it provides | Representative tools |
|---|---|---|
| `stemmy-loops` | Loop extraction + pure-DSP measurement, correction, render/export | `find-loops`, `analyze-loops`, `measure-loudness`, `measure-spectrum`, `measure-stereo`, `check-clipping`, `measure-distortion`, `inspect-loop`, `detect-masking`, `compare-tonality`, `apply-eq`, `compress-loop`, `adjust-stereo`, `saturate-loop`, `shape-bands`, `clean-loop`, `optimize-seam`, `tune-kick`, `render-mastered`, `render-ab`, `tag-deliverable`, `export-deliverables` |
| `stemmy-gemini` | Gemini perceptual understanding + DSP measurement | `transcribe-audio`, `describe-audio-region`, `compare-audio-files`, `classify-audio`, `extract-audio-events`, `audio-to-json`, `analyze-mix-balance`, `detect-mix-issues`, `compare-to-reference`, `mastering-feedback`, `find-resonances`, `find-sibilance`, `analyze-phase-mono`, `check-streaming-targets`, `match-reference-numeric`, `recommend-mastering-chain` |

LLM-backed loops tools need `ANTHROPIC_API_KEY`; `describe-loops` and every
Gemini perceptual tool need `GEMINI_API_KEY`. The DSP measurement/correction
tools on both servers need neither.

## Troubleshooting

- **Loops tools don't appear / "unknown tool".** The loops server is
  extra-gated. Re-run its sync with at least
  `uv sync --extra loops-mcp --extra mixing` in `../stemmy-loops-mcp`; the
  `loops-mcp` extra is what installs the MCP server itself, and `mixing` is
  required for the loudness/render tools. Add `--extra llm` / `--extra listen`
  if you want the LLM- and Gemini-backed loops tools.
- **A tool errors about a missing key.** That tool is LLM- or Gemini-backed.
  Confirm `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` are set in `.env` or the
  environment Claude Code (or the CLI) was launched from.
- **Servers fail to launch.** Verify the siblings are at `../stemmy-loops-mcp`
  and `../stemmy-gemini-mcp` and that each has been `uv sync`'d. The hub
  launches them with `uv --directory <rel> run <console-script>`.
- **Gemini path refused.** If `STEMMY_MCP_ALLOWED_ROOTS` is set, the Gemini
  server rejects audio outside those roots — add your `projects/` /
  `artifacts/` paths or unset it for local use.
