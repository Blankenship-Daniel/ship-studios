export const meta = {
  name: 'fool-in-the-rain',
  description: "Tune + lock the Bonham 'Fool In The Rain' drum-bus chain: render N variants of fool_in_the_rain_bus.py (15 vs 30 IPS, Helios on/off, SSL glue, room/top), then score them through a PARALLEL multi-lens Gemini judge panel against the Bonham brief and pick the winner (whose meters become the preset's approved_signature). args = { pre_bus(ABSOLUTE balanced room-forward bus), out_dir(ABSOLUTE), venv?, script?, variants?:[{name,flags}], criteria?:[{key,q}], genre?, intent? }.",
  phases: [
    { title: 'Render', detail: 'one agent per variant runs the bus script via Bash + reports its FINAL meters' },
    { title: 'Judge', detail: 'one independent Gemini lens agent per (variant × criterion)' },
    { title: 'Rank', detail: 'aggregate lens scores, pick the winner' },
  ],
}

// ---- inputs (parameterized via args) ------------------------------------------------------------
// Defensive: args may arrive as an object OR a JSON string depending on how it was passed.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const REPO = A.repo || '/Users/ship/Documents/code/ship-studios'   // canonical checkout (artifacts/projects live here, not in a worktree)
const venv = A.venv || `${REPO}/../stemmy-loops-mcp/.venv/bin/python`
const script = A.script || `${REPO}/scripts/mix/fool_in_the_rain_bus.py`
const preBus = A.pre_bus
const outDir = A.out_dir
const genre = A.genre || 'rock'
const intent = A.intent ||
  "the John Bonham 'Fool In The Rain' drum sound — ROOM-DOMINANT, warm/dark, fat low-mids, breathing " +
  'glue; the room mic is the reverb; NOT bright, NOT crushed, NOT a modern close-mic kit'

// The default sweep — the decision points from the plan. Each renders with the bare-default chain + these flags.
const variants = A.variants || [
  { name: 'default_15ips',  flags: '' },                              // the approved baseline
  { name: 'tight_30ips',    flags: '--ips "30 IPS"' },               // tighter bottom (less bloom)
  { name: 'no_helios',      flags: '--no-helios' },                  // SSL+tape only (most historically literal)
  { name: 'more_glue',      flags: '--ssl-thresh -20 --ssl-makeup 6' }, // harder bus glue
  { name: 'slow_breathe',   flags: '--ssl-attack 30' },             // slow attack = pump (RAISES crest on peaky drums)
  { name: 'darker_top',     flags: '--repro-hf 1.0 --helios-hs -4' }, // darkest / most vintage top
]

const criteria = A.criteria || [
  { key: 'roominess', q: 'ROOM as the star — big, natural ambience out front; the room IS the reverb (no thin/dry close-mic kit)' },
  { key: 'warmth',    q: 'WARM / DARK tone — full low-mids, rolled-off top; NOT bright, brittle, or harsh' },
  { key: 'glue',      q: 'BREATHING glue — cohesive but alive; NOT crushed/squashed and NOT pumping' },
  { key: 'lowmid',    q: 'FAT LOW-MID WEIGHT — boomy-but-controlled bottom and 200-400 Hz body' },
  { key: 'dynamics',  q: 'NATURAL dynamics + stereo width — the kit breathes and the room image is wide' },
]

if (!preBus || !outDir) return { error: 'pass args.pre_bus (ABSOLUTE balanced room-forward bus) and args.out_dir (ABSOLUTE)' }

const METERS = {
  type: 'object', additionalProperties: false,
  properties: {
    centroid: { type: 'number', description: 'spectral_centroid_hz from the FINAL line' },
    tilt: { type: 'number', description: 'spectral_tilt_db_per_octave from the FINAL line' },
    crest: { type: 'number', description: 'crest_factor_db from the FINAL line' },
    lufs: { type: 'number', description: 'integrated LUFS from the FINAL line' },
    corr: { type: 'number', description: 'L-R correlation from the FINAL line' },
    ok: { type: 'boolean', description: 'true if the render succeeded and the FINAL line was parsed' },
    note: { type: 'string', description: 'one short note; the error text if the render failed' },
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

// ---- Phase 0: render the variants (each agent runs the deterministic bus script via Bash) --------
phase('Render')
const rendered = (await parallel(variants.map(v => () =>
  agent(
    `Render ONE Bonham drum-bus tuning variant, then report its meters.\n` +
    `Run EXACTLY this with the Bash tool (it writes the variant WAV and prints meter lines to stderr/stdout):\n` +
    `  ${venv} "${script}" "${preBus}" "${outDir}/${v.name}.wav" ${v.flags}\n\n` +
    `The script prints two meter lines: one starting "  in" and one starting "  FINAL", each formatted ` +
    `"centroid <Hz> | tilt <dB/oct> | crest <dB> | LUFS <dB> | corr <0-1>". Ignore the noisy UADx/objc log ` +
    `lines. Parse the **FINAL** line and return its five numbers. Set ok=true if it rendered and you parsed ` +
    `FINAL; if the command errored, set ok=false, put the error in note, and return zeros.`,
    { label: `render:${v.name}`, phase: 'Render', schema: METERS, agentType: 'general-purpose' },
  ).then(r => ({
    name: v.name, flags: v.flags, path: `${outDir}/${v.name}.wav`,
    ok: !!(r && r.ok), meters: r ? { centroid: r.centroid, tilt: r.tilt, crest: r.crest, lufs: r.lufs, corr: r.corr } : null,
    note: (r && r.note) || '',
  })),
))).filter(v => v && v.ok)

log(`rendered ${rendered.length}/${variants.length} variants`)
if (!rendered.length) return { error: 'no variants rendered — check the venv/script/pre_bus paths and the vst extra', variants }

const metersLine = v => v.meters
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${v.meters.centroid} Hz · tilt ${v.meters.tilt} dB/oct · crest ${v.meters.crest} dB · L-R corr ${v.meters.corr} · ${v.meters.lufs} LUFS.`
  : '(no meters — judge by ear.)'

// ---- Phase 1: parallel multi-lens judging -------------------------------------------------------
phase('Judge')
const judged = await pipeline(
  rendered,
  v => parallel(criteria.map(c => () =>
    agent(
      `You are ONE judge on a blind panel scoring drum-bus tuning variants for ${intent} (genre: ${genre}).\n` +
      `Score ONLY this single criterion: ${c.q}\n\n` +
      `Listen to this ABSOLUTE audio path using the stemmy-gemini MCP tools: run ToolSearch for ` +
      `"mcp__stemmy-gemini__analyze-mix-balance", then call it with path="${v.path}", genre="${genre}", ` +
      `intent="${intent}". (You may also load "mcp__stemmy-gemini__detect-mix-issues" if useful.)\n` +
      `${metersLine(v)}\n` +
      `Gemini hears ~16 kbps MONO — trust the meter ground truth for loudness/tilt/low-end/correlation, and ` +
      `use your ears only for the perceptual FEEL of this one criterion. If the perceptual tool is ` +
      `unavailable, still return a best-effort score reasoned from the meter ground truth alone.\n\n` +
      `Return a 0-10 score (10 = best on THIS criterion only) and a one-sentence reason.`,
      { label: `judge:${v.name}:${c.key}`, phase: 'Judge', schema: SCORE, agentType: 'general-purpose' },
    ).then(r => ({
      variant: v.name, criterion: c.key,
      score: (r && typeof r.score === 'number') ? r.score : 0,
      reason: (r && r.reason) || 'no result',
    })),
  )),
)

// ---- Phase 2: aggregate + rank ------------------------------------------------------------------
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
  note: "write the winner's meters into presets/mix/fool-in-the-rain.json approved_signature_full_kit",
}
