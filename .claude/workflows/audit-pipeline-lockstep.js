export const meta = {
  name: 'audit-pipeline-lockstep',
  description: 'Audit that each CODED canonical pipeline stays in lockstep across three sources: the CLAUDE.md "Canonical pipelines" prose, the async def in ship_studios/pipelines.py, and the ordered tool-call assertions in tests/test_pipelines.py. One agent per pipeline reads all three and reports drift (step reordered/renamed/missing, prose↔code↔test mismatch, wrong [L]/[G] server, missing test coverage). Reduce to a drift report. args = { pipelines?:[{name,fn}], pipelinesPath?, testPath?, claudeMdPath? }.',
  phases: [
    { title: 'Check',  detail: 'one agent per coded pipeline diffs prose ↔ pipelines.py ↔ test_pipelines.py' },
    { title: 'Report', detail: 'reduce drift findings into a report (by pipeline, by class)' },
  ],
}

// Defensive: args may arrive as an object OR a JSON string.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}

const pipelines = A.pipelines || [
  { name: 'master-track',          fn: 'master_track' },
  { name: 'batch-master',          fn: 'batch_master' },
  { name: 'mix-check',             fn: 'mix_check' },
  { name: 'reference-match',       fn: 'reference_match' },
  { name: 'house-curve',           fn: 'house_curve' },
  { name: 'stem-master',           fn: 'stem_master' },
  { name: 'unmask-stems',          fn: 'unmask_stems' },
  { name: 'loops-to-deliverables', fn: 'loops_to_deliverables' },
  { name: 'understand-audio',      fn: 'understand_audio' },
]
const pipelinesPath = A.pipelinesPath || 'ship_studios/pipelines.py'
const testPath      = A.testPath      || 'tests/test_pipelines.py'
const claudeMdPath  = A.claudeMdPath  || 'CLAUDE.md'
log(`lockstep audit of ${pipelines.length} pipelines vs ${pipelinesPath} + ${testPath} + ${claudeMdPath}`)

const LOCKSTEP = {
  type: 'object',
  additionalProperties: false,
  properties: {
    inSync: { type: 'boolean', description: 'true if prose, code, and test agree on the ordered tool-call sequence' },
    proseSteps: { type: 'number', description: 'count of tool-call steps in the CLAUDE.md prose, or -1 if not found' },
    codeSteps:  { type: 'number', description: 'count of MCP tool calls in the pipelines.py function, or -1 if not found' },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          class:    { type: 'string', enum: ['prose-code-mismatch', 'code-test-mismatch', 'tool-name', 'server-mismatch', 'missing-coverage', 'other'] },
          severity: { type: 'string', enum: ['error', 'warn'] },
          detail:   { type: 'string', description: 'what diverges + the three values (prose / code / test)' },
        },
        required: ['class', 'severity', 'detail'],
      },
    },
  },
  required: ['inSync', 'issues'],
}

// ---- Phase 1: one agent per pipeline (9 < 16 → a single parallel barrier is fine) ---------------
phase('Check')
const results = (await parallel(pipelines.map(p => () =>
  agent(
    `You audit ONE canonical pipeline for lockstep across three sources. Pipeline: "${p.name}" ` +
    `(code function: \`${p.fn}\`).\n` +
    `Read all three:\n` +
    `1. PROSE: the "${p.name}" subsection under "## Canonical pipelines" in ${claudeMdPath} — the numbered ordered ` +
    `tool-call recipe (each step prefixed [L] or [G]).\n` +
    `2. CODE: the \`async def ${p.fn}(\` function in ${pipelinesPath} — the ordered MCP tool calls it makes ` +
    `(look for the server key + tool name passed to the hub's call_tool / run helper).\n` +
    `3. TEST: the assertion in ${testPath} that pins this pipeline's ordered (server, tool) sequence.\n\n` +
    `Compare the ORDERED tool-call sequence across all three. Report drift:\n` +
    `- a tool present/ordered differently in prose vs code → prose-code-mismatch (error)\n` +
    `- code calls a tool the test doesn't assert, or vice-versa → code-test-mismatch (error)\n` +
    `- a tool name spelled differently (hyphen vs underscore) anywhere → tool-name (error)\n` +
    `- a step attributed to the wrong server ([L] vs [G]) → server-mismatch (error)\n` +
    `- the pipeline lacks a test assertion at all → missing-coverage (error)\n` +
    `Set inSync=true only if prose, code, and test agree on the ordered sequence. Return proseSteps, codeSteps, ` +
    `and the issues array (empty if clean).`,
    { label: `lockstep:${p.name}`, phase: 'Check', schema: LOCKSTEP, agentType: 'general-purpose' },
  ).then(r => ({ pipeline: p.name, fn: p.fn,
                 inSync: r ? !!r.inSync : false,
                 proseSteps: r ? r.proseSteps : -1, codeSteps: r ? r.codeSteps : -1,
                 issues: (r && r.issues) || [] })),
))).filter(Boolean)

// ---- Phase 2: reduce ----------------------------------------------------------------------------
phase('Report')
const flat = results.flatMap(r => r.issues.map(i => ({ pipeline: r.pipeline, ...i })))
const byClass = {}
flat.forEach(i => { (byClass[i.class] = byClass[i.class] || []).push(i) })
const drifted = results.filter(r => !r.inSync || r.issues.length).map(r => r.pipeline)
const errors = flat.filter(i => i.severity === 'error')
log(`lockstep: ${results.length - drifted.length}/${results.length} in sync — ${errors.length} errors`)
return {
  summary: { pipelines: results.length, inSync: results.length - drifted.length, drifted, errors: errors.length },
  byClass,
  results,
}
