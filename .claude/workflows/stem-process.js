export const meta = {
  name: 'stem-process',
  description: "Per-stem corrective+color batch for a multi-mic kit. Phase 1 DIAGNOSE fans out one agent per stem — each measures its own stem (loudness/spectrum/microdynamics/stereo/clipping, all read-only, no cross-stem dependency) and authors a role-aware typed plan (clean/eq/de-harsh/dynamic-eq/transient/excite/color) — the step the [[stem-process]] skill explicitly asks to fan out. Phase 2 PROCESS runs scripts/mix/process_stems.py ONCE over the assembled plans.json (a SINGLE serial process): the executor always loads the API Vision uaudio_* plugin per stem, so concurrent runs would hit the documented UADx render non-determinism — process is intentionally NOT fanned out. args = { stems:[name|{name,file}], srcDir, outDir, durationS?, venv?, process?, plansOut? }.",
  phases: [
    { title: 'Diagnose', detail: 'one agent per stem → measure + author a role-aware corrective plan (parallel, no UADx)' },
    { title: 'Process',  detail: 'assemble plans.json → ONE serial process_stems.py run (UADx-safe)' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const rawStems = A.stems || []
const stems = rawStems.map(s => {
  if (typeof s === 'string') return { name: s, file: s }
  return { name: s.name || (s.file ? String(s.file).split('/').pop() : ''), file: s.file || s.name }
}).filter(s => s.name)
const srcDir    = A.srcDir || ''         // ABSOLUTE dir holding the (phase-aligned) stems
const outDir    = A.outDir || ''         // ABSOLUTE dir for processed stems
const durationS = A.durationS || 0       // >0 = fast audition on the first N s; 0 = full length
const venv      = A.venv || '../stemmy-loops-mcp/.venv/bin/python'
const doProcess = A.process !== false    // false → return plans only (review/edit before processing)
const plansOut  = A.plansOut || (outDir ? `${outDir}/stem-process.plans.json` : '')

if (!stems.length) return { error: 'no stems — pass args.stems = [name|{name,file}, ...] (gather inline: ls the kit dir)' }
if (!srcDir)  return { error: 'pass args.srcDir = ABSOLUTE dir holding the stems (e.g. the phase-aligned dir)' }
if (!outDir)  return { error: 'pass args.outDir = ABSOLUTE dir for the processed stems' }
log(`stem-process: ${stems.length} stems · src=${srcDir} · out=${outDir} · ${durationS ? durationS + 's audition' : 'full length'}`)

// The plan schema mirrors scripts/mix/process_stems.py (only the stages present run; omit a stage to skip it).
const PLAN = {
  type: 'object',
  additionalProperties: false,
  properties: {
    stem: { type: 'string', description: 'the stem basename (with .wav), e.g. "kick in.wav"' },
    role: { type: 'string', description: 'inferred role + one-line tonal read (kick_in / snare_top / overhead / room / hat / tom …)' },
    rationale: { type: 'string', description: 'one sentence: the corrective intent, grounded in the measured spectrum/crest' },
    clean: {
      type: 'object', description: 'DC/HPF cleanup (declick is FORCED off — percussive). Omit to skip.',
      properties: { hpf_hz: { type: 'number' }, denoise: { type: 'boolean' }, denoise_db: { type: 'number' } },
    },
    eq_bands: {
      type: 'array', description: 'zero-phase corrective EQ — CUTS for de-box/de-mud; a high_pass for rumble. Warm philosophy: cut, do not bright-boost.',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          type:    { type: 'string', enum: ['bell', 'low_shelf', 'high_shelf', 'high_pass', 'low_pass'] },
          freq_hz: { type: 'number' }, gain_db: { type: 'number' }, q: { type: 'number' },
        },
        required: ['type', 'freq_hz', 'gain_db'],
      },
    },
    de_harsh: {
      type: 'object', description: 'suppress_resonances (Soothe-style) — only catches NARROW ringing, no-op on broadband. Omit unless a real peak rings.',
      properties: { depth: { type: 'number' }, max_reduction_db: { type: 'number' }, focus_lo_hz: { type: 'number' }, focus_hi_hz: { type: 'number' } },
    },
    dynamic_eq: {
      type: 'array', description: 'threshold-gated per-band EQ for LEVEL-DEPENDENT problems (mud only when the kick hits). Omit unless level-dependent.',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          freq_hz: { type: 'number' }, q: { type: 'number' }, threshold_dbfs: { type: 'number' },
          ratio: { type: 'number' }, range_db: { type: 'number' }, mode: { type: 'string', enum: ['cut', 'boost'] },
        },
        required: ['freq_hz'],
      },
    },
    transient: {
      type: 'object', description: 'multiband transient design (LR4) for attack/punch. Omit unless transients are soft.',
      properties: {
        crossovers_hz: { type: 'array', items: { type: 'number' } },
        bands: { type: 'array', items: { type: 'object', additionalProperties: false, properties: { transient: { type: 'number' }, gain_db: { type: 'number' } }, required: ['transient'] } },
      },
    },
    excite: {
      type: 'object', description: 'parallel harmonic air/presence (hiss-safe). Omit on warm jobs / hissy room mics.',
      properties: { band: { type: 'string' }, drive_db: { type: 'number' }, mix: { type: 'number' } },
    },
    color_api: {
      type: 'object', description: 'OPTIONAL API Vision console color (conservative; keep the 550 top FLAT). Omit for near-passthrough (the strip still runs at line_gain 0).',
      properties: { line_gain_db: { type: 'number' }, eq_on: { type: 'boolean' } },
    },
  },
  required: ['stem', 'role', 'rationale'],
}

// ---- Phase 1: diagnose each stem in parallel (read-only meters + role-aware plan) ----------------
phase('Diagnose')
const DBATCH = 16
const dbatches = []
for (let i = 0; i < stems.length; i += DBATCH) dbatches.push(stems.slice(i, i + DBATCH))

const plans = (await pipeline(
  dbatches,
  b => parallel(b.map(s => () =>
    agent(
      `You diagnose ONE drum stem and author a measured, role-aware corrective plan for it. The stem file is ` +
      `"${srcDir}/${s.name}" (absolute). All your tool calls are READ-ONLY — you write NO audio.\n\n` +
      `1. Run ToolSearch, then MEASURE the stem: mcp__stemmy-loops__measure-loudness, ` +
      `mcp__stemmy-loops__measure-spectrum (third-octave + tilt), mcp__stemmy-loops__measure-microdynamics ` +
      `(crest/punch), mcp__stemmy-loops__measure-stereo, and mcp__stemmy-loops__check-clipping. These are ` +
      `independent reads of the same file — gather them all.\n` +
      `2. Infer the ROLE from the SIGNAL (spectrum/crest), not the filename: kick = LF-dominant <120 Hz; ` +
      `snare = mid+HF body; tom = low-mid focus, little HF; hat/ride/crash = bright, high centroid, ~no lows; ` +
      `overhead = full-range cymbal field; room = ambient/wide.\n` +
      `3. Author a CONSERVATIVE, role-aware plan (these are usually finished bounces). Repo doctrine:\n` +
      `   - declick is forced OFF (percussive). HPF every stem to clear rumble/bleed (kick ~30, snare ~70, ` +
      `overhead ~110 to kill kick bleed, room ~120).\n` +
      `   - CUTS, not bright boosts — de-box (250-500), de-mud; warmth/air is added at the BUS, not here. ` +
      `Only de-box where there is a REAL peak (don't cut a region already ~10 dB down — that just brightens it).\n` +
      `   - de_harsh only for NARROW ringing (no-op on broadband presence); dynamic_eq only for LEVEL-DEPENDENT ` +
      `collisions; transient only if attack is genuinely soft; excite only if dull AND not hissy.\n` +
      `   - color_api: OMIT for a near-passthrough strip (it runs anyway at line_gain 0); include only for a ` +
      `deliberate, conservative console color (550 top FLAT).\n` +
      `Return the plan: stem="${s.name}", role, rationale (grounded in your meters), and ONLY the stages this ` +
      `stem actually needs (omit the rest — every present stage runs).`,
      { label: `diagnose:${s.name}`, phase: 'Diagnose', schema: PLAN, agentType: 'general-purpose' },
    ).then(r => r ? { ...r, stem: r.stem || s.name } : null),
  )),
)).flat().filter(Boolean)

if (!plans.length) return { error: 'diagnosis produced no plans', stems: stems.map(s => s.name) }
log(`diagnosed ${plans.length}/${stems.length} stems`)

// ---- Phase 2: assemble plans.json → ONE serial executor run (UADx-safe) -------------------------
// NOT fanned out: process_stems.py loads the API Vision uaudio_* plugin per stem, and concurrent UADx
// hosts render non-deterministically (see MEMORY: "UADx workflow render nondeterminism"). One process,
// stems handled sequentially inside it, is the safe path — same as the skill's direct call.
let processResult = null
if (doProcess) {
  phase('Process')
  const durArg = durationS > 0 ? ` ${durationS}` : ''
  processResult = await agent(
    `You run the per-stem corrective+color executor over an ALREADY-DIAGNOSED plan set (a single serial ` +
    `process — do NOT parallelize; it loads UADx per stem).\n\n` +
    `1. Write this plans JSON verbatim to "${plansOut}" (create parent dirs if needed):\n` +
    `${JSON.stringify(plans, null, 1)}\n\n` +
    `2. From the repo root run exactly:\n` +
    `   ${venv} scripts/mix/process_stems.py "${plansOut}" "${srcDir}" "${outDir}"${durArg}\n` +
    `3. Read the printed per-stem "LUFS b>a / crest b>a / centroid b>a / tilt b>a / notes" table.\n\n` +
    `Return: the plans path, the output dir, one row per stem (the before→after numbers + any FAIL note), ` +
    `and whether any stem FAILED a stage. If the command errors (e.g. no pedalboard in the venv, missing ` +
    `uaudio plugin), return ok=false with the error tail.`,
    {
      label: 'process', phase: 'Process', agentType: 'general-purpose',
      schema: {
        type: 'object', additionalProperties: false,
        properties: {
          ok:        { type: 'boolean' },
          plansPath: { type: 'string' },
          outDir:    { type: 'string' },
          rows: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
            stem: { type: 'string' }, lufs: { type: 'string' }, crest: { type: 'string' },
            centroid: { type: 'string' }, tilt: { type: 'string' }, note: { type: 'string' },
          }, required: ['stem'] } },
          error: { type: 'string' },
        },
        required: ['ok'],
      },
    },
  )
}

log(`stem-process done — ${plans.length} plans${doProcess ? `, processed → ${outDir}` : ' (process skipped)'}`)
return { plans, plansOut, processed: doProcess, processResult, srcDir, outDir }
