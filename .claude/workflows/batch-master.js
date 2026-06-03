export const meta = {
  name: 'batch-master',
  description: 'Master a folder of near-final mixes to ONE shared target IN PARALLEL, then emit a cross-track loudness/true-peak consistency table (Δ-from-album-median, outliers flagged) + the album playback-gain read. Per-track renders are pure-DSP [L] (no UADx) so they parallelize. Each track-agent runs the master chain (measure → mastering-feedback → render-mastered → check-streaming-targets → export-deliverables) via MCP; then a reduce computes consistency. args = { tracks:[absPath|{path,name}], target_lufs, ceiling_dbtp, platform?, mastersDir?, deliverablesDir?, exportPresets?, albumNorm? }.',
  phases: [
    { title: 'Master',      detail: 'one agent per track runs the shared-target master chain via MCP' },
    { title: 'Consistency', detail: 'cross-track LUFS/TP/LRA + Δ-from-median table; optional album-gain read' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const rawTracks = A.tracks || []
const tracks = rawTracks.map(t => {
  const path = typeof t === 'string' ? t : t.path
  const name = (typeof t === 'object' && t.name) ? t.name : String(path).split('/').pop().replace(/\.[^.]+$/, '')
  return { path, name }
})
const targetLufs   = A.target_lufs
const ceiling      = (A.ceiling_dbtp !== undefined) ? A.ceiling_dbtp : -1
const platform     = A.platform || 'spotify'
const mastersDir   = A.mastersDir || ''        // ABSOLUTE if given; else agent uses a masters/ sibling
const deliverables = A.deliverablesDir || ''
const presets      = A.exportPresets || ['distribution_44k_16', 'production_48k_24', 'master_96k_24']
const albumNorm    = A.albumNorm !== false

if (!tracks.length) return { error: 'no tracks — pass args.tracks = [absPath|{path,name}, ...]' }
if (targetLufs === undefined) return { error: 'pass args.target_lufs (a number, the ONE shared album target)' }
log(`batch-master ${tracks.length} tracks → ${targetLufs} LUFS / ${ceiling} dBTP (platform ${platform})`)

const TRACK_MASTER = {
  type: 'object',
  additionalProperties: false,
  properties: {
    track:        { type: 'string' },
    masterPath:   { type: 'string', description: 'absolute path of the rendered master, or empty on failure' },
    lufs:         { type: 'number', description: 'integrated LUFS of the rendered master' },
    tp:           { type: 'number', description: 'true-peak dBTP of the rendered master' },
    lra:          { type: 'number', description: 'loudness range LU' },
    releaseReady: { type: 'boolean', description: 'mastering-feedback release-ready verdict' },
    willAttenuate:{ type: 'boolean', description: 'check-streaming-targets says the platform will turn it down' },
    note:         { type: 'string', description: 'one line: harshness flags / re-render reason / failure' },
  },
  required: ['track', 'masterPath', 'lufs', 'tp', 'releaseReady', 'note'],
}

const mastersLine = mastersDir
  ? `Write the master to "${mastersDir}/${'${name}'}.wav" (absolute).`
  : `Write the master to a "masters/" sibling of the source file, named "<trackbasename>.wav".`
const delivLine = deliverables
  ? `Export deliverables into "${deliverables}".`
  : `Export deliverables into a "deliverables/" sibling of the master.`

// ---- Phase 1: master each track to the shared target (parallel, batched ≤16) --------------------
phase('Master')
const SObatch = 16
const batches = []
for (let i = 0; i < tracks.length; i += SObatch) batches.push(tracks.slice(i, i + SObatch))

const mastered = (await pipeline(
  batches,
  b => parallel(b.map(t => () =>
    agent(
      `You master ONE track to a SHARED album target. Source (absolute): "${t.path}". Track name: "${t.name}".\n` +
      `Shared target (do NOT drift to a per-track value): target_lufs=${targetLufs}, ceiling_dbtp=${ceiling}, platform="${platform}".\n` +
      `Use the MCP tools (run ToolSearch first for each). In order:\n` +
      `1. mcp__stemmy-loops__measure-loudness on the source (baseline).\n` +
      `2. mcp__stemmy-gemini__mastering-feedback {path, target_platform:"${platform}"} → release-ready + harshness flags.\n` +
      `3. mcp__stemmy-loops__render-mastered to target_lufs=${targetLufs}, ceiling_dbtp=${ceiling}. ` +
      `${mastersLine.replace('${name}', t.name)}\n` +
      `4. mcp__stemmy-gemini__check-streaming-targets on the rendered master (pure DSP, no key) → will the platform attenuate it / breach ceiling? If so, note it.\n` +
      `5. mcp__stemmy-loops__export-deliverables {presets:${JSON.stringify(presets)}, tag:true}. ${delivLine}\n` +
      `6. mcp__stemmy-loops__measure-loudness on the rendered master for the FINAL lufs/tp/lra.\n\n` +
      `Return the master's absolute path, its measured integrated LUFS / true-peak dBTP / LRA, the release-ready ` +
      `boolean, whether the platform will attenuate it, and a one-line note (harshness flags or failure). ` +
      `If a step fails, return masterPath="" and put the error in note.`,
      { label: `master:${t.name}`, phase: 'Master', schema: TRACK_MASTER, agentType: 'general-purpose' },
    ).then(r => r || { track: t.name, masterPath: '', lufs: 0, tp: 0, lra: 0, releaseReady: false, willAttenuate: false, note: 'no result' }),
  )),
)).flat().filter(Boolean)

// ---- Phase 2: cross-track consistency -----------------------------------------------------------
phase('Consistency')
const ok = mastered.filter(m => m.masterPath)
const lufsVals = ok.map(m => m.lufs).slice().sort((a, b) => a - b)
const median = lufsVals.length
  ? (lufsVals.length % 2
      ? lufsVals[(lufsVals.length - 1) / 2]
      : (lufsVals[lufsVals.length / 2 - 1] + lufsVals[lufsVals.length / 2]) / 2)
  : 0
const round = x => Math.round(x * 100) / 100
const table = mastered.map(m => {
  const delta = m.masterPath ? round(m.lufs - median) : null
  return {
    track: m.track,
    lufs: m.lufs,
    tp: m.tp,
    lra: m.lra,
    deltaFromMedian: delta,
    outlier: delta !== null && (Math.abs(delta) > 0.5 || m.tp > ceiling),
    releaseReady: m.releaseReady,
    willAttenuate: m.willAttenuate,
    note: m.note,
  }
})
const notReady = table.filter(t => !t.releaseReady).map(t => t.track)
const outliers = table.filter(t => t.outlier).map(t => t.track)
const failed   = mastered.filter(m => !m.masterPath).map(m => m.track)

// Optional: shared album playback gain (TD1008 + album-integrated) via one reduce agent.
let albumGain = null
if (albumNorm && mastersDir) {
  albumGain = await agent(
    `Run ToolSearch then mcp__stemmy-loops__analyze-album-normalization {dir:"${mastersDir}", target_lufs:${targetLufs}, ceiling_dbtp:${ceiling}}. ` +
    `Return its full result as text: the TD1008 (loudest-track) offset, the album-integrated offset, and per-track which play quieter under album vs track mode.`,
    { label: 'album-gain', phase: 'Consistency', agentType: 'general-purpose' },
  )
}

log(`mastered ${ok.length}/${tracks.length} — median ${round(median)} LUFS, ${outliers.length} outliers, ${notReady.length} not-ready, ${failed.length} failed`)
return {
  medianLufs: round(median),
  table,
  outliers,
  notReady,   // route these to mix-check — do NOT loudness-paper a broken mix
  failed,
  albumGain,
  sharedTarget: { target_lufs: targetLufs, ceiling_dbtp: ceiling, platform },
}
