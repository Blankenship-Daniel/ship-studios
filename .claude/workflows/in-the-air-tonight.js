export const meta = {
  name: 'in-the-air-tonight',
  description: "Tune + lock the Phil Collins 'In the Air Tonight' (Padgham gated-reverb) drum-bus chain: render N variants of in_the_air_tonight_bus.py (reverb decay, gate hold/release, wet blend, width, ambience-crush amount, gated-vs-ungated), then score them through a PARALLEL multi-lens Gemini judge panel against the gated-reverb brief (explosive ambience, the ABRUPT gated cutoff, HUGE width, dry punch-through) and pick the winner (whose meters become the preset's approved_signature). The default path is deterministic (no VST), so the winner re-renders exactly. args = { pre_bus(ABSOLUTE balanced snare/tom-forward bus), out_dir(ABSOLUTE), venv?, script?, variants?:[{name,flags}], criteria?:[{key,q}], genre?, intent? }.",
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
const script = A.script || `${REPO}/scripts/mix/in_the_air_tonight_bus.py`
const preBus = A.pre_bus
const outDir = A.out_dir
const genre = A.genre || 'pop-rock'
const intent = A.intent ||
  "the Phil Collins 'In the Air Tonight' (Hugh Padgham, 1981) GATED-REVERB drum sound — EXPLOSIVE: a big, " +
  'slightly dark room ambience that is HEAVILY COMPRESSED so it explodes around the hits, then CUT OFF ' +
  'ABRUPTLY by a noise gate (no decaying tail — the reverb stops dead), blended big under the dry kit and ' +
  'spread WIDE/HUGE across the stereo field, with the dry hits punching cleanly THROUGH the explosion'

// The default sweep — the decision points from the recipe. Each renders with the bare-default chain + these flags.
const variants = A.variants || [
  { name: 'default',      flags: '' },                                       // the approved baseline
  { name: 'bigger_room',  flags: '--decay-s 2.2' },                          // larger ambience
  { name: 'tighter_gate', flags: '--gate-hold-ms 200 --gate-release-ms 18' }, // shorter, snappier gate
  { name: 'longer_gate',  flags: '--gate-hold-ms 450' },                     // longer open window
  { name: 'wetter',       flags: '--wet 0.95' },                             // more ambience vs dry
  { name: 'more_crush',   flags: '--rev-comp-ratio 12 --rev-comp-thresh -34' }, // more explosive
  { name: 'ungated_ab',   flags: '--no-gate' },                             // A/B: should LOSE the gated lens
]

const criteria = A.criteria || [
  { key: 'explosive', q: 'EXPLOSIVE ambience — a heavily-compressed room that EXPLODES/whoomphs around each hit (big, dense, powerful), not a thin or polite reverb' },
  { key: 'gated',     q: 'ABRUPT GATED cutoff — the reverb stops DEAD after each hit with NO decaying tail (the 80s gated-reverb slam); a long smooth tail is WRONG here' },
  { key: 'huge',      q: 'HUGE / WIDE stereo image — the ambience fills the field, big and wide (NOT mono/narrow); mono-compatible enough to translate' },
  { key: 'punch',     q: 'DRY PUNCH-THROUGH — the dry kit hits cut cleanly THROUGH the explosion (transients survive); the reverb does not smear or swallow the hits' },
  { key: 'vibe',      q: 'OVERALL 80s gated-reverb VIBE — does it read as the big, explosive, gated In-the-Air-Tonight drum sound?' },
]

if (!preBus || !outDir) return { error: 'pass args.pre_bus (ABSOLUTE balanced snare/tom-forward bus) and args.out_dir (ABSOLUTE)' }

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
    `Render ONE In-the-Air-Tonight (gated-reverb) drum-bus tuning variant, then report its meters.\n` +
    `Run EXACTLY this with the Bash tool (it writes the variant WAV and prints meter lines):\n` +
    `  ${venv} "${script}" "${preBus}" "${outDir}/${v.name}.wav" ${v.flags}\n\n` +
    `The script prints two meter lines: one starting "  in" and one starting "  FINAL", each formatted ` +
    `"centroid <Hz> | tilt <dB/oct> | crest <dB> | LUFS <dB> | corr <0-1>". Parse the **FINAL** line and ` +
    `return its five numbers. Set ok=true if it rendered and you parsed FINAL; if the command errored, set ` +
    `ok=false, put the error in note, and return zeros. (The default path is PURE DSP — no UADx — so it ` +
    `should not be flaky; if it errors, the venv/script/pre_bus path is likely wrong.)`,
    { label: `render:${v.name}`, phase: 'Render', schema: METERS, agentType: 'general-purpose' },
  ).then(r => ({
    name: v.name, flags: v.flags, path: `${outDir}/${v.name}.wav`,
    ok: !!(r && r.ok), meters: r ? { centroid: r.centroid, tilt: r.tilt, crest: r.crest, lufs: r.lufs, corr: r.corr } : null,
    note: (r && r.note) || '',
  })),
))).filter(v => v && v.ok)

log(`rendered ${rendered.length}/${variants.length} variants`)
if (!rendered.length) return { error: 'no variants rendered — check the venv/script/pre_bus paths and the mixing extra', variants }

const metersLine = v => v.meters
  ? `METER GROUND TRUTH (stereo, authoritative): centroid ${v.meters.centroid} Hz · tilt ${v.meters.tilt} dB/oct · crest ${v.meters.crest} dB · L-R corr ${v.meters.corr} · ${v.meters.lufs} LUFS. (LOWER corr = WIDER/HUGER = better here, the opposite of mono; HIGHER LUFS at the same peak = denser explosion; centroid UP = the snare CRACK; crest HIGH = dry hits punch through. NOTE: the gated-vs-ungated difference is mostly the TAIL — judge that by ear, not these integrated meters.)`
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
      `intent="${intent}". (You may also load "mcp__stemmy-gemini__detect-mix-issues" if useful — e.g. to ` +
      `hear whether the gated tail cuts off abruptly.)\n` +
      `${metersLine(v)}\n` +
      `Gemini hears ~16 kbps MONO — trust the meter ground truth for loudness/tilt/crest/correlation, and ` +
      `use your ears only for the perceptual FEEL of this one criterion (especially the GATED tail cutoff, ` +
      `which the meters can't show). If the perceptual tool is unavailable, still return a best-effort score ` +
      `reasoned from the meter ground truth alone.\n\n` +
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
  note: "write the winner's meters into presets/mix/in-the-air-tonight.json approved_signature_full_kit (the default path is deterministic — no VST/UADx — so a re-render reproduces the winner exactly)",
}
