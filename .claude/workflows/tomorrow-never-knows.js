export const meta = {
  name: 'tomorrow-never-knows',
  description: "Tune + lock the Beatles 'Tomorrow Never Knows' drum-bus chain: render N variants of tomorrow_never_knows_bus.py (Fairchild drive, +LA-3A crush, +Vibe lo-fi, dark/narrow amounts), then score them through a PARALLEL multi-lens Gemini judge panel against the TNK brief (pump/dark/grit/mono/weight) and pick the winner. args = { pre_bus(ABSOLUTE tom-forward bus), out_dir(ABSOLUTE), venv?, script?, variants?:[{name,flags}], criteria?:[{key,q}], genre?, intent? }.",
  phases: [
    { title: 'Render', detail: 'one agent per variant runs the bus script via Bash + reports its FINAL meters' },
    { title: 'Judge', detail: 'one independent Gemini lens agent per (variant × criterion)' },
    { title: 'Rank', detail: 'aggregate lens scores, pick the winner' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const REPO = '/Users/ship/Documents/code/ship-studios'
const WORKTREE = `${REPO}/.claude/worktrees/temporal-stirring-pretzel`
const venv = A.venv || `${REPO}/../stemmy-loops-mcp/.venv/bin/python`
// default to the worktree script (pre-merge); pass A.script to override (e.g. the merged REPO path)
const script = A.script || `${WORKTREE}/scripts/mix/tomorrow_never_knows_bus.py`
const preBus = A.pre_bus
const outDir = A.out_dir
const genre = A.genre || 'rock'
const intent = A.intent ||
  "The Beatles 'Tomorrow Never Knows' (Ringo/Emerick 1966) drum sound — heavily COMPRESSED with audible " +
  'PUMP/breathing, DARK/lo-fi/saturated (no air), MONO/narrow, tom-forward, deep damped kick. NOT bright, ' +
  'NOT wide, NOT clean/modern.'

const variants = A.variants || [
  { name: 'fairchild_default', flags: '' },                              // authentic gentle pump
  { name: 'fairchild_hard',    flags: '--fc-input -4 --fc-headroom 4 --fc-tc 1' }, // drive the Fairchild harder
  { name: 'plus_la3a',         flags: '--la3a' },                        // heavy crush (real crest reduction)
  { name: 'plus_vibe',         flags: '--vibe' },                        // lo-fi grit
  { name: 'la3a_vibe',         flags: '--la3a --vibe' },                 // max crush + lo-fi
  { name: 'less_dark',         flags: '--repro-hf 3 --dark -2' },        // lighter top if the default over-darkens
]

const criteria = A.criteria || [
  { key: 'pump',   q: 'PUMP / breathing — obvious gain-reduction that swells the ambience between hits; crushed not dynamic' },
  { key: 'dark',   q: 'DARK / lo-fi — rolled-off top, no air, vintage tape character; not bright/modern' },
  { key: 'grit',   q: 'SATURATED grit — tape/tube harmonic colour, thick and a touch dirty (the 1966 feel)' },
  { key: 'mono',   q: 'NARROW / mono image — tight, centered, not wide/roomy (the 1966 mono drums)' },
  { key: 'weight', q: 'LOW-MID WEIGHT — deep damped kick + fat 200-400 Hz body; boomy-but-controlled' },
]

if (!preBus || !outDir) return { error: 'pass args.pre_bus (ABSOLUTE tom-forward bus) and args.out_dir (ABSOLUTE)' }

const METERS = {
  type: 'object', additionalProperties: false,
  properties: {
    centroid: { type: 'number' }, tilt: { type: 'number' }, crest: { type: 'number' },
    lufs: { type: 'number' }, corr: { type: 'number' },
    ok: { type: 'boolean' }, note: { type: 'string' },
  },
  required: ['centroid', 'tilt', 'crest', 'lufs', 'corr', 'ok', 'note'],
}
const SCORE = {
  type: 'object', additionalProperties: false,
  properties: {
    score: { type: 'number', description: '0-10 for THIS one criterion (10 = best)' },
    reason: { type: 'string', description: 'one sentence; cite the meter ground truth where relevant' },
  },
  required: ['score', 'reason'],
}

// ---- Phase 0: render variants (agents run the deterministic bus script via Bash) ----------------
phase('Render')
const rendered = (await parallel(variants.map(v => () =>
  agent(
    `Render ONE Tomorrow-Never-Knows drum-bus tuning variant, then report its meters.\n` +
    `Run EXACTLY this with the Bash tool:\n` +
    `  ${venv} "${script}" "${preBus}" "${outDir}/${v.name}.wav" ${v.flags}\n\n` +
    `It prints two meter lines ("  in" and "  FINAL"), each "centroid <Hz> | tilt <dB/oct> | crest <dB> | ` +
    `LUFS <dB> | corr <0-1>". Ignore the noisy UADx/objc log lines. Parse the **FINAL** line and return its ` +
    `five numbers. ok=true if it rendered + parsed; on error ok=false, put the error in note, return zeros.`,
    { label: `render:${v.name}`, phase: 'Render', schema: METERS, agentType: 'general-purpose' },
  ).then(r => ({
    name: v.name, flags: v.flags, path: `${outDir}/${v.name}.wav`,
    ok: !!(r && r.ok), meters: r ? { centroid: r.centroid, tilt: r.tilt, crest: r.crest, lufs: r.lufs, corr: r.corr } : null,
    note: (r && r.note) || '',
  })),
))).filter(v => v && v.ok)

log(`rendered ${rendered.length}/${variants.length} variants`)
if (!rendered.length) return { error: 'no variants rendered — check venv/script/pre_bus paths and the vst extra', variants }

const metersLine = v => v.meters
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${v.meters.centroid} Hz · tilt ${v.meters.tilt} dB/oct · crest ${v.meters.crest} dB · L-R corr ${v.meters.corr} · ${v.meters.lufs} LUFS. (Lower centroid / more-negative tilt = darker; lower crest = more pump/crush; corr toward 1.0 = mono/narrow.)`
  : '(no meters — judge by ear.)'

// ---- Phase 1: parallel multi-lens judging ------------------------------------------------------
phase('Judge')
const judged = await pipeline(
  rendered,
  v => parallel(criteria.map(c => () =>
    agent(
      `You are ONE judge on a blind panel scoring drum-bus tuning variants for ${intent} (genre: ${genre}).\n` +
      `Score ONLY this single criterion: ${c.q}\n\n` +
      `Listen to this ABSOLUTE audio path using the stemmy-gemini MCP tools: run ToolSearch for ` +
      `"mcp__stemmy-gemini__analyze-mix-balance", then call it with path="${v.path}", genre="${genre}", ` +
      `intent="${intent}". (You may also load "mcp__stemmy-gemini__detect-mix-issues".)\n` +
      `${metersLine(v)}\n` +
      `Gemini hears ~16 kbps MONO — trust the meter ground truth for loudness/tilt/crest/correlation, and use ` +
      `your ears only for the perceptual FEEL of this one criterion (the pump, the grit, the darkness). If the ` +
      `perceptual tool is unavailable, score from the meters alone.\n\n` +
      `Return a 0-10 score (10 = best on THIS criterion only) and a one-sentence reason.`,
      { label: `judge:${v.name}:${c.key}`, phase: 'Judge', schema: SCORE, agentType: 'general-purpose' },
    ).then(r => ({
      variant: v.name, criterion: c.key,
      score: (r && typeof r.score === 'number') ? r.score : 0,
      reason: (r && r.reason) || 'no result',
    })),
  )),
)

// ---- Phase 2: aggregate + rank -----------------------------------------------------------------
phase('Rank')
const ranking = rendered.map((v, i) => {
  const lenses = (judged[i] || []).filter(Boolean)
  const total = lenses.reduce((s, l) => s + (l.score || 0), 0)
  const byCrit = {}
  lenses.forEach(l => { byCrit[l.criterion] = { score: l.score, reason: l.reason } })
  return {
    variant: v.name, flags: v.flags, path: v.path,
    total: Math.round(total * 10) / 10, max: criteria.length * 10,
    meters: v.meters || null, lenses: byCrit,
  }
}).sort((a, b) => b.total - a.total)

log(`ranked ${ranking.length} variants — winner: ${ranking[0].variant} (${ranking[0].total}/${ranking[0].max})`)
return {
  winner: ranking[0], ranking, criteria: criteria.map(c => c.key),
  note: "write the winner's meters into presets/mix/tomorrow-never-knows.json approved_signature",
}
