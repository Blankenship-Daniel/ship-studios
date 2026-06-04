export const meta = {
  name: 'funky-drummer',
  description: "Tune + lock the James Brown 'Funky Drummer' (Clyde Stubblefield) drum-bus chain: render N variants of funky_drummer_bus.py (API/MEQ-5 mid amounts, dbx knock, Pultec HLF-3C high-cut, narrow width, ±vintage tape), then score them through a PARALLEL multi-lens Gemini judge panel against the Funky-Drummer brief (DRY, tight knock, MID-FORWARD, vintage band-limit, NARROW/mono-ish) and pick the winner (whose meters become the preset's approved_signature). args = { pre_bus(ABSOLUTE balanced snare/kick-forward bus), out_dir(ABSOLUTE), venv?, script?, variants?:[{name,flags}], criteria?:[{key,q}], genre?, intent? }.",
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
const script = A.script || `${REPO}/scripts/mix/funky_drummer_bus.py`
const preBus = A.pre_bus
const outDir = A.out_dir
const genre = A.genre || 'funk'
const intent = A.intent ||
  "the James Brown 'Funky Drummer' (Clyde Stubblefield, 1969) drum sound — DRY, TIGHT, VINTAGE FUNK: a tight " +
  'VCA KNOCK on the snare/kick, a MID-FORWARD balance (the funk presence is in the midrange, not scooped), a ' +
  'BAND-LIMITED vintage/sample-ready top (rolled-off highs, no modern air), and a NARROW/mono-ish 1969 image'

// The default sweep — the decision points from the recipe. Each renders with the bare-default chain + these flags.
const variants = A.variants || [
  { name: 'default',     flags: '' },                                        // the approved baseline
  { name: 'more_knock',  flags: '--dbx-thresh -18 --api-comp-thresh -10' },  // harder VCA knock
  { name: 'more_mids',   flags: '--meq-hm 5 --api-hmf 4' },                  // pushier mid-forward
  { name: 'darker_top',  flags: '--hlf-highcut "8 KCS"' },                    // more lo-fi band-limit
  { name: 'brighter_top', flags: '--hlf-highcut "15 KCS"' },                 // less band-limit (brighter)
  { name: 'with_tape',   flags: '--tape' },                                  // + vintage 15 IPS warmth
  { name: 'wider_ab',    flags: '--width 0.8' },                            // A/B: wider (should LOSE on 'narrow')
]

const criteria = A.criteria || [
  { key: 'dry',         q: 'DRY / tight — no reverb wash or ambience; a close, compact, in-the-room funk sound' },
  { key: 'knock',       q: 'tight VCA KNOCK — punchy snare/kick attack with snap (crest UP); the funk pocket hits, not squashed' },
  { key: 'midforward',  q: 'MID-FORWARD — the snare/kit midrange (bark + presence) is forward and funky, NOT scooped or hollow' },
  { key: 'vintage',     q: 'VINTAGE / sample-ready — a band-limited, rolled-off-top, period feel (NOT modern hi-fi air/sub)' },
  { key: 'narrow',      q: 'NARROW / mono-ish — the 1969 breakbeat image (centered, not wide); mono-compatible' },
]

if (!preBus || !outDir) return { error: 'pass args.pre_bus (ABSOLUTE balanced snare/kick-forward bus) and args.out_dir (ABSOLUTE)' }

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
    `Render ONE Funky-Drummer drum-bus tuning variant, then report its meters.\n` +
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
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${v.meters.centroid} Hz · tilt ${v.meters.tilt} dB/oct · crest ${v.meters.crest} dB · L-R corr ${v.meters.corr} · ${v.meters.lufs} LUFS. (HIGHER crest = the tight KNOCK = good; LOWER centroid + slightly warmer tilt = the BAND-LIMITED vintage top = good here; corr toward 1.0 = NARROW/mono = good for the breakbeat image.)`
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
      `use your ears only for the perceptual FEEL of this one criterion. Note the codec already sounds ` +
      `band-limited/mono, so confirm 'vintage' and 'narrow' against the meters, not just the codec. If the ` +
      `perceptual tool is unavailable, still return a best-effort score from the meter ground truth alone.\n\n` +
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
  note: "write the winner's meters into presets/mix/funky-drummer.json approved_signature_full_kit (re-render the winner SEQUENTIALLY first — UADx is non-deterministic across the concurrent workflow renders)",
}
