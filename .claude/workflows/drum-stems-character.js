export const meta = {
  name: 'drum-stems-character',
  description: "Two-mode per-stem fan-out for a multi-mic drum kit, parameterized by a tonal CHARACTER (Clean/Warm/Punchy/Crushed/Aggressive/Bonham/TNK). mode:'correct' fans out one agent per stem — each measures its own stem (read-only) and authors a PURE-DSP corrective plan (clean/eq/de-harsh/dynamic-eq), then ONE serial process_stems.py pass applies them (pure DSP is parallel-safe, but the executor loads one UADx strip per stem at line_gain 0 so the apply stays serial). mode:'character' fans out one agent per stem to PLAN a role+character-aware UADx VST chain (parallel, read-only measure), then ONE serial character_stems.py pass applies the chains one stem at a time (concurrent UADx renders are non-deterministic). The skill (session) owns the AskUserQuestion between the two invocations + the serial bus tail. args = { mode:'correct'|'character', stems:[name|{name,file}], srcDir, outDir, character?, plansOut?, durationS?, venv?, process? }.",
  phases: [
    { title: 'Plan',  detail: 'one agent per stem → measure + author a plan (parallel, read-only, no UADx)' },
    { title: 'Apply', detail: 'assemble plans.json → ONE serial executor run (process_stems.py | character_stems.py), UADx-safe' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const mode = A.mode || 'correct'                     // 'correct' (step 2) | 'character' (step 4)
const rawStems = A.stems || []
const stems = rawStems.map(s => {
  if (typeof s === 'string') return { name: s, file: s }
  return { name: s.name || (s.file ? String(s.file).split('/').pop() : ''), file: s.file || s.name }
}).filter(s => s.name)
const srcDir    = A.srcDir || ''                     // ABSOLUTE: correct=phase-aligned dir · character=corrected dir
const outDir    = A.outDir || ''                     // ABSOLUTE dir for processed stems
const character = A.character || ''                  // REQUIRED iff mode:'character'
const durationS = A.durationS || 0                   // >0 = fast audition on the first N s; 0 = full length
const venv      = A.venv || '../stemmy-loops-mcp/.venv/bin/python'
const doProcess = A.process !== false                // false → return plans only (review/edit before applying)
const plansOut  = A.plansOut || (outDir ? `${outDir}/drum-stems-character.${mode}.plans.json` : '')

// ---- Per-stem CHARACTER templates -------------------------------------------------------------------
// Per-stem character intentionally uses ONLY the two UADx plugins with proven, exact Pedalboard param
// templates (Studer A800 + API Vision) — zero param-name guesswork. It stays LIGHTER than the bus; the
// SIGNATURE color (Fairchild/Helios/SSL/Vibe) is applied at the bus by the matching *_bus.py script.
const STUDER = '/Library/Audio/Plug-Ins/VST3/uaudio_studer_a800.vst3'
const API    = '/Library/Audio/Plug-Ins/VST3/uaudio_api_vision_channel_strip.vst3'
const CHAR_SPECS = {
  Clean: {
    summary: 'No added color — the pure-DSP corrective is already done. Per-stem chain is EMPTY (faithful passthrough + the -1 dBFS normalize) for EVERY stem.',
    close:   { chain: [] },
    ambient: { chain: [] },
  },
  Warm: {
    summary: 'Light Studer A800 @ 30 IPS tape warmth (30 IPS = tight lows, no bloom). Studer DARKENS, so go lighter (lower input_level) on bright/hissy ambient mics; skip if a room is hissy.',
    close:   { chain: [{ file: STUDER, params: { path_select: 'Repro', ips: '30 IPS', tape_type: '456', auto_cal: true, input_level: 3.0, repro_hf_eq: 2.0, emphasis_eq: 'NAB' } }] },
    ambient: { chain: [{ file: STUDER, params: { path_select: 'Repro', ips: '30 IPS', tape_type: '456', auto_cal: true, input_level: 1.5, repro_hf_eq: 2.5, emphasis_eq: 'NAB' } }] },
  },
  Punchy: {
    summary: 'API Vision 225 comp (Old(FB)/Slow) lightly driven — punch comes from the COMP, not EQ. 550 EQ stays OFF (eq_on=false). Drive via input_gain_db. Do NOT drive cymbals into the comp.',
    close:   { input_gain_db: 3.0, chain: [{ file: API, params: { input_select: 'Line', line_gain: 0.0, eq_on: false, sc_link: true, '215_on': true, '215_hp_filter': 50.0, '225_on': true, '225_type': 'Old (FB)', '225_attack': 'Slow', '225_ratio': 3.0, '225_thresh': -6.0, '225_knee': 'Hard', '225_release': '0.30 s' } }] },
    ambient: { input_gain_db: 0.0, chain: [{ file: API, params: { input_select: 'Line', line_gain: 0.0, eq_on: false, sc_link: true, '215_on': false, '225_on': true, '225_type': 'Old (FB)', '225_attack': 'Slow', '225_ratio': 2.0, '225_thresh': 0.0, '225_knee': 'Hard', '225_release': '0.30 s' } }] },
  },
  Aggressive: {
    summary: 'API Vision driven HARDER than Punchy (more input_gain_db, lower thresh, ratio 4) for density/grit. Still NO top EQ. Protect cymbals: back the thresh off on ambient mics.',
    close:   { input_gain_db: 6.0, chain: [{ file: API, params: { input_select: 'Line', line_gain: 0.0, eq_on: false, sc_link: true, '215_on': true, '215_hp_filter': 50.0, '225_on': true, '225_type': 'Old (FB)', '225_attack': 'Slow', '225_ratio': 4.0, '225_thresh': -10.0, '225_knee': 'Hard', '225_release': '0.30 s' } }] },
    ambient: { input_gain_db: 2.0, chain: [{ file: API, params: { input_select: 'Line', line_gain: 0.0, eq_on: false, sc_link: true, '215_on': false, '225_on': true, '225_type': 'Old (FB)', '225_attack': 'Slow', '225_ratio': 3.0, '225_thresh': -4.0, '225_knee': 'Hard', '225_release': '0.30 s' } }] },
  },
  Crushed: {
    summary: 'Studer A800 @ 15 IPS DARK/fat (15 IPS blooms + darkens). The real pump/crush + mono is applied at the BUS (tomorrow_never_knows_bus.py --width 1.0 --dark -2). Skip on cymbals.',
    close:   { chain: [{ file: STUDER, params: { path_select: 'Repro', ips: '15 IPS', tape_type: '456', auto_cal: true, input_level: 3.0, repro_hf_eq: 1.5, emphasis_eq: 'NAB' } }] },
    ambient: { chain: [{ file: STUDER, params: { path_select: 'Repro', ips: '15 IPS', tape_type: '456', auto_cal: true, input_level: 1.5, repro_hf_eq: 1.5, emphasis_eq: 'NAB' } }] },
  },
  Bonham: {
    summary: 'Light Studer @ 30 IPS warmth on close mics; the ROOM is the star → leave room/overheads (ambient) UNTOUCHED (empty chain). The Helios+SSL+15IPS signature is at the BUS (fool_in_the_rain_bus.py).',
    close:   { chain: [{ file: STUDER, params: { path_select: 'Repro', ips: '30 IPS', tape_type: '456', auto_cal: true, input_level: 2.0, repro_hf_eq: 2.0, emphasis_eq: 'NAB' } }] },
    ambient: { chain: [] },
  },
  TNK: {
    summary: 'Studer @ 15 IPS DARK on close mics (tom-forward). The Fairchild pump + mono-narrow + optional Vibe lo-fi is at the BUS (tomorrow_never_knows_bus.py). Leave cymbals/ambient empty.',
    close:   { chain: [{ file: STUDER, params: { path_select: 'Repro', ips: '15 IPS', tape_type: '456', auto_cal: true, input_level: 2.5, repro_hf_eq: 1.5, emphasis_eq: 'NAB' } }] },
    ambient: { chain: [] },
  },
}

// ---- Validate args ---------------------------------------------------------------------------------
if (!['correct', 'character'].includes(mode)) return { error: `bad mode "${mode}" — use 'correct' or 'character'` }
if (!stems.length) return { error: 'no stems — pass args.stems = [name|{name,file}, ...] (gather inline: ls the kit dir)' }
if (!srcDir)  return { error: "pass args.srcDir = ABSOLUTE dir holding the input stems (correct=phase-aligned dir, character=corrected dir)" }
if (!outDir)  return { error: 'pass args.outDir = ABSOLUTE dir for the processed stems' }
if (mode === 'character' && !CHAR_SPECS[character]) {
  return { error: `mode:'character' needs args.character in {${Object.keys(CHAR_SPECS).join(', ')}}` }
}
log(`drum-stems-character[${mode}${mode === 'character' ? ':' + character : ''}]: ${stems.length} stems · src=${srcDir} · out=${outDir} · ${durationS ? durationS + 's audition' : 'full length'}`)

// ---- Schemas ---------------------------------------------------------------------------------------
// correct: a subset of the stem-process plan — only EQ + soothe (de-harsh / dynamic) + clean; no color,
//          no excite, no transient. process_stems.py runs the API strip at line_gain 0 (near-passthrough)
//          and ALWAYS peak-normalizes to -1 dBFS (= the "normalize" step). Only present stages run.
const CORRECT_PLAN = {
  type: 'object', additionalProperties: false,
  properties: {
    stem: { type: 'string', description: 'the stem basename (with extension), e.g. "kick in.wav"' },
    role: { type: 'string', description: 'role inferred from the SIGNAL + one-line tonal read (kick_in/snare_top/tom/overhead/room/hat/ride/crash)' },
    rationale: { type: 'string', description: 'one sentence: the corrective intent, grounded in the measured spectrum/crest' },
    clean: {
      type: 'object', description: 'DC/HPF cleanup (declick is FORCED off — percussive). Omit to skip.',
      properties: { hpf_hz: { type: 'number' }, denoise: { type: 'boolean' }, denoise_db: { type: 'number' } },
    },
    eq_bands: {
      type: 'array', description: 'zero-phase corrective EQ — CUTS for de-box/de-mud + a high_pass for rumble. No bright boosts (tone is added later).',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          type: { type: 'string', enum: ['bell', 'low_shelf', 'high_shelf', 'high_pass', 'low_pass'] },
          freq_hz: { type: 'number' }, gain_db: { type: 'number' }, q: { type: 'number' },
        },
        required: ['type', 'freq_hz', 'gain_db'],
      },
    },
    de_harsh: {
      type: 'object', description: 'suppress_resonances (Soothe-style) — only catches NARROW ringing, no-op on broadband. Omit unless a real peak rings. THIS is the "soothe" step.',
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
  },
  required: ['stem', 'role', 'rationale'],
}

// character: a per-stem UADx recipe in the shape character_stems.py / apply_vst_preset.py consume.
const CHARACTER_PLAN = {
  type: 'object', additionalProperties: false,
  properties: {
    stem: { type: 'string', description: 'the stem basename (with extension)' },
    role: { type: 'string', description: 'role inferred from the SIGNAL' },
    character: { type: 'string', description: 'the chosen character (echo it)' },
    rationale: { type: 'string', description: 'one sentence: which template variant (close/ambient/skip) and why, grounded in the meters' },
    recipe: {
      type: 'object', additionalProperties: false,
      description: 'the per-stem chain. Empty chain = faithful passthrough (Clean, or an ambient mic the character skips).',
      properties: {
        input_gain_db: { type: 'number', description: 'digital pre-gain into the chain (drive for the API comp characters)' },
        width: { type: 'number', description: 'M/S width (1.0 = unchanged); leave 1.0 — bus owns the mono narrow' },
        output_peak_dbfs: { type: 'number', description: 'peak-normalize target (default -1.0; keep -1.0 so Stage-5 LUFS balance hands off cleanly)' },
        chain: {
          type: 'array',
          items: {
            type: 'object', additionalProperties: false,
            properties: {
              file: { type: 'string', description: 'absolute uaudio_*.vst3 path from the template' },
              params: { type: 'object', additionalProperties: true, description: 'the exact param dict from the template (do not invent keys)' },
            },
            required: ['file', 'params'],
          },
        },
      },
      required: ['chain'],
    },
  },
  required: ['stem', 'role', 'character', 'recipe'],
}

// ---- Phase 1: PLAN each stem in parallel (read-only meters → typed plan) ---------------------------
phase('Plan')
const DBATCH = 16
const dbatches = []
for (let i = 0; i < stems.length; i += DBATCH) dbatches.push(stems.slice(i, i + DBATCH))

const correctPrompt = (s) =>
  `You diagnose ONE drum stem and author a measured, role-aware PURE-DSP corrective plan (EQ + soothe + ` +
  `normalize — NO tonal character/color; that comes later). The stem is "${srcDir}/${s.name}" (absolute). ` +
  `ALL your tool calls are READ-ONLY — you write NO audio.\n\n` +
  `1. Run ToolSearch, then MEASURE: mcp__stemmy-loops__measure-loudness, mcp__stemmy-loops__measure-spectrum ` +
  `(third-octave + tilt), mcp__stemmy-loops__measure-microdynamics, mcp__stemmy-loops__measure-stereo, ` +
  `mcp__stemmy-loops__check-clipping. Independent reads of the same file — gather them all.\n` +
  `2. Infer the ROLE from the SIGNAL (spectrum/crest), not the filename: kick = LF-dominant <120 Hz; ` +
  `snare = mid+HF body; tom = low-mid focus; hat/ride/crash = bright/high-centroid; overhead = full-range ` +
  `cymbal field; room = ambient/wide.\n` +
  `3. Author a CONSERVATIVE corrective plan (usually finished bounces):\n` +
  `   - HPF every stem to clear rumble/bleed (kick ~30, snare ~70, overhead ~110 to kill kick bleed, room ~120).\n` +
  `   - eq_bands: CUTS only (de-box 250-500, de-mud) where a REAL peak exists — don't cut a region already ~10 dB down.\n` +
  `   - de_harsh ONLY for NARROW ringing (the "soothe" step; no-op on broadband). dynamic_eq ONLY for ` +
  `LEVEL-DEPENDENT collisions.\n` +
  `   - declick is forced off; the executor always peak-normalizes to -1 dBFS (the "normalize" step) — don't ` +
  `ask for it.\n` +
  `Return ONLY the stages this stem needs (omit the rest): stem="${s.name}", role, rationale.`

const charSpec = mode === 'character' ? CHAR_SPECS[character] : null
const characterPrompt = (s) =>
  `You PLAN the tonal character "${character}" for ONE drum stem, role-aware. The stem is "${srcDir}/${s.name}" ` +
  `(absolute, already corrected). ALL your tool calls are READ-ONLY — you write NO audio; you only author a recipe.\n\n` +
  `1. Run ToolSearch, then MEASURE: mcp__stemmy-loops__measure-loudness, mcp__stemmy-loops__measure-spectrum, ` +
  `mcp__stemmy-loops__measure-microdynamics, mcp__stemmy-loops__measure-stereo. Gather them.\n` +
  `2. Classify the stem from the SIGNAL into one of: CLOSE (kick/snare/tom — focused, transient) or AMBIENT ` +
  `(overhead/room/hat/ride/crash — full-range or wide cymbal field).\n` +
  `3. The character "${character}" template (USE THESE EXACT plugin files + param keys — do NOT invent keys):\n` +
  `${JSON.stringify(charSpec, null, 1)}\n` +
  `   - Pick the CLOSE recipe for close mics, the AMBIENT recipe for ambient mics. An empty "chain" means a ` +
  `faithful passthrough (correct for Clean, and for ambient mics this character deliberately leaves alone).\n` +
  `   - Per-stem character is LIGHT (the bus carries the signature). You MAY trim intensity for THIS stem ` +
  `(e.g. lower input_level / input_gain_db / raise a comp thresh on a hot or bright stem, or drop to an empty ` +
  `chain if the template's ambient variant would over-color a hissy room) — but keep the template's plugin + ` +
  `param keys; only adjust numeric values.\n` +
  `   - Keep width=1.0 and output_peak_dbfs=-1.0 (the bus owns mono-narrowing; -1 dBFS hands off to the LUFS balance).\n` +
  `Return the recipe for stem="${s.name}" with role and character="${character}".`

const plans = (await pipeline(
  dbatches,
  b => parallel(b.map(s => () =>
    agent(
      mode === 'character' ? characterPrompt(s) : correctPrompt(s),
      {
        label: `${mode}:${s.name}`, phase: 'Plan',
        schema: mode === 'character' ? CHARACTER_PLAN : CORRECT_PLAN,
        agentType: 'general-purpose',
      },
    ).then(r => r ? { ...r, stem: r.stem || s.name } : null),
  )),
)).flat().filter(Boolean)

if (!plans.length) return { error: 'planning produced no plans', mode, stems: stems.map(s => s.name) }
log(`planned ${plans.length}/${stems.length} stems`)

// ---- Phase 2: assemble plans.json → ONE serial executor run (UADx-safe) ----------------------------
// NOT fanned out: each executor loads a UADx plugin per stem, and concurrent UADx hosts render
// non-deterministically (MEMORY: "UADx workflow render nondeterminism"). One process, stems handled
// sequentially inside it, is the safe path.
let processResult = null
if (doProcess) {
  phase('Apply')
  const durArg = durationS > 0 ? ` ${durationS}` : ''
  const script = mode === 'character' ? 'scripts/mix/character_stems.py' : 'scripts/mix/process_stems.py'
  const what = mode === 'character' ? `the "${character}" per-stem UADx character chains` : 'the per-stem corrective plans'
  processResult = await agent(
    `You run the per-stem executor over an ALREADY-PLANNED set — ${what}. This is a SINGLE serial process ` +
    `(do NOT parallelize; it loads a UADx plugin per stem).\n\n` +
    `1. Write this plans JSON verbatim to "${plansOut}" (create parent dirs if needed):\n` +
    `${JSON.stringify(plans, null, 1)}\n\n` +
    `2. From the repo root run exactly:\n` +
    `   ${venv} ${script} "${plansOut}" "${srcDir}" "${outDir}"${durArg}\n` +
    `3. Read the printed per-stem "LUFS b>a / crest b>a / centroid b>a / tilt b>a / notes" table.\n\n` +
    `Return: the plans path, the output dir, one row per stem (the before→after numbers + any FAIL note), and ` +
    `whether any stem FAILED (a "FAIL:" note = a param that didn't set / a passthrough render). If the command ` +
    `errors (no pedalboard in the venv, missing uaudio plugin, missing input), return ok=false with the error tail.`,
    {
      label: `apply:${mode}`, phase: 'Apply', agentType: 'general-purpose',
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

log(`drum-stems-character[${mode}] done — ${plans.length} plans${doProcess ? `, applied → ${outDir}` : ' (apply skipped)'}`)
return { mode, character: mode === 'character' ? character : null, plans, plansOut, processed: doProcess, processResult, srcDir, outDir }
