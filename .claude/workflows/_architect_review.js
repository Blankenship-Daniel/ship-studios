export const meta = {
  name: 'architect-review',
  description: "Software Architect's review of ship-studios: fan out by architectural dimension, adversarially verify each finding, return verified findings + per-dimension assessments",
  phases: [
    { title: 'Review', detail: 'one architect agent per dimension reads the code and reports findings + an assessment' },
    { title: 'Verify', detail: 'adversarially verify each finding against the actual source (real? by-design? severity?)' },
  ],
}

const REPO = '/Users/ship/Documents/code/ship-studios/.claude/worktrees/quiet-popping-plum'

const CONTEXT = [
  'You are a senior SOFTWARE ARCHITECT reviewing the ship-studios repository at:',
  '  ' + REPO,
  'Run all tools from that directory. Cite evidence as file:line.',
  '',
  'WHAT THIS REPO IS (architecture in one paragraph):',
  'ship-studios is a DSP-FREE MCP host - a thin async client hub that composes two sibling',
  'MCP servers (stemmy-loops = pure-DSP mix/master + loops; stemmy-gemini = perceptual critique)',
  'into one create-mix-master-deliver pipeline surface. Its OWN Python is two uv packages:',
  '  * ship_studios/ - the hub: config.py (sibling/env/timeout resolution), mcp_client.py (Hub:',
  '    one MCP ClientSession per server over a stdio subprocess, driven via call_tool), perf.py',
  '    (opt-in JSONL tracing), pipelines.py (async orchestrators that sequence hub.call_tool in a',
  '    fixed verified order, recording every step), cli.py (click entry points to pipelines).',
  '  * drum_prep/ - the ONLY local DSP: phase-align + per-stem reference-match a multi-mic drum kit',
  '    (numpy/scipy/soundfile). dsp.py holds proven numerics marked must-not-drift.',
  'Key design facts you must respect (do NOT flag these as bugs unless you find a real defect IN them):',
  '  * The hub is intentionally DSP-free; all DSP lives in the sibling servers (out of this repo).',
  '  * Pipelines must use ONLY verified tool names/params and a FIXED call order; CLAUDE.md prose,',
  '    pipelines.py, and tests/test_pipelines.py (which asserts the ordered tool-call log) are kept',
  '    in deliberate three-way lockstep.',
  '  * The whole test suite runs OFFLINE via tests/conftest.py FakeSession/fake_hub that monkeypatch',
  '    Hub._open_session - no real servers, keys, audio, or network.',
  '  * Many swallow-the-error / degrade-to-no-op and intentional-broad-except paths are documented',
  '    on purpose (perf tracing, best-effort result parsing, worktree resolution). Judge whether the',
  '    INTENT is sound and the boundary is correct - not merely that a broad except exists.',
  '  * Lint reality: ruff enforces only E4/E7/E9/F/B/I/UP (NOT E501); the repo is intentionally not',
  '    ruff-format-clean. Do not raise line-length or formatting nits.',
  '',
  'Be an ARCHITECT, not a linter: focus on boundaries, coupling, abstraction quality, change-',
  'amplification, failure-mode design, security posture, determinism, and testability. For each',
  'finding give concrete file:line evidence and a claim that could be checked. Distinguish a genuine',
  'architectural risk from a documented-and-sound intentional choice. Quality over quantity - report',
  'the findings that matter, not nitpicks. It is fine and expected to also note real STRENGTHS in the',
  'per-dimension assessment.',
].join('\n')

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['dimension', 'assessment', 'findings'],
  properties: {
    dimension: { type: 'string' },
    assessment: {
      type: 'string',
      description: 'A few sentences: the architectural state of this dimension - notable STRENGTHS and the most important WEAKNESSES/risks.',
    },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'title', 'severity', 'evidence', 'claim', 'why_it_matters', 'recommendation', 'confidence'],
        properties: {
          id: { type: 'string', description: 'short slug, e.g. coupling-tool-name-literals' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] },
          evidence: { type: 'string', description: 'file:line reference(s) + a short quote/paraphrase of the actual code' },
          claim: { type: 'string', description: 'the precise, checkable assertion' },
          why_it_matters: { type: 'string', description: 'architectural impact: what breaks / what cost it imposes' },
          recommendation: { type: 'string' },
          confidence: { type: 'number', description: '0..1 self-rated confidence the claim is correct and material' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['id', 'evidence_confirmed', 'is_real_issue', 'is_by_design', 'severity_final', 'rationale'],
  properties: {
    id: { type: 'string' },
    evidence_confirmed: { type: 'boolean', description: 'did the cited file:line actually say what the finding claims (you READ it)?' },
    is_real_issue: { type: 'boolean', description: 'is this a genuine architectural problem (not invented, not already-mitigated)?' },
    is_by_design: { type: 'boolean', description: 'is it a documented, sound, intentional design choice rather than a defect?' },
    severity_final: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INVALID'] },
    rationale: { type: 'string', description: 'what you checked and why you ruled this way; correct the finding if it overstated/understated.' },
  },
}

const DIMENSIONS = [
  {
    key: 'boundaries-layering',
    prompt: [
      'DIMENSION: Module boundaries and layering.',
      'Read ship_studios/{__init__,config,mcp_client,perf,pipelines,cli}.py and drum_prep/__init__.py.',
      'Assess: Is the layering clean and one-directional (cli -> pipelines -> mcp_client/Hub -> config; perf as a cross-cutting leaf)? Is the hub-is-DSP-free boundary actually upheld (no numpy/audio leaking into ship_studios)? Is drum_prep properly isolated (no import coupling to ship_studios, opt-in DSP deps)? Is the SupportsCallTool Protocol seam a clean abstraction boundary or leaky? Any circular/back-edge imports, god-modules, or responsibilities in the wrong layer? Are lazy imports (deferred mcp SDK import for cheap doctor) used consistently and for sound reasons?',
    ].join('\n'),
  },
  {
    key: 'coupling-change-amplification',
    prompt: [
      'DIMENSION: Coupling, single-source-of-truth and change-amplification.',
      'Focus on what it costs to add/rename a tool, a pipeline, a server, an export preset, or a platform.',
      'Read pipelines.py, cli.py, config.py, and skim tests/test_pipelines.py + CLAUDE.md tool tables.',
      'Assess: The CLAUDE.md-prose <-> pipelines.py <-> test_pipelines.py THREE-WAY lockstep - is it a sound contract or a fragile manual-sync liability, and is anything (lint/audit) enforcing it? Tool names and parameter keys are bare string literals scattered across pipelines.py - is that duplication a real maintenance hazard given the servers own the real schema (and the hub deliberately cannot see it)? The platform/preset/severity allow-lists (PLATFORM_CHOICES, DEFAULT_PRESETS, SEVERITY_CHOICES) are re-declared client-side to mirror server Literals - single-source-of-truth risk? Quantify change-amplification: to do X you must edit N places.',
    ].join('\n'),
  },
  {
    key: 'error-failure-modes',
    prompt: [
      'DIMENSION: Error-handling and failure-mode architecture.',
      'Read mcp_client.py (call_tool / _open_session / ToolCallError / _parse_result / _result_text), cli.py (_run / _format_error / ExceptionGroup peeling), perf.py (record / sample_rss broad excepts), pipelines.py (_Recorder finally-record; _streaming_compliant / _profile_delta_curve / _loop_paths best-effort None-returns).',
      'Assess: Is the error taxonomy coherent (timeout vs tool_error vs exception kinds; the no-timeout vs wait_for branches)? Are the return-None / swallow-and-no-op best-effort paths drawing the line in the right place, or do any silently hide a real failure that should fail the pipeline loudly (e.g. a shape change in find-loops/check-streaming-targets results degrading silently)? Is partial-failure handling in batch_master sound (one bad track aborts the album vs continues)? Is the ExceptionGroup/BaseExceptionGroup handling in _run correct and complete?',
    ].join('\n'),
  },
  {
    key: 'concurrency-resources',
    prompt: [
      'DIMENSION: Concurrency, async correctness and resource lifecycle.',
      'Read mcp_client.py (AsyncExitStack, __aenter__/__aexit__ rollback, re-entrancy guard, asyncio.wait_for around initialize/call_tool), cli.py (asyncio.run per command), pipelines.py (everything is sequential awaits).',
      'Also consider the documented doctrine: pipelines are SERIAL by design; the SERVERS thread-offload pure-DSP and serialize VST renders; batch tools loop internally; the hub itself never fans out call_tool concurrently.',
      'Assess: Is subprocess/session teardown leak-proof on every path (partial-open failure, mid-call exception, cancellation/Ctrl-C, timeout)? Does asyncio.wait_for cancel the underlying call cleanly or can it orphan an in-flight tool/subprocess? Is the run-one-pipeline-per-asyncio.run model sound? Are there missed opportunities OR hidden hazards in the serial-only client design? Any place a TimeoutError is caught/relabelled incorrectly vs one bubbling from the tool itself?',
    ].join('\n'),
  },
  {
    key: 'config-security',
    prompt: [
      'DIMENSION: Configuration and security architecture.',
      'Read config.py in full (sibling resolution, _resolve_main_root worktree/commondir logic, _sibling_dir, checked_server_dir, _passthrough_env, FORWARDED_ENV vs _SERVER_ENV_KEYS, server_parameters), and scripts/mcp_launch.py, and .mcp.json.',
      'Assess: The env-to-code-execution surface - SHIP_STUDIOS_*_DIR turns an env var into uv --directory <path> run i.e. arbitrary code execution; is the trust boundary clearly drawn and is checked_server_dir an adequate guard (it is not meant to stop a planted pyproject - is that documented and acceptable)? The worktree .git/commondir resolution: is the only-trust-a-real-.git-dir guard sufficient against a tampered commondir redirecting sibling resolution? Is the env-passthrough model (stdio transport drops the parent env except an allowlist; only-when-set forwarding; ${VAR:-} in .mcp.json; mcp_launch stripping empties) coherent, and is STEMMY_MCP_ALLOWED_ROOTS ownership (enforced by the gemini server, passed through unvalidated by the hub) a sound boundary? Any secret-leak risk (keys in argv/logs/perf trace)? Note repo_root() vs main_repo_root() usage for artifacts/projects vs siblings - is that split correct?',
    ].join('\n'),
  },
  {
    key: 'dsp-correctness-determinism',
    prompt: [
      'DIMENSION: DSP correctness, determinism and numerics (drum_prep).',
      'Read drum_prep/dsp.py in full and skim phase_align.py, reference_match.py, stem_mix.py, mix.py, sub_design.py, normalize.py.',
      'Assess as an architect of a DSP library: Are the must-not-drift invariants (coherent time-domain sum not power-sum; zero-phase real-symmetric EQ preserving prior phase alignment; envelope-coarse to waveform-refine alignment; cuts-to-all/boosts-to-owners; one global headroom trim) actually upheld by the code and guarded by tests? Specific numerics to scrutinize: zero_phase_eq does a direct rfft*gain*irfft with NO zero-padding so it is CIRCULAR convolution; does that risk time-domain wrap-around/edge artifacts, and is that an acceptable documented tradeoff? fractional_delay dtype preservation; estimate() parabolic-interp small-denominator guard; band_power 1e-20 flooring; determinism (any nondeterministic ordering, threading, or float reduction that breaks the determinism tests). Is the dsp module a clean, stateless, testable seam?',
    ].join('\n'),
  },
  {
    key: 'testing-architecture',
    prompt: [
      'DIMENSION: Testing architecture and its blind spots.',
      'Read tests/conftest.py in full; skim tests/test_pipelines.py, test_mcp_client.py, test_config.py, test_cli.py, test_perf.py, and a couple drum_prep tests. List files: tests/.',
      'Assess: The FakeSession/fake_hub seam - does the fake faithfully model the REAL server contract, or can pipelines pass the offline tests while breaking against a real server (the fake returns canned shapes; the real tools have strict input schemas the hub never validates)? The test_pipelines.py strategy asserts the ORDERED tool-call log (server, tool, args) - does testing call-ORDER rather than behavior give false confidence (e.g. wrong arg VALUES, or a tool that would reject the args, still passes)? Coverage gaps that matter architecturally (drum_prep DSP opt-in import boundary; overheads.py; error/timeout/cancellation paths in mcp_client). Is offline-no-network/keys/audio actually guaranteed, or can a test escape the fake?',
    ].join('\n'),
  },
  {
    key: 'surface-design-naming',
    prompt: [
      'DIMENSION: Public surface design, API/CLI ergonomics and naming consistency.',
      'Read cli.py and drum_prep/cli.py (skim), ship_studios/__init__.py, pipelines.py public signatures.',
      'Assess: Is the CLI a clean, consistent facade over the pipelines (subcommand parity with pipelines, option naming, defaults, validation-at-the-edge via Click choices/ranges/_parse_* helpers)? Is the platform vocabulary mapping (_feedback_mood vs _streaming_service; one --platform arg driving two disjoint server vocabularies) a sound abstraction or a leaky workaround? Naming: hyphen-vs-underscore tool names, command names vs function names, the open_hub server-subset optimization (loops/understand open one server). Is the ship_studios package public API (__all__/__version__/exports) deliberate? Is the result-dict shape returned by pipelines a stable, well-designed contract for both CLI and workflow callers?',
    ].join('\n'),
  },
  {
    key: 'docs-as-contract',
    prompt: [
      'DIMENSION: Documentation-as-contract architecture (is CLAUDE.md a sound binding spec, and is it actually enforced?).',
      'Read the top ~200 lines of CLAUDE.md, scripts/lint_skills.py, and skim .claude/workflows/ names + the Developing this repo section of CLAUDE.md. Note there are ~102 SKILL.md files and audit workflows (audit-skill-consistency, audit-pipeline-lockstep).',
      'Assess as an architect, NOT a proofreader: Is treating a 52KB CLAUDE.md + ~102 skill files as the binding contract for tool usage a scalable, maintainable architecture, or a drift-magnet? What is ACTUALLY enforced mechanically (scripts/lint_skills.py is CI-gated and dependency-light) vs only by on-demand agent audits (which can silently rot)? Is the contract DRY or does the same fact live in CLAUDE.md + a skill + a doc + code (e.g. tool surface, env-var table, pipeline order)? Identify the highest-leverage structural improvement to keep docs and code in lockstep. Do NOT enumerate individual wording typos - that is a different review.',
    ].join('\n'),
  },
]

phase('Review')
log('Architect review fanning out across ' + DIMENSIONS.length + ' dimensions (review -> adversarial verify per finding)')

const results = await pipeline(
  DIMENSIONS,
  (d) =>
    agent(CONTEXT + '\n\n' + d.prompt, {
      label: 'review:' + d.key,
      phase: 'Review',
      schema: FINDINGS_SCHEMA,
    }),
  (review, d) => {
    if (!review || !Array.isArray(review.findings) || review.findings.length === 0) {
      return { dimension: d.key, assessment: (review && review.assessment) || '(no assessment)', findings: [] }
    }
    return parallel(
      review.findings.map((f) => () =>
        agent(
          CONTEXT +
            '\n\nYou are an adversarial VERIFIER. Independently check this finding from the "' +
            d.key +
            '" review by READING the cited code yourself - do not trust the finding summary. Decide: (a) does the evidence actually exist and say what is claimed, (b) is it a real architectural issue or invented/already-mitigated, (c) is it instead a documented sound intentional design choice, (d) the correct final severity. Be skeptical; default to downgrading vague or speculative findings. Correct the record in your rationale.\n\nFINDING:\n' +
            JSON.stringify(f, null, 2),
          {
            label: 'verify:' + d.key + ':' + (f.id || 'finding'),
            phase: 'Verify',
            schema: VERDICT_SCHEMA,
          },
        ).then((v) => ({ finding: f, verdict: v })),
      ),
    ).then((verified) => ({
      dimension: d.key,
      assessment: review.assessment,
      findings: verified.filter(Boolean),
    }))
  },
)

return { dimensions: results.filter(Boolean) }
