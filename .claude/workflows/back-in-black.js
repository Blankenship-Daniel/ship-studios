export const meta = {
  name: 'back-in-black',
  description: "Tune + lock the AC/DC 'Back in Black' (Mutt Lange / Tony Platt) drum-bus chain: render N variants of back_in_black_bus.py (Transient Shaper punch, SSL 4K E colour/threshold/FAST, dbx ratio, present-top amount), then score them through a PARALLEL multi-lens Gemini judge panel against the Back-in-Black brief (tight, punchy, DRY, present-not-dark, natural width) and pick the winner (whose meters become the preset's approved_signature). args = { pre_bus(ABSOLUTE balanced kick/snare-forward bus), out_dir(ABSOLUTE), venv?, script?, variants?:[{name,flags}], criteria?:[{key,q}], genre?, intent? }.",
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
const script = A.script || `${REPO}/scripts/mix/back_in_black_bus.py`
const preBus = A.pre_bus
const outDir = A.out_dir
const genre = A.genre || 'rock'
const intent = A.intent ||
  "the AC/DC 'Back in Black' (Mutt Lange / Tony Platt, 1980) drum sound — TIGHT, PUNCHY, DRY and PRESENT " +
  'arena rock: low-tuned controlled drums, strong upfront transients (the kick + snare punch), a present ' +
  '(NEVER dark) top, captured dry and compact with MINIMAL effects (no tape, no reverb), natural width'

// The default sweep — the decision points from the recipe. Each renders with the bare-default chain + these flags.
const variants = A.variants || [
  { name: 'default',     flags: '' },                                        // the approved baseline (Black, FAST out, dbx 4:1)
  { name: 'more_punch',  flags: '--ts-punch 3 --dbx-thresh -22' },           // harder punch (watch for snare spit)
  { name: 'tighter',     flags: '--ts-sustain -4 --ssl-thresh -18' },        // tighter boom + more glue
  { name: 'brown_eq',    flags: '--ssl-colour Brown' },                      // brightest top + air (vs Black weight)
  { name: 'orange_eq',   flags: '--ssl-colour Orange' },                     // forward 2.5-5k mids (kick/snare card)
  { name: 'more_present', flags: '--present 2 --ssl-air 2.5' },              // pushier present top
  { name: 'ssl_fast_in', flags: '--ssl-fast In' },                          // A/B: denser/tamer (should LOSE on punch)
]

const criteria = A.criteria || [
  { key: 'tight',   q: 'TIGHT / controlled low end — low-tuned but no boom, mud, or ring; the kick & snare body are compact' },
  { key: 'punchy',  q: 'PUNCHY transients — strong upfront kick + snare attack (crest UP); the hits hit hard, not squashed/over-glued' },
  { key: 'dry',     q: 'DRY / compact — no audible reverb, tape wash, or ambience; an in-your-face close sound (minimal effects)' },
  { key: 'present', q: 'PRESENT top — clear, forward, present cymbals/snare; bright-enough and articulate, NOT dark or rolled-off' },
  { key: 'width',   q: 'NATURAL width — a believable rock kit image, neither mono/narrow nor hyper-wide, and mono-compatible' },
]

if (!preBus || !outDir) return { error: 'pass args.pre_bus (ABSOLUTE balanced kick/snare-forward bus) and args.out_dir (ABSOLUTE)' }

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

// ---- Phase 0: render the variants (each agent runs the bus script via Bash) ----------------------
phase('Render')
const rendered = (await parallel(variants.map(v => () =>
  agent(
    `Render ONE Back-in-Black drum-bus tuning variant, then report its meters.\n` +
    `Run EXACTLY this with the Bash tool (it writes the variant WAV and prints meter lines):\n` +
    `  ${venv} "${script}" "${preBus}" "${outDir}/${v.name}.wav" ${v.flags}\n\n` +
    `The script prints two meter lines: one starting "  in" and one starting "  FINAL", each formatted ` +
    `"centroid <Hz> | tilt <dB/oct> | crest <dB> | LUFS <dB> | corr <0-1>". Ignore the noisy UADx/objc log ` +
    `lines. Parse the **FINAL** line and return its five numbers. Set ok=true if it rendered and you parsed ` +
    `FINAL; if the command errored, set ok=false, put the error in note, and return zeros. (NOTE: UADx ` +
    `renders can be flaky run back-to-back — if it fails once, retry the SAME command once before giving up.)`,
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
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${v.meters.centroid} Hz · tilt ${v.meters.tilt} dB/oct · crest ${v.meters.crest} dB · L-R corr ${v.meters.corr} · ${v.meters.lufs} LUFS. (HIGHER crest = MORE punch = better for Back in Black; centroid UP / tilt held = PRESENT not dark = good; corr toward 1.0 = narrower/mono = WORSE — keep it natural.)`
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
      `Gemini hears ~16 kbps MONO — trust the meter ground truth for loudness/tilt/crest/correlation, and ` +
      `use your ears only for the perceptual FEEL of this one criterion (esp. 'dry' and 'present', which the ` +
      `codec can mis-read). If the perceptual tool is unavailable, still return a best-effort score reasoned ` +
      `from the meter ground truth alone.\n\n` +
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
  note: "write the winner's meters into presets/mix/back-in-black.json approved_signature_full_kit (re-render the winner SEQUENTIALLY first — UADx is non-deterministic across the concurrent workflow renders)",
}
