export const meta = {
  name: 'warm-bus-shootout',
  description: 'Score N pre-rendered drum-bus (or any audio) variants through a PARALLEL multi-lens Gemini judge panel, then rank and pick the best. Hybrid: render the variants inline first (deterministic DSP), then fan out the perceptual judging here — one independent agent per (variant × criterion). args = { variants:[{name,spec?,path(ABSOLUTE),meters?}], criteria?:[{key,q}], genre?, intent? }.',
  phases: [
    { title: 'Judge', detail: 'one independent Gemini lens agent per (variant × criterion)' },
    { title: 'Rank', detail: 'aggregate lens scores, pick the winner' },
  ],
}

// ---- inputs (parameterized via args; sensible warm/tight defaults) -------------------------------
// Defensive: args may arrive as an object OR a JSON string depending on how it was passed.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
log(`args type=${typeof args}; variants=${(A.variants || []).length}`)
const variants = A.variants || []
const intent = A.intent ||
  'a WARM drum bus with a TIGHT, controlled low end — warmth from tape + tilt, never a bright EQ boost'
const genre = A.genre || 'rock'
const criteria = A.criteria || [
  { key: 'warmth',    q: 'WARMTH / tonal richness — full and warm, NOT dull or muddy' },
  { key: 'tightness', q: 'TIGHT, CONTROLLED low end — punchy bottom with no boom, bloom, or flubby sub' },
  { key: 'life',      q: 'TRANSIENT LIFE / punch — the kit breathes and hits, NOT over-glued or squashed' },
]

if (!variants.length) return { error: 'no variants — pass args.variants = [{name, path, meters?}]' }

const SCORE = {
  type: 'object',
  additionalProperties: false,
  properties: {
    score: { type: 'number', description: '0-10 for THIS one criterion (10 = best)' },
    reason: { type: 'string', description: 'one sentence; cite the meter ground truth where relevant' },
  },
  required: ['score', 'reason'],
}

const metersLine = v => v.meters
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${v.meters.centroid} Hz · tilt ${v.meters.tilt} dB/oct · crest ${v.meters.crest} dB · L-R corr ${v.meters.corr} · ${v.meters.lufs} LUFS.`
  : '(no meters supplied — judge by ear.)'

// ---- Phase 1: parallel multi-lens judging -------------------------------------------------------
// pipeline over variants (no barrier between variants); the criteria for each variant run in parallel.
phase('Judge')
const judged = await pipeline(
  variants,
  v => parallel(criteria.map(c => () =>
    agent(
      `You are ONE judge on a blind panel scoring drum-bus tuning variants for ${intent} (genre: ${genre}).\n` +
      `Score ONLY this single criterion: ${c.q}\n\n` +
      `Listen to this ABSOLUTE audio path using the stemmy-gemini MCP tools: run ToolSearch for ` +
      `"mcp__stemmy-gemini__analyze-mix-balance", then call it with path="${v.path}", genre="${genre}", ` +
      `intent="${intent}". (You may also load "mcp__stemmy-gemini__detect-mix-issues" if useful.)\n` +
      `${metersLine(v)}\n` +
      `Gemini hears ~16 kbps MONO — trust the meter ground truth for loudness/tilt/low-end, and use your ` +
      `ears only for the perceptual FEEL of this one criterion. If the perceptual tool is unavailable, ` +
      `still return a best-effort score reasoned from the meter ground truth alone.\n\n` +
      `Return a 0-10 score (10 = best on THIS criterion only) and a one-sentence reason.`,
      { label: `judge:${v.name}:${c.key}`, phase: 'Judge', schema: SCORE, agentType: 'general-purpose' },
    ).then(r => ({
      variant: v.name,
      criterion: c.key,
      score: (r && typeof r.score === 'number') ? r.score : 0,
      reason: (r && r.reason) || 'no result',
    })),
  )),
)

// ---- Phase 2: aggregate + rank ------------------------------------------------------------------
phase('Rank')
const ranking = variants.map((v, i) => {
  const lenses = (judged[i] || []).filter(Boolean)
  const total = lenses.reduce((s, l) => s + (l.score || 0), 0)
  const byCrit = {}
  lenses.forEach(l => { byCrit[l.criterion] = { score: l.score, reason: l.reason } })
  return {
    variant: v.name,
    spec: v.spec || null,
    total: Math.round(total * 10) / 10,
    max: criteria.length * 10,
    meters: v.meters || null,
    lenses: byCrit,
  }
}).sort((a, b) => b.total - a.total)

log(`ranked ${ranking.length} variants — winner: ${ranking[0].variant} (${ranking[0].total}/${ranking[0].max})`)
return { winner: ranking[0], ranking, criteria: criteria.map(c => c.key) }
