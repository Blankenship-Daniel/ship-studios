export const meta = {
  name: 'vst-probe-inventory',
  description: 'Parallel headless-RENDER verification across an installed plugin set → a render-verified inventory. LOAD-verified (demo/headless-safe-titles.txt, ~779) is NOT render-verified ("load != render": UADx uaudio_* native vs UAD *.component passthrough twins, Tape J-37 self-bypass). Each agent shells presets/vst/probe_plugin.py via the loops vst venv on a CHUNK of plugins and reports RENDERS / PASSTHROUGH + Δparam + build. The plugin LIST is gathered INLINE first (list-vst-plugins / headless-safe-titles.txt) and passed in args. args = { plugins:[name|absPath], chunkSize?, venv?, twinCheck? }.',
  phases: [
    { title: 'Probe',             detail: 'one agent per chunk runs probe_plugin.py and parses the verdict table' },
    { title: 'Twin-trap recheck', detail: 'OPTIONAL — re-probe suspected passthroughs against their uaudio_* twin' },
    { title: 'Inventory',         detail: 'merge chunks → render-verified list + per-plugin verdict table' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const plugins   = A.plugins || []
const chunkSize = A.chunkSize || 24
const venv      = A.venv || '../stemmy-loops-mcp/.venv/bin/python'
const twinCheck = A.twinCheck !== false

if (!plugins.length) {
  return { error: 'no plugins — pass args.plugins = [name|absPath, ...] (gather inline via list-vst-plugins / demo/headless-safe-titles.txt)' }
}

// Chunk so agent-count = ceil(plugins/chunkSize) (e.g. 779/24 ≈ 33), not one-per-plugin.
// Each chunk agent shells ONE probe_plugin.py process that probes its plugins sequentially in-process,
// so concurrent Pedalboard hosts ≤ min(16, #chunks) — gentle on UADx (raise chunkSize to reduce further).
const chunks = []
for (let i = 0; i < plugins.length; i += chunkSize) chunks.push(plugins.slice(i, i + chunkSize))
log(`probing ${plugins.length} plugins in ${chunks.length} chunks of ${chunkSize}`)

const PROBE_RESULT = {
  type: 'object',
  additionalProperties: false,
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          plugin:  { type: 'string' },
          path:    { type: 'string', description: 'resolved plugin path, or empty' },
          verdict: { type: 'string', enum: ['RENDERS', 'PASSTHROUGH', 'LOAD-FAIL', 'NO-PARAMS', 'NO-PUSHABLE-PARAM', 'PROBE-ERR'] },
          dparam:  { type: 'string', description: 'Δparam from the probe (e.g. "3.2e-01") or empty' },
          build:   { type: 'string', description: 'build note: uaudio_* (native) / UAD component (passthrough!) / empty' },
          detail:  { type: 'string', description: 'raw detail column' },
        },
        required: ['plugin', 'verdict'],
      },
    },
  },
  required: ['results'],
}

// single-quote-safe shell arg list
const shellList = list => list.map(p => `'${String(p).replace(/'/g, "'\\''")}'`).join(' ')

const verdictMap =
  'Map "RENDERS ✓"→RENDERS, "PASSTHROUGH ✗ ..."→PASSTHROUGH, "LOAD-FAIL"→LOAD-FAIL, ' +
  '"NO-PARAMS"→NO-PARAMS, "NO-PUSHABLE-PARAM"→NO-PUSHABLE-PARAM, "PROBE-ERR"→PROBE-ERR.'

// ---- Phase 1: probe each chunk ------------------------------------------------------------------
phase('Probe')
const probed = await pipeline(
  chunks,
  (ch, _item, idx) => agent(
    `You verify whether VST plugins actually RENDER headless (vs LOAD-only / passthrough).\n` +
    `From the repo root, run this ONE bash command and read its printed table:\n` +
    `  ${venv} presets/vst/probe_plugin.py ${shellList(ch)}\n\n` +
    `Each output line is "<verdict> <plugin> <detail>". ${verdictMap}\n` +
    `From the detail column extract Δparam (the "Δparam=..." number, else empty) and the build note ` +
    `("uaudio_* (native)" / "UAD component/legacy (likely passthrough!)" / empty). Return one row per ` +
    `plugin in this chunk. If the probe import-fails (no pedalboard in the venv), mark every plugin PROBE-ERR.`,
    { label: `probe:chunk${idx}`, phase: 'Probe', schema: PROBE_RESULT, agentType: 'general-purpose' },
  ).then(r => (r && r.results) || []),
)
const all = probed.flat().filter(Boolean)

// ---- Phase 2: twin-trap recheck (optional) ------------------------------------------------------
let twinResults = []
if (twinCheck) {
  phase('Twin-trap recheck')
  const suspects = all.filter(r => r.verdict === 'PASSTHROUGH')
  // Chunk ALL suspects into ≤16-wide batches and run them via pipeline — drop nothing in one pass.
  const twinBatches = []
  for (let i = 0; i < suspects.length; i += 16) twinBatches.push(suspects.slice(i, i + 16))
  log(`twin-trap: re-probing ${suspects.length} suspected passthroughs against uaudio_* twins in ${twinBatches.length} batch(es)`)
  twinResults = (await pipeline(twinBatches, batch => parallel(batch.map(s => () =>
    agent(
      `A plugin probed PASSTHROUGH: "${s.plugin}". If it is a UAD title, the UADx NATIVE build ` +
      `(/Library/Audio/Plug-Ins/VST3/uaudio_*.vst3) often RENDERS where the "UAD ….component"/twin does not. ` +
      `Pick a likely uaudio_* glob for this plugin and run from the repo root:\n` +
      `  ${venv} presets/vst/probe_plugin.py '<uaudio_glob>'\n` +
      `Return the twin's verdict row (path = the uaudio_* path tried). If no uaudio_* twin plausibly exists, ` +
      `return a single row with verdict NO-PARAMS and path "".`,
      { label: `twin:${s.plugin}`, phase: 'Twin-trap recheck', schema: PROBE_RESULT, agentType: 'general-purpose' },
    ).then(r => ({ plugin: s.plugin, twin: (r && r.results && r.results[0]) || null })),
  )))).flat().filter(Boolean)
}

// ---- Phase 3: merge → inventory -----------------------------------------------------------------
phase('Inventory')
const renderVerified = all
  .filter(r => r.verdict === 'RENDERS')
  .map(r => r.path ? `${r.plugin} (${r.path})` : r.plugin)
const counts = all.reduce((c, r) => { c[r.verdict] = (c[r.verdict] || 0) + 1; c.total++; return c }, { total: 0 })
log(`render-verified ${renderVerified.length}/${all.length}`)
return { renderVerified, table: all, passthroughTraps: twinResults, counts }
