export const meta = {
  name: 'fix-perf-issues',
  description:
    'Apply a set of TRIAGED fixes partitioned by DISJOINT file groups — one edit agent per group, run in parallel so they cannot conflict — then a single centralized CI gate (pytest + benchmarks + ruff + mypy) and an automatic repair pass on any red. Generic: the fixes come from args.fixes (e.g. the actionable findings from a /measure-performance run), so it is not tied to any one set of changes.',
  whenToUse:
    'After /measure-performance (or any review) produced actionable, file-scoped fixes. Pass them as args.fixes=[{id,title,files:[...],instr}] where every fix OWNS A DISJOINT file set (no file appears in two fixes). The edit agents only py_compile their own files; ALL test execution happens once at the centralized gate after the barrier, so cross-file imports cannot race a half-written file. Repair preserves each change\'s intent (it updates tests to new-correct behavior, never reverts a fix to make a test pass). args (optional): { root, venv, syncCmd, gate:[{name,cmd}], fixes:[...] }.',
  phases: [
    { title: 'Fix', detail: 'one edit agent per disjoint file group (parallel, batched to 16)' },
    { title: 'Verify', detail: 'central CI gate: pytest + benchmarks + ruff + mypy (single env, no uv race)' },
    { title: 'Repair', detail: 'fix any gate failure, preserving each change\'s intent' },
  ],
}

// ---- args / config -----------------------------------------------------------------------------
const A = typeof args === 'object' && args ? args : {}
const VENV = A.venv || '.venv/bin/python'
const SYNC = A.syncCmd || 'uv sync --extra drum-prep --extra bench --extra metrics'
const ROOTHINT = A.root || '(detect it yourself: git rev-parse --show-toplevel)'
const FIXES = Array.isArray(A.fixes) ? A.fixes.filter((f) => f && f.id && Array.isArray(f.files) && f.files.length && f.instr) : []

// Default CI gate (override via args.gate=[{name,cmd}]). `uv run --no-sync` avoids re-syncing per call.
const GATE_CMDS =
  Array.isArray(A.gate) && A.gate.length
    ? A.gate
    : [
        { name: 'sync', cmd: SYNC },
        { name: 'pytest', cmd: 'uv run --no-sync pytest -q -p no:cacheprovider' },
        { name: 'benchmarks', cmd: 'uv run --no-sync --extra bench --extra drum-prep pytest benchmarks/ -q' },
        { name: 'ruff', cmd: 'uv run --no-sync ruff check' },
        { name: 'mypy', cmd: 'uv run --no-sync mypy' },
      ]

// ---- guard: nothing to do / overlapping files --------------------------------------------------
if (!FIXES.length) {
  log('NO FIXES PROVIDED. Pass args.fixes=[{id,title,files:[...],instr}] (one disjoint file set each). Example shape is in the file header comment.')
  return { error: 'no fixes provided', expected: 'args.fixes=[{id,title,files:[<paths>],instr:<what to change & why>}]' }
}
// Detect file overlaps across fixes — overlapping files would let two parallel edit agents race.
const seen = {}
const overlaps = []
for (const f of FIXES) for (const p of f.files) { if (seen[p]) overlaps.push(p + ' (in ' + seen[p] + ' and ' + f.id + ')'); else seen[p] = f.id }
if (overlaps.length) log('WARNING: file groups are NOT disjoint — these files are claimed by >1 fix and may race: ' + overlaps.join('; ') + '. Proceeding, but split them into one fix or merge the fixes.')

// ---- schemas -----------------------------------------------------------------------------------
const EDIT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    id: { type: 'string' },
    status: { type: 'string', enum: ['done', 'partial', 'skipped', 'failed'] },
    files_changed: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string', description: 'what the diff does, concretely' },
    self_check: { type: 'string', description: 'the py_compile / sanity result' },
    notes: { type: 'string', description: 'anything the gate or repair agent should know (e.g. a test updated, a fn skipped + why)' },
  },
  required: ['id', 'status', 'files_changed', 'summary', 'self_check'],
}

const CI_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    passed: { type: 'boolean', description: 'true ONLY if pytest 0-fail AND benchmarks pass AND ruff passes AND mypy passes' },
    pytest_summary: { type: 'string' },
    benchmarks_summary: { type: 'string' },
    ruff_summary: { type: 'string' },
    mypy_summary: { type: 'string' },
    failures: { type: 'array', items: { type: 'string' }, description: 'verbatim excerpts per failure (empty if green)' },
    notes: { type: 'string' },
  },
  required: ['passed', 'pytest_summary', 'ruff_summary', 'mypy_summary', 'failures'],
}

// ---- shared edit guardrails --------------------------------------------------------------------
const COMMON =
  'You are applying a TRIAGED fix in the repo at ' + ROOTHINT + '. Edit ONLY the file(s) you are assigned — other agents edit other files in parallel, so touching anything else risks a conflict. ' +
  'Read each assigned file fully before editing; make the MINIMAL change for the task and keep it behavior-preserving except where the task says otherwise. ' +
  'This repo is INTENTIONALLY not ruff-format-clean: NEVER run "ruff format"; hand-wrap to <=100 cols and keep imports sorted so "ruff check" (E4/E7/E9/F/B/I/UP) stays clean. ' +
  'Files under ship_studios/ and drum_prep/ are mypy-checked; keep any you touch type-clean. tests/ and benchmarks/ are ruff-checked but not mypy-checked. ' +
  'Do NOT run the full test suite, "uv sync", or "uv run" — a centralized CI gate runs all of that AFTER every edit finishes. Run ONLY a lightweight self-check on your OWN file(s): `' + VENV + ' -m py_compile <file>` (py_compile reads only the file it compiles, so it never imports another agent\'s half-written file). ' +
  'Return the schema: the exact files you changed, a crisp diff summary, and your self-check result.'

// ---- Phase 1: Fix (parallel; disjoint files => safe; batched to the ≤16 cap) --------------------
phase('Fix')
log('applying ' + FIXES.length + ' fix group(s) across disjoint files')
const editPrompt = (fx) =>
  COMMON + '\n\n=== YOUR TASK: ' + fx.title + ' ===\n' +
  'YOU OWN ONLY THESE FILES (touch nothing else): ' + fx.files.join(', ') + '\n\n' +
  'WHAT TO CHANGE (and why):\n' + fx.instr

const BATCH = 16
const batches = []
for (let i = 0; i < FIXES.length; i += BATCH) batches.push(FIXES.slice(i, i + BATCH))
const edits = (
  await pipeline(batches, (b) =>
    parallel(
      b.map((fx) => () =>
        agent(editPrompt(fx), { label: 'fix:' + fx.id, phase: 'Fix', schema: EDIT_SCHEMA, agentType: 'general-purpose' }).then(
          (r) => r || { id: fx.id, status: 'failed', files_changed: [], summary: 'no result', self_check: 'n/a' },
        ),
      ),
    ),
  )
)
  .flat()
  .filter(Boolean)
log('edits done: ' + edits.map((e) => e.id + '=' + e.status).join(', '))

// ---- Phase 2: Verify (single agent, single env => no uv race) ----------------------------------
phase('Verify')
const gateCmdList = GATE_CMDS.map((g, i) => i + 1 + ') [' + g.name + '] ' + g.cmd).join('\n')
const ci = await agent(
  'You are the centralized CI gate for the repo at ' + ROOTHINT + ' (measure-and-report only — do NOT fix anything). All parallel edits are complete. Run these commands IN ORDER from the repo root and capture the tail of each:\n' +
    gateCmdList + '\n\n' +
    'Set passed=true ONLY if pytest has 0 failures AND 0 errors AND the benchmarks step passes AND ruff passes AND mypy passes. (If a benchmarks/ dir or a gate step is not applicable here, say so in notes and do not let its absence flip passed to false.) For EVERY failure put a verbatim excerpt — the failing test id + assertion, or the ruff/mypy file:line — into failures[] so a repair agent can act precisely. Note in notes[] whether uv.lock changed.',
  { label: 'ci-gate', phase: 'Verify', schema: CI_SCHEMA, agentType: 'general-purpose' },
)
log('CI gate: passed=' + ci.passed + ' | pytest: ' + ci.pytest_summary + ' | ruff: ' + ci.ruff_summary + ' | mypy: ' + ci.mypy_summary)

// ---- Phase 3: Repair (only on red) -------------------------------------------------------------
phase('Repair')
let repair = null
if (!ci.passed) {
  log('CI failed (' + (ci.failures || []).length + ' failure group(s)) — launching repair')
  repair = await agent(
    'You are the repair agent for the repo at ' + ROOTHINT + '. The centralized CI gate FAILED. Diagnose and FIX the failures so the gate goes green; you may edit ANY file.\n\n' +
      'CI RESULT:\n' + JSON.stringify(ci, null, 1) + '\n\n' +
      'APPLIED EDITS (the INTENT of each change — do NOT revert these intents):\n' + JSON.stringify(edits, null, 1) + '\n\n' +
      'Likely causes: a test asserting the OLD behavior a fix deliberately changed (update the test to the new-correct behavior, do NOT revert the fix); a numeric/determinism signature shift (verify it is a real change vs a too-tight tolerance before touching code); a ruff import-order/unused nit; a mypy typing nit. Make the MINIMAL correct fix that PRESERVES each change. NEVER run "ruff format"; hand-wrap long lines.\n\n' +
      'Then RE-RUN to confirm FINAL green:\n' + gateCmdList + '\n\n' +
      'Report the CI schema with passed reflecting the FINAL state, failures[] empty if fixed, and notes[] listing exactly what you changed and why.',
    { label: 'repair', phase: 'Repair', schema: CI_SCHEMA, agentType: 'general-purpose' },
  )
  log('repair: passed=' + repair.passed)
}

const finalPassed = repair ? repair.passed : ci.passed
return { finalPassed, fixes: FIXES.length, overlaps, edits, ci, repair }
