export const meta = {
  name: 'audio-shootout',
  description: 'Domain-neutral A/B/C judge panel for ANY pre-rendered, level-matched audio variants — master-loudness targets, reference-match strengths, drum-mix feels, VST chains, FX-on/off. RENDER + LEVEL-MATCH the variants INLINE first (deterministic DSP/VST), then this fans out a multi-lens Gemini judge panel: one independent agent per (variant × criterion), each scores 0-10 against a SCORE schema citing the stereo meter ground truth, then aggregate + rank + report dissent. args = { variants:[{name,spec?,path(ABSOLUTE),meters?}], criteria?:[{key,q}], intent?, genre?, anchorPath? }.',
  phases: [
    { title: 'Judge', detail: 'one independent Gemini lens agent per (variant × criterion)' },
    { title: 'Rank',  detail: 'aggregate lens scores across variants, pick the winner, report dissent' },
  ],
}

// ---- inputs (parameterized via args; NEUTRAL defaults — NOT warm-drum-bus taste) ----------------
// Defensive: args may arrive as an object OR a JSON string depending on how it was passed.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
log(`args type=${typeof args}; variants=${(A.variants || []).length}`)

const variants = A.variants || []
const intent   = A.intent || 'the best-sounding variant for its stated purpose — clean, balanced, musical'
const genre    = A.genre  || 'unspecified'
const criteria = A.criteria || [
  { key: 'tone',     q: 'TONAL BALANCE vs the intent — full, not dull or harsh' },
  { key: 'dynamics', q: 'DYNAMICS / punch — controlled, not squashed or spiky' },
  { key: 'image',    q: 'STEREO IMAGE / depth — wide but mono-safe' },
]

if (!variants.length) {
  return { error: 'no variants — pass args.variants = [{name, path(ABSOLUTE, level-matched), meters?}]' }
}

const SCORE = {
  type: 'object',
  additionalProperties: false,
  properties: {
    score:  { type: 'number', description: '0-10 for THIS one criterion (10 = best)' },
    reason: { type: 'string', description: 'one sentence; cite the meter ground truth where relevant' },
  },
  required: ['score', 'reason'],
}

const metersLine = v => v.meters
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${v.meters.centroid} Hz · tilt ${v.meters.tilt} dB/oct · crest ${v.meters.crest} dB · L-R corr ${v.meters.corr} · ${v.meters.lufs} LUFS.`
  : '(no meters supplied — judge by ear.)'
const anchorLine = A.anchorPath
  ? `A level-matched baseline for context is at "${A.anchorPath}" — you MAY load it to anchor your sense of "better", but score THIS variant on its own.`
  : ''

// ---- Phase 1: parallel multi-lens judging -------------------------------------------------------
// pipeline over variants (no barrier between variants); the criteria for each variant run in parallel.
phase('Judge')
const judged = await pipeline(
  variants,
  v => parallel(criteria.map(c => () =>
    agent(
      `You are ONE judge on a blind panel scoring pre-rendered audio variants for this intent: ${intent} (genre: ${genre}).\n` +
      `Score ONLY this single criterion: ${c.q}\n\n` +
      `Listen to this ABSOLUTE audio path using the stemmy-gemini MCP tools: run ToolSearch for ` +
      `"mcp__stemmy-gemini__analyze-mix-balance", then call it with path="${v.path}", genre="${genre}", ` +
      `intent="${intent}". (You may also load "mcp__stemmy-gemini__detect-mix-issues" if useful.)\n` +
      `${metersLine(v)}\n${anchorLine}\n` +
      `Gemini hears ~16 kbps MONO — trust the meter ground truth for loudness/tilt/low-end/stereo, and use ` +
      `your ears only for the perceptual FEEL of this one criterion. If the perceptual tool is unavailable, ` +
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

const winner = ranking[0]
// dissent: a criterion where a non-winner outscores the winner (surface, don't bury)
const dissent = criteria.map(c => {
  const best = ranking
    .map(r => ({ v: r.variant, s: (r.lenses[c.key] || {}).score || 0 }))
    .sort((a, b) => b.s - a.s)[0]
  return best && best.v !== winner.variant ? { criterion: c.key, prefers: best.v, score: best.s } : null
}).filter(Boolean)

log(`ranked ${ranking.length} variants — winner: ${winner.variant} (${winner.total}/${winner.max})`)
return { winner, ranking, criteria: criteria.map(c => c.key), dissent }
