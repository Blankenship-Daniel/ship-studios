export const meta = {
  name: 'architect-fix',
  description: 'Apply every finding from reviews/ARCHITECT-REVIEW.md per reviews/FIX-SPEC.md: disjoint-file edit agents in dependency tiers (define contracts -> consume), then a centralized CI gate (pytest/ruff/mypy/lint_skills) that fixes any failures',
  phases: [
    { title: 'Edit-tier-1', detail: 'define shared contracts + independent file-owner edits (config/pipelines-behavioral/mcp_client/dsp/ci+docs/audit-js)' },
    { title: 'Edit-tier-2', detail: 'consume the contracts (pipelines tool-name enums, cli, new tests)' },
    { title: 'Gate', detail: 'uv sync + pytest + ruff + mypy + lint_skills; fix any failure until green' },
  ],
}

const REPO = '/Users/ship/Documents/code/ship-studios/.claude/worktrees/quiet-popping-plum'

const BASE = [
  'You are a senior engineer applying a precise, pre-approved fix to the ship-studios repo at:',
  '  ' + REPO,
  'Run all tools from that directory. This is a coordinated multi-agent edit: OTHER agents are editing',
  'OTHER files concurrently, so you must TOUCH ONLY the files your GROUP owns (listed in your task).',
  '',
  'BEFORE editing: read reviews/FIX-SPEC.md (the authoritative change spec) and the relevant slice of',
  'reviews/ARCHITECT-REVIEW.md. Follow the SHARED CONTRACTS section of FIX-SPEC.md EXACTLY (exact enum',
  'names, constant names, helper names) so your edits line up with the other agents you cannot see.',
  '',
  'Repo rules: the hub (ship_studios/) is DSP-free (never import numpy/scipy/drum_prep there);',
  'keep `from __future__ import annotations` first in every hub module; ruff lints only E4/E7/E9/F/B/I/UP',
  '(line length NOT enforced — do not reflow existing code; keep imports sorted for ruff-I). Tests are',
  'OFFLINE (tests/conftest.py: RecordingHub/FakeSession/fake_hub) — new tests must not need servers,',
  'keys, audio, or network. Preserve all existing behavior and keep existing tests passing.',
  '',
  'After editing, self-check what you safely can: `uv run ruff check <your files>` and (if it imports',
  'only stable/your-own modules) `uv run pytest <your test file> -q`. Do NOT run the full suite or git',
  'commands; the final CI gate runs everything. Do NOT edit files outside your group.',
].join('\n')

const EDIT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['group', 'files_changed', 'summary', 'self_check', 'issues'],
  properties: {
    group: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' }, description: 'repo-relative paths you actually edited/created' },
    summary: { type: 'string', description: 'what you changed, mapped to the FIX-SPEC items (e.g. B1/B2/C1...)' },
    self_check: { type: 'string', description: 'what you ran (ruff/pytest on your files) and the result' },
    issues: { type: 'string', description: 'anything you could NOT complete, an ambiguity you resolved, or a risk for the gate to watch; "none" if clean' },
  },
}

const GATE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['green', 'pytest', 'ruff', 'mypy', 'lint_skills', 'fixes_applied', 'remaining'],
  properties: {
    green: { type: 'boolean', description: 'true only if pytest + ruff + mypy + lint_skills ALL pass' },
    pytest: { type: 'string', description: 'final pytest result line (passed/failed counts)' },
    ruff: { type: 'string' },
    mypy: { type: 'string' },
    lint_skills: { type: 'string' },
    fixes_applied: { type: 'array', items: { type: 'string' }, description: 'files touched + what you fixed to reach green' },
    remaining: { type: 'string', description: 'any failure you could NOT resolve and why; "none" if fully green' },
  },
}

function editAgent(group, label, phase, task) {
  return agent(BASE + '\n\n' + task, { label: label, phase: phase, schema: EDIT_SCHEMA })
}

// ---------------- Tier 1: define contracts + independent edits ----------------
phase('Edit-tier-1')
log('Fix tier 1: 6 disjoint-file edit agents (config/pipelines-behavioral/mcp_client/dsp/ci+docs/audit-js)')

const tier1 = await parallel([
  () => editAgent('G2', 'edit:G2-config', 'Edit-tier-1',
    'Do GROUP G2 from reviews/FIX-SPEC.md. Own ONLY ship_studios/config.py and tests/test_config.py. ' +
    'Add the LoopsTool/GeminiTool StrEnum registry (SHARED CONTRACT C1 — derive members from the tool names ' +
    'currently used in ship_studios/pipelines.py, member = TOOLNAME upper with - -> _, value = the exact string), ' +
    'harden _resolve_main_root against a tampered commondir (S1, round-trip check), and add the two tests. ' +
    'Do NOT edit pipelines.py (G1b consumes the registry separately).'),

  () => editAgent('G1a', 'edit:G1a-pipelines', 'Edit-tier-1',
    'Do GROUP G1a from reviews/FIX-SPEC.md. Own ONLY ship_studios/pipelines.py and tests/test_pipelines.py. ' +
    'Add the C2 constants (INTENT_CHOICES/INTENSITY_CHOICES/MATCH_PHASE_CHOICES); B1 (batch_master partial-failure ' +
    'isolation + continue_on_error kwarg + album summary); B2 (_loop_paths None-vs-[] + fell_back/loop_count in ' +
    'loops_to_deliverables); D2 (factor the shared per-stem corrective chain used by mix_check and ' +
    '_apply_stem_corrections, preserving EXACT call order for both — the existing ordered-call tests are your oracle); ' +
    'D3 light (module-docstring result contract + a Step TypedDict on _Recorder.steps); plus the new tests. ' +
    'DO NOT swap tool-name string literals to enums — that is G1b, a later tier on the same file. Keep every ' +
    'existing assertion in test_pipelines.py passing.'),

  () => editAgent('G4', 'edit:G4-mcp_client', 'Edit-tier-1',
    'Do GROUP G4 from reviews/FIX-SPEC.md. Own ONLY ship_studios/mcp_client.py and tests/test_mcp_client.py. ' +
    'B3: expand Hub.call_tool docstring (a client timeout abandons the wait but does NOT abort server-side work; ' +
    'set SHIP_STUDIOS_CALL_TIMEOUT generously). B4: add the three offline fake_hub tests (post-error reuse, ' +
    'relabelled handshake timeout carrying the server key, teardown-on-mid-call-raise). No behavior change to the code.'),

  () => editAgent('G5', 'edit:G5-dsp', 'Edit-tier-1',
    'Do GROUP G5 from reviews/FIX-SPEC.md. Own ONLY drum_prep/dsp.py and tests/test_drum_prep_dsp.py. ' +
    'DOC/COMMENT ONLY — change NO numerics (the pinned determinism signature must stay identical). C1: document the ' +
    'circular-convolution edge tradeoff in zero_phase_eq docstring. C2: fix the false float32 comment in ' +
    'fractional_delay. Optional non-fragile interior-clean test only if safe. Note: this needs `uv sync --extra ' +
    'drum-prep` to run the dsp tests; the gate will sync — you may just ruff-check + py_compile your files.'),

  () => editAgent('G6', 'edit:G6-ci-docs', 'Edit-tier-1',
    'Do GROUP G6 from reviews/FIX-SPEC.md. Own ONLY .github/workflows/ci.yml and CLAUDE.md. A2: add a SEPARATE, ' +
    'additive workflow_dispatch/schedule CI job that runs the live-contract test when siblings are reachable and ' +
    'skips cleanly otherwise (do NOT make it block the normal PR job; keep existing jobs intact + valid YAML) + a ' +
    'CLAUDE.md "Developing this repo" pre-release/live-contract note. B3: add to the CLAUDE.md SHIP_STUDIOS_CALL_TIMEOUT ' +
    'env-table row that a call timeout abandons the client wait but does not abort server work. Validate the YAML parses ' +
    "(python -c \"import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))\"). Edit ONLY the timeout row + the " +
    'one new note in CLAUDE.md — do NOT touch the Canonical-pipelines prose blocks (a new test parses them).'),

  () => editAgent('G7', 'edit:G7-audit-js', 'Edit-tier-1',
    'Do GROUP G7 from reviews/FIX-SPEC.md. Own ONLY .claude/workflows/audit-pipeline-lockstep.js. A1b: extend the ' +
    'default pipeline list from 5 to all 9 coded pipelines (add batch-master, house-curve, stem-master, unmask-stems ' +
    'with the same {name, fn} field shape already used in the file). Read the file first to match its exact format. ' +
    'No logic changes.'),
])

// ---------------- Tier 2: consume the contracts ----------------
phase('Edit-tier-2')
log('Fix tier 2: 3 agents consume the contracts (pipelines enum-swap, cli, new tests)')

const tier2 = await parallel([
  () => editAgent('G1b', 'edit:G1b-pipelines-enums', 'Edit-tier-2',
    'Do GROUP G1b from reviews/FIX-SPEC.md. Own ONLY ship_studios/pipelines.py (G1a + G2 are already done; re-read ' +
    'both pipelines.py and config.py first). Per SHARED CONTRACT C1: import LoopsTool/GeminiTool from ship_studios.config ' +
    'and replace EVERY bare tool-name string literal passed as the tool argument to rec.run(SERVER, "<name>", ...) / ' +
    'hub.call_tool(...) with the matching LoopsTool.<MEMBER> / GeminiTool.<MEMBER> (LOOPS_SERVER calls -> LoopsTool, ' +
    'GEMINI_SERVER calls -> GeminiTool). Change NOTHING else — no call order, args, or behavior changes; do not touch ' +
    'tests (StrEnum == str keeps them green). Verify with grep that no plain tool-name string literal remains as a ' +
    'rec.run 2nd positional arg, and that every enum member you reference exists in config (run a quick python import ' +
    'check: `uv run python -c "import ship_studios.pipelines"`).'),

  () => editAgent('G3', 'edit:G3-cli', 'Edit-tier-2',
    'Do GROUP G3 from reviews/FIX-SPEC.md. Own ONLY ship_studios/cli.py and tests/test_cli.py (G1a is done; ' +
    'pipelines.py now exports INTENT_CHOICES/INTENSITY_CHOICES/MATCH_PHASE_CHOICES and has _master_out). C2: import + ' +
    'use those choice constants in the master --intent/--intensity and the reference-match/house-curve --match-phase ' +
    'Choices. C3/D1: delete _default_master_out and call pipelines._master_out(mix_path, None) in the master command. ' +
    'D4: add --presets (reuse _parse_presets) to the master command, threaded into master_track. Update test_cli.py ' +
    '(remove _default_master_out refs; add the --presets-threading test + a default-master-out parity test). ' +
    'Run `uv run pytest tests/test_cli.py -q` and `uv run ruff check ship_studios/cli.py` to self-verify.'),

  () => editAgent('G8', 'edit:G8-new-tests', 'Edit-tier-2',
    'Do GROUP G8 from reviews/FIX-SPEC.md. CREATE ONLY new files: tests/test_pipeline_lockstep.py (A1a deterministic ' +
    'prose<->code subsequence check), tests/test_docs_env_table.py (A5 env-table superset of FORWARDED_ENV), ' +
    'scripts/snapshot_tool_schemas.py (A6 generator, needs live siblings — manual), tests/test_arg_schemas.py (A6 ' +
    'skip-if-fixture-absent validator, NO jsonschema dep). Do NOT edit any existing file. AUTHOR the tests but do NOT ' +
    'run pytest on anything that imports ship_studios.pipelines (another agent is editing it concurrently this tier) — ' +
    'only `uv run ruff check` + `uv run python -m py_compile` your new files; the gate runs the suite. Make the ' +
    'lockstep parser robust (skip unparseable blocks, but require master-track/mix-check/reference-match to be checked) ' +
    'and the arg-schema test skip cleanly when tests/fixtures/tool_schemas.json is absent.'),
])

// ---------------- Tier 3: centralized CI gate ----------------
phase('Gate')
log('CI gate: uv sync + pytest + ruff + mypy + lint_skills; fix to green')

const gate = await agent(
  BASE +
    '\n\nYou are the CENTRALIZED CI GATE. All edits are done; you may now edit ANY file to reach green. ' +
    'Steps: (1) `uv sync --extra drum-prep` (so DSP test deps import). (2) Run, capturing output: ' +
    '`uv run pytest -q`, `uv run ruff check`, `uv run mypy`, `uv run python scripts/lint_skills.py`. ' +
    '(3) For EACH failure, diagnose the root cause and FIX it with the smallest correct edit that honors ' +
    'reviews/FIX-SPEC.md and the SHARED CONTRACTS (e.g. an enum member name mismatch between G1b and G2, a stale ' +
    'test, a ruff-I import-order nit, a mypy type gap, or genuine prose<->code drift surfaced by the new lockstep ' +
    'test — for prose drift prefer fixing CLAUDE.md to match the code, since tests pin the code). Re-run the failing ' +
    'check after each fix. Iterate until ALL FOUR are green or you have made ~8 fix rounds. Do NOT weaken a check to ' +
    'pass it (no skipping real tests, no blanket type: ignore, no deleting assertions) and do NOT run git. ' +
    'Report the final status of each check, every file you touched, and anything still red with the reason.',
  { label: 'gate:ci', phase: 'Gate', schema: GATE_SCHEMA },
)

return { tier1: tier1.filter(Boolean), tier2: tier2.filter(Boolean), gate: gate }
