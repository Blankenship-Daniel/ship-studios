export const meta = {
  name: 'house-curve',
  description: "Align a whole EP/album to ONE shared tonal target IN PARALLEL. Build (or reuse) a house-curve profile from references, then fan out one agent per mix — each measures its gap to the profile (match-to-profile), renders the correction (match-eq/apply-eq to its OWN file, no conflict), and re-measures — then a reduce reports per-track before→after deltas AND the cross-track SPREAD tightening (the consistency win). All pure-DSP [L], no UADx, no key (match-eq needs the `mixing` extra) → fully parallelizable. The tonal companion to /batch-master (which makes the same set LOUDNESS-consistent). args = { mixes:[absPath|{path,name}], profileJson?, references?:[absPath], matchStrength?, phase?, outDir?, venv? }.",
  phases: [
    { title: 'Profile',  detail: 'build the shared house-curve profile from references (skipped if profileJson given)' },
    { title: 'Align',    detail: 'one agent per mix → match-to-profile → match-eq → re-measure (parallel)' },
    { title: 'Consistency', detail: 'per-track before→after deltas + cross-track spread tightening' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const rawMixes = A.mixes || []
const mixes = rawMixes.map(m => {
  const path = typeof m === 'string' ? m : m.path
  const name = (typeof m === 'object' && m.name) ? m.name : String(path).split('/').pop().replace(/\.[^.]+$/, '')
  return { path, name }
}).filter(m => m.path)
let profileJson  = A.profileJson || ''           // ABSOLUTE path to a prebuilt profile JSON
const references = A.references || []             // ABSOLUTE ref paths to build the profile (if no profileJson)
const matchStrength = (A.matchStrength !== undefined) ? A.matchStrength : 0.5
const matchPhase = A.phase || 'min'              // match-eq phase: min | linear
const outDir = A.outDir || ''                    // ABSOLUTE; else each agent writes a mix/ sibling
const venv   = A.venv || ''                      // optional; the MCP tools don't need it (pure DSP)

if (!mixes.length) return { error: 'no mixes — pass args.mixes = [absPath|{path,name}, ...]' }
if (!profileJson && !references.length) return { error: 'pass args.profileJson (prebuilt) OR args.references = [absPath, ...] to build one' }
log(`house-curve: ${mixes.length} mixes · ${profileJson ? 'profile=' + profileJson : references.length + ' references'} · strength ${matchStrength}`)

// ---- Phase 0: build the shared profile (single aggregating call; skipped if one was supplied) ----
if (!profileJson) {
  phase('Profile')
  profileJson = outDir ? `${outDir}/house-curve.json` : `${String(mixes[0].path).replace(/[^/]+$/, '')}house-curve.json`
  const built = await agent(
    `Build ONE shared tonal target profile from these reference tracks (curated to agree on the sound): ` +
    `${JSON.stringify(references)}.\n` +
    `Run ToolSearch, then mcp__stemmy-loops__build-target-profile {paths: <the references>, out_json: "${profileJson}"}. ` +
    `It power-averages the references' third-octave spectra (+ loudness/dynamics/width) into a versioned JSON.\n` +
    `Return the profile path written and a one-line summary of its tilt/shape.`,
    {
      label: 'build-profile', phase: 'Profile', agentType: 'general-purpose',
      schema: { type: 'object', additionalProperties: false, properties: { profilePath: { type: 'string' }, summary: { type: 'string' } }, required: ['profilePath'] },
    },
  )
  if (built && built.profilePath) profileJson = built.profilePath
  log(`built profile → ${profileJson}`)
}

const MIX_RESULT = {
  type: 'object', additionalProperties: false,
  properties: {
    mix:        { type: 'string' },
    outPath:    { type: 'string', description: 'absolute path of the tonally-matched mix, or empty on failure' },
    fitBefore:  { type: 'number', description: 'pre-match fit = RMS of |per-band delta dB| vs the profile (lower = closer)' },
    fitAfter:   { type: 'number', description: 'post-match fit = RMS of |per-band delta dB| after the correction' },
    tiltAfter:  { type: 'number', description: 'measured spectral tilt (dB/oct) of the matched mix — for the cross-track spread' },
    note:       { type: 'string', description: 'one line: the largest band gap closed, or the failure reason' },
  },
  required: ['mix', 'outPath', 'fitBefore', 'fitAfter', 'note'],
}

// ---- Phase 1: align each mix to the profile (parallel, batched ≤16) -----------------------------
phase('Align')
const MBATCH = 16
const mbatches = []
for (let i = 0; i < mixes.length; i += MBATCH) mbatches.push(mixes.slice(i, i + MBATCH))
const outLine = outDir
  ? `Write the matched mix to "${outDir}/${'${name}'}.housematched.wav" (absolute).`
  : `Write the matched mix to a "mix/" sibling of the source, named "<mixbasename>.housematched.wav".`

const aligned = (await pipeline(
  mbatches,
  b => parallel(b.map(m => () =>
    agent(
      `You tonally align ONE mix to a SHARED house-curve profile (all tools pure-DSP [L], no key). ` +
      `Mix (absolute): "${m.path}". Profile JSON: "${profileJson}". Run ToolSearch for each tool first.\n` +
      `1. mcp__stemmy-loops__match-to-profile {path:"${m.path}", profile_json:"${profileJson}"} → per-band delta ` +
      `(input − target). Record the BEFORE fit = RMS of |per-band delta dB|.\n` +
      `2. mcp__stemmy-loops__match-eq {source_path:"${m.path}", out_path:<the out path below>, ` +
      `profile_json:"${profileJson}", match_strength:${matchStrength}, phase:"${matchPhase}"} — render the ` +
      `correction as a ${matchPhase}-phase FIR toward the profile. (If match-eq cannot consume the profile ` +
      `directly on this build, fall back to mcp__stemmy-loops__apply-eq with a few shelves/bells that close the ` +
      `biggest band gaps from step 1.) ${outLine.replace('${name}', m.name)}\n` +
      `3. mcp__stemmy-loops__match-to-profile on the OUTPUT → the AFTER fit; also note its spectral tilt ` +
      `(mcp__stemmy-loops__measure-spectrum) for the cross-track spread.\n\n` +
      `Do NOT force the curve flat — partial correction (strength ~${matchStrength}) keeps each track musical. ` +
      `Return the out path, fitBefore, fitAfter, tiltAfter, and a one-line note (largest gap closed). On failure ` +
      `return outPath="" and the reason in note.`,
      { label: `align:${m.name}`, phase: 'Align', schema: MIX_RESULT, agentType: 'general-purpose' },
    ).then(r => r || { mix: m.name, outPath: '', fitBefore: 0, fitAfter: 0, note: 'no result' }),
  )),
)).flat().filter(Boolean)

// ---- Phase 2: cross-track consistency (the headline) --------------------------------------------
phase('Consistency')
const ok = aligned.filter(a => a.outPath)
const round = x => Math.round(x * 100) / 100
const spread = vals => {
  const v = vals.filter(x => typeof x === 'number')
  if (v.length < 2) return null
  return round(Math.max(...v) - Math.min(...v))
}
const table = aligned.map(a => ({
  mix: a.mix,
  fitBefore: round(a.fitBefore),
  fitAfter: round(a.fitAfter),
  improved: a.outPath ? a.fitAfter < a.fitBefore : null,
  tiltAfter: (typeof a.tiltAfter === 'number') ? round(a.tiltAfter) : null,
  outPath: a.outPath,
  note: a.note,
}))
const failed = aligned.filter(a => !a.outPath).map(a => a.mix)
const tiltSpreadAfter = spread(ok.map(a => a.tiltAfter))
const meanFitBefore = ok.length ? round(ok.reduce((s, a) => s + a.fitBefore, 0) / ok.length) : null
const meanFitAfter  = ok.length ? round(ok.reduce((s, a) => s + a.fitAfter, 0) / ok.length) : null

log(`aligned ${ok.length}/${mixes.length} — mean fit ${meanFitBefore}→${meanFitAfter}, tilt spread after ${tiltSpreadAfter}, ${failed.length} failed`)
return {
  profileJson,
  table,
  consistency: { meanFitBefore, meanFitAfter, tiltSpreadAfter },  // spread tightening = the consistency win
  failed,
  settings: { matchStrength, phase: matchPhase },
  next: 'hand the tonally-aligned set to /batch-master for one shared LOUDNESS target',
}
