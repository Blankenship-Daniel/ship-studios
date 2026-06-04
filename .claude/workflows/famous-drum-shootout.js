export const meta = {
  name: 'famous-drum-shootout',
  description: "Cross-character RECOMMENDER (NOT a per-recipe tuner): render ONE prepared/balanced drum bus through ALL the famous-drum character bus scripts at their DEFAULTS (fool-in-the-rain, tomorrow-never-knows, home-at-last, in-the-air-tonight, when-the-levee-breaks, back-in-black, funky-drummer), then a PARALLEL multi-lens Gemini panel scores each character's fit to the user's brief and RECOMMENDS the best-fit iconic character for this material. args = { pre_bus(ABSOLUTE balanced drum bus), out_dir(ABSOLUTE), brief, genre?, venv?, characters?:[{name,script}], criteria?:[{key,q}] }.",
  phases: [
    { title: 'Render', detail: 'one agent per CHARACTER runs its bus script (defaults) on the shared pre-bus + reports its FINAL meters' },
    { title: 'Judge', detail: 'one independent Gemini lens agent per (character × criterion) scores fit-to-brief' },
    { title: 'Recommend', detail: 'aggregate, rank, recommend the best-fit iconic character + dissent' },
  ],
}

// ---- inputs (parameterized via args) ------------------------------------------------------------
// Defensive: args may arrive as an object OR a JSON string depending on how it was passed.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const REPO = A.repo || '/Users/ship/Documents/code/ship-studios'   // canonical checkout (artifacts/projects live here, not in a worktree)
const venv = A.venv || `${REPO}/../stemmy-loops-mcp/.venv/bin/python`
const preBus = A.pre_bus
const outDir = A.out_dir
const genre = A.genre || 'drums'
const brief = A.brief ||
  'pick the iconic drum character that best fits this material (no specific brief given — judge each on its ' +
  'own merits: cohesion, musicality, and how distinctive/usable the character is on this kit)'

// The 7 famous-drum characters -> their default bus scripts. Each is rendered with BARE DEFAULTS on the SAME pre-bus.
const characters = A.characters || [
  { name: 'fool-in-the-rain',     script: `${REPO}/scripts/mix/fool_in_the_rain_bus.py`,      id: 'Bonham / room-warm, wide, clean glue, big-but-open' },
  { name: 'tomorrow-never-knows', script: `${REPO}/scripts/mix/tomorrow_never_knows_bus.py`,  id: 'Beatles / crushed, dark, lo-fi, MONO/narrow' },
  { name: 'home-at-last',         script: `${REPO}/scripts/mix/home_at_last_bus.py`,          id: 'Steely Dan Aja / clean, hi-fi, DYNAMIC, silky, natural width' },
  { name: 'in-the-air-tonight',   script: `${REPO}/scripts/mix/in_the_air_tonight_bus.py`,    id: 'Phil Collins / EXPLOSIVE gated reverb, HUGE/WIDE' },
  { name: 'when-the-levee-breaks', script: `${REPO}/scripts/mix/when_the_levee_breaks_bus.py`, id: 'Bonham stairwell / distant-mic CRUSH, dark/cavernous, narrow' },
  { name: 'back-in-black',        script: `${REPO}/scripts/mix/back_in_black_bus.py`,         id: 'AC/DC / TIGHT, PUNCHY, DRY, PRESENT arena rock' },
  { name: 'funky-drummer',        script: `${REPO}/scripts/mix/funky_drummer_bus.py`,         id: 'James Brown / DRY, tight, MID-FORWARD, band-limited, narrow breakbeat' },
]

// Fit-to-brief lenses (descriptive + brief-relative). The recommendation is the highest total.
const criteria = A.criteria || [
  { key: 'fit',     q: 'OVERALL FIT to the brief — how well this drum character serves the stated material/goal' },
  { key: 'impact',  q: 'IMPACT / energy — is the punch/weight/drive appropriate to the brief (not too soft, not over-squashed)?' },
  { key: 'tone',    q: 'TONE fit — does the tonal character (warm/dark/present/bright) suit the brief?' },
  { key: 'space',   q: 'SPACE / width fit — does the sense of room/width (dry-narrow vs ambient-wide) suit the brief?' },
  { key: 'musical', q: 'MUSICAL & COHESIVE — does it sound intentional, balanced, and usable (not broken, harsh, or over-processed)?' },
]

if (!preBus || !outDir) return { error: 'pass args.pre_bus (ABSOLUTE balanced drum bus) and args.out_dir (ABSOLUTE), plus args.brief' }

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
    score: { type: 'number', description: '0-10 for THIS one criterion (10 = best fit)' },
    reason: { type: 'string', description: 'one sentence; cite the meter ground truth where relevant' },
  },
  required: ['score', 'reason'],
}

// ---- Phase 0: render each character through its bus script (bare defaults) on the SAME pre-bus ----
phase('Render')
const rendered = (await parallel(characters.map(c => () =>
  agent(
    `Render ONE famous-drum CHARACTER on a shared pre-bus (bare defaults), then report its meters.\n` +
    `Run EXACTLY this with the Bash tool (it writes the character WAV and prints meter lines):\n` +
    `  ${venv} "${c.script}" "${preBus}" "${outDir}/${c.name}.wav"\n\n` +
    `The script prints two meter lines: one starting "  in" and one starting "  FINAL", each formatted ` +
    `"centroid <Hz> | tilt <dB/oct> | crest <dB> | LUFS <dB> | corr <0-1>". Ignore the noisy UADx/objc log ` +
    `lines. Parse the **FINAL** line and return its five numbers. Set ok=true if it rendered and you parsed ` +
    `FINAL; if the command errored, set ok=false, put the error in note, and return zeros. (NOTE: most of ` +
    `these load UADx plugins and can be flaky run back-to-back — if it fails once, retry the SAME command once.)`,
    { label: `render:${c.name}`, phase: 'Render', schema: METERS, agentType: 'general-purpose' },
  ).then(r => ({
    name: c.name, id: c.id, path: `${outDir}/${c.name}.wav`,
    ok: !!(r && r.ok), meters: r ? { centroid: r.centroid, tilt: r.tilt, crest: r.crest, lufs: r.lufs, corr: r.corr } : null,
    note: (r && r.note) || '',
  })),
))).filter(c => c && c.ok)

log(`rendered ${rendered.length}/${characters.length} characters`)
if (!rendered.length) return { error: 'no characters rendered — check the venv/script/pre_bus paths and the vst extra', characters }

const metersLine = c => c.meters
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${c.meters.centroid} Hz · tilt ${c.meters.tilt} dB/oct · crest ${c.meters.crest} dB · L-R corr ${c.meters.corr} · ${c.meters.lufs} LUFS.`
  : '(no meters — judge by ear.)'

// ---- Phase 1: parallel fit-to-brief judging (blind to the character's identity) ------------------
phase('Judge')
const judged = await pipeline(
  rendered,
  c => parallel(criteria.map(cr => () =>
    agent(
      `You are ONE judge on a blind panel choosing the best DRUM CHARACTER for this brief (genre: ${genre}).\n` +
      `THE BRIEF: ${brief}\n\n` +
      `Score ONLY this single criterion: ${cr.q}\n\n` +
      `Listen to this ABSOLUTE audio path using the stemmy-gemini MCP tools: run ToolSearch for ` +
      `"mcp__stemmy-gemini__analyze-mix-balance", then call it with path="${c.path}", genre="${genre}", ` +
      `intent="${brief}". (You may also load "mcp__stemmy-gemini__detect-mix-issues".)\n` +
      `${metersLine(c)}\n` +
      `Judge this one variant on its own merit against the brief — do NOT try to guess which famous record it ` +
      `is. Gemini hears ~16 kbps MONO — trust the meter ground truth for loudness/tilt/crest/correlation, and ` +
      `use your ears only for the perceptual FEEL of this one criterion. If the perceptual tool is ` +
      `unavailable, still return a best-effort score reasoned from the meter ground truth alone.\n\n` +
      `Return a 0-10 score (10 = best fit on THIS criterion only) and a one-sentence reason.`,
      { label: `judge:${c.name}:${cr.key}`, phase: 'Judge', schema: SCORE, agentType: 'general-purpose' },
    ).then(r => ({
      character: c.name, criterion: cr.key,
      score: (r && typeof r.score === 'number') ? r.score : 0,
      reason: (r && r.reason) || 'no result',
    })),
  )),
)

// ---- Phase 2: aggregate + recommend -------------------------------------------------------------
phase('Recommend')
const ranking = rendered.map((c, i) => {
  const lenses = (judged[i] || []).filter(Boolean)
  const total = lenses.reduce((s, l) => s + (l.score || 0), 0)
  const byCrit = {}
  lenses.forEach(l => { byCrit[l.criterion] = { score: l.score, reason: l.reason } })
  return {
    character: c.name, id: c.id, path: c.path,
    total: Math.round(total * 10) / 10, max: criteria.length * 10,
    meters: c.meters || null, lenses: byCrit,
  }
}).sort((a, b) => b.total - a.total)

log(`ranked ${ranking.length} characters — recommended: ${ranking[0].character} (${ranking[0].total}/${ranking[0].max})`)
return {
  recommended: ranking[0],
  runner_up: ranking[1] || null,
  ranking,
  criteria: criteria.map(c => c.key),
  note: "this RECOMMENDS an iconic drum character for THIS material (rendered at bare defaults on a single pre-bus, so the balance is not yet recipe-optimal). To commit: run the recommended character's full /<name> pipeline (re-balance per its preset), then its /<name> tuning workflow with a SEQUENTIAL re-render to lock approved_signature — UADx is non-deterministic across these concurrent renders, so treat this ranking as a RELATIVE guide, not locked meters.",
}
