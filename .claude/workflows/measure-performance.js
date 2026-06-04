export const meta = {
  name: 'measure-performance',
  description:
    'Measure ship-studios performance (import/startup cost, offline test-suite timing, the DSP benchmark + scaling + memory, perf-instrumentation overhead, CLI cold-start) on a SINGLE SERIAL measure pass so the numbers stay honest, then fan out one analysis agent per surface to read the code against those measured numbers, adversarially verify every finding, and synthesize a prioritized report. Re-runnable: it re-measures the repo each run rather than trusting baked-in numbers.',
  whenToUse:
    'When you want a fresh, evidence-grounded performance read of this repo + a prioritized, adversarially-verified findings report. Pairs with /fix-perf-issues (turn its actionable findings into that workflow\'s args.fixes). args (all optional): { root, venv, syncCmd, dimensions:[{key,title,files,focus}], thoroughness:"standard"|"deep" }. The script returns { report, repo_root, ground_truth, surfaces, stats }; the SESSION writes report to disk (workflow scripts cannot).',
  phases: [
    { title: 'Measure', detail: 'ONE serial agent runs every timing-sensitive measurement (no concurrency to corrupt timing)' },
    { title: 'Analyze', detail: 'one agent per surface reads the code vs the measured ground truth' },
    { title: 'Verify', detail: 'an adversarial skeptic per finding (confirm / overstated / refuted)' },
    { title: 'Synthesize', detail: 'one prioritized, verified markdown report' },
  ],
}

// ---- args / config -----------------------------------------------------------------------------
const A = typeof args === 'object' && args ? args : {}
const VENV = A.venv || '.venv/bin/python'
const SYNC = A.syncCmd || 'uv sync --extra drum-prep --extra bench --extra metrics'
const ROOTHINT = A.root || '(detect it yourself: git rev-parse --show-toplevel)'
const DEEP = A.thoroughness === 'deep'
const VERIFIERS = DEEP ? 3 : 1

// ---- default analysis surfaces (override via args.dimensions) -----------------------------------
const DEFAULT_DIMENSIONS = [
  {
    key: 'import-startup',
    title: 'Import & startup efficiency',
    files: 'ship_studios/__init__.py, ship_studios/config.py, ship_studios/mcp_client.py, ship_studios/cli.py, drum_prep/__init__.py, pyproject.toml',
    focus:
      'The dependency-light + lazy-import architecture and user-facing cold-start. Verify the lazy-import design is complete (no heavy import — mcp/numpy/scipy/soundfile/pyloudnorm/psutil — leaking into the base `import ship_studios` or the CLI path). Assess any one-time import tax on the critical path, whether `doctor` stays light, and the per-fresh-interpreter cost.',
  },
  {
    key: 'dsp-numerics',
    title: 'DSP numerics performance (drum_prep)',
    files: 'drum_prep/dsp.py, drum_prep/phase_align.py, drum_prep/reference_match.py, drum_prep/mix.py, drum_prep/qc.py, drum_prep/stem_mix.py, drum_prep/audition.py, drum_prep/sub_design.py, drum_prep/tune.py',
    focus:
      'Algorithmic complexity + memory/copy-volume of the local DSP. Hunt for O(n^2)/O(n*m) patterns (esp. cross-correlation), per-sample Python loops vs vectorized numpy, redundant/repeated FFTs, FFT-length padding waste, unnecessary float64, and full-length intermediate copies that inflate peak RSS. Cross-check the benchmark coverage (which functions are benchmarked vs the true per-kit hotspot).',
  },
  {
    key: 'hub-async-runtime',
    title: 'Hub async/runtime efficiency',
    files: 'ship_studios/mcp_client.py, ship_studios/pipelines.py, ship_studios/config.py',
    focus:
      'The hub per-call path: the single call_tool chokepoint, the handshake/_open_session, the _Recorder timing seam, and timeout handling (asyncio.wait_for; the timeout budgets can be None when the env var is 0). Are sessions opened once and reused? Anything serialized that could overlap, or concurrent that races? Redundant per-call config/filesystem work? Blocking IO on the event loop? (The DSP/Gemini concurrency lives in the sibling servers — out of scope.)',
  },
  {
    key: 'perf-instrumentation',
    title: 'Perf-instrumentation overhead & correctness',
    files: 'ship_studios/perf.py, ship_studios/mcp_client.py, ship_studios/pipelines.py',
    focus:
      'Is the performance instrumentation itself a net cost or liability anywhere? Read perf.py and EVERY call site. Determine where the expensive pieces run (e.g. the psutil RSS process-tree scan), whether the disabled/default path is truly cheap, and whether any best-effort error-swallowing hides a cost. Be calibrated: explicitly mark negligible costs as info so they are not over-weighted.',
  },
  {
    key: 'test-suite',
    title: 'Test-suite execution efficiency',
    files: 'tests/conftest.py, tests/test_drum_prep_chain.py, tests/test_config.py, tests/test_pipelines.py, pyproject.toml, benchmarks/test_dsp_bench.py',
    focus:
      'Developer-loop speed. Where is the wall-clock spent (cold import tax vs real work)? Which tests dominate and why? Would pytest-xdist help on this CPU-bound suite? Any oversized synth audio or redundant fixture work? Are benchmarks correctly excluded from the default suite? Keep recommendations honest about the real savings.',
  },
  {
    key: 'static-complexity',
    title: 'Static complexity & whole-tree hotspots',
    files: 'all of ship_studios/ and drum_prep/ (use grep/wc/python -c ast, read-only)',
    focus:
      'Whole-codebase static performance posture. Rank the longest/most-complex functions and the biggest files; find any quadratic loops, repeated work, or list/dict rebuilds; identify dead/duplicate import cost. Assess maintainability-as-performance-risk (where a future change would most likely regress) and where benchmark/profiling coverage should be extended next.',
  },
]
const DIMENSIONS =
  Array.isArray(A.dimensions) && A.dimensions.length ? A.dimensions : DEFAULT_DIMENSIONS

// ---- schemas -----------------------------------------------------------------------------------
const MEASURE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    repo_root: { type: 'string', description: 'absolute repo root used for the run' },
    machine: { type: 'string', description: 'CPU / cores / RAM / python + key lib versions' },
    ground_truth_markdown: {
      type: 'string',
      description:
        'ALL measured numbers as compact markdown tables: (a) import/startup cost per module, (b) test-suite timing (cold collection + warm run + slowest tests), (c) DSP benchmark + scaling + peak memory, (d) perf-instrumentation overhead, (e) CLI cold-start. Each number must be something you actually ran.',
    },
    raw_notes: { type: 'string', description: 'anything skipped/failed/odd during measurement' },
  },
  required: ['repo_root', 'machine', 'ground_truth_markdown'],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    surface: { type: 'string' },
    characterization: { type: 'string', description: 'what this surface\'s perf profile IS, grounded in the measured numbers + the code' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['info', 'low', 'medium', 'high'] },
          evidence: { type: 'string', description: 'file:line + the measured number or code fact' },
          claim: { type: 'string', description: 'the single falsifiable load-bearing assertion' },
          recommendation: { type: 'string' },
          effort: { type: 'string', enum: ['trivial', 'small', 'medium', 'large'] },
        },
        required: ['id', 'title', 'severity', 'evidence', 'claim', 'recommendation', 'effort'],
      },
    },
  },
  required: ['surface', 'characterization', 'findings'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    id: { type: 'string' },
    verdict: { type: 'string', enum: ['confirmed', 'overstated', 'refuted', 'uncertain'] },
    corrected_severity: { type: 'string', enum: ['info', 'low', 'medium', 'high'] },
    reasoning: { type: 'string', description: 'cite the file/line or measured number that confirms or refutes the claim' },
  },
  required: ['id', 'verdict', 'reasoning'],
}

// ---- Phase 1: Measure (ONE serial agent → honest numbers) --------------------------------------
phase('Measure')
log('measuring performance on a single serial pass (root hint: ' + ROOTHINT + ')')
const measurePrompt =
  'You are a performance engineer taking honest, serial measurements of the ship-studios repo. Working dir = the repo root (' + ROOTHINT + '). ' +
  'Run measurements ONE AT A TIME (you are the only agent running now, so the timings are clean). Use ' + VENV + ' as the python interpreter. If a command/dir/module is absent, skip it and note why in raw_notes — never fail the whole pass.\n\n' +
  'STEPS:\n' +
  '1. MACHINE: capture CPU model + physical/logical cores + RAM + python version + key lib versions (numpy/scipy/pyloudnorm/soundfile). On macOS use `sysctl -n machdep.cpu.brand_string hw.physicalcpu hw.logicalcpu hw.memsize`; otherwise `uname -a` + `nproc`. Get lib versions via ' + VENV + ' -c.\n' +
  '2. PROVISION: run `' + SYNC + '` (tail the output). This creates/refreshes .venv with the DSP + bench + metrics deps.\n' +
  '3. IMPORT COST (cold, FRESH interpreter each): for each of ship_studios, ship_studios.cli, ship_studios.pipelines, ship_studios.config, ship_studios.mcp_client, drum_prep, drum_prep.dsp, numpy, scipy.signal, soundfile, pyloudnorm, mcp, click — run `' + VENV + ' -c "import time;s=time.perf_counter();import <mod>;print((time.perf_counter()-s)*1000)"` and record ms. Also check the lazy-import claim: in a fresh interpreter, `import ship_studios` then print whether mcp/numpy/scipy are in sys.modules; same for `import ship_studios.cli` re psutil.\n' +
  '4. TEST SUITE: time COLD collection `' + VENV + ' -m pytest --collect-only -q` (this pays the first numpy/scipy import), then a WARM run `' + VENV + ' -m pytest -q -p no:cacheprovider --durations=25`. Record collected count, passed/skipped, total time, and the slowest ~10 tests. If a slow test looks like a one-time import tax mis-attributed, note it.\n' +
  '5. DSP BENCHMARK: if benchmarks/ exists, run `uv run --no-sync --extra bench --extra drum-prep pytest benchmarks/ -q --benchmark-columns=min,mean,median,max,stddev,ops,rounds` and record each case\'s min/median/mean.\n' +
  '6. DSP SCALING + MEMORY: write a short ' + VENV + ' -c snippet that, for the main pure-DSP render primitive (e.g. drum_prep.dsp.zero_phase_eq on synthetic audio of 0.5/2/10/30/120 s @ 48kHz, 3 bands), measures min wall time (warm the FFT plan first) and tracemalloc peak. Report a time/peak-RSS table + the realtime ratio + whether scaling is linear or n*log n + the peak-RSS-to-input ratio.\n' +
  '7. CLI COLD-START: time `ship-studios --help`, `ship-studios doctor`, `drum-prep --help` via the .venv console scripts (5 runs each; report range+median) and a bare `' + VENV + ' -c pass` baseline.\n' +
  '8. PERF INSTRUMENTATION: if ship_studios/perf.py exists, write a ' + VENV + ' -c snippet timing perf.now() (ns/call), record() on the DISABLED default path (ns/call), record() ENABLED (us/call, to a temp file), and sample_rss() (ms/call) if psutil present.\n\n' +
  'Return repo_root (absolute), machine, and ground_truth_markdown containing ALL of the above as compact markdown tables with every number you measured. Put anything skipped/failed in raw_notes. Do NOT analyze or recommend — just measure.'
const gt = await agent(measurePrompt, {
  label: 'measure',
  phase: 'Measure',
  schema: MEASURE_SCHEMA,
  agentType: 'general-purpose',
})
const GT = (gt && gt.ground_truth_markdown) || '(measurement unavailable)'
const MACHINE = (gt && gt.machine) || '(unknown machine)'
const ROOT = (gt && gt.repo_root) || A.root || '.'
log('measured ground truth captured (root=' + ROOT + ')')

const GROUND =
  'AUTHORITATIVE GROUND TRUTH (measured THIS run, serially, by a dedicated agent — treat as fact; do NOT re-run the test suite or benchmarks, that would corrupt timing AND waste work; read-only static probes via grep/wc/Read/`' + VENV + ' -c` AST are fine):\n\n' +
  'MACHINE: ' + MACHINE + '\n\n' + GT

// ---- Phase 2/3: Analyze each surface, then adversarially verify each finding --------------------
phase('Analyze')
log('analyzing ' + DIMENSIONS.length + ' surfaces vs the measured ground truth, then verifying every finding')
const reviewed = await pipeline(
  DIMENSIONS,
  (d) =>
    agent(
      'You are a performance engineer auditing the repo at ' + ROOT + '. Analyze ONE surface: ' + d.title + '.\n\n' +
        'Read these files (and anything they reference): ' + d.files + '.\n\n' +
        'FOCUS:\n' + d.focus + '\n\n' + GROUND + '\n\n' +
        'Produce a tight characterization of this surface, then concrete findings. Each finding needs a real file:line or measured-number as evidence, ONE falsifiable load-bearing claim, a calibrated severity (most things in a well-instrumented repo are info/low), a recommendation, and an effort estimate. Do NOT invent problems; an honest "already good because X" is a valid info finding. Return the schema.',
      { label: 'analyze:' + d.key, phase: 'Analyze', schema: FINDINGS_SCHEMA, agentType: 'general-purpose' },
    ),
  (review, d) => {
    if (!review || !review.findings || !review.findings.length) return review
    return parallel(
      review.findings.map((f) => () =>
        parallel(
          Array.from({ length: VERIFIERS }, (_unused, vi) => () =>
            agent(
              'You are a SKEPTICAL performance reviewer at ' + ROOT + ' (verifier ' + (vi + 1) + '). A prior agent made this finding about the "' + d.title + '" surface:\n\n' +
                'Title: ' + f.title + '\nSeverity: ' + f.severity + '\nClaim: ' + f.claim + '\nEvidence: ' + f.evidence + '\nRecommendation: ' + f.recommendation + '\n\n' +
                'Try to REFUTE or DOWNGRADE it. Open the cited file/line and check the claim against the actual code; cross-check the ground truth below. Default to skepticism: refuted if the evidence does not hold; overstated (with corrected_severity) if real but the severity is inflated (e.g. a sub-microsecond cost called high when calls are >=10ms); confirmed only if code + numbers genuinely back it. Cite a file/line or number.\n\n' + GROUND,
              { label: 'verify:' + d.key + ':' + f.id + ':' + (vi + 1), phase: 'Verify', schema: VERDICT_SCHEMA, agentType: 'general-purpose' },
            ),
          ),
        ).then((votes) => {
          const v = votes.filter(Boolean)
          // majority verdict (ties favor the more skeptical reading)
          const tally = {}
          for (const x of v) tally[x.verdict] = (tally[x.verdict] || 0) + 1
          const order = ['refuted', 'overstated', 'uncertain', 'confirmed']
          let best = v[0] || { verdict: 'uncertain', reasoning: 'no verdict' }
          let bestN = -1
          for (const verd of order) if ((tally[verd] || 0) > bestN) { bestN = tally[verd] || 0; best = v.find((x) => x.verdict === verd) || best }
          return { ...f, surface: d.key, verdict: best, votes: v }
        }),
      ),
    ).then((withVerdicts) => ({ ...review, findings: withVerdicts.filter(Boolean) }))
  },
)

const surfaces = reviewed.filter(Boolean)
const allFindings = surfaces.flatMap((s) => (s.findings || []).map((f) => ({ surface: s.surface, ...f })))
const confirmed = allFindings.filter((f) => f.verdict && (f.verdict.verdict === 'confirmed' || f.verdict.verdict === 'overstated'))
const refuted = allFindings.filter((f) => f.verdict && f.verdict.verdict === 'refuted')
log(allFindings.length + ' findings | ' + confirmed.length + ' confirmed/overstated | ' + refuted.length + ' refuted')

// ---- Phase 4: Synthesize -----------------------------------------------------------------------
phase('Synthesize')
const report = await agent(
  'You are the lead performance engineer. Write the FINAL performance measurement report for the repo at ' + ROOT + ' as polished GitHub-flavored markdown.\n\n' +
    'INPUTS:\n1) MEASURED GROUND TRUTH:\n' + GROUND + '\n\n' +
    '2) Per-surface characterizations + ADVERSARIALLY-VERIFIED findings (each finding carries a verdict; apply corrected_severity where overstated, drop/segregate refuted):\n' +
    JSON.stringify(surfaces, null, 1) + '\n\n' +
    'SECTIONS: TL;DR (4-6 bullets: overall posture, the 2-3 things that genuinely matter, what is already good); Measured numbers (compact tables, verbatim); Findings by surface (one-line characterization + a table title|severity-after-verification|claim|recommendation|effort; segregate refuted under a short note); Prioritized recommendations (ranked value/effort, quick-wins vs larger, with file:line); Coverage gaps (what is NOT measured and should be); Bottom line (one honest paragraph). Be precise, cite file:line, never overstate, mark measured vs analyzed. Return ONLY the markdown.',
  { label: 'synthesize', phase: 'Synthesize', agentType: 'general-purpose' },
)

return {
  report,
  repo_root: ROOT,
  machine: MACHINE,
  ground_truth: GT,
  surfaces,
  stats: { findings: allFindings.length, confirmed: confirmed.length, refuted: refuted.length },
}
