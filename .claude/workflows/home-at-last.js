export const meta = {
  name: 'home-at-last',
  description: "Tune + lock the Steely Dan 'Home at Last' (Aja / Purdie shuffle) drum-bus chain: render N variants of home_at_last_bus.py (Pultec air/low amounts, Manley threshold/attack, 30-vs-15 IPS, tape drive), then score them through a PARALLEL multi-lens Gemini judge panel against the Aja brief (clean/hi-fi, preserved ghost-note DYNAMICS, silky top, tight-round low, natural width) and pick the winner (whose meters become the preset's approved_signature). args = { pre_bus(ABSOLUTE balanced snare/kit-forward bus), out_dir(ABSOLUTE), venv?, script?, variants?:[{name,flags}], criteria?:[{key,q}], genre?, intent? }.",
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
const script = A.script || `${REPO}/scripts/mix/home_at_last_bus.py`
const preBus = A.pre_bus
const outDir = A.out_dir
const genre = A.genre || 'jazz-rock'
const intent = A.intent ||
  "the Steely Dan 'Home at Last' (Aja, 1977 / Bernard Purdie shuffle) drum sound — CLEAN / hi-fi and " +
  'DETAILED, warm-but-not-dark, DYNAMIC with the snare ghost-note contrast preserved (NOT crushed, NOT pumping), ' +
  'tight/ROUND controlled low end, silky extended top with no harshness, NATURAL balanced width (not mono, not wide-room)'

// The default sweep — the decision points from the recipe. Each renders with the bare-default chain + these flags.
const variants = A.variants || [
  { name: 'default_30ips', flags: '' },                                  // the approved baseline (tight/controlled low)
  { name: 'bloom_15ips',   flags: '--ips "15 IPS"' },                    // looser/fuller low (the Bonham move) — A/B
  { name: 'more_glue',     flags: '--mu-thresh 3' },                     // harder Manley glue (watch the crest!)
  { name: 'most_dynamic',  flags: '--mu-thresh 7 --tape-in 1.0 --mu-attack 2' }, // maximum dynamics preserved
  { name: 'airier_top',    flags: '--pul-hf-boost 6 --pul-hf-atten 1' }, // more silky air
  { name: 'bigger_low',    flags: '--pul-lf-boost 6 --pul-lf-atten 5' }, // bigger-but-tighter low-end trick
]

const criteria = A.criteria || [
  { key: 'clean',    q: 'CLEAN / hi-fi DETAIL — articulate, well-separated, audiophile; NO murk, smear, lo-fi grit, or distortion' },
  { key: 'dynamics', q: 'PRESERVED ghost-note DYNAMICS — clear loud-backbeat vs quiet-ghost contrast (crest held/up); NOT compressed/pumping/flattened' },
  { key: 'top',      q: 'WARM-but-SILKY top — open and extended air, NO harshness/fizz/sibilance in 3-8 kHz, and NOT rolled-off-dark' },
  { key: 'low',      q: 'TIGHT / ROUND low end — weighty and full at the fundamental but controlled and clean; no boom, bloom, mud, or low-mid build-up' },
  { key: 'width',    q: 'NATURAL / balanced width — a believable studio kit, neither mono/narrow nor hyper-wide, and mono-compatible' },
]

if (!preBus || !outDir) return { error: 'pass args.pre_bus (ABSOLUTE balanced snare/kit-forward bus) and args.out_dir (ABSOLUTE)' }

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
    `Render ONE Home-at-Last drum-bus tuning variant, then report its meters.\n` +
    `Run EXACTLY this with the Bash tool (it writes the variant WAV and prints meter lines to stderr/stdout):\n` +
    `  ${venv} "${script}" "${preBus}" "${outDir}/${v.name}.wav" ${v.flags}\n\n` +
    `The script prints two meter lines: one starting "  in" and one starting "  FINAL", each formatted ` +
    `"centroid <Hz> | tilt <dB/oct> | crest <dB> | LUFS <dB> | corr <0-1>". Ignore the noisy UADx/objc log ` +
    `lines. Parse the **FINAL** line and return its five numbers. Set ok=true if it rendered and you parsed ` +
    `FINAL; if the command errored, set ok=false, put the error in note, and return zeros. (NOTE: UADx renders ` +
    `can be flaky run back-to-back — if it fails once, retry the SAME command once before giving up.)`,
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
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${v.meters.centroid} Hz · tilt ${v.meters.tilt} dB/oct · crest ${v.meters.crest} dB · L-R corr ${v.meters.corr} · ${v.meters.lufs} LUFS. (HIGHER crest = MORE dynamics preserved = better for Home at Last; centroid HELD = top detail kept; corr toward 1.0 = narrower/mono = WORSE here.)`
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
  note: "write the winner's meters into presets/mix/home-at-last.json approved_signature_full_kit (re-render the winner SEQUENTIALLY first — UADx is non-deterministic across the concurrent workflow renders)",
}
